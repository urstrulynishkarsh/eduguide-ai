"""Previous-year paper analysis: read the papers of a book, report on them, and plan a test like them.

A "Previous-year papers" book holds one paper per file; reading a file found its sections and
questions. Analysing the book reads every paper again with the AI (analytics/paper_reading.py) - one
background job per paper - and matches each question to a chapter of the family's textbooks of the
same class (the paper's subject first). The report and the test plan are worked out on reading
(analytics/papers.py), so they always follow the papers and textbooks there are now.

Who: anyone who may see the book reads the analysis; parents and students who signed up alone
start one (it uses the AI). Papers are analysed from Class 9 (`previous_year_questions`).
"""

import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import llm
from app.analytics import paper_reading
from app.analytics import papers as numbers
from app.auth.principal import Principal
from app.class_profiles import get_class_profile
from app.core.enums import ContentType, DocumentStatus, MaterialType
from app.core.errors import InvalidInputError
from app.core.tasks import TaskQueue
from app.models import (
    Book,
    Chapter,
    Document,
    DocumentChunk,
    Exercise,
    PaperAnalysis,
    PaperQuestion,
    Student,
    Topic,
)
from app.rag.ingestion.labels import chapter_label, exercise_title, topic_label
from app.schemas.library import DocumentError
from app.schemas.mock_test import MockTestCreate
from app.schemas.paper import (
    ChapterMarks,
    FormatShare,
    LayoutSection,
    PaperAnalysisOut,
    PaperOut,
    TopicAsked,
    Unmatched,
    YearMarks,
)
from app.schemas.practice import PracticeCreate
from app.services import library_service, student_service

logger = logging.getLogger(__name__)

MAX_CHAPTERS = 80  # listed to the AI; a family's textbooks of one class are far fewer
_ERRORS = {
    "ai_unavailable": llm.AIUnavailableError.message,
    "no_questions": "No numbered questions were found in this paper.",
    "analysis_failed": "We couldn't analyse this paper this time. Please try again.",
}


async def _paper_book(db: AsyncSession, principal: Principal, book_id: uuid.UUID) -> Book:
    book = await library_service.get_book(db, principal, book_id)
    if book.material_type != MaterialType.PREVIOUS_YEAR_PAPER:
        raise InvalidInputError("This book is not a book of previous-year papers.", code="not_a_paper_book")
    return book


def _read_papers(book: Book) -> list[Document]:
    return [d for d in book.documents if d.status == DocumentStatus.READY and d.stats.get("questions")]


async def start(
    db: AsyncSession, principal: Principal, book_id: uuid.UUID, *, queue: TaskQueue
) -> PaperAnalysisOut:
    """Analyses every paper of the book again (a paper added later, or a textbook, changes the result)."""
    library_service.ensure_can_manage(principal)
    book = await _paper_book(db, principal, book_id)
    profile = get_class_profile(book.class_level)
    if not profile.features.previous_year_questions:
        raise InvalidInputError(
            f"Previous-year papers are analysed from Class 9. This book is for {profile.label}.",
            code="not_for_class",
        )
    papers = _read_papers(book)
    if not papers:
        raise InvalidInputError(
            "No paper with questions has been read yet. Upload one and wait until it is ready.",
            code="no_papers",
        )
    llm.get_llm_provider()  # 503 now when the AI is switched off
    for document in papers:
        row = await db.get(PaperAnalysis, document.id) or PaperAnalysis(
            document_id=document.id, book_id=book.id
        )
        row.status, row.error_code = "preparing", None
        db.add(row)
    await db.commit()
    for document in papers:
        await queue.enqueue(analyse_paper, document_id=document.id)
    return await analysis(db, principal, book_id)


# ---------------------------------------------------------------------------- the background job


