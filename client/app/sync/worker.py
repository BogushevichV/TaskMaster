from PySide6.QtCore import QThread, Signal

from client.app.db.sync_ops import SyncResult
from client.app.session import Session
from client.app.sync.engine import run_sync


class SyncWorker(QThread):
    finished = Signal(object)

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session

    def run(self) -> None:
        db = self.session.db_factory()
        try:
            result = run_sync(self.session.api, db)
        finally:
            db.close()
        self.finished.emit(result)
