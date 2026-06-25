from __future__ import annotations

from datetime import datetime

import httpx
from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from client.app.api.client import ApiError
from client.app.config import ROLE_LABELS, STATUS_LABELS
from client.app.db import cache_tasks, load_cached_tasks, pending_count
from client.app.db.sync_ops import SyncResult
from client.app.services.task_service import TaskService
from client.app.session import Session
from client.app.sync.network import is_server_online
from client.app.sync.worker import SyncWorker
from client.app.ui.task_dialog import TaskDialog


class MainWindow(QMainWindow):
    SYNC_INTERVAL_MS = 15_000

    def __init__(self, session: Session) -> None:
        super().__init__()
        self.session = session
        self.task_service = TaskService(session)
        self._tasks: list[dict] = []
        self._employees: list[dict] = []
        self._sync_worker: SyncWorker | None = None
        self._online = True

        self.setWindowTitle("TaskMaster")
        self.setMinimumSize(1024, 640)

        role = ROLE_LABELS.get(session.user.get("role", ""), "")
        self._online_label = QLabel("Онлайн")
        self.statusBar().addPermanentWidget(self._online_label)
        self.statusBar().showMessage(f"{session.display_name} ({role})")

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        root.addLayout(self._build_filters())
        root.addLayout(self._build_toolbar())
        root.addWidget(self._build_table())

        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._on_sync_timer)
        self._sync_timer.start(self.SYNC_INTERVAL_MS)

        self._load_employees()
        self.refresh_tasks()
        self._update_online_status()

    def _build_filters(self) -> QHBoxLayout:
        layout = QHBoxLayout()

        self.status_filter = QComboBox()
        self.status_filter.addItem("Все статусы", "")
        for value, label in STATUS_LABELS.items():
            self.status_filter.addItem(label, value)

        self.assignee_filter = QComboBox()
        self.assignee_filter.addItem("Все сотрудники", None)

        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setDate(QDate.currentDate().addMonths(-1))

        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setDate(QDate.currentDate().addMonths(1))

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по названию...")

        apply_btn = QPushButton("Применить")
        apply_btn.clicked.connect(self.refresh_tasks)
        self.search_edit.returnPressed.connect(self.refresh_tasks)

        layout.addWidget(QLabel("Статус:"))
        layout.addWidget(self.status_filter)
        if self.session.is_manager:
            layout.addWidget(QLabel("Ответственный:"))
            layout.addWidget(self.assignee_filter)
        layout.addWidget(QLabel("С:"))
        layout.addWidget(self.date_from)
        layout.addWidget(QLabel("По:"))
        layout.addWidget(self.date_to)
        layout.addWidget(self.search_edit, stretch=1)
        layout.addWidget(apply_btn)
        return layout

    def _build_toolbar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(8)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.clicked.connect(self.refresh_tasks)

        sync_btn = QPushButton("Синхронизировать")
        sync_btn.setObjectName("SecondaryBtn")
        sync_btn.clicked.connect(self._start_sync)

        layout.addWidget(refresh_btn)
        layout.addWidget(sync_btn)

        if self.session.is_manager:
            new_btn = QPushButton("+ Новая задача")
            new_btn.clicked.connect(self._on_new_task)

            edit_btn = QPushButton("Редактировать")
            edit_btn.setObjectName("SecondaryBtn")
            edit_btn.clicked.connect(self._on_edit_task)

            delete_btn = QPushButton("Удалить")
            delete_btn.setObjectName("DangerBtn")
            delete_btn.clicked.connect(self._on_delete_task)

            layout.addWidget(new_btn)
            layout.addWidget(edit_btn)
            layout.addWidget(delete_btn)
        else:
            edit_btn = QPushButton("Изменить статус / заметки")
            edit_btn.setObjectName("SecondaryBtn")
            edit_btn.clicked.connect(self._on_edit_task)
            layout.addWidget(edit_btn)

        layout.addStretch()
        return layout

    def _build_table(self) -> QTableWidget:
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Название", "Статус", "Дедлайн", "Ответственный", "Sync"]
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 130)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(4, 80)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self._on_edit_task)
        return self.table

    def _update_online_status(self) -> None:
        online = is_server_online(self.session.api)
        self._online = online
        self._online_label.setText("Онлайн" if online else "Офлайн")
        self._online_label.setStyleSheet(
            "color: green;" if online else "color: red; font-weight: bold;"
        )

    def _on_sync_timer(self) -> None:
        was_offline = not self._online
        self._update_online_status()
        if self._online:
            db = self.session.db_factory()
            try:
                has_pending = pending_count(db) > 0
            finally:
                db.close()
            if was_offline or has_pending:
                self._start_sync()

    def _start_sync(self) -> None:
        if not is_server_online(self.session.api):
            self._update_online_status()
            return
        if self._sync_worker and self._sync_worker.isRunning():
            return
        self._sync_worker = SyncWorker(self.session)
        self._sync_worker.finished.connect(self._on_sync_finished)
        self._sync_worker.start()

    def _on_sync_finished(self, result: SyncResult) -> None:
        if result.conflicts:
            QMessageBox.warning(
                self,
                "Конфликт синхронизации",
                "Применено правило «последняя запись побеждает»:\n\n"
                + "\n".join(result.conflicts),
            )
        if result.synced or result.conflicts:
            self.refresh_tasks()
        elif result.errors:
            self.statusBar().showMessage("Ошибка синхронизации части изменений", 5000)

    def _load_employees(self) -> None:
        if not self.session.is_manager:
            return
        try:
            self._employees = self.session.api.list_users(role="employee")
            self.assignee_filter.clear()
            self.assignee_filter.addItem("Все сотрудники", None)
            for emp in self._employees:
                self.assignee_filter.addItem(emp["full_name"], emp["id"])
        except (ApiError, httpx.RequestError, OSError) as exc:
            QMessageBox.warning(
                self, "Предупреждение", f"Не удалось загрузить сотрудников:\n{exc}"
            )

    def refresh_tasks(self) -> None:
        db = self.session.db_factory()
        try:
            status = self.status_filter.currentData() or None
            assigned = (
                self.assignee_filter.currentData()
                if self.session.is_manager
                else None
            )
            search = self.search_edit.text().strip() or None

            d_from = self.date_from.date()
            d_to = self.date_to.date()
            date_from = datetime(d_from.year(), d_from.month(), d_from.day())
            date_to = datetime(d_to.year(), d_to.month(), d_to.day(), 23, 59, 59)

            data = self.session.api.list_tasks(
                status=status,
                assigned_to_id=assigned,
                date_from=date_from,
                date_to=date_to,
                search=search,
            )
            self._tasks = data.get("items", [])
            cache_tasks(db, self._tasks)
            pending = pending_count(db)
            self._fill_table()
            self.statusBar().showMessage(
                f"{self.session.display_name} — задач: {data.get('total', 0)}"
                + (f" | ожидают sync: {pending}" if pending else ""),
            )
            self._update_online_status()
        except (ApiError, httpx.RequestError, OSError):
            self._tasks = load_cached_tasks(db)
            pending = pending_count(db)
            self._fill_table()
            self._update_online_status()
            self.statusBar().showMessage(
                f"Офлайн — локальный кэш ({len(self._tasks)} задач)"
                + (f" | ожидают sync: {pending}" if pending else ""),
            )
        finally:
            db.close()

    def _fill_table(self) -> None:
        self.table.setRowCount(len(self._tasks))
        for row, task in enumerate(self._tasks):
            title = task.get("title", "")
            if task.get("_offline") or task.get("sync_status") == "pending":
                title = f"⏳ {title}"
            title_item = QTableWidgetItem(title)
            title_item.setData(Qt.ItemDataRole.UserRole, task.get("id"))
            status = STATUS_LABELS.get(task.get("status", ""), task.get("status", ""))
            deadline = task.get("deadline")
            deadline_str = ""
            if deadline:
                try:
                    dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                    deadline_str = dt.strftime("%d.%m.%Y %H:%M")
                except ValueError:
                    deadline_str = str(deadline)
            assignee = task.get("assignee") or {}
            assignee_name = assignee.get("full_name", "—")
            sync_label = task.get("sync_status", "synced")

            self.table.setItem(row, 0, title_item)
            self.table.setItem(row, 1, QTableWidgetItem(status))
            self.table.setItem(row, 2, QTableWidgetItem(deadline_str))
            self.table.setItem(row, 3, QTableWidgetItem(assignee_name))
            self.table.setItem(row, 4, QTableWidgetItem(sync_label))

    def _selected_task(self) -> dict | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._tasks):
            QMessageBox.information(self, "Выбор", "Выберите задачу в таблице")
            return None
        return self._tasks[row]

    def _on_new_task(self) -> None:
        dialog = TaskDialog(
            self.session,
            employees=self._employees,
            parent=self,
        )
        if dialog.exec():
            self.refresh_tasks()
            if not self._online:
                self._start_sync()

    def _on_edit_task(self) -> None:
        task = self._selected_task()
        if not task:
            return
        dialog = TaskDialog(
            self.session,
            task=task,
            employees=self._employees,
            parent=self,
        )
        if dialog.exec():
            self.refresh_tasks()

    def _on_delete_task(self) -> None:
        task = self._selected_task()
        if not task:
            return
        answer = QMessageBox.question(
            self,
            "Удаление",
            f"Удалить задачу «{task.get('title')}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.task_service.delete_task(task["id"])
            if self._online:
                self.refresh_tasks()
            else:
                db = self.session.db_factory()
                try:
                    self._tasks = load_cached_tasks(db)
                finally:
                    db.close()
                self._fill_table()
                QMessageBox.information(
                    self, "Офлайн", "Удаление будет синхронизировано позже."
                )
        except ApiError as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))

    def closeEvent(self, event) -> None:
        self._sync_timer.stop()
        if self._sync_worker and self._sync_worker.isRunning():
            self._sync_worker.wait(3000)
        self.session.api.close()
        super().closeEvent(event)
