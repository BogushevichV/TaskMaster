from __future__ import annotations

import json
from datetime import datetime

from client.app.api.client import ApiClient, ApiError
from client.app.db.config import SyncStatus
from client.app.db.sync_ops import (
    SyncResult,
    apply_server_task,
    get_pending_queue,
    mark_queue_item,
    remove_local_task,
    replace_local_task_id,
)
from client.app.db.models import LocalTask


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def run_sync(api: ApiClient, session) -> SyncResult:
    result = SyncResult()
    items = get_pending_queue(session)

    for item in items:
        try:
            if item.action == "CREATE":
                payload = json.loads(item.payload or "{}")
                server_task = api.create_task(payload)
                replace_local_task_id(session, item.task_id, server_task)
                mark_queue_item(session, item, SyncStatus.SYNCED)
                result.synced += 1

            elif item.action == "UPDATE":
                payload = json.loads(item.payload or "{}")
                local = session.get(LocalTask, item.task_id)
                if local is None:
                    mark_queue_item(session, item, SyncStatus.SYNCED)
                    continue

                if item.task_id > 0:
                    server_task = api.get_task(item.task_id)
                    server_ts = _parse_dt(server_task.get("updated_at"))
                    local_ts = local.updated_at
                    if server_ts and local_ts and server_ts > local_ts:
                        apply_server_task(session, server_task)
                        mark_queue_item(session, item, SyncStatus.SYNCED)
                        local.sync_status = SyncStatus.SYNCED
                        session.commit()
                        result.conflicts.append(
                            f"Задача «{server_task['title']}»: применена серверная версия (конфликт)"
                        )
                        continue

                api.update_task(item.task_id, payload)
                if item.task_id > 0:
                    server_task = api.get_task(item.task_id)
                    apply_server_task(session, server_task)
                else:
                    local.sync_status = SyncStatus.SYNCED
                    session.commit()
                mark_queue_item(session, item, SyncStatus.SYNCED)
                result.synced += 1

            elif item.action == "DELETE":
                if item.task_id > 0:
                    api.delete_task(item.task_id)
                remove_local_task(session, item.task_id)
                mark_queue_item(session, item, SyncStatus.SYNCED)
                result.synced += 1

        except (ApiError, Exception):
            mark_queue_item(session, item, SyncStatus.ERROR)
            result.errors += 1

    return result
