from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
)

from client.app.api.client import ApiError
from client.app.config import STATUS_LABELS
from client.app.services.task_service import TaskService
from client.app.session import Session


class TaskDialog(QDialog):
    def __init__(
        self,
        session: Session,
        *,
        task: dict | None = None,
        employees: list[dict] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.task_service = TaskService(session)
        self.task = task
        self.is_edit = task is not None
        self.is_manager = session.is_manager
        self._saved_offline = False

        title = "Редактировать задачу" if self.is_edit else "Новая задача"
        self.setWindowTitle(title)
        self.setMinimumWidth(520)

        self.title_edit = QLineEdit()
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(100)
        self.deadline_edit = QDateEdit()
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat("dd.MM.yyyy")
        self.deadline_edit.setSpecialValueText("Не задан")
        self.deadline_edit.setMinimumDate(QDate(2000, 1, 1))
        self.deadline_edit.setDate(QDate.currentDate())

        self.assignee_combo = QComboBox()
        self.status_combo = QComboBox()
        for value, label in STATUS_LABELS.items():
            if not self.is_manager and value == "done":
                continue
            self.status_combo.addItem(label, value)
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Заметки сотрудника")

        form = QFormLayout(self)
        form.setSpacing(10)
        form.setContentsMargins(20, 20, 20, 20)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.addRow("Название:", self.title_edit)

        if self.is_manager or not self.is_edit:
            form.addRow("Описание:", self.description_edit)
            form.addRow("Дедлайн:", self.deadline_edit)
            if self.is_manager:
                form.addRow("Ответственный:", self.assignee_combo)
                self._fill_employees(employees or [])

        if self.is_edit:
            form.addRow("Статус:", self.status_combo)
            form.addRow("Заметки:", self.notes_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        if self.is_edit and task:
            self._load_task(task)
        elif not self.is_manager and not self.is_edit:
            self.reject()

    def _fill_employees(self, employees: list[dict]) -> None:
        self.assignee_combo.clear()
        for emp in employees:
            self.assignee_combo.addItem(emp["full_name"], emp["id"])

    def _load_task(self, task: dict) -> None:
        self.title_edit.setText(task.get("title", ""))
        if self.is_manager:
            self.description_edit.setPlainText(task.get("description") or "")
            deadline = task.get("deadline")
            if deadline:
                dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                self.deadline_edit.setDate(QDate(dt.year, dt.month, dt.day))
            assignee_id = task.get("assigned_to_id")
            idx = self.assignee_combo.findData(assignee_id)
            if idx >= 0:
                self.assignee_combo.setCurrentIndex(idx)
        status = task.get("status", "pending")
        idx = self.status_combo.findData(status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)
        self.notes_edit.setPlainText(task.get("employee_notes") or "")

        if not self.is_manager:
            self.title_edit.setReadOnly(True)

    def _on_save(self) -> None:
        title = self.title_edit.text().strip()
        if not title and self.is_manager:
            QMessageBox.warning(self, "Ошибка", "Укажите название задачи")
            return

        try:
            if self.is_edit:
                self._save_edit()
            else:
                self._save_create()
            if self._saved_offline:
                QMessageBox.information(
                    self,
                    "Офлайн",
                    "Изменения сохранены локально и будут синхронизированы при появлении сети.",
                )
            self.accept()
        except ApiError as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))

    def _save_create(self) -> None:
        title = self.title_edit.text().strip()
        deadline = self._deadline_iso()
        assignee_id = self.assignee_combo.currentData()
        if assignee_id is None:
            raise ApiError("Выберите ответственного сотрудника")
        assignee_name = self.assignee_combo.currentText()
        payload = {
            "title": title,
            "description": self.description_edit.toPlainText().strip() or None,
            "deadline": deadline,
            "assigned_to_id": assignee_id,
        }
        result = self.task_service.create_task(payload, assignee_name=assignee_name)
        self._saved_offline = bool(result and result.get("_offline"))

    def _save_edit(self) -> None:
        assert self.task is not None
        task_id = self.task["id"]
        if self.is_manager:
            payload = {
                "title": self.title_edit.text().strip(),
                "description": self.description_edit.toPlainText().strip() or None,
                "deadline": self._deadline_iso(),
                "assigned_to_id": self.assignee_combo.currentData(),
                "status": self.status_combo.currentData(),
            }
        else:
            payload = {
                "status": self.status_combo.currentData(),
                "employee_notes": self.notes_edit.toPlainText().strip() or None,
            }
        result = self.task_service.update_task(task_id, payload)
        self._saved_offline = bool(result and result.get("_offline"))

    def _deadline_iso(self) -> str | None:
        qd = self.deadline_edit.date()
        dt = datetime(qd.year(), qd.month(), qd.day(), 23, 59, 59)
        return dt.isoformat()
