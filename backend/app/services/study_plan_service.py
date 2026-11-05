"""Study plans: one per learner, planned again each day from what the learner knows.

A plan is made when it is created and, after that, on the first visit of each day (India time): the
tasks of past days still pending become `missed`, and the pending tasks from today on are replaced by
a new plan from the latest mastery (adaptive_learning/planner.py). Tasks already done or skipped
stay, and their minutes count. Today's list is then fixed for the day, like the recommendations.

Finishing a practice or a test of a task's place marks it done; learn tasks are ticked off by hand.
Who may see it: whoever may see the learner. A child in child mode can tick tasks off but not make or
remove a plan.
"""

import uuid
from datetime import date, timedelta
from itertools import groupby

from sqlalchemy import ColumnElement, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adaptive_learning import mastery, planner, recommendations
from app.auth.principal import Principal
from app.core.errors import InvalidInputError, NotFoundError
from app.models import (
    Book,
    Chapter,
    MockTest,
    PracticeSession,
    Student,
    StudentMastery,
    StudyPlan,
    StudyPlanItem,
    Topic,
)
from app.question_generation import paper
from app.schemas.mock_test import MockTestCreate
from app.schemas.study_plan import PlanDay, PlanItemOut, StudyPlanCreate, StudyPlanOut
from app.services import library_service, student_service

MAX_DAYS_AHEAD = 366
_ORDER = {"easy": 0, "medium": 1, "mixed": 1, "hard": 2}


def _plan_not_found() -> NotFoundError:
    return NotFoundError("We couldn't find this study plan.", code="study_plan_not_found")


def _final_test(student: Student) -> planner.FinalTest | None:
    """The test the last day ends with: a full mock where the class has them, else a practice test -
    in the pattern of the learner's exam (JEE / NEET / CUET), as the test itself will be."""
    assert student.profile is not None
    profile = student_service.class_profile(student)
    pattern = paper.pattern_for(profile, student.profile.goal)
    for kind in ("full_mock", "practice"):
        if paper.allowed(profile, kind):
            planned = paper.sections(profile, paper.default_count(profile, kind), pattern)
            return planner.FinalTest(kind, paper.minutes(planned, pattern.minutes_per_mark))
    return None


async def _chapters(
    db: AsyncSession, plan: StudyPlan, student: Student, owner: uuid.UUID, learnt: set[tuple]
) -> list[planner.Chapter]:
    """The chapters the plan covers, in book order, with what the learner knows of each."""
    assert student.profile is not None
    query = (
        select(Chapter.id, Chapter.book_id)
        .join(Book, Book.id == Chapter.book_id)
        .where(library_service.books_for_learner(owner, student.id))
        .order_by(Book.created_at, Chapter.number.asc().nulls_last(), Chapter.position)
    )
    if plan.chapter_ids:
        query = query.where(Chapter.id.in_(plan.chapter_ids))
    else:
        query = query.where(Book.class_level == student.profile.class_level)
    chapters = (await db.execute(query)).all()
    areas = (
        await db.scalars(
            select(StudentMastery).where(
                StudentMastery.student_id == student.id,
                StudentMastery.chapter_id.in_([chapter_id for chapter_id, _ in chapters]),
            )
        )
    ).all()
    features = student_service.class_profile(student).features
    states = []
    for chapter_id, book_id in chapters:
        known = [area for area in areas if area.chapter_id == chapter_id]
        answers = sum(area.attempts for area in known)
        levels = [mastery.practice_level(area, features, "mixed") for area in known]
        states.append(
            planner.Chapter(
                book_id=book_id,
                chapter_id=chapter_id,
                mastery=sum(a.mastery * a.attempts for a in known) / answers if known else None,
                difficulty=min(levels, key=_ORDER.__getitem__) if levels else "mixed",
                weak=[
                    planner.WeakArea(
                        area.topic_id,
                        mastery.practice_level(area, features, "easy"),
                        mastery.right_lately(area),
                    )
                    for area in known
                    if mastery.is_weak(area)
                ],
                learnt=frozenset(topic for chapter, topic in learnt if chapter == chapter_id),
            )
        )
    return states


