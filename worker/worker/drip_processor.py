"""
Drip Email Processor — processa enrollments com next_send_at <= now.
Envia emails via SMTP/SES e avanca o enrollment para o proximo step.
"""
import logging
import os
import smtplib
import threading
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy import select, text

logger = logging.getLogger("worker.drip_processor")

# Email config (mesmas variaveis do API)
AWS_SES_REGION = os.getenv("AWS_SES_REGION", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Brand Brain")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@brandbrain.com.br")


def poll_drip_jobs(session) -> int:
    """Busca drip_enrollments com next_send_at <= now e status=active. Processa cada um."""
    now = datetime.utcnow()

    rows = session.execute(
        text("""
            SELECT e.id, e.campaign_id, e.user_id, e.org_id, e.current_step
            FROM drip_enrollments e
            WHERE e.status = 'active'
              AND e.next_send_at IS NOT NULL
              AND e.next_send_at <= :now
            ORDER BY e.next_send_at ASC
            LIMIT 20
        """),
        {"now": now},
    ).fetchall()

    if not rows:
        return 0

    processed = 0
    for row in rows:
        try:
            _process_enrollment(session, row)
            processed += 1
        except Exception:
            logger.exception("Error processing drip enrollment %s", row[0])

    return processed


def _process_enrollment(session, row) -> None:
    enrollment_id, campaign_id, user_id, org_id, current_step = row

    # Buscar steps da campanha
    steps = session.execute(
        text("""
            SELECT id, step_order, delay_hours, subject, body_template
            FROM drip_steps
            WHERE campaign_id = :cid
            ORDER BY step_order ASC
        """),
        {"cid": campaign_id},
    ).fetchall()

    if current_step >= len(steps):
        # Completar enrollment
        session.execute(
            text("""
                UPDATE drip_enrollments
                SET status = 'completed', completed_at = :now, next_send_at = NULL
                WHERE id = :eid
            """),
            {"now": datetime.utcnow(), "eid": enrollment_id},
        )
        session.commit()
        logger.info("Enrollment %s completed (all steps sent)", enrollment_id)
        return

    step = steps[current_step]
    _step_id, _step_order, delay_hours, subject_tpl, body_tpl = step

    # Buscar dados do usuario
    user_row = session.execute(
        text("SELECT email, name FROM users WHERE id = :uid"),
        {"uid": user_id},
    ).first()

    if not user_row:
        logger.warning("User %s not found, cancelling enrollment %s", user_id, enrollment_id)
        session.execute(
            text("UPDATE drip_enrollments SET status = 'cancelled' WHERE id = :eid"),
            {"eid": enrollment_id},
        )
        session.commit()
        return

    user_email, user_name = user_row
    name = user_name or user_email

    # Buscar nome da org
    org_name = ""
    if org_id:
        org_row = session.execute(
            text("SELECT name FROM organizations WHERE id = :oid"),
            {"oid": org_id},
        ).first()
        if org_row:
            org_name = org_row[0] or ""

    # Renderizar template
    replacements = {
        "name": name,
        "org_name": org_name,
        "email": user_email,
        "upgrade_url": "https://app.brandbrain.com.br/billing",
    }

    try:
        subject = subject_tpl.format(**replacements)
        body_content = body_tpl.format(**replacements)
    except (KeyError, ValueError) as e:
        logger.warning("Template rendering error for enrollment %s: %s", enrollment_id, e)
        subject = subject_tpl
        body_content = body_tpl

    html = _base_template(body_content)

    # Enviar email
    _dispatch_email(user_email, subject, html)
    logger.info("Sent drip step %d to %s (campaign=%s)", current_step, user_email, campaign_id)

    # Avancar enrollment
    next_step = current_step + 1
    if next_step >= len(steps):
        session.execute(
            text("""
                UPDATE drip_enrollments
                SET current_step = :ns, status = 'completed', completed_at = :now, next_send_at = NULL
                WHERE id = :eid
            """),
            {"ns": next_step, "now": datetime.utcnow(), "eid": enrollment_id},
        )
    else:
        next_delay = steps[next_step][2]  # delay_hours
        next_send = datetime.utcnow() + timedelta(hours=next_delay)
        session.execute(
            text("""
                UPDATE drip_enrollments
                SET current_step = :ns, next_send_at = :nsa
                WHERE id = :eid
            """),
            {"ns": next_step, "nsa": next_send, "eid": enrollment_id},
        )

    session.commit()


# ---------------------------------------------------------------------------
# Email dispatch (replica simplificada do email_service do API)
# ---------------------------------------------------------------------------

def _dispatch_email(to: str, subject: str, body: str) -> None:
    if AWS_SES_REGION:
        thread = threading.Thread(target=_send_ses, args=(to, subject, body), daemon=True)
        thread.start()
    elif SMTP_HOST:
        thread = threading.Thread(target=_send_smtp, args=(to, subject, body), daemon=True)
        thread.start()
    else:
        logger.info("[EMAIL SIMULADO] Para: %s | Assunto: %s", to, subject)


def _send_ses(to: str, subject: str, body: str) -> None:
    try:
        import boto3
        client = boto3.client("ses", region_name=AWS_SES_REGION)
        client.send_email(
            Source=f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>",
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": body, "Charset": "UTF-8"}},
            },
        )
        logger.info("[SES] Email enviado para %s: %s", to, subject)
    except Exception:
        logger.exception("[SES] Erro ao enviar email para %s", to)


def _send_smtp(to: str, subject: str, body: str) -> None:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to
        msg.attach(MIMEText(body, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, to, msg.as_string())
        logger.info("[SMTP] Email enviado para %s: %s", to, subject)
    except Exception:
        logger.exception("[SMTP] Erro ao enviar email para %s", to)


def _base_template(content: str) -> str:
    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f4f4f5; margin: 0; padding: 32px; color: #18181b; }}
  .card {{ background: #ffffff; border-radius: 12px; padding: 40px;
           max-width: 520px; margin: 0 auto; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .logo {{ font-size: 22px; font-weight: 700; color: #6d28d9; margin-bottom: 24px; }}
  .btn {{ display: inline-block; background: #6d28d9; color: #ffffff !important;
          padding: 12px 28px; border-radius: 8px; text-decoration: none;
          font-weight: 600; font-size: 15px; margin: 20px 0; }}
  .footer {{ margin-top: 32px; font-size: 12px; color: #71717a; }}
  p {{ line-height: 1.6; margin: 8px 0; }}
</style></head><body>
<div class="card">
  <div class="logo">Brand Brain</div>
  {content}
  <div class="footer">
    Voce recebeu este email porque esta inscrito no Brand Brain.<br>
    &copy; 2026 Brand Brain — contato@brandbrain.com.br
  </div>
</div></body></html>"""
