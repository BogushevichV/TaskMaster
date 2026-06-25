from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.deps import get_current_user, require_manager
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.crud.task import get_employee_metrics
from backend.app.crud.user import get_user_by_id, list_users, update_user
from backend.app.models.enums import UserRole
from backend.app.models.user import User
from backend.app.schemas.user import UserMetrics, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
async def get_users(
    role: UserRole | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.PAGE_SIZE, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
) -> list[User]:
    skip = (page - 1) * page_size
    users, _ = await list_users(db, role=role, skip=skip, limit=page_size)
    return users


@router.get("/employees/metrics", response_model=list[UserMetrics])
async def employees_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
) -> list[UserMetrics]:
    users, _ = await list_users(db, role=UserRole.EMPLOYEE, limit=1000)
    result = []
    for user in users:
        metrics = await get_employee_metrics(db, user)
        result.append(
            UserMetrics(
                user=UserRead.model_validate(user),
                **metrics,
            )
        )
    return result


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.MANAGER and current_user.id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead)
async def patch_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.MANAGER and current_user.id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return await update_user(db, user, data)
