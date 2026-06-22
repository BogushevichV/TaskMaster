from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from client.app.db.base import Base
from client.app.db.config import DB_PATH, SyncStatus
from client.app.db.models import LocalTask, LocalUser


def init_db() -> sessionmaker[Session]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    Base.metadata.create_all(engine)
    _migrate_schema(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _migrate_schema(engine) -> None:
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if insp.has_table("tasks"):
        cols = {c["name"] for c in insp.get_columns("tasks")}
        if "is_deleted" not in cols:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE tasks ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
                )


def cache_tasks(session: Session, tasks: list[dict]) -> None:
    for task in tasks:
        row = session.get(LocalTask, task["id"])
        if row and row.sync_status == SyncStatus.PENDING:
            continue

        assignee = task.get("assignee") or {}
        deadline = task.get("deadline")
        deadline_dt = None
        if deadline:
            try:
                deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            except ValueError:
                pass

        row = session.get(LocalTask, task["id"])
        if row is None:
            row = LocalTask(id=task["id"])
            session.add(row)

        row.title = task["title"]
        row.description = task.get("description")
        row.status = task.get("status", "pending")
        row.deadline = deadline_dt
        row.assigned_to_id = task["assigned_to_id"]
        row.assignee_name = assignee.get("full_name")
        row.employee_notes = task.get("employee_notes")
        row.sync_status = SyncStatus.SYNCED
        row.is_deleted = False

    session.commit()


def load_cached_tasks(session: Session) -> list[dict]:
    rows = session.scalars(
        select(LocalTask)
        .where(LocalTask.is_deleted.is_(False))
        .order_by(LocalTask.deadline)
    ).all()
    result = []
    for row in rows:
        result.append(
            {
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "status": row.status,
                "deadline": row.deadline.isoformat() if row.deadline else None,
                "assigned_to_id": row.assigned_to_id,
                "employee_notes": row.employee_notes,
                "assignee": {"full_name": row.assignee_name or "—"},
                "_offline": row.sync_status != SyncStatus.SYNCED,
                "sync_status": row.sync_status.value,
            }
        )
    return result


def pending_count(session: Session) -> int:
    from sqlalchemy import func

    return session.scalar(
        select(func.count())
        .select_from(LocalTask)
        .where(LocalTask.sync_status == SyncStatus.PENDING)
    ) or 0
