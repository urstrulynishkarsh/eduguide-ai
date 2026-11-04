"""Previous-year paper analysis of a book of papers."""

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentPrincipal, DbSession, Queue
from app.schemas.paper import PaperAnalysisOut
from app.services import paper_analysis_service

router = APIRouter(tags=["Previous-year papers"])


@router.post(
    "/books/{book_id}/paper-analysis",
    response_model=PaperAnalysisOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Analyse the papers",
)
async def start_analysis(
    book_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession, queue: Queue
) -> PaperAnalysisOut:
    """Reads every paper of a "Previous-year papers" book (Class 9-12) with the AI, in the background:
    the marks, format and textbook chapter of each question, and each paper's year, time and negative
    marking. `status` is `preparing` until done. `422 not_a_paper_book`, `not_for_class`, `no_papers`;
    `503 ai_not_configured` when the AI is off. Not in child mode."""
    return await paper_analysis_service.start(db, principal, book_id, queue=queue)


@router.get("/books/{book_id}/paper-analysis", response_model=PaperAnalysisOut, summary="The analysis")
async def get_analysis(book_id: uuid.UUID, principal: CurrentPrincipal, db: DbSession) -> PaperAnalysisOut:
    """Where the marks go (chapters, trend over the years), the topics asked most, the kinds of
    questions, the layout of the latest paper, and `test`: the body of a test like the papers for
    `POST /mock-tests` (add `student_id`)."""
    return await paper_analysis_service.analysis(db, principal, book_id)
