from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.enums import TaskStatus, UserRole
from backend.app.models.task import Task
from backend.app.models.task_history import TaskHistory
from backend.app.models.user import User
from backend.app.schemas.task import TaskCreate, TaskUpdate


async def get_task_by_id(db: AsyncSession, task_id: int) -> Task | None:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.assignee), selectinload(Task.creator))
        .where(Task.id == task_id)
    )
    return result.scalar_one_or_none()


async def list_tasks(
    db: AsyncSession,
    *,
    user: User,
    status: TaskStatus | None = None,
    assigned_to_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Task], int]:
    query = select(Task).options(
        selectinload(Task.assignee),
        selectinload(Task.creator),
    )

    if user.role == UserRole.EMPLOYEE:
        query = query.where(Task.assigned_to_id == user.id)
    elif assigned_to_id is not None:
        query = query.where(Task.assigned_to_id == assigned_to_id)

    if status is not None:
        query = query.where(Task.status == status)
    if date_from is not None:
        query = query.where(Task.deadline >= date_from)
    if date_to is not None:
        query = query.where(Task.deadline <= date_to)
    if search:
        query = query.where(
            or_(
                Task.title.ilike(f"%{search}%"),
                Task.description.ilike(f"%{search}%"),
            )
        )

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        query.order_by(Task.deadline.asc().nullslast(), Task.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def _add_history(
    db: AsyncSession,
    *,
    task_id: int,
    user_id: int,
    action_type: str,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    db.add(
        TaskHistory(
            task_id=task_id,
            user_id=user_id,
            action_type=action_type,
            old_value=old_value,
            new_value=new_value,
        )
    )


async def create_task(db: AsyncSession, data: TaskCreate, creator: User) -> Task:
    task = Task(
        title=data.title,
        description=data.description,
        deadline=data.deadline,
        assigned_to_id=data.assigned_to_id,
        created_by_id=creator.id,
    )
    db.add(task)
    await db.flush()
    await _add_history(
        db,
        task_id=task.id,
        user_id=creator.id,
        action_type="CREATE",
        new_value=task.title,
    )
    await db.refresh(task)
    return await get_task_by_id(db, task.id)  # type: ignore[return-value]


async def update_task(
    db: AsyncSession,
    task: Task,
    data: TaskUpdate,
    actor: User,
) -> Task:
    updates = data.model_dump(exclude_unset=True)

    if actor.role == UserRole.EMPLOYEE:
        allowed = {"employee_notes", "status"}
        updates = {k: v for k, v in updates.items() if k in allowed}
        if "status" in updates and task.assigned_to_id != actor.id:
            raise PermissionError("Not your task")

    for field, value in updates.items():
        old = getattr(task, field)
        if old != value:
            if field == "status":
                await _add_history(
                    db,
                    task_id=task.id,
                    user_id=actor.id,
                    action_type="UPDATE_STATUS",
                    old_value=str(old.value if hasattr(old, "value") else old),
                    new_value=str(value.value if hasattr(value, "value") else value),
                )
            setattr(task, field, value)

    await db.flush()
    await db.refresh(task)
    return await get_task_by_id(db, task.id)  # type: ignore[return-value]


async def delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)


async def get_task_history(
    db: AsyncSession,
    task_id: int,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[TaskHistory]:
    result = await db.execute(
        select(TaskHistory)
        .where(TaskHistory.task_id == task_id)
        .order_by(TaskHistory.changed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_employee_metrics(db: AsyncSession, user: User) -> dict:
    total_q = select(func.count()).where(Task.assigned_to_id == user.id)
    total = (await db.execute(total_q)).scalar_one()

    done_q = total_q.where(Task.status == TaskStatus.DONE)
    completed = (await db.execute(done_q)).scalar_one()

    rate = (completed / total * 100) if total else 0.0

    avg_q = select(
        func.avg(
            func.extract("epoch", Task.updated_at - Task.created_at) / 3600
        )
    ).where(
        Task.assigned_to_id == user.id,
        Task.status == TaskStatus.DONE,
    )
    avg_hours = (await db.execute(avg_q)).scalar_one()

    return {
        "total_tasks": total,
        "completed_tasks": completed,
        "completion_rate": round(rate, 2),
        "avg_completion_hours": round(float(avg_hours), 2) if avg_hours else None,
    }