async def _replan(db: AsyncSession, plan: StudyPlan, student: Student, today: date) -> None:
    """Plans the days from today to the exam again (not committed)."""
    mine = StudyPlanItem.plan_id == plan.id
    await db.execute(
        update(StudyPlanItem)
        .where(mine, StudyPlanItem.day < today, StudyPlanItem.status == "pending")
        .values(status="missed")
    )
    await db.execute(
        delete(StudyPlanItem).where(mine, StudyPlanItem.day >= today, StudyPlanItem.status == "pending")
    )
    kept = (await db.scalars(select(StudyPlanItem).where(mine))).all()
    booked: dict[int, int] = {}
    taken: dict[int, int] = {}  # positions used on a day
    for item in kept:
        if item.day >= today:
            day = (item.day - today).days
            booked[day] = booked.get(day, 0) + item.minutes
            taken[day] = max(taken.get(day, 0), item.position + 1)
    learnt = {
        (item.chapter_id, item.topic_id) for item in kept if item.kind == "learn" and item.status == "done"
    }

    owner = await student_service.account_of(db, student)
    chapters = await _chapters(db, plan, student, owner, learnt)
    final_test = _final_test(student)
    work, final = planner.tasks(chapters, target=plan.target_score / 100, final_test=final_test)
    placed, plan.unscheduled = planner.schedule(
        work,
        final,
        days=max(0, (plan.exam_date - today).days),
        daily_minutes=plan.daily_minutes,
        booked=booked,
    )
    for p in placed:
        position = taken.get(p.day, 0)
        taken[p.day] = position + 1
        task = p.task
        db.add(
            StudyPlanItem(
                plan_id=plan.id,
                day=today + timedelta(days=p.day),
                position=position,
                kind=task.kind,
                book_id=task.book_id,
                chapter_id=task.chapter_id,
                topic_id=task.topic_id,
                difficulty=task.difficulty,
                minutes=task.minutes,
                reason=task.reason,
                status="pending",
            )
        )
    plan.planned_on = today
    await db.flush()


# ---------------------------------------------------------------------------- reading


async def _items(db: AsyncSession, student: Student, *where: ColumnElement[bool]) -> list[PlanItemOut]:
    final_test = _final_test(student)
    items = []
    rows = await db.execute(
        select(StudyPlanItem, Book.id, Book.title, Chapter.number, Chapter.title, Topic.number, Topic.title)
        .join(Book, Book.id == StudyPlanItem.book_id)
        .outerjoin(Chapter, Chapter.id == StudyPlanItem.chapter_id)
        .outerjoin(Topic, Topic.id == StudyPlanItem.topic_id)
        .where(*where)
        .order_by(StudyPlanItem.day, StudyPlanItem.position)
    )
    for row in rows:
        item: StudyPlanItem = row[0]
        place = mastery.names(row)
        practice = revise = test = None
        if item.kind == "practice":
            practice = recommendations.practice_body(student.id, place, item.difficulty)
        elif item.kind == "learn":
            revise = recommendations.revise_body(student.id, place)
        elif final_test is not None:
            test = MockTestCreate(student_id=student.id, kind=final_test.kind, book_id=item.book_id)
        items.append(
            PlanItemOut(
                **place,
                id=item.id,
                day=item.day,
                kind=item.kind,
                status=item.status,
                minutes=item.minutes,
                difficulty=item.difficulty,
                reason=item.reason,
                practice=practice,
                revise=revise,
                test=test,
            )
        )
    return items


async def _view(db: AsyncSession, plan: StudyPlan, student: Student, today: date) -> StudyPlanOut:
    items = await _items(db, student, StudyPlanItem.plan_id == plan.id)
    days_left = max(0, (plan.exam_date - today).days)
    return StudyPlanOut(
        id=plan.id,
        student_id=plan.student_id,
        exam_date=plan.exam_date,
        daily_minutes=plan.daily_minutes,
        target_score=plan.target_score,
        chapter_ids=plan.chapter_ids,
        status="active" if days_left else "finished",
        days_left=days_left,
        planned_on=plan.planned_on,
        unscheduled=plan.unscheduled,
        done=sum(item.status == "done" for item in items),
        missed=sum(item.status == "missed" for item in items),
        total=len(items),
        days=[
            PlanDay(day=day, minutes=sum(item.minutes for item in group), items=group)
            for day, group in ((day, list(group)) for day, group in groupby(items, key=lambda item: item.day))
        ],
    )


# ---------------------------------------------------------------------------- the endpoints


