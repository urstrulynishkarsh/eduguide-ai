"""Dependencies shared by the routes."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, ParentPrincipal
from app.core.database import get_db
from app.core.tasks import TaskQueue, get_task_queue
from app.storage import FileStorage, get_file_storage

DbSession = Annotated[AsyncSession, Depends(get_db)]
Storage = Annotated[FileStorage, Depends(get_file_storage)]
Queue = Annotated[TaskQueue, Depends(get_task_queue)]

__all__ = ["CurrentPrincipal", "DbSession", "ParentPrincipal", "Queue", "Storage"]