async def _textbook_chapters(db: AsyncSession, book: Book) -> list[tuple[Chapter, Book, list[Topic]]]:
    """The chapters the paper's questions may come from: the family's other books of its class that
    the paper's learner may see - those of the paper's subject when there are any."""
    for_learner = (
        library_service.books_for_learner(book.owner_user_id, book.student_id)
        if book.student_id
        else Book.owner_user_id == book.owner_user_id
    )
    rows = (
        await db.execute(
            select(Chapter, Book)
            .join(Book, Book.id == Chapter.book_id)
            .where(
                for_learner,
                Book.class_level == book.class_level,
                Book.material_type != MaterialType.PREVIOUS_YEAR_PAPER,
            )
            .order_by(Book.created_at, Chapter.number.asc().nulls_last(), Chapter.position)
        )
    ).all()
    same_subject = [row for row in rows if row[1].subject.casefold() == book.subject.casefold()]
    chosen = (same_subject or rows)[:MAX_CHAPTERS]
    topics: dict[uuid.UUID, list[Topic]] = {}
    for topic in await db.scalars(
        select(Topic).where(Topic.chapter_id.in_([c.id for c, _ in chosen])).order_by(Topic.position)
    ):
        topics.setdefault(topic.chapter_id, []).append(topic)
    return [(chapter, textbook, topics.get(chapter.id, [])) for chapter, textbook in chosen]


async def _fail(db: AsyncSession, document_id: uuid.UUID, code: str) -> None:
    await db.rollback()
    row = await db.get(PaperAnalysis, document_id, populate_existing=True)
    if row is not None:
        row.status, row.error_code = "failed", code
        await db.commit()


async def analyse_paper(db: AsyncSession, *, document_id: uuid.UUID) -> None:
    """The background job of one paper: the AI reads it; its questions are stored. Safe to run again."""
    row = await db.get(PaperAnalysis, document_id)
    if row is None or row.status != "preparing":
        return
    document = await db.get(Document, document_id)
    book = await db.get(Book, row.book_id)
    assert document is not None and book is not None
    try:
        chunks = (
            await db.execute(
                select(DocumentChunk, Exercise.label)
                .outerjoin(Exercise, Exercise.id == DocumentChunk.exercise_id)
                .where(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.position)
            )
        ).all()
        questions = [(c, label) for c, label in chunks if c.content_type == ContentType.EXERCISE_QUESTION]
        if not questions:
            await _fail(db, document_id, "no_questions")
            return
        front_page = "\n".join(c.content for c, _ in chunks if c.content_type == ContentType.OTHER)
        textbooks = await _textbook_chapters(db, book)
        listed = paper_reading.areas(
            [
                (
                    f"{textbook.title} · {chapter_label(chapter.number, chapter.title)}",
                    [topic_label(t.number, t.title) for t in topics],
                )
                for chapter, textbook, topics in textbooks
            ]
        )
        reading = await paper_reading.read(
            front_page,
            [
                paper_reading.PaperQuestionText(exercise_title(label or ""), c.content)
                for c, label in questions
            ],
            listed,
        )

        await db.execute(delete(PaperQuestion).where(PaperQuestion.document_id == document_id))
        codes = {area.code: area for area in listed}
        read = {q.number: q for q in reading.questions}
        for number, (chunk, _) in enumerate(questions, start=1):
            question = read.get(number)
            if question is None:
                continue
            area = codes.get(question.area.strip())
            chapter, _, topics = textbooks[area.chapter_index] if area else (None, None, [])
            db.add(
                PaperQuestion(
                    chunk_id=chunk.id,
                    document_id=document_id,
                    marks=question.marks if question.marks and question.marks > 0 else None,
                    format=question.format,
                    chapter_id=chapter.id if chapter else None,
                    topic_id=topics[area.topic_index].id if area and area.topic_index is not None else None,
                )
            )
        year = reading.year if reading.year and 1980 <= reading.year <= 2100 else None
        row.year = year or paper_reading.year_from(document.original_filename)
        row.duration_minutes = reading.duration_minutes if reading.duration_minutes else None
        row.negative_marks = max(0.0, reading.negative_marks)
        row.status = "ready"
        await db.commit()
        logger.info("Paper %s analysed: %d of %d questions read", document_id, len(read), len(questions))
    except (llm.AIUnavailableError, llm.AINotConfiguredError):
        await _fail(db, document_id, "ai_unavailable")
    except Exception:
        logger.exception("Analysing paper %s failed", document_id)
        await _fail(db, document_id, "analysis_failed")


