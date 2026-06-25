import enum
from pathlib import Path

DB_PATH = Path.home() / ".taskmaster" / "local.db"


class SyncStatus(str, enum.Enum):
    PENDING = "pending"
    SYNCED = "synced"
    ERROR = "error"
