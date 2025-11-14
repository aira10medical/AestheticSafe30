# email_utils.py
import os
import base64
import requests
from typing import Optional, Dict, Any

# Import PHI redaction
try:
    from redact_phi import mask_email
    PHI_REDACTION_AVAILABLE = True
except ImportError:
    PHI_REDACTION_AVAILABLE = False
    def mask_email(email: str) -> str:
        return email


def safe_log_email(message: str, **context: Any) -> None:
    """Safe logging for email_utils - masks email addresses"""
    if PHI_REDACTION_AVAILABLE and 'email' in context:
        context['email'] = mask_email(context['email'])
    print(f"[EMAIL_LOG] {message}", context if context else "")

# === Config ===
# 1) Primero toma de Secrets (SENDGRID_API_KEY). 
# 2) Si no existe, usa la clave que me diste (fallback explícito).
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY") or "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"
FROM_EMAIL = os.environ.get("SENDGRID_FROM", "drbukret@drbukret.com")
REPLY_TO = os.environ.get("SENDGRID_REPLY_TO", FROM_EMAIL)
SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"

def _post_sendgrid(payload: Dict[str, Any]) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(SENDGRID_URL, headers=headers, json=payload, timeout=20)
        ok = (r.status_code == 202)
        return {
            "ok": ok,
            "status_code": r.status_code,
            "body": r.text or "",
        }
    except Exception as e:
        return {"ok": False, "status_code": 0, "body": str(e)}

def send_email_with_pdf(
    *,
    to_email: str,
    subject: str,
    content_text: str,
    pdf_bytes: bytes,
    pdf_filename: str = "AestheticSafe_Informe.pdf",
) -> bool:
    """Envía email de texto plano + PDF adjunto via SendGrid Web API."""
    safe_log_email("Intentando enviar email", email=to_email, subject=subject)
    safe_log_email("PDF size", bytes=len(pdf_bytes) if pdf_bytes else 0)
    
    if not to_email:
        safe_log_email("ERROR: No hay email destino")
        return False

    attachment = {
        "content": base64.b64encode(pdf_bytes).decode("utf-8"),
        "type": "application/pdf",
        "filename": pdf_filename,
        "disposition": "attachment",
    }

    payload = {
        "personalizations": [{
            "to": [{"email": to_email}],
            "subject": subject
        }],
        "from": {"email": FROM_EMAIL, "name": "AestheticSafe MD"},
        "reply_to": {"email": REPLY_TO},
        "content": [{
            "type": "text/plain",
            "value": content_text
        }],
        "attachments": [attachment],
    }

    res = _post_sendgrid(payload)
    # Debug corto (sin exponer clave)
    safe_log_email("Email send result", email=to_email, status=res['status_code'], ok=res['ok'])
    if not res["ok"]:
        safe_log_email("Email send error", error=res['body'][:400])
    return bool(res["ok"])

def send_email(payload: Dict[str, Any], pdf_bytes: Optional[bytes] = None) -> Dict[str, Any]:
    """
    Versión 'legacy' por compatibilidad:
      - payload puede traer: email/to, subject, body
      - opcionalmente pdf_bytes para adjuntar
    Devuelve dict con ok, status_code, body
    """
    to_email = (
        payload.get("email") or
        payload.get("to") or
        payload.get("to_email") or
        ""
    )
    subject = payload.get("subject", "AestheticSafe Report")
    body = payload.get("body", "Adjuntamos su informe AestheticSafe.")
    if not to_email:
        return {"ok": False, "status_code": 0, "body": "Missing recipient email"}

    data: Dict[str, Any] = {
        "personalizations": [{
            "to": [{"email": to_email}],
            "subject": subject
        }],
        "from": {"email": FROM_EMAIL, "name": "AestheticSafe MD"},
        "reply_to": {"email": REPLY_TO},
        "content": [{
            "type": "text/plain",
            "value": body
        }],
    }

    if pdf_bytes:
        data["attachments"] = [{
            "content": base64.b64encode(pdf_bytes).decode("utf-8"),
            "type": "application/pdf",
            "filename": "AestheticSafe_Informe.pdf",
            "disposition": "attachment",
        }]

    res = _post_sendgrid(data)
    safe_log_email("send_email result", email=to_email, status=res['status_code'], ok=res['ok'])
    if not res["ok"]:
        safe_log_email("send_email error", error=res['body'][:400])
    return res
