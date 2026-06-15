from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import TaskStatus
from backend.app.schemas.user import UserRead


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    deadline: datetime | None = None
    assigned_to_id: int


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    deadline: datetime | None = None
    assigned_to_id: int | None = None
    status: TaskStatus | None = None
    employee_notes: str | None = None


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: TaskStatus
    employee_notes: str | None
    created_by_id: int
    created_at: datetime
    updated_at: datetime
    assignee: UserRead | None = None
    creator: UserRead | None = None


class TaskHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    user_id: int
    action_type: str
    old_value: str | None
    new_value: str | None
    changed_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskRead]
    total: int
    page: int
    page_size: int
