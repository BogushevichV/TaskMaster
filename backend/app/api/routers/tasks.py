from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, require_manager
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.crud.task import (
    create_task,
    delete_task,
    get_task_by_id,
    get_task_history,
    list_tasks,
    update_task,
)
from backend.app.models.enums import TaskStatus, UserRole
from backend.app.models.user import User
from backend.app.schemas.task import (
    TaskCreate,
    TaskHistoryRead,
    TaskListResponse,
    TaskRead,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=TaskListResponse)
async def get_tasks(
    status_filter: TaskStatus | None = Query(None, alias="status"),
    assigned_to_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.PAGE_SIZE, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskListResponse:
    skip = (page - 1) * page_size
    items, total = await list_tasks(
        db,
        user=current_user,
        status=status_filter,
        assigned_to_id=assigned_to_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        skip=skip,
        limit=page_size,
    )
    return TaskListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def post_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_manager),
) -> TaskRead:
    return await create_task(db, data, current_user)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    task = await get_task_by_id(db, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if (
        current_user.role == UserRole.EMPLOYEE
        and task.assigned_to_id != current_user.id
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
async def patch_task(
    task_id: int,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskRead:
    task = await get_task_by_id(db, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if (
        current_user.role == UserRole.EMPLOYEE
        and task.assigned_to_id != current_user.id
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    if current_user.role == UserRole.EMPLOYEE:
        forbidden = {"title", "description", "deadline", "assigned_to_id"}
        if any(getattr(data, f) is not None for f in forbidden):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Employees can only update status and notes",
            )
    try:
        return await update_task(db, task, data, current_user)
    except PermissionError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
) -> None:
    task = await get_task_by_id(db, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    await delete_task(db, task)


@router.get("/{task_id}/history", response_model=list[TaskHistoryRead])
async def task_history(
    task_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.PAGE_SIZE, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskHistoryRead]:
    task = await get_task_by_id(db, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if (
        current_user.role == UserRole.EMPLOYEE
        and task.assigned_to_id != current_user.id
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    skip = (page - 1) * page_size
    return await get_task_history(db, task_id, skip=skip, limit=page_size)