async def resume_unfinished_analyses(
    session_factory: async_sessionmaker[AsyncSession], queue: TaskQueue
) -> None:
    """At start-up: papers that were being analysed when the server stopped are queued again."""
    async with session_factory() as db:
        ids = (
            await db.scalars(select(PaperAnalysis.document_id).where(PaperAnalysis.status == "preparing"))
        ).all()
    for document_id in ids:
        await queue.enqueue(analyse_paper, document_id=document_id)


# ---------------------------------------------------------------------------- reading the analysis


async def _analysed(db: AsyncSession, book: Book) -> tuple[list[numbers.Paper], list[numbers.Asked]]:
    """The book's analysed papers and their questions, in each paper's order."""
    ready = {d.id: d for d in _read_papers(book)}
    rows = (
        await db.scalars(
            select(PaperAnalysis).where(
                PaperAnalysis.book_id == book.id,
                PaperAnalysis.status == "ready",
                PaperAnalysis.document_id.in_(ready),
            )
        )
    ).all()
    papers = [
        numbers.Paper(
            row.document_id,
            row.year,
            row.duration_minutes,
            row.negative_marks,
            ready[row.document_id].created_at,
        )
        for row in rows
    ]
    asked = [
        numbers.Asked(q.document_id, exercise_title(label or ""), q.marks, q.format, q.chapter_id, q.topic_id)
        for q, label in await db.execute(
            select(PaperQuestion, Exercise.label)
            .join(DocumentChunk, DocumentChunk.id == PaperQuestion.chunk_id)
            .outerjoin(Exercise, Exercise.id == DocumentChunk.exercise_id)
            .where(PaperQuestion.document_id.in_([p.document_id for p in papers]))
            .order_by(PaperQuestion.document_id, DocumentChunk.position)
        )
    ]
    return papers, asked


async def analysis(db: AsyncSession, principal: Principal, book_id: uuid.UUID) -> PaperAnalysisOut:
    book = await _paper_book(db, principal, book_id)
    rows = {
        row.document_id: row
        for row in await db.scalars(select(PaperAnalysis).where(PaperAnalysis.book_id == book.id))
    }
    papers, asked = await _analysed(db, book)
    documents = _read_papers(book)
    titles = dict(
        (
            await db.execute(
                select(Chapter.document_id, Chapter.title).where(
                    Chapter.document_id.in_([d.id for d in documents])
                )
            )
        ).all()
    )
    statuses = {row.status for row in rows.values()}
    status = next((s for s in ("preparing", "ready", "failed") if s in statuses), "none")

    per_paper: dict[uuid.UUID, list[numbers.Asked]] = {}
    for q in asked:
        per_paper.setdefault(q.document_id, []).append(q)
    paper_list = []
    for document in documents:
        row = rows.get(document.id)
        mine = per_paper.get(document.id, [])
        paper_list.append(
            PaperOut(
                document_id=document.id,
                title=titles.get(document.id, document.original_filename),
                status=row.status if row else "new",
                error=DocumentError(
                    code=row.error_code, message=_ERRORS.get(row.error_code, _ERRORS["analysis_failed"])
                )
                if row and row.error_code
                else None,
                year=row.year if row else None,
                duration_minutes=row.duration_minutes if row else None,
                negative_marks=row.negative_marks if row else 0,
                questions=len(mine),
                total_marks=sum(q.weight for q in mine),
            )
        )
    paper_list.sort(key=lambda p: (p.year or 0, p.status != "new"), reverse=True)

    weights = numbers.chapters(asked)
    names = await _names(db, {w.chapter_id for w in weights})
    topic_names = {
        t.id: topic_label(t.number, t.title)
        for t in await db.scalars(
            select(Topic).where(Topic.id.in_({q.topic_id for q in asked if q.topic_id}))
        )
    }
    total = sum(q.weight for q in asked)
    timeline = numbers.dated(papers)
    chapters = []
    for w in weights:
        if w.chapter_id not in names:
            continue  # removed since
        by_year = [YearMarks(year=p.year, marks=w.by_paper.get(p.document_id, 0)) for p in timeline if p.year]
        chapters.append(
            ChapterMarks(
                **names[w.chapter_id],
                topic_id=None,
                topic=None,
                questions=w.questions,
                marks_per_paper=round(w.marks / len(papers), 1),
                share=round(w.marks / total, 3),
                papers=len(w.papers),
                trend=numbers.trend([y.marks for y in by_year]),
                by_year=by_year,
                practice=PracticeCreate(chapter_id=w.chapter_id),
            )
        )
    unmatched = [q for q in asked if q.chapter_id is None or q.chapter_id not in names]
    latest = numbers.latest(papers) if papers else None
    return PaperAnalysisOut(
        book_id=book.id,
        status=status,
        papers=paper_list,
        chapters=chapters,
        unmatched=Unmatched(questions=len(unmatched), marks=sum(q.weight for q in unmatched)),
        topics=[
            TopicAsked(**names[c], topic_id=t, topic=topic_names[t], questions=n, papers=k)
            for c, t, n, k in numbers.topics(asked)
            if c in names and t in topic_names
        ],
        formats=[
            FormatShare(format=f, questions=n, marks=m, share=round(n / len(asked), 3))
            for f, n, m in numbers.formats(asked)
        ],
        layout=[
            LayoutSection(title=s.title, questions=s.questions, marks=s.marks, formats=list(s.formats))
            for s in numbers.pattern(per_paper.get(latest.document_id, []))
        ]
        if latest
        else [],
        layout_year=latest.year if latest else None,
        test=MockTestCreate(kind="previous_year", book_id=book.id) if chapters else None,
    )


