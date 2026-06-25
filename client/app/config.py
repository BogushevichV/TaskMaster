import os
from pathlib import Path

_FALLBACK = "http://127.0.0.1:8001/api/v1"
_SERVER_FILE = Path(__file__).parent.parent.parent / "server.txt"


def _resolve_api_url() -> str:
    # 1. Переменная окружения — наивысший приоритет
    if url := os.environ.get("TASKMASTER_API_URL"):
        return url.rstrip("/")
    # 2. Файл server.txt рядом с проектом — админ обновляет и рассылает
    if _SERVER_FILE.exists():
        url = _SERVER_FILE.read_text(encoding="utf-8").strip()
        if url:
            return url.rstrip("/")
    # 3. Локальный дефолт
    return _FALLBACK


DEFAULT_API_URL = _resolve_api_url()

STATUS_LABELS = {
    "pending": "К выполнению",
    "in_progress": "В работе",
    "review": "На проверке",
    "done": "Завершена",
}

ROLE_LABELS = {
    "manager": "Руководитель",
    "employee": "Сотрудник",
}
