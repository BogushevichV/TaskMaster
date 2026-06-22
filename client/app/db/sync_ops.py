import json
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from client.app.db.config import SyncStatus
from client.app.db.models import LocalTask, SyncQueueItem


@dataclass
class SyncResult:
    synced: int = 0
    errors: int = 0
    conflicts: list[str] = field(default_factory=list)


def _next_local_id(session: Session) -> int:
    minimum = session.scalar(select(func.min(LocalTask.id))) or 0
    if minimum >= 0:
        return -1
    return minimum - 1


def _task_to_dict(row: LocalTask) -> dict:
    return {
        "id": row.id,
        "title": row.title,
        "description": row.description,
        "status": row.status,
        "deadline": row.deadline.isoformat() if row.deadline else None,
        "assigned_to_id": row.assigned_to_id,
        "employee_notes": row.employee_notes,
        "assignee": {"full_name": row.assignee_name or "—"},
        "sync_status": row.sync_status.value,
        "_offline": row.sync_status != SyncStatus.SYNCED,
    }


def queue_offline_create(session: Session, payload: dict) -> int:
    assignee_name = payload.pop("_assignee_name", None)
    task_id = _next_local_id(session)
    deadline = payload.get("deadline")
    deadline_dt = None
    if deadline:
        deadline_dt = datetime.fromisoformat(deadline)

    session.add(
        LocalTask(
            id=task_id,
            title=payload["title"],
            description=payload.get("description"),
            status="pending",
            deadline=deadline_dt,
            assigned_to_id=payload["assigned_to_id"],
            assignee_name=assignee_name,
            sync_status=SyncStatus.PENDING,
            updated_at=datetime.now(),
        )
    )
    session.add(
        SyncQueueItem(
            task_id=task_id,
            action="CREATE",
            payload=json.dumps(payload, ensure_ascii=False),
            sync_status=SyncStatus.PENDING,
        )
    )
    session.commit()
    return task_id


def queue_offline_update(session: Session, task_id: int, payload: dict) -> None:
    row = session.get(LocalTask, task_id)
    if row is None:
        return

    if "title" in payload:
        row.title = payload["title"]
    if "description" in payload:
        row.description = payload["description"]
    if "deadline" in payload:
        dl = payload["deadline"]
        row.deadline = datetime.fromisoformat(dl) if dl else None
    if "assigned_to_id" in payload:
        row.assigned_to_id = payload["assigned_to_id"]
    if "status" in payload:
        row.status = payload["status"]
    if "employee_notes" in payload:
        row.employee_notes = payload["employee_notes"]
    row.sync_status = SyncStatus.PENDING
    row.updated_at = datetime.now()

    session.add(
        SyncQueueItem(
            task_id=task_id,
            action="UPDATE",
            payload=json.dumps(payload, ensure_ascii=False),
            sync_status=SyncStatus.PENDING,
        )
    )
    session.commit()


def queue_offline_delete(session: Session, task_id: int) -> None:
    row = session.get(LocalTask, task_id)
    if row is None:
        return

    if task_id < 0:
        session.execute(delete(SyncQueueItem).where(SyncQueueItem.task_id == task_id))
        session.delete(row)
        session.commit()
        return

    row.sync_status = SyncStatus.PENDING
    row.is_deleted = True
    row.updated_at = datetime.now()
    session.add(
        SyncQueueItem(
            task_id=task_id,
            action="DELETE",
            payload="{}",
            sync_status=SyncStatus.PENDING,
        )
    )
    session.commit()


def get_pending_queue(session: Session) -> list[SyncQueueItem]:
    return list(
        session.scalars(
            select(SyncQueueItem)
            .where(SyncQueueItem.sync_status == SyncStatus.PENDING)
            .order_by(SyncQueueItem.id)
        ).all()
    )


def mark_queue_item(session: Session, item: SyncQueueItem, status: SyncStatus) -> None:
    item.sync_status = status
    session.commit()


def replace_local_task_id(session: Session, old_id: int, server_task: dict) -> None:
    old = session.get(LocalTask, old_id)
    if old:
        session.delete(old)

    assignee = server_task.get("assignee") or {}
    deadline = server_task.get("deadline")
    deadline_dt = None
    if deadline:
        try:
            deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except ValueError:
            pass

    new_id = server_task["id"]
    session.add(
        LocalTask(
            id=new_id,
            title=server_task["title"],
            description=server_task.get("description"),
            status=server_task.get("status", "pending"),
            deadline=deadline_dt,
            assigned_to_id=server_task["assigned_to_id"],
            assignee_name=assignee.get("full_name"),
            employee_notes=server_task.get("employee_notes"),
            sync_status=SyncStatus.SYNCED,
            is_deleted=False,
            updated_at=datetime.now(),
        )
    )
    _remap_queue_task_id(session, old_id, new_id)
    session.commit()


def _remap_queue_task_id(session: Session, old_id: int, new_id: int) -> None:
    pending = session.scalars(
        select(SyncQueueItem).where(
            SyncQueueItem.task_id == old_id,
            SyncQueueItem.sync_status == SyncStatus.PENDING,
        )
    ).all()
    for item in pending:
        item.task_id = new_id


def apply_server_task(session: Session, server_task: dict) -> None:
    assignee = server_task.get("assignee") or {}
    deadline = server_task.get("deadline")
    deadline_dt = None
    if deadline:
        try:
            deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except ValueError:
            pass

    row = session.get(LocalTask, server_task["id"])
    if row is None:
        row = LocalTask(id=server_task["id"])
        session.add(row)

    row.title = server_task["title"]
    row.description = server_task.get("description")
    row.status = server_task.get("status", "pending")
    row.deadline = deadline_dt
    row.assigned_to_id = server_task["assigned_to_id"]
    row.assignee_name = assignee.get("full_name")
    row.employee_notes = server_task.get("employee_notes")
    row.sync_status = SyncStatus.SYNCED
    row.is_deleted = False
    session.commit()


def remove_local_task(session: Session, task_id: int) -> None:
    row = session.get(LocalTask, task_id)
    if row:
        session.delete(row)
    session.commit()
