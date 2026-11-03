"""Mock tests: make the paper, take it, mark it, report on it.

A test is a paper in sections (question_generation/paper.py) filled like a practice: checked
questions the learner has never been given first, the rest written by the AI in the background
(services/question_bank.py). Which tests a class may take, and whether they may be timed, follows
the class profile (docs/07 §7.6).

Taking it: a sitting starts the clock. Answers are saved one at a time and can be changed until the
test is submitted; a test has no hints or steps. After the deadline (and a minute's grace for the
network) no answer is saved; a late submission marks what was saved. Submitting marks every answer -
written ones by the AI, with part marks for the key points covered - stores each one as a question
attempt with its marks and updates mastery, so a test counts like practice. Questions left out earn
nothing and do not count for mastery.

Who sees what: a test belongs to one learner and is visible to whoever may see that learner.
"""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, literal, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import llm
from app.adaptive_learning import mastery
from app.auth.principal import Principal
from app.core.enums import QuestionFormat
from app.core.errors import InvalidInputError, NotFoundError
from app.core.tasks import TaskQueue
from app.models import (
    Book,
    Chapter,
    Exercise,
    MockTest,
    MockTestAttempt,
    MockTestQuestion,
    Question,
    QuestionAttempt,
    Student,
    Topic,
)
from app.models.base import utcnow
from app.question_generation import checking, paper
from app.rag.ingestion.labels import chapter_label, topic_label
from app.schemas.library import DocumentError
from app.schemas.mock_test import (
    AreaResult,
    AttemptOut,
    AttemptSummary,
    MockTestCreate,
    MockTestOut,
    MockTestPage,
    MockTestSummary,
    PaperSection,
    ReportQuestion,
    SectionResult,
    Solution,
    TestReport,
)
from app.schemas.practice import QuestionView, Response
from app.services import library_service, question_bank, student_service, study_plan_service
from app.utils import pagination

GRACE = timedelta(minutes=1)  # answers sent just after the deadline are still saved
_KIND_NAMES = {"practice": "Practice tests", "chapter": "Chapter tests", "full_mock": "Full mock tests"}


def _add_questions(
    db: AsyncSession, test: MockTest, section: dict, questions: list[Question], start: int
) -> None:
    db.add_all(
        MockTestQuestion(
            mock_test_id=test.id,
            question_id=question.id,
            section=section["code"],
            position=start + i,
            marks=section["marks"],
        )
        for i, question in enumerate(questions)
    )


async def create_test(
    db: AsyncSession, principal: Principal, data: MockTestCreate, *, queue: TaskQueue
) -> MockTest:
    student = await student_service.learner_for(db, principal, data.student_id)
    profile = student_service.class_profile(student)
    assert student.profile is not None
    if not paper.allowed(profile, data.kind):
        raise InvalidInputError(
            f"{_KIND_NAMES[data.kind]} are not part of {profile.label}.",
            code="test_not_for_class",
            details=[{"field": "kind", "message": "Not for this class."}],
        )
    if data.duration_minutes is not None and not profile.features.timed_tests:
        raise InvalidInputError(
            f"Timed tests are not part of {profile.label}.",
            code="test_not_for_class",
            details=[{"field": "duration_minutes", "message": "Not for this class."}],
        )
    count = data.count or paper.default_count(profile, data.kind)
    question_bank.check_count(profile, count)
    planned = paper.sections(profile, count)

    test = MockTest(
        student_id=student.id,
        kind=data.kind,
        question_count=count,
        difficulty=data.difficulty,
        language=data.language or student.profile.primary_language,
        duration_minutes=data.duration_minutes
        or (paper.minutes(planned) if data.kind == "full_mock" else None),
        sections=planned,
        status="preparing",
    )
    await question_bank.set_place(db, principal, test, data)
    db.add(test)
    await db.flush()

    owner = await student_service.account_of(db, student)
    complete = True
    for section in planned:
        reused = await question_bank.from_bank(db, owner, test, student, section["formats"], section["count"])
        _add_questions(db, test, section, reused, 0)
        complete = complete and len(reused) == section["count"]
    if complete:
        test.status = "ready"
    else:
        llm.get_llm_provider()  # 503 now, rather than a failed test later, when AI is switched off
    await db.commit()
    if test.status == "preparing":
        await queue.enqueue(prepare_test, test_id=test.id)
    return test