async def _names(db: AsyncSession, chapter_ids: set[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """The `Area` fields of each chapter that still exists (without a topic)."""
    rows = await db.execute(
        select(Chapter.id, Chapter.number, Chapter.title, Book.id, Book.title)
        .join(Book, Book.id == Chapter.book_id)
        .where(Chapter.id.in_(chapter_ids))
    )
    return {
        chapter_id: {
            "book_id": book_id,
            "book_title": book_title,
            "chapter_id": chapter_id,
            "chapter": chapter_label(number, title),
        }
        for chapter_id, number, title, book_id, book_title in rows
    }


# ---------------------------------------------------------------------------- a test like the papers


async def test_plan(
    db: AsyncSession, principal: Principal, book_id: uuid.UUID, student: Student, count: int | None
) -> tuple[list[dict], float]:
    """The sections of a previous-year pattern test for this learner, and its minutes per mark."""
    book = await _paper_book(db, principal, book_id)
    assert student.profile is not None
    profile = student_service.class_profile(student)
    if book.class_level != student.profile.class_level:
        raise InvalidInputError(f"These papers are not for {profile.label}.", code="paper_not_for_class")
    papers, asked = await _analysed(db, book)
    owner = await student_service.account_of(db, student)
    learner_chapters = set(
        (
            await db.scalars(
                select(Chapter.id)
                .join(Book, Book.id == Chapter.book_id)
                .where(library_service.books_for_learner(owner, student.id))
            )
        ).all()
    )
    weights = [w for w in numbers.chapters(asked) if w.chapter_id in learner_chapters]
    not_analysed = InvalidInputError(
        "Analyse the papers first. A test like them needs questions that match the chapters of the "
        "learner's textbooks.",
        code="paper_not_analysed",
    )
    if not papers or not weights:
        raise not_analysed
    latest = numbers.latest(papers)
    layout = numbers.pattern([q for q in asked if q.document_id == latest.document_id])
    wanted = count or min(sum(s.questions for s in layout), profile.max_session_questions)
    planned = numbers.test_sections(
        layout, weights, count=wanted, negative_marks=latest.negative_marks, allowed=profile.question_formats
    )
    if not planned:
        raise not_analysed
    return planned, numbers.minutes_per_mark(latest, asked)
