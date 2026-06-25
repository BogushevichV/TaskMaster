from __future__ import annotations

from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


def _make_default_icon() -> QIcon:
    """Create a simple colored square icon as fallback when no theme icon exists."""
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor("#2563eb"))
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    """System tray icon with balloon-notification support for TaskMaster."""

    def __init__(self, app: QApplication, main_window=None) -> None:
        icon = QIcon.fromTheme("taskmaster")
        if icon.isNull():
            icon = _make_default_icon()
        super().__init__(icon, parent=app)
        self._main_window = main_window

        menu = QMenu()
        show_action = menu.addAction("Открыть TaskMaster")
        show_action.triggered.connect(self._show_window)
        menu.addSeparator()
        quit_action = menu.addAction("Выйти")
        quit_action.triggered.connect(app.quit)
        self.setContextMenu(menu)

        self.setToolTip("TaskMaster")
        self.activated.connect(self._on_activated)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _show_window(self) -> None:
        if self._main_window is None:
            return
        self._main_window.showNormal()
        self._main_window.activateWindow()
        self._main_window.raise_()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_window(self, main_window) -> None:
        """Attach (or replace) the main window reference after creation."""
        self._main_window = main_window

    def notify(self, title: str, message: str, duration_ms: int = 5000) -> None:
        """Show a balloon/notification if the platform supports it."""
        if self.isVisible() and self.supportsMessages():
            self.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                duration_ms,
            )

    def notify_sync_done(self, synced: int, conflicts: int) -> None:
        """Notify the user about the result of a background sync."""
        if conflicts:
            self.showMessage(
                "TaskMaster — конфликты синхронизации",
                f"Обнаружено конфликтов: {conflicts}. Применено правило LWW (последняя запись).",
                QSystemTrayIcon.MessageIcon.Warning,
                7000,
            )
        elif synced:
            self.notify(
                "TaskMaster — синхронизация",
                f"Синхронизировано изменений: {synced}.",
            )

    def notify_offline(self) -> None:
        """Notify the user that the app switched to offline mode."""
        self.notify(
            "TaskMaster — офлайн",
            "Соединение с сервером потеряно. Изменения будут сохранены локально.",
        )

    def notify_online(self) -> None:
        """Notify the user that connectivity was restored."""
        self.notify(
            "TaskMaster — онлайн",
            "Соединение восстановлено. Запуск фоновой синхронизации...",
        )

    def notify_task_updated(self, task_title: str) -> None:
        """Notify that a specific task was updated (e.g. after remote change)."""
        self.notify(
            "TaskMaster — задача обновлена",
            f"«{task_title}»",
        )