async def _write_the_rest(db: AsyncSession, test: MockTest, student: Student, owner: uuid.UUID) -> int:
    total = 0
    for section in test.sections:
        have = (
            await db.scalar(
                select(func.count()).where(
                    MockTestQuestion.mock_test_id == test.id, MockTestQuestion.section == section["code"]
                )
            )
            or 0
        )
        written: list[Question] = []
        if have < section["count"]:
            formats = [QuestionFormat(f) for f in section["formats"]]
            written = await question_bank.write(
                db, owner, test, student, formats=formats, count=section["count"] - have
            )
            _add_questions(db, test, section, written, have)
            await db.commit()  # kept in the bank even if a later section fails
        total += have + len(written)
    return total


async def prepare_test(db: AsyncSession, *, test_id: uuid.UUID) -> None:
    """The background job that writes the questions a test still needs, section by section."""
    await question_bank.prepare(db, MockTest, test_id, _write_the_rest)


async def resume_unfinished_tests(
    session_factory: async_sessionmaker[AsyncSession], queue: TaskQueue
) -> None:
    """At start-up: tests whose questions were being written when the server stopped are queued again."""
    for test_id in await question_bank.preparing(session_factory, MockTest):
        await queue.enqueue(prepare_test, test_id=test_id)


# ---------------------------------------------------------------------------- the paper


async def get_test(db: AsyncSession, principal: Principal, test_id: uuid.UUID) -> MockTest:
    test = await db.scalar(
        select(MockTest)
        .join(Student, Student.id == MockTest.student_id)
        .where(MockTest.id == test_id, student_service.visible_to(principal))
        .execution_options(populate_existing=True)
    )
    if test is None:
        raise NotFoundError("We couldn't find this test.", code="test_not_found")
    return test


async def _questions(
    db: AsyncSession, test: MockTest
) -> list[tuple[MockTestQuestion, Question, QuestionView]]:
    """The paper's questions in order, numbered through the paper, as the learner sees them."""
    rows = (
        await db.execute(
            select(MockTestQuestion, Question)
            .join(Question, Question.id == MockTestQuestion.question_id)
            .where(MockTestQuestion.mock_test_id == test.id)
            .order_by(MockTestQuestion.section, MockTestQuestion.position)
        )
    ).all()
    sources = await library_service.describe_sources(
        db, [(q.book_id, q.chapter_id, q.exercise_id, q.page) for _, q in rows]
    )
    return [
        (link, question, QuestionView.of(question, number, source))
        for number, ((link, question), source) in enumerate(zip(rows, sources, strict=True), start=1)
    ]


def _sections(
    test: MockTest, questions: list[tuple[MockTestQuestion, Question, QuestionView]]
) -> list[PaperSection]:
    sections = [
        PaperSection(code=section["code"], title=section["title"], marks=section["marks"], questions=[])
        for section in test.sections
    ]
    by_code = {section.code: section for section in sections}
    for link, _, view in questions:
        by_code[link.section].questions.append(view)
    return [section for section in sections if section.questions]


