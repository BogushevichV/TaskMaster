from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
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
        self.setWindowTitle("TaskMaster")
        self.setFixedSize(420, 380)

        # ── Card ──────────────────────────────────────────────
        card = QFrame()
        card.setObjectName("LoginCard")

        title = QLabel("TaskMaster")
        title.setObjectName("AppTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Система управления задачами")
        subtitle.setObjectName("AppSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Логин")
        self.username.setMinimumHeight(40)

        self.password = QLineEdit()
        self.password.setPlaceholderText("Пароль")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setMinimumHeight(40)
        self.password.returnPressed.connect(self._on_login)

        self.login_btn = QPushButton("Войти")
        self.login_btn.setMinimumHeight(42)
        self.login_btn.clicked.connect(self._on_login)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(20)
        card_layout.addWidget(self.username)
        card_layout.addWidget(self.password)
        card_layout.addSpacing(10)
        card_layout.addWidget(self.login_btn)

        # ── Root ──────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.addWidget(card)

    def _on_login(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()

        if not username or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return

        self.login_btn.setEnabled(False)
        try:
            api = ApiClient(DEFAULT_API_URL)
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