async def create_plan(db: AsyncSession, principal: Principal, data: StudyPlanCreate) -> StudyPlanOut:
    library_service.ensure_can_manage(principal)
    student = await student_service.learner_for(db, principal, data.student_id)
    today = recommendations.today()
    if not today < data.exam_date <= today + timedelta(days=MAX_DAYS_AHEAD):
        raise InvalidInputError(
            "Choose an exam date after today, at most a year ahead.",
            details=[{"field": "exam_date", "message": "After today, at most a year ahead."}],
        )
    owner = await student_service.account_of(db, student)
    chapter_ids = list(dict.fromkeys(data.chapter_ids))
    if chapter_ids:
        found = await db.scalars(
            select(Chapter.id)
            .join(Book, Book.id == Chapter.book_id)
            .where(Chapter.id.in_(chapter_ids), library_service.books_for_learner(owner, student.id))
        )
        if len(found.all()) != len(chapter_ids):
            raise NotFoundError("We couldn't find this chapter.", code="chapter_not_found")

    await db.execute(delete(StudyPlan).where(StudyPlan.student_id == student.id))
    plan = StudyPlan(
        student_id=student.id,
        exam_date=data.exam_date,
        daily_minutes=data.daily_minutes,
        target_score=data.target_score,
        chapter_ids=chapter_ids,
        planned_on=today,
        unscheduled=0,
    )
    db.add(plan)
    await db.flush()
    await _replan(db, plan, student, today)
    await db.commit()
    return await _view(db, plan, student, today)


async def current_plan(db: AsyncSession, student: Student) -> StudyPlanOut | None:
    """The learner's plan, planned again first if this is the first visit of the day. The plan is
    locked and read again to plan it: two first visits at the same moment (the child's device and the
    parent's) plan it once, rather than each adding the day's tasks."""
    mine = select(StudyPlan).where(StudyPlan.student_id == student.id)
    plan = await db.scalar(mine)
    today = recommendations.today()
    if plan is not None and plan.planned_on < today:
        plan = await db.scalar(mine.with_for_update().execution_options(populate_existing=True))
        if plan is not None and plan.planned_on < today:
            await _replan(db, plan, student, today)
        await db.commit()
    return await _view(db, plan, student, today) if plan is not None else None


async def get_plan(db: AsyncSession, principal: Principal, student_id: uuid.UUID) -> StudyPlanOut:
    student = student_service.require_profile(await student_service.get_student(db, principal, student_id))
    plan = await current_plan(db, student)
    if plan is None:
        raise _plan_not_found()
    return plan


async def update_item(db: AsyncSession, principal: Principal, item_id: uuid.UUID, status: str) -> PlanItemOut:
    row = (
        await db.execute(
            select(StudyPlanItem, Student)
            .join(StudyPlan, StudyPlan.id == StudyPlanItem.plan_id)
            .join(Student, Student.id == StudyPlan.student_id)
            .where(StudyPlanItem.id == item_id, student_service.visible_to(principal))
        )
    ).first()
    if row is None:
        raise NotFoundError("We couldn't find this task.", code="plan_item_not_found")
    item, student = row
    item.status = status
    await db.commit()
    return (await _items(db, student, StudyPlanItem.id == item.id))[0]


async def delete_plan(db: AsyncSession, principal: Principal, plan_id: uuid.UUID) -> None:
    library_service.ensure_can_manage(principal)
    plan = await db.scalar(
        select(StudyPlan)
        .join(Student, Student.id == StudyPlan.student_id)
        .where(StudyPlan.id == plan_id, student_service.visible_to(principal))
    )
    if plan is None:
        raise _plan_not_found()
    await db.delete(plan)
    await db.commit()


# ---------------------------------------------------------------------------- ticked off by practice


async def _tick(db: AsyncSession, student_id: uuid.UUID, *where: ColumnElement[bool]) -> None:
    """Marks the learner's pending tasks of today or before that match `where` as done (not committed)."""
    plans = select(StudyPlan.id).where(StudyPlan.student_id == student_id)
    await db.execute(
        update(StudyPlanItem)
        .where(
            StudyPlanItem.plan_id.in_(plans),
            StudyPlanItem.status == "pending",
            StudyPlanItem.day <= recommendations.today(),
            *where,
        )
        .values(status="done")
    )


async def practice_done(db: AsyncSession, session: PracticeSession) -> None:
    """A finished practice: the practice tasks for its place are done."""
    if session.chapter_id is not None:
        await _tick(
            db,
            session.student_id,
            StudyPlanItem.kind == "practice",
            StudyPlanItem.chapter_id == session.chapter_id,
            StudyPlanItem.topic_id.is_not_distinct_from(session.topic_id),
        )


async def book_test_done(db: AsyncSession, test: MockTest) -> None:
    """A submitted test of a whole book: the test task for that book is done."""
    if test.book_id is not None and test.chapter_id is None:
        await _tick(db, test.student_id, StudyPlanItem.kind == "test", StudyPlanItem.book_id == test.book_id)