async def _summaries(db: AsyncSession, tests: list[MockTest]) -> list[MockTestSummary]:
    ids = [test.id for test in tests]
    names = {
        row[0]: row[1:]
        for row in await db.execute(
            select(
                MockTest.id,
                Book.title,
                Chapter.number,
                Chapter.title,
                Topic.number,
                Topic.title,
                Exercise.label,
            )
            .outerjoin(Book, Book.id == MockTest.book_id)
            .outerjoin(Chapter, Chapter.id == MockTest.chapter_id)
            .outerjoin(Topic, Topic.id == MockTest.topic_id)
            .outerjoin(Exercise, Exercise.id == MockTest.exercise_id)
            .where(MockTest.id.in_(ids))
        )
    }
    marks = dict(
        (
            await db.execute(
                select(MockTestQuestion.mock_test_id, func.sum(MockTestQuestion.marks))
                .where(MockTestQuestion.mock_test_id.in_(ids))
                .group_by(MockTestQuestion.mock_test_id)
            )
        ).all()
    )
    sittings = (
        await db.scalars(
            select(MockTestAttempt)
            .where(MockTestAttempt.mock_test_id.in_(ids))
            .order_by(MockTestAttempt.created_at)
        )
    ).all()
    summaries = []
    for test in tests:
        book_title, chapter_number, chapter_title, topic_number, topic_title, exercise = names[test.id]
        summaries.append(
            MockTestSummary(
                id=test.id,
                student_id=test.student_id,
                kind=test.kind,
                status=test.status,
                book_id=test.book_id,
                book_title=book_title,
                chapter_id=test.chapter_id,
                chapter=chapter_label(chapter_number, chapter_title) if chapter_title else None,
                topic_id=test.topic_id,
                topic=topic_label(topic_number, topic_title) if topic_title else None,
                exercise_id=test.exercise_id,
                exercise=exercise or None,
                question_count=test.question_count,
                total_marks=marks.get(test.id, 0),
                duration_minutes=test.duration_minutes,
                difficulty=test.difficulty,
                language=test.language,
                attempts=[
                    AttemptSummary(
                        id=s.id, started_at=s.started_at, submitted_at=s.submitted_at, score=s.score
                    )
                    for s in sittings
                    if s.mock_test_id == test.id
                ],
                created_at=test.created_at,
            )
        )
    return summaries


async def mock_test_out(db: AsyncSession, test: MockTest) -> MockTestOut:
    (summary,) = await _summaries(db, [test])
    error = None
    if test.status == "failed" and test.error_code:
        error = DocumentError(code=test.error_code, message=question_bank.error_message(test.error_code))
    return MockTestOut(
        **summary.model_dump(), error=error, sections=_sections(test, await _questions(db, test))
    )


async def list_tests(
    db: AsyncSession, principal: Principal, student_id: uuid.UUID, *, limit: int, cursor: str | None
) -> MockTestPage:
    student = await student_service.get_student(db, principal, student_id)
    tests, next_cursor = await pagination.newest_first(
        db, select(MockTest).where(MockTest.student_id == student.id), MockTest, limit=limit, cursor=cursor
    )
    return MockTestPage(items=await _summaries(db, tests), next_cursor=next_cursor)


# ---------------------------------------------------------------------------- taking it


async def _sitting(
    db: AsyncSession, principal: Principal, attempt_id: uuid.UUID
) -> tuple[MockTestAttempt, MockTest]:
    row = (
        await db.execute(
            select(MockTestAttempt, MockTest)
            .join(MockTest, MockTest.id == MockTestAttempt.mock_test_id)
            .join(Student, Student.id == MockTestAttempt.student_id)
            .where(MockTestAttempt.id == attempt_id, student_service.visible_to(principal))
            .execution_options(populate_existing=True)
        )
    ).first()
    if row is None:
        raise NotFoundError("We couldn't find this test.", code="test_attempt_not_found")
    attempt, test = row
    return attempt, test


def _deadline(test: MockTest, attempt: MockTestAttempt) -> datetime | None:
    return attempt.started_at + timedelta(minutes=test.duration_minutes) if test.duration_minutes else None


async def _attempt_out(db: AsyncSession, attempt: MockTestAttempt, test: MockTest) -> AttemptOut:
    questions = await _questions(db, test)
    deadline = _deadline(test, attempt)
    seconds_left = None
    if deadline is not None and attempt.submitted_at is None:
        seconds_left = max(0, int((deadline - utcnow()).total_seconds()))
    return AttemptOut(
        id=attempt.id,
        mock_test_id=test.id,
        status="submitted" if attempt.submitted_at else "in_progress",
        started_at=attempt.started_at,
        deadline=deadline,
        seconds_left=seconds_left,
        submitted_at=attempt.submitted_at,
        total_marks=sum(link.marks for link, _, _ in questions),
        sections=_sections(test, questions),
        responses=attempt.responses,
    )


