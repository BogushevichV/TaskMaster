from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from client.app.api.client import ApiClient, ApiError
from client.app.config import DEFAULT_API_URL
from client.app.session import Session


class LoginWindow(QWidget):
    logged_in = Signal(object)

    def __init__(self, db_factory) -> None:
        super().__init__()
        self._db_factory = db_factory
        self.setWindowTitle("TaskMaster — Вход")
        self.setMinimumWidth(400)

        self.api_url = QLineEdit(DEFAULT_API_URL)
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.addRow("API URL:", self.api_url)
        form.addRow("Логин:", self.username)
        form.addRow("Пароль:", self.password)

        self.login_btn = QPushButton("Войти")
        self.login_btn.clicked.connect(self._on_login)
        self.password.returnPressed.connect(self._on_login)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("TaskMaster"))
        layout.addLayout(form)
        layout.addWidget(self.login_btn)

    def _on_login(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        api_url = self.api_url.text().strip().rstrip("/")

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return

        self.login_btn.setEnabled(False)
        try:
            api = ApiClient(api_url)
            api.login(username, password)
            user = api.get_me()
            session = Session(api=api, user=user, db_factory=self._db_factory)
            self.logged_in.emit(session)
        except ApiError as exc:
            QMessageBox.critical(self, "Ошибка входа", str(exc))
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Ошибка подключения",
                f"Не удалось подключиться к серверу:\n{exc}",
            )
        finally:
            self.login_btn.setEnabled(True)
