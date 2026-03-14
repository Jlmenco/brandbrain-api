import logging
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dispatch principal
# ---------------------------------------------------------------------------

def send_email(to: str, subject: str, body: str) -> None:
    """Envia email em background. Usa SES boto3 se AWS_SES_REGION estiver configurado,
    senao tenta SMTP. Se nenhum estiver configurado, loga e pula."""
    if settings.AWS_SES_REGION:
        thread = threading.Thread(target=_send_ses, args=(to, subject, body), daemon=True)
        thread.start()
    elif settings.SMTP_HOST:
        thread = threading.Thread(target=_send_smtp, args=(to, subject, body), daemon=True)
        thread.start()
    else:
        logger.info(f"[EMAIL SIMULADO] Para: {to} | Assunto: {subject}")


# ---------------------------------------------------------------------------
# Backend SES boto3
# ---------------------------------------------------------------------------

def _send_ses(to: str, subject: str, body: str) -> None:
    try:
        import boto3
        client = boto3.client(
            "ses",
            region_name=settings.AWS_SES_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )
        client.send_email(
            Source=f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>",
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": body, "Charset": "UTF-8"}},
            },
        )
        logger.info(f"[SES] Email enviado para {to}: {subject}")
    except Exception:
        logger.exception(f"[SES] Erro ao enviar email para {to}")


# ---------------------------------------------------------------------------
# Backend SMTP (fallback)
# ---------------------------------------------------------------------------

def _send_smtp(to: str, subject: str, body: str) -> None:
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
        logger.info(f"[SMTP] Email enviado para {to}: {subject}")
    except Exception:
        logger.exception(f"[SMTP] Erro ao enviar email para {to}")


# ---------------------------------------------------------------------------
# Templates HTML
# ---------------------------------------------------------------------------

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
    Se voce nao solicitou isso, ignore este email.<br>
    &copy; 2026 Brand Brain — contato@brandbrain.com.br
  </div>
</div></body></html>"""


def send_reset_password_email(to: str, name: str, reset_url: str) -> None:
    body = _base_template(f"""
      <p>Ola, <strong>{name}</strong>!</p>
      <p>Recebemos uma solicitacao para redefinir a senha da sua conta Brand Brain.</p>
      <p>Clique no botao abaixo para criar uma nova senha:</p>
      <a class="btn" href="{reset_url}">Redefinir minha senha</a>
      <p>Este link expira em <strong>2 horas</strong>.</p>
    """)
    send_email(to, "Redefina sua senha — Brand Brain", body)


def send_invite_email(to: str, org_name: str, inviter_name: str, role: str, invite_url: str) -> None:
    role_labels = {"owner": "Dono", "admin": "Administrador", "editor": "Editor", "viewer": "Visualizador"}
    role_label = role_labels.get(role, role)
    body = _base_template(f"""
      <p>Ola!</p>
      <p><strong>{inviter_name}</strong> convidou voce para fazer parte de
         <strong>{org_name}</strong> no Brand Brain como <strong>{role_label}</strong>.</p>
      <p>Clique no botao abaixo para aceitar o convite:</p>
      <a class="btn" href="{invite_url}">Aceitar convite</a>
      <p>Este convite expira em <strong>7 dias</strong>.</p>
    """)
    send_email(to, f"Voce foi convidado para {org_name} — Brand Brain", body)


def send_trial_expiry_email(to: str, name: str, days_left: int, upgrade_url: str) -> None:
    urgency = "critico" if days_left <= 1 else "importante"
    if days_left == 0:
        subject = "Seu trial expira hoje — Brand Brain"
        when = "expira <strong>hoje</strong>"
    else:
        subject = f"Seu trial expira em {days_left} dia(s) — Brand Brain"
        when = f"expira em <strong>{days_left} dia(s)</strong>"
    body = _base_template(f"""
      <p>Ola, <strong>{name}</strong>!</p>
      <p>Este e um aviso <strong>{urgency}</strong>: o seu trial gratuito do Brand Brain {when}.</p>
      <p>Para continuar usando a plataforma sem interrupcao, assine um dos nossos planos:</p>
      <a class="btn" href="{upgrade_url}">Ver planos e assinar</a>
      <p>Tem duvidas? Fale com a gente em contato@brandbrain.com.br</p>
    """)
    send_email(to, subject, body)