async def start_attempt(db: AsyncSession, principal: Principal, test_id: uuid.UUID) -> AttemptOut:
    """Starts the clock - or returns the sitting already in progress."""
    test = await get_test(db, principal, test_id)
    if test.status != "ready":
        raise InvalidInputError("This test is not ready yet.", code="test_not_ready")
    attempt = await db.scalar(
        select(MockTestAttempt).where(
            MockTestAttempt.mock_test_id == test.id, MockTestAttempt.submitted_at.is_(None)
        )
    )
    if attempt is None:
        attempt = MockTestAttempt(
            mock_test_id=test.id, student_id=test.student_id, started_at=utcnow(), responses={}
        )
        db.add(attempt)
        await db.commit()
    return await _attempt_out(db, attempt, test)


async def get_attempt(db: AsyncSession, principal: Principal, attempt_id: uuid.UUID) -> AttemptOut:
    return await _attempt_out(db, *await _sitting(db, principal, attempt_id))


async def save_answer(
    db: AsyncSession, principal: Principal, attempt_id: uuid.UUID, question_id: uuid.UUID, data: Response
) -> None:
    attempt, test = await _sitting(db, principal, attempt_id)
    if attempt.submitted_at is not None:
        raise InvalidInputError("This test has been submitted.", code="test_already_submitted")
    deadline = _deadline(test, attempt)
    if deadline is not None and utcnow() > deadline + GRACE:
        raise InvalidInputError("Time is up for this test.", code="test_time_over")
    question = await db.scalar(
        select(Question)
        .join(MockTestQuestion, MockTestQuestion.question_id == Question.id)
        .where(MockTestQuestion.mock_test_id == test.id, Question.id == question_id)
    )
    if question is None:
        raise NotFoundError("This question is not part of this test.", code="question_not_found")
    response = data.model_dump(exclude_none=True)
    checking.is_correct(question, response)  # only that it fits the question; marked on submission
    # One statement, so two answers saved at the same moment cannot overwrite each other.
    await db.execute(
        update(MockTestAttempt)
        .where(MockTestAttempt.id == attempt.id)
        .values(responses=MockTestAttempt.responses.op("||")(literal({str(question.id): response}, JSONB)))
    )
    await db.commit()


async def submit(db: AsyncSession, principal: Principal, attempt_id: uuid.UUID) -> TestReport:
    """Marks the sitting (once; submitting again returns the same report)."""
    attempt, test = await _sitting(db, principal, attempt_id)
    if attempt.submitted_at is None:
        await _mark(db, attempt, test)
    return await _report(db, attempt, test)


async def _mark(db: AsyncSession, attempt: MockTestAttempt, test: MockTest) -> None:
    student = await db.get(Student, test.student_id)
    assert student is not None and student.profile is not None
    profile = student_service.class_profile(student)
    rows = (
        await db.execute(
            select(MockTestQuestion, Question)
            .join(Question, Question.id == MockTestQuestion.question_id)
            .where(MockTestQuestion.mock_test_id == test.id)
            .order_by(MockTestQuestion.section, MockTestQuestion.position)
        )
    ).all()
    # Every answer is marked before anything is stored: if the AI fails, the sitting stays as it was.
    marked = []
    for link, question in rows:
        saved = attempt.responses.get(str(question.id))
        if saved is None:
            continue
        response = {key: value for key, value in saved.items() if key != "time_taken_ms"}
        correct, feedback = checking.is_correct(question, response), None
        if correct is None:
            grade = await checking.mark_written(
                question, response["text"], profile=profile, student=student.profile
            )
            correct, feedback = grade.is_correct, grade.feedback
            marks = checking.written_marks(question, grade, link.marks)
        else:
            marks = link.marks if correct else 0
        marked.append(
            QuestionAttempt(
                student_id=student.id,
                question_id=question.id,
                test_attempt_id=attempt.id,
                response=response,
                is_correct=correct,
                feedback=feedback,
                time_taken_ms=saved.get("time_taken_ms"),
                hints_used=0,
                solution_viewed=False,
                difficulty=question.difficulty,
                marks=marks,
            )
        )
    db.add_all(marked)
    await db.flush()
    questions = {question.id: question for _, question in rows}
    areas = {(q.chapter_id, q.topic_id): q for q in (questions[a.question_id] for a in marked)}
    for question in areas.values():
        await mastery.record_answer(db, student, question)
    attempt.submitted_at = utcnow()
    attempt.score = sum(a.marks or 0 for a in marked)
    await study_plan_service.book_test_done(db, test)
    await db.commit()


