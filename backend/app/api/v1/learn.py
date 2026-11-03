"""Learn a concept from the child's own books."""

from fastapi import APIRouter

from app.api.deps import CurrentPrincipal, DbSession
from app.schemas.common import ErrorResponse
from app.schemas.learn import ExplainRequest, ExplainResponse
from app.services import learn_service

router = APIRouter(prefix="/learn", tags=["Learn"])


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Explain a concept from the child's books",
    responses={
        422: {"model": ErrorResponse, "description": "`insufficient_context`: the books do not cover this"},
        503: {"model": ErrorResponse, "description": "`ai_not_configured` or `ai_unavailable`"},
    },
)
async def explain(data: ExplainRequest, principal: CurrentPrincipal, db: DbSession) -> ExplainResponse:
    """Answers only from the uploaded books, with the chapter and page it used. Styles: normal,
    simple, like_10 ("Explain like I'm 10"), hindi, hinglish. When the books do not cover the
    question the answer is `422 insufficient_context` - the AI never answers from memory."""
    return await learn_service.explain(db, principal, data)
