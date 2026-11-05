"""Learn a concept from the child's own books."""

from fastapi import APIRouter

from app.api.deps import CurrentPrincipal, DbSession, limit_account
from app.core.rate_limits import AI_PER_DAY, AI_PER_MINUTE
from app.schemas.common import ErrorResponse
from app.schemas.learn import ExplainRequest, ExplainResponse
from app.services import learn_service

router = APIRouter(prefix="/learn", tags=["Learn"])


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Explain a concept from the child's books",
    dependencies=[limit_account(AI_PER_MINUTE, AI_PER_DAY)],
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
