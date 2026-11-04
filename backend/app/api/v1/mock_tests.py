"""Mock tests: make a paper, take it (timed or not), submit it, read the report."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentPrincipal, DbSession, Queue
from app.schemas import practice
from app.schemas.mock_test import AttemptOut, MockTestCreate, MockTestOut, MockTestPage, TestReport
from app.services import mock_test_service

router = APIRouter(tags=["Mock tests"])


@router.post(
    "/mock-tests", response_model=MockTestOut, status_code=status.HTTP_201_CREATED, summary="Create a test"
)
async def create_test(
    data: MockTestCreate, principal: CurrentPrincipal, db: DbSession, queue: Queue
) -> MockTestOut:
    """A paper in sections - objective, numerical, short and long answers, as the class uses them.
    `practice` tests from Class 3, `chapter` tests from Class 6, `full_mock` and `previous_year` tests
    and time limits from Class 9 (`422 test_not_for_class` otherwise). A learner whose goal is JEE,
    NEET or CUET (Class 11-12) gets the exam's pattern: its sections, marks and negative marks. Saved
    questions the learner has not seen are used first; the rest are written in the background -
    `status` is `preparing` until then."""
    test = await mock_test_service.create_test(db, principal, data, queue=queue)
    return await mock_test_service.mock_test_out(db, test)


@router.get("/mock-tests/{test_id}", response_model=MockTestOut, summary="A test and its paper")
async def get_test(test_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> MockTestOut:
    """Questions never include their answers. Poll while `status` is `preparing`."""
    return await mock_test_service.mock_test_out(db, await mock_test_service.get_test(db, principal, test_id))


@router.get("/students/{student_id}/mock-tests", response_model=MockTestPage, summary="A learner's tests")
async def list_tests(
    student_id: uuid.UUID,
    principal: CurrentPrincipal,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: str | None = None,
) -> MockTestPage:
    """Newest first, with every sitting and its score."""
    return await mock_test_service.list_tests(db, principal, student_id, limit=limit, cursor=cursor)


@router.post(
    "/mock-tests/{test_id}/attempts",
    response_model=AttemptOut,
    status_code=status.HTTP_201_CREATED,
    summary="Start the test",
)
async def start_attempt(test_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> AttemptOut:
    """Starts the clock. A sitting still in progress is returned instead of starting a second one;
    after a submitted one, this is a retake of the same paper."""
    return await mock_test_service.start_attempt(db, principal, test_id)


@router.get("/test-attempts/{attempt_id}", response_model=AttemptOut, summary="A sitting of a test")
async def get_attempt(attempt_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> AttemptOut:
    """The paper with the answers saved so far and the seconds left - to carry on after a reload."""
    return await mock_test_service.get_attempt(db, principal, attempt_id)


@router.put(
    "/test-attempts/{attempt_id}/answers/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Save an answer",
)
async def save_answer(
    attempt_id: uuid.UUID,
    question_id: uuid.UUID,
    data: practice.Response,
    principal: CurrentPrincipal,
    db: DbSession,
) -> Response:
    """Saved, not marked: it can be changed until the test is submitted. Refused once time is up
    (`test_time_over`) or the test is submitted (`test_already_submitted`)."""
    await mock_test_service.save_answer(db, principal, attempt_id, question_id, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test-attempts/{attempt_id}/submit", response_model=TestReport, summary="Submit the test")
async def submit(
    attempt_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession, queue: Queue
) -> TestReport:
    """Marks every saved answer (written ones by the AI tutor, with part marks; a wrong one loses the
    section's negative marks) and returns the report. Also accepted after the time is up; submitting
    twice returns the same report."""
    return await mock_test_service.submit(db, principal, attempt_id, queue=queue)


@router.get("/test-attempts/{attempt_id}/report", response_model=TestReport, summary="The result report")
async def report(attempt_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> TestReport:
    """Score, sections, chapters and topics weakest first, and every question with its solution."""
    return await mock_test_service.report(db, principal, attempt_id)
