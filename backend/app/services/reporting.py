from __future__ import annotations

from datetime import datetime

from backend.app.models.enums import TaskStatus
from backend.app.models.task import Task


def build_task_report_stats(
    items: list[Task],
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    now = now or datetime.now(tz=items[0].deadline.tzinfo if items and items[0].deadline else None)
    created = len(items)
    on_time = sum(
        1
        for t in items
        if t.status == TaskStatus.DONE
        and t.deadline
        and t.updated_at <= t.deadline
    )
    overdue = sum(
        1
        for t in items
        if t.deadline and t.deadline < now and t.status != TaskStatus.DONE
    )
    return {
        "created": created,
        "completed_on_time": on_time,
        "overdue": overdue,
    }
