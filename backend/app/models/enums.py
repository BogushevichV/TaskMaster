import enum


class UserRole(str, enum.Enum):
    MANAGER = "manager"
    EMPLOYEE = "employee"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class SyncStatus(str, enum.Enum):
    PENDING = "pending"
    SYNCED = "synced"
    ERROR = "error"
