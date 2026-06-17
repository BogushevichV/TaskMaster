import sys

from PySide6.QtWidgets import QApplication

from client.app.db import init_db
from client.app.ui.login_window import LoginWindow
from client.app.ui.main_window import MainWindow
from client.app.ui.tray import TrayIcon


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("TaskMaster")
    app.setQuitOnLastWindowClosed(False)

    tray = TrayIcon(app)
    tray.show()

    db_factory = init_db()
    login = LoginWindow(db_factory)
    login.show()

    def on_logged_in(session) -> None:
        login.close()
        window = MainWindow(session)
        tray.set_window(window)
        window.show()

    login.logged_in.connect(on_logged_in)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
