# app/email.py
import smtplib
from email.message import EmailMessage
from flask import current_app

def _send_email(subject: str, to_email: str, html: str, plain: str | None = None):
    cfg = current_app.config
    if not cfg.get("MAIL_ENABLED"):
        current_app.logger.warning("[MAIL_DISABLED] To:%s Subject:%s", to_email, subject)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg.get("MAIL_FROM")
    msg["To"] = to_email
    msg.set_content(plain or "Verifica tu correo.")
    msg.add_alternative(html, subtype="html")

    host = cfg.get("SMTP_HOST")
    port = int(cfg.get("SMTP_PORT", 587))
    user = cfg.get("SMTP_USER")
    password = cfg.get("SMTP_PASSWORD")
    use_ssl = cfg.get("SMTP_USE_SSL", False)
    use_tls = cfg.get("SMTP_USE_TLS", True)

    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=20)
    else:
        server = smtplib.SMTP(host, port, timeout=20)

    try:
        server.ehlo()
        if use_tls and not use_ssl:
            server.starttls()
            server.ehlo()
        if user:
            server.login(user, password)
        server.send_message(msg)
    finally:
        server.quit()

def send_verification_email(to_email: str, verify_link: str, code: str | None = None):
    """Envía un correo con link de verificación (y opcionalmente muestra el código)."""
    base = current_app.config.get("APP_BASE_URL", "")
    subject = "Verifica tu cuenta"
    html = f"""
    <div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;max-width:580px;margin:auto">
      <h2 style="margin-bottom:16px">Verifica tu cuenta</h2>
      <p>Gracias por registrarte. Por favor, verifica tu correo haciendo clic en el botón:</p>
      <p style="margin:24px 0">
        <a href="{verify_link}" style="background:#0d6efd;color:#fff;text-decoration:none;padding:10px 16px;border-radius:6px;display:inline-block">Verificar ahora</a>
      </p>
      {"<p>También puedes usar este código: <strong>"+ code + "</strong></p>" if code else ""}
      <p style="font-size:12px;color:#6c757d">Si no fuiste tú, ignora este mensaje.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
      <p style="font-size:12px;color:#6c757d">© {base}</p>
    </div>
    """
    _send_email(subject, to_email, html, plain=f"Verifica tu cuenta: {verify_link}")
