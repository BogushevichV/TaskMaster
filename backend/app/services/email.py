from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, reset_token: str) -> None:
    """Send a password-reset email via SMTP.

    Silently skips when SMTP_HOST is not configured (dev mode).
    Logs a warning on delivery failure instead of propagating the exception,
    so the HTTP response is not affected by mail server issues.
    """
    if not settings.SMTP_HOST:
        logger.info(
            "SMTP not configured — skipping email to %s (dev_token=%s)",
            to_email,
            reset_token,
        )
        return

    text_body = (
        "Вы запросили сброс пароля в TaskMaster.\n\n"
        f"Токен для сброса пароля: {reset_token}\n\n"
        "Используйте его в запросе POST /api/v1/auth/password-reset/confirm "
        "в поле \"token\".\n\n"
        "Токен действителен 1 час.\n\n"
        "Если вы не делали этот запрос — проигнорируйте письмо."
    )
    html_body = f"""\
<!DOCTYPE html>
<html lang="ru">
<body style="font-family: Arial, sans-serif; max-width: 480px; margin: auto;">
  <h2>TaskMaster — сброс пароля</h2>
  <p>Вы запросили сброс пароля.</p>
  <p>Ваш токен:</p>
  <pre style="background:#f4f4f4;padding:12px;border-radius:4px;font-size:14px;">{reset_token}</pre>
  <p>Используйте его в запросе <code>POST /api/v1/auth/password-reset/confirm</code>.</p>
  <p>Токен действителен <strong>1 час</strong>.</p>
  <hr/>
  <p style="color:gray;font-size:12px;">Если вы не делали этот запрос — проигнорируйте письмо.</p>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "TaskMaster — сброс пароля"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, [to_email], msg.as_string())
        logger.info("Password-reset email sent to %s", to_email)
    except Exception:
        logger.warning("Failed to send password-reset email to %s", to_email, exc_info=True)
