import logging
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    """Send email in a background thread. If SMTP_HOST is empty, log and skip."""
    if not settings.SMTP_HOST:
        logger.info(f"Email simulado para {to}: {subject}")
        return

    thread = threading.Thread(target=_send, args=(to, subject, body), daemon=True)
    thread.start()


def _send(to: str, subject: str, body: str) -> None:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to, msg.as_string())
        logger.info(f"Email enviado para {to}: {subject}")
    except Exception:
        logger.exception(f"Erro ao enviar email para {to}")