# ---------------------------------------------------------------------------- the report


async def report(db: AsyncSession, principal: Principal, attempt_id: uuid.UUID) -> TestReport:
    attempt, test = await _sitting(db, principal, attempt_id)
    if attempt.submitted_at is None:
        raise InvalidInputError("This test has not been submitted yet.", code="test_not_submitted")
    return await _report(db, attempt, test)


async def _areas(
    db: AsyncSession, results: list[tuple[Question, QuestionAttempt | None]]
) -> list[AreaResult]:
    """Right answers by chapter and topic, weakest first."""
    tally: dict[tuple, list[int]] = {}
    for question, answer in results:
        if question.chapter_id is not None:
            counts = tally.setdefault((question.chapter_id, question.topic_id), [0, 0])
            counts[0] += 1
            counts[1] += bool(answer and answer.is_correct)
    chapters = {
        row[0]: row[1:]
        for row in await db.execute(
            select(Chapter.id, Chapter.number, Chapter.title, Book.id, Book.title)
            .join(Book, Book.id == Chapter.book_id)
            .where(Chapter.id.in_({chapter_id for chapter_id, _ in tally}))
        )
    }
    topics = {
        topic.id: topic
        for topic in await db.scalars(select(Topic).where(Topic.id.in_({topic for _, topic in tally})))
    }
    areas = []
    for (chapter_id, topic_id), (count, right) in tally.items():
        number, title, book_id, book_title = chapters[chapter_id]
        topic = topics.get(topic_id)
        areas.append(
            AreaResult(
                book_id=book_id,
                book_title=book_title,
                chapter_id=chapter_id,
                chapter=chapter_label(number, title),
                topic_id=topic_id,
                topic=topic_label(topic.number, topic.title) if topic else None,
                questions=count,
                correct=right,
                accuracy=round(right / count, 3),
            )
        )
    return sorted(areas, key=lambda area: (area.accuracy, -area.questions))


async def _report(db: AsyncSession, attempt: MockTestAttempt, test: MockTest) -> TestReport:
    assert attempt.submitted_at is not None and attempt.score is not None
    questions = await _questions(db, test)
    answers = {
        answer.question_id: answer
        for answer in await db.scalars(
            select(QuestionAttempt).where(QuestionAttempt.test_attempt_id == attempt.id)
        )
    }
    report_questions = []
    sections = {
        section["code"]: SectionResult(
            code=section["code"], title=section["title"], score=0, total_marks=0, answered=0, correct=0
        )
        for section in test.sections
    }
    for link, question, view in questions:
        answer = answers.get(question.id)
        section = sections[link.section]
        section.total_marks += link.marks
        if answer is not None:
            section.answered += 1
            section.correct += answer.is_correct
            section.score += answer.marks or 0
        report_questions.append(
            ReportQuestion(
                question=view,
                section=link.section,
                marks=link.marks,
                marks_awarded=answer.marks if answer else None,
                correct=answer.is_correct if answer else None,
                response=Response(**answer.response) if answer else None,
                feedback=answer.feedback if answer else None,
                solution=Solution(**question.solution),
            )
        )
    total = sum(link.marks for link, _, _ in questions)
    right = sum(answer.is_correct for answer in answers.values())
    return TestReport(
        attempt_id=attempt.id,
        mock_test_id=test.id,
        kind=test.kind,
        score=attempt.score,
        total_marks=total,
        percentage=round(attempt.score / total * 100, 1) if total else 0,
        time_taken_ms=int((attempt.submitted_at - attempt.started_at).total_seconds() * 1000),
        submitted_at=attempt.submitted_at,
        answered=len(answers),
        correct=right,
        wrong=len(answers) - right,
        unanswered=len(questions) - len(answers),
        sections=[section for section in sections.values() if section.total_marks],
        areas=await _areas(db, [(question, answers.get(question.id)) for _, question, _ in questions]),
        questions=report_questions,
    )
