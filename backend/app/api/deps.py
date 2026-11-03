"""Dependencies shared by the routes."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, ParentPrincipal
from app.core.database import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]

__all__ = ["CurrentPrincipal", "DbSession", "ParentPrincipal"]
