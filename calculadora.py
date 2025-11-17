# ruff: noqa
# pyright: reportUnusedExpression=false

from __future__ import annotations

# ===================== Imports =====================
import os
import json
import csv
import pathlib
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Optional, Mapping, cast
import streamlit as st
import streamlit.components.v1 as components
import base64
import requests
import re as regex
import re as _re
from datetime import datetime, timezone
import time
import secrets
import registro


# Language detection (i18n)
try:
    from i18n_auto import detect_language, i18n_label as i18n_auto_label
    I18N_AUTO_AVAILABLE = True
except ImportError:
    I18N_AUTO_AVAILABLE = False
    def detect_language() -> str:
        return "es"
    def i18n_auto_label(es: str, en: str, pt: str) -> str:
        return es

# Email utilities with fallback
try:
    from email_utils import send_email, send_email_with_pdf  # type: ignore
except Exception:

    def send_email(*args, **kwargs):
        return {"status_code": 0, "ok": False, "detail": "email_utils missing"}

    def send_email_with_pdf(*args, **kwargs):
        return {"status_code": 0, "ok": False, "detail": "email_utils missing"}

# PDF Generator v3.1 (modern medical-grade design)
try:
    from pdf_generator_v3_1 import generar_pdf_v3_1
except ImportError:
    generar_pdf_v3_1 = None

# PHI/PII Redaction Layer (for public logs, NOT for Google Sheets)
try:
    from redact_phi import redact_dict, mask_email, hash_identifier
    PHI_REDACTION_AVAILABLE = True
except ImportError:
    PHI_REDACTION_AVAILABLE = False
    def redact_dict(data: Dict[str, Any], mode: str = "hash", allowlist: Optional[List[str]] = None) -> Dict[str, Any]:
        return data  # Fallback: no redaction
    def mask_email(email: str) -> str:
        return email
    def hash_identifier(value: str) -> str:
        return value


def safe_log(message: str, **context: Any) -> None:
    """
    Safe logging function that redacts PHI/PII before printing to console.
    Only affects console/debug logs - Google Sheets data is unaffected.
    
    Args:
        message: Log message template
        **context: Context variables (will be redacted if PHI)
    """
    if PHI_REDACTION_AVAILABLE and context:
        redacted_context = redact_dict(context, mode="mask")
        print(f"[SAFE_LOG] {message}", redacted_context)
    else:
        print(f"[LOG] {message}", context if context else "")


def sstr(x: object | None) -> str:
    return "" if x is None else str(x)


def sget(ss: Mapping[Any, Any], k: str, default: Any = None) -> Any:
    try:
        # streamlit SessionState expone .get
        return ss.get(k, default)  # type: ignore[attr-defined]
    except Exception:
        return default


def _safe_bool(x: object | None) -> bool:
    return bool(x)


# --- Normalizador de fila (único) ---
def _norm_resumen(x: Any) -> Dict[str, Any]:
    if isinstance(x, dict):
        return x
    try:
        return dict(x)  # lista/tupla de pares -> dict
    except Exception:
        return {"raw_fila": str(x)}


# Alias legacy (para llamadas antiguas)
_normalize_fila_resumen = _norm_resumen


def _ensure_dict(d: Any) -> Dict[str, Any]:
    return _norm_resumen(d)


# ==== LOGGING A SHEETS (dedupe por sesión y eventos) ====
from typing import Optional, Any, List, Tuple

try:
    # Import only available functions from gsheets
    from gsheets import (
        append_row_safe, 
        utc_now_str, 
        service_account_email as _sae,
        FUNNEL_PROGRESS_TAB,
        INTEROPERABILITY_TAB
    )  # type: ignore[attr-defined]
except Exception:
    # Fallbacks si no hay gsheets
    def append_row_safe(
            row: List[Any],
            tab: str = "Logs",
            tab_gid: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        return False, "gsheets_not_available"

    def utc_now_str() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    def _sae() -> Optional[str]:
        return None
    
    FUNNEL_PROGRESS_TAB = "V3_Funnel_Progress"
    INTEROPERABILITY_TAB = "V3_Interoperability_Log"


def service_account_email() -> str:
    try:
        v = _sae()
    except Exception:
        v = None
    if not v:
        import os as _os
        v = _os.environ.get("SERVICE_EMAIL") or _os.environ.get(
            "SERVICE_SENDER") or "service@example.com"
    return v


def tr(es: str, en: str, pt: str, fr: str = "") -> str:
    import streamlit as st
    lang = st.session_state.get("pdf_lang", "ES")
    return {"ES": es, "EN": en, "PT": pt, "FR": fr or es}.get(lang, es)


# --- Gating helpers (no usan st; reciben session_state) ---
def _b(ss: Mapping[Any, Any], *keys: str) -> bool:
    """
    Devuelve True si alguno de los keys existe en ss y es truthy.
    Acepta strings tipo 'true', 'yes', 'si', 'sí', 'ok', '1'.
    """
    TRUE_STR = {"1", "true", "yes", "si", "sí", "ok"}
    for k in keys:
        v = ss.get(k)
        if isinstance(v, str):
            if v.strip().lower() in TRUE_STR:
                return True
        elif bool(v):
            return True
    return False


def _s(ss: Mapping[Any, Any], *keys: str) -> str:
    """Primer string no vacío que encuentre en las keys dadas; si no, ''."""
    for k in keys:
        v = ss.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _ss_bool(state: Mapping[Any, Any], k: str) -> bool:
    return bool(state.get(k))


def _ss_str(state: Mapping[Any, Any], k: str) -> str:
    return str(state.get(k) or "").strip()


def can_release_report(state: Mapping[Any, Any]) -> bool:
    # claves tolerantes: tomamos la que exista
    consent = _safe_bool(state.get("consent_checkbox"))
    pay     = _safe_bool(state.get("pay_and_download"))
    share   = _safe_bool(state.get("share_and_download"))
    shared  = _safe_bool(state.get("whatsapp_shared") or state.get("whatsapp_shared_true"))
    phone   = sstr(state.get("whatsapp_phone") or state.get("phone") or state.get("telefono")).strip()
    return bool(consent and (pay or (share and shared and phone)))


# FIN helpers gating


# === i18n para bullets de RECOMENDACIONES (ES/EN/PT) ===
_RECS_I18N = {
    "bariatric_eval": {
        "ES": "Evaluar cirugía bariátrica si corresponde.",
        "EN": "Consider bariatric surgery if appropriate.",
        "PT": "Considerar cirurgia bariátrica se apropriado.",
    },
    "limit_duration": {
        "ES":
        "Limitar cirugías a máximo 5 h; combinaciones hasta 4 h (según criterio).",
        "EN":
        "Limit surgeries to a maximum of 5 h; combinations up to 4 h (per clinical judgement).",
        "PT":
        "Limitar cirurgias a no máximo de 5 h; combinações até 4 h (a critério clínico).",
    },
}


def _lang() -> str:
    """Lee el idioma del selector y normaliza a ES/EN/PT/FR."""
    try:
        import streamlit as st
        val = st.session_state.get("idioma", "ES") or "ES"
    except Exception:
        val = "ES"
    up = str(val).upper()
    if up.startswith("E") and up != "ES":
        return "EN"
    if up.startswith("P"):
        return "PT"
    if up.startswith("F"):
        return "FR"
    return "ES"


def _t(key: str) -> str:
    """Devuelve el texto traducido según el idioma actual (fallback ES)."""
    lang = _lang()
    entry = _RECS_I18N.get(key, {})
    return entry.get(lang, entry.get("ES", ""))


def button_label(es: str, en: str, fr: str, pt: str = "") -> str:
    """
    Devuelve la etiqueta del botón según el idioma actual.
    Soporta ES/EN/FR/PT con fallback a ES (español).
    Usa _lang() para normalizar códigos de locale.
    """
    lang = _lang()  # Normaliza y usa ES como default
    labels = {"ES": es, "EN": en, "FR": fr, "PT": pt or es}
    return labels.get(lang, es)


def log_to_funnel_progress(
    satisfaction_step: str,  # "step1" or "step2"
    emoji: str,  # "happy", "neutral", "sad"
    comment: str = ""
) -> Tuple[bool, Optional[str]]:
    """
    Logs user feedback to Funnel_Progress sheet.
    Columns: Timestamp, satisfaction_step1, satisfaction_step1_comment,
    satisfaction_step2, satisfaction_step2_comment, session_id,
    user_agent, country, doctor_email, stage, substage,
    last_contact_at, next_contact_at, contact_attempts,
    sequence_name, wa_template
    """
    import streamlit as st
    from datetime import datetime, timezone
    from gsheets import append_row_safe, FUNNEL_PROGRESS_TAB
    
    # Dedupe logic
    has_comment = bool(comment and comment.strip())
    log_key = f"funnel_logged_{satisfaction_step}_{emoji}_{'comment' if has_comment else 'emoji'}"
    
    if st.session_state.get(log_key):
        return True, None  # Already logged, skip
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    session_id = st.session_state.get("sess_ref", "")
    user_email = st.session_state.get("email", "")
    
    # Build row matching V3_FUNNEL_PROGRESS_HEADERS
    idioma_ui = st.session_state.get("idioma", "ES")
    logo_faded = st.session_state.get("logo_faded", False)
    
    row = [
        timestamp,  # Timestamp
        emoji if satisfaction_step == "step1" else "",  # satisfaction_step1
        comment if satisfaction_step == "step1" else "",  # satisfaction_step1_comment
        emoji if satisfaction_step == "step2" else "",  # satisfaction_step2
        comment if satisfaction_step == "step2" else "",  # satisfaction_step2_comment
        session_id,  # session_id
        "",  # user_agent (optional)
        "",  # country (optional)
        user_email,  # doctor_email
        "feedback",  # stage
        satisfaction_step,  # substage
        timestamp,  # last_contact_at
        "",  # next_contact_at
        "",  # contact_attempts
        "",  # sequence_name
        "",  # wa_template
        "V3.1",  # app_version
        idioma_ui,  # idioma_ui
        str(logo_faded),  # logo_fade_triggered
        ""  # scroll_events
    ]
    
    try:
        success, error = append_row_safe(
            row=row,
            tab=FUNNEL_PROGRESS_TAB,
            tab_gid=None
        )
        
        if success:
            st.session_state[log_key] = True
        
        return success, error
    except Exception as e:
        return False, str(e)


def log_to_interoperability(
    request_data: str,
    response_data: str,
    stage: str = "",
    substage: str = ""
) -> Tuple[bool, Optional[str]]:
    """
    Logs technical events to V3_Interoperability_Log sheet.
    Columns: Timestamp | Request_Data | Response_Data | App_Version | Browser_Lang | 
             Idioma_Detected | Session_ID | User_Agent | Country | Stage | Substage
    """
    import streamlit as st
    from datetime import datetime, timezone
    from gsheets import append_row_safe, INTEROPERABILITY_TAB
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    session_id = st.session_state.get("sess_ref", "")
    idioma_detected = st.session_state.get("idioma_autodetected", False)
    browser_lang = st.session_state.get("browser_lang", st.session_state.get("idioma", "ES"))
    user_agent = st.session_state.get("user_agent", "")
    country = st.session_state.get("country", "")
    
    row = [
        timestamp,  # Timestamp
        request_data,  # Request_Data (JSON string)
        response_data,  # Response_Data (JSON string)
        "V3.1",  # App_Version
        browser_lang,  # Browser_Lang
        str(idioma_detected),  # Idioma_Detected
        session_id,  # Session_ID
        user_agent,  # User_Agent
        country,  # Country
        stage,  # Stage
        substage  # Substage
    ]
    
    try:
        success_result, error = append_row_safe(
            row=row,
            tab=INTEROPERABILITY_TAB,
            tab_gid=None
        )
        
        return success_result, error
    except Exception as e:
        return False, str(e)


# === Helper: completa y normaliza fila_resumen para Google Sheets ===
def _completar_campos_gsheet(fila_resumen):
    import streamlit as st
    from datetime import datetime, timezone

    # Flags / estado
    paid_flag = bool(st.session_state.get("paid_flag", False))
    shared_whatsapp = bool(st.session_state.get("shared_whatsapp", False))
    clicked_final = bool(st.session_state.get("clicked_final_pdf", False))
    email_sent_ok = bool(st.session_state.get("email_sent_ok", False))
    entrega_via = "email" if email_sent_ok else (
        "download" if clicked_final else "")

    # IDs / referencias
    rep_id = st.session_state.get(
        "rep_id"
    ) or f"ESTH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    # Pago / share
    paid_amount_usd = float(st.session_state.get("paid_amount_usd", 0) or 0)
    paid_ref = str(st.session_state.get("paid_ref", "") or "")
    share_ref = str(st.session_state.get("share_ref", "") or "")

    # Origen (utm) — sin deprecations
    try:
        utm_source = st.query_params.get("utm_source", "app")
        if isinstance(utm_source, list):
            utm_source = (utm_source or ["app"])[0]
    except Exception:
        utm_source = "app"

    # Clínicos
    caprini_score_val = st.session_state.get("caprini_score_val", "")
    caprini_cat_val = st.session_state.get("caprini_cat_val", "")
    caprini_factores = "; ".join(st.session_state.get("caprini_selected", []))
    factor_riesgo_val = st.session_state.get("factor_riesgo_val", "")
    nivel_riesgo_val = st.session_state.get("nivel_riesgo_val", "")

    # Consentimiento y TDC
    consent_ok = bool(
        st.session_state.get("consentimiento", False)
        or st.session_state.get("consent_ok", False))
    tdc_positive = bool(st.session_state.get("tdc_positive", False))
    # --- WhatsApp share flags (con defaults seguros) ---
    shared_whatsapp = bool(st.session_state.get("shared_whatsapp", False))
    shared_number = (st.session_state.get("wa_phone_confirmed")
                     or st.session_state.get("shared_number", "")
                     or "").strip()

    # Estado de pago / share
    pago_estado = "PAID" if paid_flag else (
        "SHARED" if shared_whatsapp else "FREE")

    # Referencia de share: si hay número y marcó que compartió, guardamos el número; si no, canal o vacío
    share_ref = shared_number if (shared_whatsapp and shared_number) else (
        "whatsapp" if shared_whatsapp else "")

    # >>> IMPORTANTE: devolvemos **LISTA**, no dict, para que la Sheet reciba VALORES
    extras = [
        caprini_score_val,
        caprini_cat_val,
        caprini_factores,
        factor_riesgo_val,
        nivel_riesgo_val,
        "Sí" if consent_ok else "No",
        utm_source or "app",
        pago_estado,
        paid_amount_usd,
        paid_ref,
        "Sí" if (clicked_final or email_sent_ok) else "No",
        entrega_via,
        rep_id,
        ("whatsapp" if shared_whatsapp else ""),
        share_ref,
        "Sí" if tdc_positive else "No",
    ]

    if isinstance(fila_resumen, list):
        return fila_resumen + extras
    elif hasattr(fila_resumen, "values"):
        return list(fila_resumen.values()) + extras
    else:
        return extras


APP_VERSION = "v1.1"  # etiquetado de la app en logs
LOG_TAB = "Calculadora_Evaluaciones"  # pestaña de destino


def _ensure_session_ref() -> str:
    if "sess_ref" not in st.session_state:
        st.session_state[
            "sess_ref"] = f"S{int(time.time())}-{secrets.token_hex(3)}"
    return st.session_state["sess_ref"]


def _was_logged(step: str) -> bool:
    flags = st.session_state.setdefault("_logged_steps", {})
    return bool(flags.get(step))


def _mark_logged(step: str):
    flags = st.session_state.setdefault("_logged_steps", {})
    flags[step] = True


def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def _safe_int(x):
    try:
        return int(float(x))
    except Exception:
        return None


def _calc_bmi(peso, altura_cm):
    p = _safe_float(peso)
    h = _safe_float(altura_cm)
    if p and h:
        try:
            return round(p / ((h / 100.0)**2), 1)
        except Exception:
            return ""
    return ""


def log_step_once(step: str, payload: dict | None = None, **extras):
    """
    step:
      - 'session_open' (apertura, no conversión)
      - 'share_click'  (click en compartir, no conversión)
      - 'share_done'   (confirma que compartió, CONVERSIÓN)
      - 'pdf_final'    (descarga final, CONVERSIÓN)
      - 'share_email'  (envío por email sin pago, no conversión)
      - 'pago_email'   (envío por email con pago, no conversión — si querés contar aparte)
    """
    if _was_logged(step):
        return False

    _ensure_session_ref()
    p = payload or {}
    idioma = st.session_state.get("idioma", "ES")

    email = (p.get("email") or extras.get("email") or "").strip()
    telefono = (p.get("telefono") or extras.get("telefono") or "").strip()
    nombre = p.get("nombre", "")
    perfil = p.get("perfil", "")

    edad = p.get("edad", extras.get("edad", ""))
    peso = p.get("peso") or p.get("peso_kg") or extras.get("peso", "")
    altura = p.get("altura_cm") or p.get("altura") or extras.get("altura", "")
    tabaquismo = p.get("tabaquismo", extras.get("tabaquismo", ""))

    bmi = _calc_bmi(peso, altura)
    conversion = 1 if step in ("share_done", "pdf_final") else 0

    fila = [
        utc_now_str(),  # A  timestamp_utc
        st.session_state.get("sess_ref", ""),  # B  session_ref
        step,  # C  step
        conversion,  # D  conversion 0/1
        idioma,  # E  idioma
        APP_VERSION,  # F  app_version
        email,
        telefono,
        nombre,
        perfil,  # G-J contacto/identidad (si hubiera)
        edad,
        peso,
        altura,
        bmi,
        tabaquismo,  # K-O métricas básicas
        extras.get("share_ref", ""),  # P  share_ref (si aplica)
        extras.get("pdf_ref", ""),  # Q  pdf_ref (si aplica)
    ]

    ok, _svc = append_row_safe(fila, tab=LOG_TAB)
    if ok:
        _mark_logged(step)
    else:
        # No rompemos la UX por logging; solo avisamos permiso faltante
        # st.info(f"Compartí la hoja con: **{service_account_email()}**")
        pass

    return ok


# ===================== Idiomas (ES/EN/PT/FR) =====================
LANGS = {"ES": "Español", "EN": "English", "PT": "Português (Brasil)", "FR": "Français"}


def _read_lang_from_query() -> str:
    """
    Lee ?lang=en|pt|es desde la URL; default ES.
    Acepta alias comunes en minúsculas.
    """
    try:
        qp = st.query_params  # type: ignore[attr-defined]
        lang = None
        if isinstance(qp, dict):
            lang = qp.get("lang") or qp.get("language")
            if isinstance(lang, list):
                lang = lang[0] if lang else None
    except Exception:
        lang = None
    val = (str(lang or "")).strip().lower()
    if val in ("en", "en-us", "en-gb"):
        return "EN"
    if val in ("pt", "pt-br", "ptbr", "br"):
        return "PT"
    return "ES"


EMAIL_TPL = {
    "ES": {
        "subject":
        "Informe AestheticSafe",
        "body":
        ("Hola {name},\n\n"
         "Gracias por realizar tu evaluación con AestheticSafe. "
         "Tu informe en PDF está adjunto a este correo.\n\n"
         "Importante: este informe es orientativo y debe ser validado por un profesional médico "
         "antes de tomar decisiones.\n\n"
         "Ante cualquier duda, estamos para ayudarte:\n"
         "{brand} · {mail} · {tel}\n"
         "Sitio: {web1}\n"
         "Gracias por tu confianza."),
        "wa":
        "Conocé tu nivel de riesgo estético con AestheticSafe y compartilo con alguien que cuidás: {link}  #AestheticSafe",
    },
    "EN": {
        "subject":
        "AestheticSafe Report",
        "body":
        ("Hi {name},\n\n"
         "Thank you for completing your AestheticSafe assessment. "
         "Your PDF report is attached to this email.\n\n"
         "Important: this report is for guidance only and must be reviewed with a qualified physician "
         "before making any decisions.\n\n"
         "Questions? We’re here to help:\n"
         "{brand} · {mail} · {tel}\n"
         "Website: {web1}\n"
         "Thank you for your trust."),
        "wa":
        "Find out your aesthetic risk level with AestheticSafe and share it with someone you care about: {link}  #AestheticSafe",
    },
    "PT": {
        "subject":
        "Relatório AestheticSafe",
        "body":
        ("Olá {name},\n\n"
         "Obrigado por realizar sua avaliação com o AestheticSafe. "
         "Seu relatório em PDF está anexado a este e-mail.\n\n"
         "Importante: este relatório é orientativo e deve ser revisado com um médico "
         "antes de qualquer decisão.\n\n"
         "Dúvidas? Fale conosco:\n"
         "{brand} · {mail} · {tel}\n"
         "Site: {web1}\n"
         "Obrigado pela confiança."),
        "wa":
        "Descubra seu nível de risco estético com o AestheticSafe e compartilhe com alguém importante para você: {link}  #AestheticSafe",
    },
}

# ===================== Envío de email (SendGrid) =====================
# Email functions are imported at the top with fallback definitions

# ===================== Config (seguros si faltan secretos) =====================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _secret_safe(key: str, default: str | None = None) -> str | None:
    """Lee st.secrets[key] sin romper si no existe secrets.toml."""
    try:
        if hasattr(st, "secrets"
                   ) and st.secrets is not None:  # type: ignore[attr-defined]
            v = st.secrets.get(key)  # type: ignore[attr-defined]
            if v not in (None, ""):
                return v
    except Exception:
        pass
    return default


APP_PUBLIC_URL = os.getenv("APP_PUBLIC_URL") or _secret_safe(
    "APP_PUBLIC_URL", "https://replit.dev")
MERCADOPAGO_LINK = os.getenv("MERCADOPAGO_LINK") or _secret_safe(
    "MERCADOPAGO_LINK", "https://mpago.la/1trdbsC")
ZELLE_EMAIL = os.getenv("ZELLE_EMAIL") or _secret_safe(
    "ZELLE_EMAIL", "drbukret@drbukret.com")

SHEET_KEY = os.getenv("SHEET_KEY") or _secret_safe("SHEET_KEY", "")
WORKSHEET = os.getenv("WORKSHEET") or _secret_safe("WORKSHEET", "events")
USE_SHEETS = bool(SHEET_KEY)

# Marca e identidad
BRAND = "AestheticSafe®"
BRAND_LEGAL = "Bukret Pesce Salud y Belleza SRL"
BRAND_ADDR = "Arenales 2521, Piso 9, Buenos Aires, Argentina"
BRAND_WEB1 = "aestheticsafe.com"
BRAND_WEB2 = "aestheticsafe.com.ar"
BRAND_MAIL = "info@aestheticsafe.com"
BRAND_TEL = "+54 9 11 3121-1468"

# Si una imagen estuviera corrupta, el PDF la salta sin romper.
LOGO_PATHS = [
    # Dejá solo las que sean PNG/JPG válidas en tu repo; si “aestheticsafe_logo.png” sigue dando error, comentala.
    "attached_assets/aestheticsafe_logo.png",
    "logo.png",
]

# ===================== Google Sheets (opcional y tolerante a fallos) =====================


def _load_creds():
    try:
        from google.oauth2.service_account import Credentials  # type: ignore
    except Exception:
        return None
    raw = os.getenv("GOOGLE_CREDENTIALS") or _secret_safe("GOOGLE_CREDENTIALS")
    try:
        if raw:
            info = json.loads(raw) if isinstance(raw, str) else raw
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        if os.path.exists("credentials.json"):
            return Credentials.from_service_account_file("credentials.json",
                                                         scopes=SCOPES)
    except Exception:
        return None
    return None


@st.cache_resource(show_spinner=False)
def _ws():
    if not USE_SHEETS:
        return None
    try:
        import gspread  # type: ignore
    except Exception:
        return None
    creds = _load_creds()
    if creds is None:
        return None
    try:
        gc = gspread.authorize(creds)
        ss = gc.open_by_key(SHEET_KEY)  # type: ignore[arg-type]
        try:
            ws_title = str(WORKSHEET or st.session_state.get("sheet_title")
                           or os.environ.get("SHEET_SHEETNAME") or "events")
            ws = ss.worksheet(ws_title)
        except Exception:
            ws_title = str(WORKSHEET or "events")
            ws = ss.add_worksheet(title=ws_title, rows=2000, cols=40)
        return ws
    except Exception:
        return None


HEADERS = [
    "timestamp",
    "canal",
    "email",
    "telefono",
    "nombre",
    "perfil",
    "idioma",
    "version",
    "edad",
    "peso_kg",
    "altura_cm",
    "bmi",
    "tabaquismo",
    "caprini_score",
    "caprini_categoria",
    "caprini_factores",
    "factor_riesgo",
    "nivel_riesgo",
    "consentimiento",
    "origen",
    # tracking
    "pago_estado",
    "pago_monto_usd",
    "pago_ref",
    "pdf_entregado",
    "pdf_entrega_via",
    "pdf_ref",
    "share_via",
    "share_ref",
    "wa_destino",
    "tdc_positivo",
    "verification_uuid",
]

_ALLOWED_CHANNELS = {
    "pago_intento", "pago_ok", "pago_email", "share_click", "share_ok",
    "share_email", "download", "descarga"
}


def _dump_outbox_to_csv(rows: List[List[str]]):
    try:
        path = pathlib.Path("share/events_fallback.csv")
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(HEADERS)
            for r in rows:
                w.writerow(r)
    except Exception:
        pass


def _append_row_extended(payload: dict, canal: str, **kw) -> bool:
    if canal not in _ALLOWED_CHANNELS:
        return False

    # ---- defaults robustos desde session_state ----
    perfil = (payload.get("perfil") or st.session_state.get("perfil")
              or st.session_state.get("perfil_ui")
              or st.session_state.get("profile") or "app")

    paid_code = (st.session_state.get("paid_code") or "").strip()
    try:
        code_ok = bool(regex.fullmatch(r"[A-Za-z0-9]{6,}", paid_code))
    except Exception:
        code_ok = len(paid_code) >= 6  # fallback si no hay regex

    pago_confirmado = bool(
        st.session_state.get("mp_confirmado")
        or (st.session_state.get("pay_ok") and code_ok)
        or st.session_state.get("zelle_ok"))
    pago_estado = "Sí" if pago_confirmado else "No"

    monto = (kw.get("pago_monto_usd") or st.session_state.get("pago_monto_usd")
             or st.session_state.get("mp_amount") or "")
    try:
        pago_monto_usd = f"{float(monto):.2f}" if str(
            monto).strip() != "" else ("0" if not pago_confirmado else "")
    except Exception:
        pago_monto_usd = ("0" if not pago_confirmado else str(monto))

    pago_ref = (kw.get("pago_ref") or paid_code
                or st.session_state.get("pdf_id")
                or st.session_state.get("sess_ref") or "")

    medico = (st.session_state.get("medico")
              or st.session_state.get("medico_input")
              or payload.get("medico", "")).strip()

    codigo_verificador = (st.session_state.get("codigo_verificador")
                          or st.session_state.get("pdf_id") or paid_code
                          or pago_ref or "")

    base = {
        "timestamp":
        payload.get("timestamp",
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
        "canal":
        canal,
        "email":
        payload.get("email", ""),
        "telefono":
        payload.get("telefono", ""),
        "nombre":
        payload.get("nombre", ""),
        "perfil":
        perfil,
        "idioma":
        payload.get("idioma", "ES"),
        "version":
        payload.get("version", "v1.0"),
        "edad":
        payload.get("edad", ""),
        "peso_kg":
        payload.get("peso_kg", ""),
        "altura_cm":
        payload.get("altura_cm", ""),
        "bmi":
        payload.get("bmi", ""),
        "tabaquismo":
        payload.get("tabaquismo", ""),
        "caprini_score":
        payload.get("caprini_score", ""),
        "caprini_categoria":
        payload.get("caprini_categoria", ""),
        "caprini_factores":
        payload.get("caprini_factores", ""),
        "factor_riesgo":
        payload.get("factor_riesgo", ""),
        "nivel_riesgo":
        payload.get("nivel_riesgo", ""),
        "consentimiento":
        "Sí" if payload.get("consentimiento") else "No",
        "origen":
        payload.get("origen", BRAND),
        # tracking
        "pago_estado":
        pago_estado,
        "pago_monto_usd":
        pago_monto_usd,
        "pago_ref":
        pago_ref,
        "pdf_entregado":
        kw.get("pdf_entregado", ""),
        "pdf_entrega_via":
        kw.get("pdf_entrega_via", ""),
        "pdf_ref":
        kw.get("pdf_ref", ""),
        "share_via":
        kw.get(
            "share_via",
            ("whatsapp" if st.session_state.get("shared_whatsapp") else "")),
        "share_ref":
        kw.get("share_ref", (st.session_state.get("share_ref")
                             or payload.get("telefono", ""))),
        "wa_destino":
        kw.get("wa_destino", (st.session_state.get("wa_destino")
                              or st.session_state.get("share_ref")
                              or payload.get("telefono", ""))),
        "tdc_positivo":
        kw.get("tdc_positivo",
               ("Sí" if st.session_state.get("tdc_positive") else "No")),
        "verification_uuid":
        st.session_state.get("verification_uuid", ""),
    }

    # fila ordenada según HEADERS + extras al final (medico, codigo_verificador)
    row = [base.get(h, "") for h in HEADERS] + [medico, codigo_verificador]

    ok, _svc = append_row_safe(row, tab=LOG_TAB)
    if not ok:
        _dump_outbox_to_csv([row])
    return True


# ===================== Lógica de riesgo =====================
# Texto paciente-amigable en cada ítem
CAPRINI_1P = {
    "Realizaré cirugía menor (<45 min)",
    "Várices visibles",
    "Enfermedad inflamatoria intestinal (diagnosticada)",
    "Piernas hinchadas (edema actual)",
    "Antecedente de neumonía reciente (último mes) o infección seria",
    "Antecedente de infarto de miocardio",
    "Insuficiencia cardíaca (diagnosticada)",
    "Reposo en cama o movilidad limitada (<72 h; férula removible)",
    "Anticonceptivos / Terapia hormonal (ACO/HRT)",
    "Embarazo / puerperio (<1 mes)",
    "Antecedentes obstétricos (mortinato/≥3 abortos/RCIU/toxemia)",
}
CAPRINI_2P = {
    "Cáncer actual o previo (no piel no melanoma)",
    "Realizaré cirugía mayor (>45 min)",
    "Yeso o molde no removible en el último mes",
    "Actualmente tiene catéter venoso central / PICC / Port",
    "En reposo en cama ≥72 h",
}
CAPRINI_3P_GROUP = {
    # 🔧 corregido typo: “tombosis” → “trombosis”
    "Historia personal de trombosis venosa profunda/embolismo pulmonar",
    "Antecedente familiar de trombosis o accidente cerebrovascular (ACV)",
    "Trombofilia (test positivo de hipercoagulabilidad)",
}
CAPRINI_5P = {
    "Antecedente de artroplastia electiva de cadera/rodilla",
    "Antecedente de fractura de cadera/pelvis/pierna",
    "Antecedente de trauma mayor",
    "Lesión medular con parálisis",
    "Accidente cerebrovascular (ACV) reciente",
}
CAPRINI_TODOS = sorted(CAPRINI_1P | CAPRINI_2P | CAPRINI_3P_GROUP | CAPRINI_5P)


def caprini_desde(labels: List[str]) -> Tuple[int, Dict[str, int]]:
    sel = set(labels)
    detalle: Dict[str, int] = {}
    score = 0
    for f in CAPRINI_1P:
        if f in sel:
            detalle[f] = 1
            score += 1
    for f in CAPRINI_2P:
        if f in sel:
            detalle[f] = 2
            score += 2
    for f in CAPRINI_5P:
        if f in sel:
            detalle[f] = 5
            score += 5
    if any(f in sel for f in CAPRINI_3P_GROUP):
        detalle["Grupo trombofilia / DVT / antecedente"] = 3
        score += 3
    return score, detalle


def caprini_categoria(score: int) -> str:
    if score <= 2:
        return "Bajo (0–2)"
    if score <= 8:
        return "Intermedio (3–8)"
    return "Alto (>8)"


def factor_riesgo_fn(edad: int, bmi: float, tabaquismo: str,
                     caprini_score: int) -> float:
    f = 1.0 if edad < 18 else 1.0 + (edad / 100.0)**3.5
    if bmi >= 30:
        f += 0.4
    elif bmi >= 25:
        f += 0.2
    if tabaquismo == "Sí (1–7 por semana)":
        f += 0.1
    elif tabaquismo in ("Más de 7 por semana", ">7 por semana"):
        f += 0.3
    if caprini_score >= 5:
        f += 0.245
    return round(f, 3)


def nivel_por_factor(f: float) -> str:
    if f >= 1.4:
        return "Moderado" if f < 1.6 else "Alto"
    if f >= 1.2:
        return "Moderado"
    return "Bajo"


# ===================== Recomendaciones (AppSheet + Longevity®) =====================


def recomendaciones_txt(*, IMC: float, edad: int, tabaquismo: str,
                        hta_txt: str, diabetes_txt: str, tiroides_txt: str,
                        caprini_score: int, antecedentes: List[str],
                        riesgo: str) -> List[str]:
    recs: List[str] = []

    # Peso / IMC
    if IMC < 19.5:
        recs += [
            tr(
                "Incrementa tu peso de manera saludable para alcanzar un IMC adecuado.",
                "Increase your weight in a healthy way to reach a suitable BMI.",
                "Aumente seu peso de forma saudável para atingir um IMC adequado."
            ),
            tr(
                "Considera un plan de alimentación rico en nutrientes y actividad física para ganar masa muscular.",
                "Consider a nutrient-dense meal plan and physical activity to gain lean mass.",
                "Considere um plano alimentar rico em nutrientes e atividade física para ganhar massa magra."
            ),
        ]
    elif IMC > 25:
        recs += [
            tr("Trabaja en reducir tu peso para alcanzar un IMC saludable.",
               "Work on reducing your weight to reach a healthy BMI.",
               "Trabalhe para reduzir seu peso e atingir um IMC saudável."),
            tr(
                "Sigue una dieta balanceada y realiza actividad física regular.",
                "Follow a balanced diet and perform regular physical activity.",
                "Siga uma dieta equilibrada e pratique atividade física regularmente."
            ),
        ]
    else:
        recs += [
            tr(
                "Mantén tu peso actual con dieta balanceada y actividad física regular.",
                "Maintain your current weight with a balanced diet and regular physical activity.",
                "Mantenha seu peso atual com dieta equilibrada e atividade física regular."
            )
        ]

    # Factores puntuales
    if (tabaquismo or "") != "No":
        recs.append(
            tr(
                "Deja de fumar para reducir riesgos quirúrgicos y mejorar tu salud general. Consulta con un especialista si necesitas apoyo.",
                "Quit smoking to reduce surgical risks and improve your overall health. Seek specialist support if needed.",
                "Pare de fumar para reduzir riscos cirúrgicos e melhorar sua saúde geral. Procure apoio especializado se necessário."
            ))
    if (hta_txt or "") != "No":
        recs.append(
            tr(
                "Controla tu presión arterial regularmente y lleva un registro para tu médico.",
                "Monitor your blood pressure regularly and keep a log for your physician.",
                "Controle sua pressão arterial regularmente e mantenha um registro para seu médico."
            ))
    if (diabetes_txt or "") != "No":
        recs.append(
            tr(
                "Mantén control estricto de glucosa y sigue indicaciones de tu endocrinólogo.",
                "Keep strict glucose control and follow your endocrinologist’s recommendations.",
                "Mantenha controle estrito da glicose e siga as recomendações do seu endocrinologista."
            ))
    if edad >= 50:
        recs.append(
            tr(
                "Programa chequeos preventivos regulares acordes a tu edad.",
                "Schedule age-appropriate preventive checkups regularly.",
                "Agende exames preventivos regulares apropriados para sua idade."
            ))

    # Caprini / sugerencia por riesgo
    if riesgo == "Bajo":
        recs.append(
            tr(
                "Puedes considerar cirugía hasta 6 h; combinaciones hasta 5 h (según criterio).",
                "You may consider surgery up to 6 h; combined procedures up to 5 h (as clinically indicated).",
                "Você pode considerar cirurgia de até 6 h; combinações até 5 h (conforme indicação clínica)."
            ))
    elif riesgo == "Moderado":
        recs.append(_t("limit_duration"))  # ya usa tu i18n por clave
    else:
        recs.append(
            tr(
                "Riesgo alto: solo cirugías simples hasta 3 h. Combinaciones no recomendadas.",
                "High risk: simple procedures only up to 3 h. Combined procedures not recommended.",
                "Alto risco: apenas procedimentos simples de até 3 h. Combinações não recomendadas."
            ))

    # Condiciones adicionales tipo AppSheet
    if IMC < 18.5:
        recs.append(
            tr(
                "Aumentar de peso con nutricionista; descartar trastorno alimentario si aplica.",
                "Increase weight with a nutritionist; rule out eating disorder if applicable.",
                "Aumentar o peso com nutricionista; descartar transtorno alimentar se aplicável."
            ))

    if any(a for a in (antecedentes or [])
           if ("coagulación" in a.lower() or "trombo" in a.lower()
               or "dvt" in a.lower())):
        recs.append(
            tr(
                "Consultar con Hematología para evaluación de trastornos de coagulación.",
                "Suggest a Hematology consult for evaluation of coagulation disorders.",
                "Sugira consulta com Hematologia para avaliação de distúrbios de coagulação."
            ))

    if (tiroides_txt or "") != "Normal":
        recs.append(
            tr(
                "Consultar con Endocrinología y monitorear hormonas tiroideas.",
                "Refer to Endocrinology and monitor thyroid hormones.",
                "Consulte um endocrinologista e monitore hormônios da tireoide."
            ))

    if IMC > 31:
        recs.append(_t("bariatric_eval"))  # ya usa tu catálogo i18n

    # Cardiovascular ampliado
    if (IMC > 28) or (edad >= 45) or ((hta_txt or "") != "No"):
        recs.append(
            tr("Ergometría según criterio médico.",
               "Exercise stress test as clinically indicated.",
               "Teste ergométrico conforme critério médico."))

    # Criterios ampliados de evaluación cardiovascular
    fam_trombo = any("Antecedente familiar de trombosis" == a
                     for a in (antecedentes or []))
    if (edad >= 50) or ((hta_txt or "") != "No") or fam_trombo:
        recs.append(
            tr(
                "Doppler de carótidas y score cálcico coronario (CAC).",
                "Carotid Doppler and coronary artery calcium (CAC) score.",
                "Doppler de carótidas e escore de cálcio coronário (CAC)."
            ))
        recs.append(
            tr(
                "Presurometría 24 h y Eco-estrés (ejercicio y reposo) según criterio médico.",
                "24-hour ambulatory BP monitoring and stress echocardiography (exercise and rest) as clinically indicated.",
                "Pressurometria 24 h e Eco-estresse (exercício e repouso) conforme critério médico."
            ))

    recs.append(
        tr("Estas sugerencias no sustituyen el criterio médico.",
           "These suggestions do not replace medical judgment.",
           "Estas sugestões não substituem o julgamento clínico."))
    return recs


# ===================== PDF (ReportLab – canvas, con logo robusto) =====================


def _first_valid_logo(paths: List[str]) -> str | None:
    """
    Devuelve el primer archivo de 'paths' que sea realmente una imagen válida.
    Si ninguno sirve, retorna None (y el PDF omite el logo sin crashear).
    """
    for p in paths:
        try:
            if not os.path.exists(p):
                continue
            # Verificación dura con PIL
            from PIL import Image  # import local por si no está instalado
            with Image.open(p) as im:
                im.verify()  # valida encabezados
            return p
        except Exception:
            continue
    return None


# ===================== Texto empático para el screening psicológico =====================
def _psico_texto_empatico(resultado: str) -> str:
    """
    Devuelve un texto breve y empático según el resultado del screening.
    Posibles valores:
      - "Negativo"
      - "BDD positivo (sugerir consulta psicológica)"
      - "Posible trastorno alimentario (sin criterios de BDD)"
      - "BDD negativo; posible trastorno alimentario"
    """
    r = (resultado or "").strip()
    rlow = r.lower()

    if "bdd negativo" in rlow and "trastorno" in rlow:
        return (
            "Screening psicológico: señales compatibles con posible trastorno alimentario. "
            "Sugerimos evaluación con Nutrición y Salud Mental. Buscar ayuda es un paso de cuidado."
        )
    if "bdd positivo" in rlow:
        return (
            "Screening psicológico: indicios compatibles con preocupación excesiva por la imagen corporal (BDD). "
            "Recomendamos conversar con un profesional de salud mental; es frecuente y tiene abordaje eficaz."
        )
    if "posible trastorno alimentario" in rlow:
        return (
            "Screening psicológico: indicios de trastorno alimentario. "
            "Sugerimos evaluación nutricional/psicológica para planificar el mejor momento para cualquier procedimiento."
        )
    if "negativo" in rlow:
        return (
            "Screening psicológico sin señales preocupantes en este cuestionario breve. "
            "Si las preocupaciones aumentan, hablalo con tu médico o un profesional de confianza."
        )

    return f"Resultado del screening: {r}"


def generar_pdf(datos: dict,
                *,
                preview: bool = False,
                full: bool = False,
                lang: str | None = None) -> bytes:
    """
    Genera el PDF (preview o final).
    Idioma: usa 'lang' si se pasa; si no, toma automáticamente st.session_state['idioma'] (UI).
    """
    # ===== i18n =====
    PDF_TXT = {
        "ES": {
            "title":
            "Informe de Evaluación y Recomendaciones Personalizadas",
            "issued_by":
            "Emitido por: AestheticSafe®",
            "patient":
            "Datos del Paciente",
            "name":
            "Nombre",
            "age":
            "Edad",
            "height":
            "Altura",
            "weight":
            "Peso",
            "bmi":
            "IMC",
            "caprini":
            "Caprini",
            "factor":
            "Factor",
            "level":
            "Nivel",
            "recs":
            "Recomendaciones",
            "recs_preview_note":
            "Las recomendaciones completas estarán disponibles en el informe final.",
            "psych":
            "Evaluación Psicológica",
            "psych_label":
            "Screening psicológico",
            "conclusion":
            "Conclusión",
            "disclaimer":
            "Descargo de responsabilidad",
            "disclaimer_body":
            ("Este informe fue generado automáticamente por AestheticSafe®. "
             "La información es orientativa y debe ser validada por un profesional médico antes de tomar decisiones. "
             "No sustituye el juicio clínico."),
            "code":
            "Código verificador",
            "date":
            "Fecha",
            "id":
            "ID",
        },
        "EN": {
            "title":
            "Evaluation Report and Personalized Recommendations",
            "issued_by":
            "Issued by: AestheticSafe®",
            "patient":
            "Patient Data",
            "name":
            "Name",
            "age":
            "Age",
            "height":
            "Height",
            "weight":
            "Weight",
            "bmi":
            "BMI",
            "caprini":
            "Caprini",
            "factor":
            "Factor",
            "level":
            "Level",
            "recs":
            "Recommendations",
            "recs_preview_note":
            "Full recommendations will be available in the final report.",
            "psych":
            "Psychological Evaluation",
            "psych_label":
            "Psych screening",
            "conclusion":
            "Conclusion",
            "disclaimer":
            "Disclaimer",
            "disclaimer_body":
            ("This report was automatically generated by AestheticSafe®. "
             "The information is for guidance only and must be reviewed by a qualified physician before making any decisions. "
             "It does not replace clinical judgment."),
            "code":
            "Verification code",
            "date":
            "Date",
            "id":
            "ID",
        },
        "PT": {
            "title":
            "Relatório de Avaliação e Recomendações Personalizadas",
            "issued_by":
            "Emitido por: AestheticSafe®",
            "patient":
            "Dados do Paciente",
            "name":
            "Nome",
            "age":
            "Idade",
            "height":
            "Altura",
            "weight":
            "Peso",
            "bmi":
            "IMC",
            "caprini":
            "Caprini",
            "factor":
            "Fator",
            "level":
            "Nível",
            "recs":
            "Recomendações",
            "recs_preview_note":
            "As recomendações completas estarão disponíveis no relatório final.",
            "psych":
            "Avaliação Psicológica",
            "psych_label":
            "Triagem psicológica",
            "conclusion":
            "Conclusão",
            "disclaimer":
            "Aviso legal",
            "disclaimer_body":
            ("Este relatório foi gerado automaticamente pelo AestheticSafe®. "
             "As informações são orientativas e devem ser validadas por um médico antes de qualquer decisão. "
             "Não substitui o julgamento clínico."),
            "code":
            "Código verificador",
            "date":
            "Data",
            "id":
            "ID",
        },
    }

    # ===== Imports locales =====
    try:
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from datetime import timezone as _tz
    except Exception:
        import json as _json
        lcode = (lang
                 or (getattr(st, "session_state", {}).get("idioma") if hasattr(
                     st, "session_state") else "ES") or "ES").upper()
        return _json.dumps(
            {
                "preview": preview,
                "full": full,
                "datos": datos,
                "lang": lcode
            },
            indent=2).encode("utf-8")

    # ===== Dados / setup =====
    from datetime import datetime as _dt
    import uuid
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    ML, MR, MT, MB = 2.2 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm
    y = H - MT

    # Idioma FINAL: prioridad lang>UI
    lcode = (lang or (st.session_state.get("idioma") if hasattr(
        st, "session_state") else "ES") or "ES").upper()
    T = PDF_TXT.get(lcode, PDF_TXT["ES"])

    rep_id = datos.get(
        "rep_id") or f"ESTH-{_dt.now(_tz.utc).strftime('%Y%m%d%H%M%S')}"
    paciente = datos.get("paciente", {}) or {}
    nombre = paciente.get("nombre", "—")
    edad = paciente.get("edad", "")
    altura_cm = paciente.get("altura_cm", "")
    peso_kg = paciente.get("peso_kg", "")
    bmi = datos.get("bmi", "")
    cap_score = datos.get("caprini_score", "")
    cap_cat = datos.get("caprini_categoria", "")
    factor = datos.get("factor_riesgo", datos.get("factor", ""))
    nivel = datos.get("nivel_riesgo", datos.get("nivel", ""))
    recs = datos.get("recomendaciones", [])
    psych_txt = datos.get("bdd_resultado") or datos.get(
        "psico_resultado") or ""
    conclusion = datos.get("conclusion", "")
    ver_code = datos.get("ver_code") or uuid.uuid4().hex[:8].upper()

    if isinstance(recs, str):
        recs = [r.strip() for r in recs.split("\n") if r.strip()]
    elif not isinstance(recs, list):
        recs = []

    # ===== Traducción de Caprini, Riesgo, Psicología y Conclusión =====
    CAPRINI_CAT = {
        "EN": {
            "Bajo (0–2)": "Low (0–2)",
            "Intermedio (3–8)": "Intermediate (3–8)",
            "Alto (>8)": "High (>8)",
        },
        "PT": {
            "Bajo (0–2)": "Baixo (0–2)",
            "Intermedio (3–8)": "Intermediário (3–8)",
            "Alto (>8)": "Alto (>8)",
        }
    }

    NIVEL_RIESGO_TXT = {
        "EN": {
            "Bajo": "Low",
            "Moderado": "Moderate",
            "Alto": "High"
        },
        "PT": {
            "Bajo": "Baixo",
            "Moderado": "Moderado",
            "Alto": "Alto"
        }
    }

    if lcode in ("EN", "PT"):
        cap_cat = CAPRINI_CAT.get(lcode, {}).get(cap_cat, cap_cat)
        nivel = NIVEL_RIESGO_TXT.get(lcode, {}).get(nivel, nivel)

    # Traducción del resultado psicológico
    if lcode == "EN":
        if "positivo" in psych_txt.lower():
            psych_txt = "Positive (suggested psychological consultation)"
        elif "negativo" in psych_txt.lower():
            psych_txt = "Negative"
    elif lcode == "PT":
        if "positivo" in psych_txt.lower():
            psych_txt = "Positivo (sugerida consulta psicológica)"
        elif "negativo" in psych_txt.lower():
            psych_txt = "Negativo"

    # Traducción de la conclusión si es genérica
    if lcode == "EN" and "Optimizar salud general" in conclusion:
        conclusion = "Optimize overall health and reassess before planning combined procedures."
    elif lcode == "PT" and "Optimizar salud general" in conclusion:
        conclusion = "Otimizar a saúde geral e reavaliar antes de planejar procedimentos combinados."

    # ===== Traducción de recomendaciones si PDF es EN o PT =====
    TRAD_RECS = {
        "Trabaja en reducir tu peso para alcanzar un IMC saludable.": {
            "EN": "Work on reducing your weight to reach a healthy BMI.",
            "PT": "Trabalhe para reduzir seu peso e atingir um IMC saudável."
        },
        "Sigue una dieta balanceada y realiza actividad física regular.": {
            "EN":
            "Maintain a balanced diet and engage in regular physical activity.",
            "PT":
            "Mantenha uma dieta equilibrada e pratique atividade física regularmente."
        },
        "Mantén tu peso actual con dieta balanceada y actividad física regular.":
        {
            "EN":
            "Maintain your current weight with a balanced diet and regular physical activity.",
            "PT":
            "Mantenha seu peso atual com uma dieta equilibrada e atividade física regular."
        },
        "Estas sugerencias no sustituyen el criterio médico.": {
            "EN": "These suggestions do not replace medical judgment.",
            "PT": "Estas sugestões não substituem o julgamento médico."
        },
        # --- Nuevas traducciones ---
        "Deja de fumar para reducir riesgos quirúrgicos y mejorar tu salud general. Consulta con un especialista si necesitas apoyo.":
        {
            "EN":
            "Quit smoking to reduce surgical risks and improve your overall health. Consult a specialist if you need support.",
            "PT":
            "Pare de fumar para reduzir riscos cirúrgicos e melhorar sua saúde geral. Consulte um especialista se precisar de apoio."
        },
        "Controla tu presión arterial regularmente y lleva un registro para tu médico.":
        {
            "EN":
            "Monitor your blood pressure regularly and keep a log for your doctor.",
            "PT":
            "Controle sua pressão arterial regularmente e mantenha um registro para seu médico."
        },
        "Mantén control estricto de glucosa y sigue indicaciones de tu endocrinólogo.":
        {
            "EN":
            "Keep strict glucose control and follow your endocrinologist's instructions.",
            "PT":
            "Mantenha controle estrito da glicose e siga as orientações do seu endocrinologista."
        },
        "Riesgo alto: solo cirugías simples hasta 3 h. Combinaciones no recomendadas.":
        {
            "EN":
            "High risk: simple procedures only up to 3 h. Combined procedures not recommended.",
            "PT":
            "Alto risco: apenas procedimentos simples de até 3 h. Combinações não recomendadas."
        },
        "Consultar con Endocrinología y monitorear hormonas tiroideas.": {
            "EN": "Consult with Endocrinology and monitor thyroid hormones.",
            "PT":
            "Consulte um endocrinologista e monitore hormônios da tireoide."
        },
        "Ergometría según criterio médico.": {
            "EN": "Exercise stress test as clinically indicated.",
            "PT": "Teste ergométrico conforme critério médico."
        },
        "Doppler de carótidas y score cálcico coronario (CAC).":
        {
            "EN":
            "Carotid Doppler and coronary artery calcium (CAC) score.",
            "PT":
            "Doppler de carótidas e escore de cálcio coronário (CAC)."
        },
        "Presurometría 24 h y Eco-estrés (ejercicio y reposo) según criterio médico.":
        {
            "EN":
            "24-hour ambulatory BP monitoring and stress echocardiography (exercise and rest) as clinically indicated.",
            "PT":
            "Pressurometria 24 h e Eco-estresse (exercício e repouso) conforme critério médico."
        },
    }

    if lcode in ("EN", "PT"):
        recs = [TRAD_RECS.get(r, {}).get(lcode, r) for r in recs]

    # ===== Helpers (interlineado ~1.5 y ancho controlado, con margen extra en títulos) =====
    _LINE = 15.0  # ~1.5 para font 10.5
    _WRAP = 86  # un poco más corto para evitar saturación

    def wrap_lines(text, max_chars=_WRAP):
        """Wrapper simple; si una 'palabra' supera el ancho, la corta."""
        t = (text or "").strip()
        if not t:
            return [""]
        words = t.split()
        out, line = [], []
        for w in words:
            # si una palabra es larguísima, la partimos
            while len(w) > max_chars:
                head, w = w[:max_chars - 1] + "…", w[max_chars - 1:]
                if line:
                    out.append(" ".join(line))
                    line = []
                out.append(head)
            test = (" ".join(line + [w])).strip()
            if len(test) <= max_chars:
                line.append(w)
            else:
                if line:
                    out.append(" ".join(line))
                line = [w]
        if line:
            out.append(" ".join(line))
        return out

    def H1(txt):
        """Título principal con margen superior y inferior extra para no superponer encabezado."""
        nonlocal y
        y -= 10  # margen superior extra
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(W / 2, y, txt)
        y -= (_LINE + 4)  # margen inferior extra

    def H2(txt):
        """Subtítulo/sección con separación clara."""
        nonlocal y
        y -= 10
        c.setFont("Helvetica-Bold", 12)
        c.drawString(ML, y, txt)
        y -= (_LINE - 1)

    def P(txt):
        """Párrafo estándar."""
        nonlocal y
        c.setFont("Helvetica", 10.5)
        for ln in wrap_lines(txt, _WRAP):
            c.drawString(ML, y, ln)
            y -= _LINE

    def Bullet(txt):
        """Lista con viñetas; líneas siguientes con sangría."""
        nonlocal y
        c.setFont("Helvetica", 10.5)
        for i, ln in enumerate(wrap_lines(txt, _WRAP)):
            if i == 0:
                c.drawString(ML, y, u"• " + ln)
            else:
                c.drawString(ML + 14, y, ln)
            y -= _LINE

    def KV(label, value):
        """Par etiqueta:valor en una línea."""
        nonlocal y
        c.setFont("Helvetica", 10.5)
        c.drawString(ML, y, f"{label}: {value}")
        y -= _LINE

    # ===== Cabecera =====
    y -= 18
    H1(T["title"])
    c.setFont("Helvetica", 9.5)
    c.drawRightString(
        W - MR, H - MT + 2,
        f'{T["date"]}: {_dt.now(_tz.utc).strftime("%Y-%m-%d %H:%M UTC")}')
    c.drawString(ML, H - MT + 2, f'{T["id"]}: {rep_id}')
    y -= 6
    c.setFont("Helvetica", 10)
    P(T["issued_by"])

    # ===== Paciente =====
    H2(T["patient"])
    KV(T["name"], nombre)
    if edad != "": KV(T["age"], str(edad))
    if altura_cm != "": KV(f'{T["height"]} (cm)', str(altura_cm))
    if peso_kg != "": KV(f'{T["weight"]} (kg)', str(peso_kg))
    if bmi != "": KV(T["bmi"], f"{bmi}")
    if cap_score != "":
        KV(T["caprini"], f"{cap_score}" + (f" ({cap_cat})" if cap_cat else ""))
    if factor != "":
        KV(T["factor"], f"{factor}" + (f" ({nivel})" if nivel else ""))

    # ===== Recomendaciones =====
    H2(T["recs"])
    if preview and not full:
        P(T["recs_preview_note"])
    elif recs:
        for r in recs:
            Bullet(r)
    else:
        P("-")

    # ===== Psico =====
    H2(T["psych"])
    P(f'{T["psych_label"]}: {psych_txt or "—"}')

    # ===== Conclusión =====
    if conclusion:
        H2(T["conclusion"])
        P(conclusion)

    # ===== Descargo =====
    H2(T["disclaimer"])
    P(T["disclaimer_body"])
    # ===== Código verificador =====
    y -= 6
    c.setFont("Helvetica", 9.5)
    c.drawString(ML, y, f'{T["code"]}: {ver_code}')

    # ===== Pie de página (una sola línea) =====
    c.setFont("Helvetica", 8)
    c.drawString(
        ML, MB + 10,
        "Bukret Pesce SB SRL · Arenales 2521 Piso 9, Buenos Aires · +54 9 11 3121-1468 · info@aestheticsafe.com"
    )

    # ===== Cierre del PDF (evita NoneType en Streamlit) =====
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# ===================== UI =====================
def autoscroll_to(element_id: str):
    """Generate HTML component to smoothly scroll to a specific element."""
    components.html(
        f"""
        <script>
        setTimeout(function() {{
            // Try ID first, then data-testid
            let elem = window.parent.document.querySelector('#{element_id}');
            if (!elem) {{
                elem = window.parent.document.querySelector('[data-testid*="{element_id}"]');
            }}
            if (elem) {{
                elem.scrollIntoView({{behavior: 'smooth', block: 'start'}});
            }}
        }}, 400);
        </script>
        """,
        height=0
    )

def trigger_autoscroll(target_section: str):
    """Callback to trigger autoscroll when a field changes."""
    if "autoscroll_target" not in st.session_state:
        st.session_state["autoscroll_target"] = None
    st.session_state["autoscroll_target"] = target_section


def inject_brand_css():
    log_step_once("session_open")
    
    # Splash Screen - Final Approved Version (Spectral, Pure White on Black, ≤2.0s)
    if "splash_done" not in st.session_state:
        st.session_state.splash_done = False
    
    if not st.session_state.splash_done:
        st.markdown("""
        <link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,300;0,800;1,300&display=swap" rel="stylesheet">
        
        <style>
        .splash-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100vw;
          height: 100vh;
          background: #000000 !important;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          animation: splashFade 2.0s ease-in-out forwards;
        }
        
        .splash-content {
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        
        .splash-title {
          font-family: 'Spectral', serif;
          font-weight: 800;
          font-size: clamp(2rem, 6vw, 3.5rem);
          color: #ffffff !important;
          margin: 0;
          padding: 0;
          opacity: 0;
          animation: fadeIn 1.0s ease-in forwards;
          text-shadow: none !important;
          filter: none !important;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
          white-space: nowrap;
        }
        
        .splash-tagline {
          font-family: 'Spectral', serif;
          font-weight: 400;
          font-style: italic;
          font-size: clamp(1rem, 2.8vw, 1.35rem);
          color: #ffffff !important;
          letter-spacing: 0.19em;
          margin-top: 0.8rem;
          margin-left: auto;
          margin-right: auto;
          padding: 0;
          opacity: 0;
          animation: fadeIn 1.0s ease-in 0.2s forwards;
          text-shadow: none !important;
          filter: none !important;
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
          width: fit-content;
          text-align: center;
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        @keyframes splashFade {
          0% { opacity: 1; }
          50% { opacity: 1; }
          100% { opacity: 0; visibility: hidden; pointer-events: none; }
        }
        </style>
        
        <div class="splash-overlay">
          <div class="splash-content">
            <h1 class="splash-title">AestheticSafe®</h1>
            <p class="splash-tagline">Beyond Risk. Toward Perfection.</p>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        import time
        time.sleep(2.0)
        st.session_state.splash_done = True
        st.rerun()

    st.markdown(
        """
        <style>
        /* ==== Grayscale Theme (AestheticSafe 3.0) ==== */
        :root{
          --brand-low:#6b7280;      /* Gray for Low risk */
          --brand-moderate:#4b5563; /* Darker gray for Moderate */
          --brand-high:#1f2937;     /* Near-black for High */
          --bg-main:#f7f9fc;
          --bg-dark:#1E1E1E;
          --bg-medium:#2A2A2A;
        }

        .main { background-color: var(--bg-main); }

        /* Buttons - grayscale with dark background */
        .stButton>button{
          background:var(--bg-medium)!important;
          color:#fff!important;
          font-weight:700!important;
          border-radius:10px!important;
          padding:.55rem 1rem!important;
          border:0!important;
          margin:4px 8px!important;
        }
        .stButton>button:hover{ 
          filter:brightness(1.2);
          background:var(--bg-dark)!important;
        }

        /* Inputs */
        .stTextInput>div>div>input,
        .stNumberInput input, 
        .stSelectbox div[data-baseweb="select"]{
          border-radius:10px!important;
        }

        /* Titles */
        h1, h2, h3{ color:#0f172a; }
        hr{ border:none; border-top:1px solid #e5e7eb; margin:1rem 0; }

        /* Badges - grayscale */
        .badge{
          display:inline-block; padding:.35rem .7rem; border-radius:999px;
          font-weight:700; font-size:.95rem;
        }
        .badge-low{ background:rgba(107,114,128,.12); color:#6b7280; }
        .badge-mod{ background:rgba(75,85,99,.15); color:#4b5563; }
        .badge-high{ background:rgba(31,41,55,.15); color:#1f2937; }

        /* Multiselect chips - grayscale */
        [data-baseweb="tag"]{
          border-radius:999px!important;
          font-weight:600!important;
          padding:0 .6rem!important;
        }

        /* Mobile-friendly: lateral margins */
        @media (max-width: 768px) {
          .main .block-container {
            padding-left: 1rem!important;
            padding-right: 1rem!important;
          }
          .stButton>button {
            margin: 6px 0!important;
            width: 100%!important;
          }
        }

        /* Slider fixes - prevent jumping */
        div[data-baseweb='slider']{
          margin-top:6px!important;
          margin-bottom:6px!important;
        }
        .stSlider{
          padding-top:6px!important;
          padding-bottom:6px!important;
        }

        /* Emoji feedback buttons */
        .emoji-btn {
          font-size: 2.5rem;
          background: transparent;
          border: 2px solid #e5e7eb;
          border-radius: 12px;
          padding: 1rem;
          cursor: pointer;
          transition: all 0.3s ease;
        }
        .emoji-btn:hover {
          border-color: var(--bg-medium);
          transform: scale(1.1);
        }

        /* Smooth scrolling */
        html {
          scroll-behavior: smooth;
        }

        /* Small notes */
        .small-note {font-size: 0.85rem; color: #666;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _read_paid_flag_from_query() -> bool:
    """True si la URL trae confirmación de pago (paid/mp/status)."""
    try:
        qp = st.query_params  # type: ignore[attr-defined]
        paid_raw = None
        if isinstance(qp, dict):
            paid_raw = qp.get("paid") or qp.get("mp") or qp.get("status")
            if isinstance(paid_raw, list):
                paid_raw = paid_raw[0] if paid_raw else None
    except Exception:
        paid_raw = None
    return str(paid_raw
               or "").lower() in ("1", "true", "ok", "approved",
                                  "approved_payment", "success", "paid")


# ===== Selector único de idioma PARA EL PDF (independiente del idioma de la UI) =====
PDF_LANGS = {
    "ES": "Español (PDF)",
    "EN": "English (PDF)",
    "PT": "Português (PDF)"
}


def pdf_lang_selector():
    st.markdown("### Idioma del PDF / PDF language / Idioma do PDF")
    # valor por defecto: el idioma detectado/seleccionado de la UI, si está disponible
    _default = st.session_state.get("idioma", "ES")
    if "pdf_lang" not in st.session_state:
        st.session_state["pdf_lang"] = _default if _default in ("ES", "EN",
                                                                "PT") else "ES"

    idx_pdf = ["ES", "EN", "PT"].index(st.session_state["pdf_lang"])
    st.selectbox(
        "Idioma del informe (solo afecta el PDF)",
        options=["ES", "EN", "PT"],
        index=idx_pdf,
        format_func=lambda k: PDF_LANGS[k],
        key="pdf_lang_ui",
    )
    # sincronizar valor canónico
    st.session_state["pdf_lang"] = st.session_state.get(
        "pdf_lang_ui", st.session_state["pdf_lang"])


def calculadora():
    # --- init estados persistentes ---
    st.session_state.setdefault("mail_sent", False)

    # --- i18n fallback para TXT (evita NameError si no se cargó el diccionario) ---
    TXT = (st.session_state.get("TXT") or {}).copy()
    TXT.setdefault("send_btn", "Enviar evaluación")
    TXT.setdefault("wa_done", "Listo")
    TXT.setdefault("send_not_avail",
                   "El envío por email no está disponible en este entorno.")
    TXT.setdefault("send_err", "Error enviando email ({etype}): {emsg}")
    TXT.setdefault("sent_ok", "✅ Informe enviado a {email}")
    TXT.setdefault("sent_fail", "❌ No se pudo enviar el informe")
    st.session_state["TXT"] = TXT

    inject_brand_css()

    # === Detección automática de idioma usando i18n_auto.py ===
    # Prioridad: 1) URL param ?lang=, 2) Browser Accept-Language header, 3) Default ES
    if I18N_AUTO_AVAILABLE:
        lang_code = detect_language()  # Returns 'es', 'en', 'pt'
        detected_lang = lang_code.upper()  # Convert to 'ES', 'EN', 'PT' for backward compatibility
    else:
        detected_lang = _read_lang_from_query()  # Fallback to old method
    
    # Actualizar idioma en session state (ambas keys para compatibilidad)
    st.session_state["idioma"] = detected_lang
    st.session_state["lang"] = detected_lang.lower()
    idioma = detected_lang

    # Subtítulo por idioma
    SUBTITLE = {
        "ES": "Evaluación prequirúrgica estética predictiva",
        "EN": "Predictive pre-surgical aesthetic assessment",
        "PT": "Avaliação estética pré-operatória preditiva",
    }


    # === Detección automática de idioma (sin selector visible) ===
    # El idioma se detecta automáticamente del navegador o del parámetro ?lang=en|pt|es
    # No hay selector manual visible en la interfaz

    # --- Textos y opciones i18n (manteniendo valores internos canónicos ES) ---
    _SMOKING_CANON = ["No", "Sí (1–7 por semana)", "Más de 7 por semana"]
    _YESNO_CANON = ["No", "Sí"]
    _THY_CANON = ["Normal", "Hipotiroidismo", "Hipertiroidismo"]

    _UI_TXT = {
        "ES": {
            "age": "Edad (años)",
            "weight": "Peso (kg)",
            "height": "Altura (cm)",
            "bmi_caption": "IMC: **{bmi:.1f}** <span style='color:#999;font-size:0.9em;'>(_rango: {category}_)</span>",
            "smoking": "Tabaquismo",
            "hta": "Hipertensión arterial",
            "diabetes": "Diabetes",
            "thyroid": "Tiroides",
            "bmi_underweight": "bajo peso",
            "bmi_healthy": "saludable",
            "bmi_overweight": "sobrepeso",
            "bmi_obese": "obesidad",
        },
        "EN": {
            "age": "Age (years)",
            "weight": "Weight (kg)",
            "height": "Height (cm)",
            "bmi_caption": "BMI: **{bmi:.1f}** <span style='color:#999;font-size:0.9em;'>(_range: {category}_)</span>",
            "smoking": "Smoking",
            "hta": "Hypertension",
            "diabetes": "Diabetes",
            "thyroid": "Thyroid",
            "bmi_underweight": "underweight",
            "bmi_healthy": "healthy",
            "bmi_overweight": "overweight",
            "bmi_obese": "obesity",
        },
        "PT": {
            "age": "Idade (anos)",
            "weight": "Peso (kg)",
            "height": "Altura (cm)",
            "bmi_caption": "IMC: **{bmi:.1f}** <span style='color:#999;font-size:0.9em;'>(_faixa: {category}_)</span>",
            "smoking": "Tabagismo",
            "hta": "Hipertensão arterial",
            "diabetes": "Diabetes",
            "thyroid": "Tireoide",
            "bmi_underweight": "abaixo do peso",
            "bmi_healthy": "saudável",
            "bmi_overweight": "sobrepeso",
            "bmi_obese": "obesidade",
        },
        "FR": {
            "age": "Âge (années)",
            "weight": "Poids (kg)",
            "height": "Taille (cm)",
            "bmi_caption": "IMC: **{bmi:.1f}** <span style='color:#999;font-size:0.9em;'>(_plage: {category}_)</span>",
            "smoking": "Tabagisme",
            "hta": "Hypertension artérielle",
            "diabetes": "Diabète",
            "thyroid": "Thyroïde",
            "bmi_underweight": "insuffisance pondérale",
            "bmi_healthy": "sain",
            "bmi_overweight": "surpoids",
            "bmi_obese": "obésité",
        },
    }
    _SMOKING_T = {
        "ES": {
            "No": "No",
            "Sí (1–7 por semana)": "Sí (1–7 por semana)",
            "Más de 7 por semana": "Más de 7 por semana"
        },
        "EN": {
            "No": "No",
            "Sí (1–7 por semana)": "Yes (1–7 per week)",
            "Más de 7 por semana": "More than 7 per week"
        },
        "PT": {
            "No": "Não",
            "Sí (1–7 por semana)": "Sim (1–7 por semana)",
            "Más de 7 por semana": "Mais de 7 por semana"
        },
    }
    _YESNO_T = {
        "ES": {
            "No": "No",
            "Sí": "Sí"
        },
        "EN": {
            "No": "No",
            "Sí": "Yes"
        },
        "PT": {
            "No": "Não",
            "Sí": "Sim"
        },
    }
    _THY_T = {
        "ES": {
            "Normal": "Normal",
            "Hipotiroidismo": "Hipotiroidismo",
            "Hipertiroidismo": "Hipertiroidismo"
        },
        "EN": {
            "Normal": "Normal",
            "Hipotiroidismo": "Hypothyroidism",
            "Hipertiroidismo": "Hyperthyroidism"
        },
        "PT": {
            "Normal": "Normal",
            "Hipotiroidismo": "Hipotireoidismo",
            "Hipertiroidismo": "Hipertireoidismo"
        },
    }

    _txt = _UI_TXT.get(idioma, _UI_TXT["ES"])
    _t_sm = lambda v: _SMOKING_T.get(idioma, _SMOKING_T["ES"]).get(v, v)
    _t_yn = lambda v: _YESNO_T.get(idioma, _YESNO_T["ES"]).get(v, v)
    _t_th = lambda v: _THY_T.get(idioma, _THY_T["ES"]).get(v, v)

    # === Datos personales ===
    c1, c2, c3 = st.columns(3)
    with c1:
        edad = st.slider(_txt["age"], 10, 95, 35, key="slider_edad_pi")
    with c2:
        peso = st.slider(_txt["weight"], 40, 200, 70, key="slider_peso_pi")
    with c3:
        altura = st.slider(_txt["height"],
                           120,
                           230,
                           165,
                           key="slider_altura_pi")

    bmi = round(peso / ((altura / 100)**2), 1)
    
    # Determinar categoría del IMC
    if bmi < 18.5:
        bmi_cat_key = "bmi_underweight"
    elif 18.5 <= bmi < 25:
        bmi_cat_key = "bmi_healthy"
    elif 25 <= bmi < 30:
        bmi_cat_key = "bmi_overweight"
    else:
        bmi_cat_key = "bmi_obese"
    
    bmi_category = _txt[bmi_cat_key]
    st.markdown(_txt["bmi_caption"].format(bmi=bmi, category=bmi_category), unsafe_allow_html=True)

    # === Salud actual ===
    c4, c5, c6, c7 = st.columns(4)
    with c4:
        tabaquismo = st.selectbox(_txt["smoking"],
                                  _SMOKING_CANON,
                                  index=0,
                                  format_func=_t_sm,
                                  key="select_tabaquismo",
                                  on_change=lambda: trigger_autoscroll("section-antecedentes"))
    with c5:
        hta_txt = st.selectbox(_txt["hta"],
                               _YESNO_CANON,
                               index=0,
                               format_func=_t_yn,
                               key="select_hta",
                               on_change=lambda: trigger_autoscroll("section-antecedentes"))
    with c6:
        diabetes_txt = st.selectbox(_txt["diabetes"],
                                    _YESNO_CANON,
                                    index=0,
                                    format_func=_t_yn,
                                    key="select_diabetes",
                                    on_change=lambda: trigger_autoscroll("section-antecedentes"))
    with c7:
        tiroides_txt = st.selectbox(_txt["thyroid"],
                                    _THY_CANON,
                                    index=0,
                                    format_func=_t_th,
                                    key="select_tiroides",
                                    on_change=lambda: trigger_autoscroll("section-antecedentes"))
    
    # Trigger autoscroll if a field was just changed
    if st.session_state.get("autoscroll_target"):
        autoscroll_to(st.session_state["autoscroll_target"])
        st.session_state["autoscroll_target"] = None
    
    # === Antecedentes y condición clínica actual ===
    st.markdown('<div id="section-antecedentes"></div>', unsafe_allow_html=True)
    _SEC_TXT = {
        "ES": {
            "title":
            "Antecedentes y condición clínica actual",
            "info":
            ("Seleccioná **todos** los antecedentes personales y familiares, y las "
             "**condiciones de salud actuales** que apliquen. Si dudás, dejá el ítem sin marcar."
             ),
            "past_label":
            "Antecedentes personales y familiares (pasado)",
            "curr_label":
            "Condiciones de salud actuales (hoy / futuro cercano)",
            "placeholder":
            "Seleccionar opciones",
        },
        "EN": {
            "title":
            "Medical history and current clinical condition",
            "info":
            ("Select **all** personal & family history, and the **current health conditions** that apply. "
             "If in doubt, leave the item unchecked."),
            "past_label":
            "Personal & family history (past)",
            "curr_label":
            "Current health conditions (today / near future)",
            "placeholder":
            "Choose options",
        },
        "PT": {
            "title":
            "Antecedentes e condição clínica atual",
            "info":
            ("Selecione **todos** os antecedentes pessoais e familiares e as "
             "**condições de saúde atuais** que se aplicam. Em caso de dúvida, deixe o item desmarcado."
             ),
            "past_label":
            "Antecedentes pessoais e familiares (passado)",
            "curr_label":
            "Condições de saúde atuais (hoje / futuro próximo)",
            "placeholder":
            "Escolher opções",
        },
    }
    _sec = _SEC_TXT.get(st.session_state.get("idioma", "ES"), _SEC_TXT["ES"])

    st.subheader(_sec["title"])
    st.info(_sec["info"])

    # ==== Traducción de ítems Caprini para mostrar (el valor interno queda en ES)
    # ===== Bloque 2: Traducciones CAPRINI + normalización/regex (pasado/actual) – FIX =====
    CAPRINI_T = {
        "EN": {
            # ==== HISTORY / PAST ====
            "Accidente cerebrovascular (ACV) reciente":
            "Recent cerebrovascular accident (stroke)",
            "Historia personal de trombosis venosa profunda/embolismo pulmonar":
            "Personal history of DVT/PE",
            "Antecedente familiar de trombosis o accidente cerebrovascular (ACV)":
            "Family history of blood clots or stroke",
            "Historia de artroplastia electiva de cadera/rodilla":
            "History of elective hip/knee arthroplasty",
            "Historia de fractura de cadera/pelvis/pierna":
            "History of hip/pelvis/leg fracture",
            "Historia de infarto de miocardio":
            "History of myocardial infarction",
            "Historia de trauma mayor":
            "History of major trauma",
            "Antecedentes obstétricos":
            "History of unexplained stillborn infant, recurrent spontaneous abortion (>3), or preterm birth with toxemia or growth restriction",
            "Trombofilia (test positivo de hipercoagulabilidad)":
            "Personal or family history of positive blood test indicating increased risk of clotting",
            "Varices":
            "Varicose veins",
            "Várices venosas":
            "Varicose veins",
            "Várices visibles":
            "Visible varicose veins",
            "Varices visibles":
            "Visible varicose veins",
            "Edema en miembro inferior":
            "Swollen legs (current)",
            "Piernas hinchadas":
            "Swollen legs (current)",
            "Parálisis":
            "Paralysis",
            "Lesión medular":
            "Spinal cord injury / paralysis",
            "Enfermedad inflamatoria intestinal":
            "Inflammatory bowel disease (IBD) e.g., Crohn’s disease or ulcerative colitis",
            "Insuficiencia cardíaca":
            "Heart failure",
            "Insuficiencia cardíaca congestiva":
            "Congestive heart failure",
            "Enfermedad pulmonar crónica (EPOC)":
            "Lung disease (e.g., emphysema/COPD)",

            # ==== CURRENT / TODAY (or near future) ====
            "Cáncer actual o previo":
            "Current or previous cancer",
            "Realizaré cirugía mayor (≥ 45 min)":
            "Planned major surgery (≥ 45 min)",
            "Realizaré cirugía menor (< 45 min)":
            "Planned minor surgery (< 45 min)",
            "Reposo en cama < 72 h o inmovilización breve":
            "Bed rest < 72 h or brief immobilization",
            "Reposo en cama ≥ 72 h o inmovilización prolongada":
            "Bed rest ≥ 72 h or prolonged immobilization",
            "Reposo en cama o movilidad limitada":
            "Bed rest or limited mobility",
            "Catéter venoso central (CVC/PICC)":
            "Central venous catheter (CVC/PICC/Port)",
            "Neumonía o infección respiratoria":
            "Pneumonia or respiratory infection",
            "Embarazo / gestación":
            "Pregnancy",
            "Puerperio (posparto)":
            "Postpartum (puerperium)",
            "Anticonceptivos orales / TRH":
            "Oral contraceptives / HRT",
            "Anticonceptivos / Terapia hormonal (ACO/TRH)":
            "Oral contraceptives / HRT",
            "Obesidad (IMC ≥ 30)":
            "Obesity (BMI ≥ 30)",
            "Yeso o inmovilización en el último mes":
            "Cast or non-removable immobilization in last month",
            "Yeso o férula en miembros inferiores":
            "Cast or splint on lower limbs",
            "Actualmente: tiene catéter venoso central / PICC / Port":
            "Currently has central venous catheter / PICC / Port",
        },
        "PT": {
            # ==== HISTÓRICO / PASSADO ====
            "Accidente cerebrovascular (ACV) reciente":
            "Acidente vascular cerebral (AVC) recente",
            "Antecedentes obstétricos":
            "Histórico de natimorto sem causa, abortos espontâneos recorrentes (>3) ou parto prematuro com toxemia/restrição de crescimento",
            "Antecedentes obstetricos":
            "Histórico de natimorto sem causa, abortos espontâneos recorrentes (>3) ou parto prematuro com toxemia/restrição de crescimento",
            "Antecedente obstetrico":
            "Histórico de natimorto sem causa, abortos espontâneos recorrentes (>3) ou parto prematuro com toxemia/restrição de crescimento",
            "Antecedente obstetrico":
            "Histórico de natimorto sem causa, abortos espontâneos recorrentes (>3) ou parto prematuro com toxemia/restrição de crescimento",
            "Historia personal de trombosis venosa profunda/embolismo pulmonar":
            "História pessoal de TVP/TEP",
            "Antecedente familiar de trombosis o accidente cerebrovascular (ACV)":
            "História familiar de trombose ou AVC",
            "Historia de artroplastia electiva de cadera/rodilla":
            "Histórico de artroplastia eletiva de quadril/joelho",
            "Historia de fractura de cadera/pelvis/pierna":
            "Histórico de fratura de quadril/pelve/perna",
            "Historia de infarto de miocardio":
            "Infarto agudo do miocárdio (histórico)",
            "Historia de trauma mayor":
            "Trauma maior (histórico)",
            "Antecedentes obstétricos":
            "Histórico de natimorto sem causa, abortos espontâneos recorrentes (>3) ou parto prematuro com toxemia/restrição de crescimento",
            "Trombofilia (test positivo de hipercoagulabilidad)":
            "Histórico pessoal ou familiar de teste positivo indicando maior risco de trombose",
            "Varices":
            "Varizes",
            "Várices venosas":
            "Varizes venosas",
            "Várices visibles":
            "Varizes venosas visíveis",
            "Varices visibles":
            "Varizes venosas visíveis",
            "Edema en miembro inferior":
            "Edema em pernas (atual)",
            "Piernas hinchadas":
            "Edema em pernas (atual)",
            "Parálisis":
            "Paralisia",
            "Lesión medular":
            "Lesão medular com paralisia",
            "Enfermedad inflamatoria intestinal":
            "Doença inflamatória intestinal (DII) p.ex., Crohn/retocolite",
            "Insuficiencia cardíaca":
            "Insuficiência cardíaca",
            "Insuficiencia cardíaca congestiva":
            "Insuficiência cardíaca congestiva",
            "Enfermedad pulmonar crónica (EPOC)":
            "Doença pulmonar crônica (DPOC)",

            # ==== ATUAL / HOJE ====
            "Cáncer actual o previo":
            "Câncer atual ou prévio",
            "Realizaré cirugía mayor (≥ 45 min)":
            "Cirurgia maior planejada (≥ 45 min)",
            "Realizaré cirugía menor (< 45 min)":
            "Cirurgia menor planejada (< 45 min)",
            "Reposo en cama < 72 h o inmovilización breve":
            "Repouso < 72 h ou imobilização breve",
            "Reposo en cama ≥ 72 h o inmovilización prolongada":
            "Repouso ≥ 72 h ou imobilização prolongada",
            "Reposo en cama o movilidad limitada":
            "Repouso no leito ou mobilidade limitada",
            "Catéter venoso central (CVC/PICC)":
            "Cateter venoso central (CVC/PICC/Port)",
            "Neumonía o infección respiratoria":
            "Pneumonia ou infecção respiratória",
            "Embarazo / gestación":
            "Gestação",
            "Puerperio (posparto)":
            "Puerpério (pós-parto)",
            "Anticonceptivos orales / TRH":
            "Anticoncepcionais orais / TRH",
            "Anticonceptivos / Terapia hormonal (ACO/TRH)":
            "Anticoncepcionais orais / TRH",
            "Obesidad (IMC ≥ 30)":
            "Obesidade (IMC ≥ 30)",
            "Yeso o inmovilización en el último mes":
            "Gesso ou imobilização não removível no último mês",
            "Yeso o férula en miembros inferiores":
            "Gesso ou tala nos membros inferiores",
            "Actualmente: tiene catéter venoso central / PICC / Port":
            "Atualmente com cateter venoso central / PICC / Port",
        },
    }

    # --- Fallback por tokens (sin el error de “failure cardíaca”)
    _TOKEN_MAP = {
        "EN": [
            ("Antecedente de", "History of"),
            ("Historia de", "History of"),
            ("Actualmente", "Currently"),
            ("artroplastia", "arthroplasty"),
            ("trauma mayor", "major trauma"),
            # NO mapeamos “insuficiencia” aquí para evitar “failure cardíaca”
            ("cirugía", "surgery"),
            ("neumonía", "pneumonia"),
            ("infección", "infection"),
            ("reposo", "bed rest"),
            ("en cama", ""),
            ("movilidad limitada", "limited mobility"),
            ("gestación", "pregnancy"),
            ("embarazo", "pregnancy"),
            ("puerperio", "postpartum"),
            ("catéter", "catheter"),
            ("fractura", "fracture"),
            ("cadera", "hip"),
            ("rodilla", "knee"),
            ("pelvis", "pelvis"),
            ("pierna", "leg"),
            ("obstétricos", "obstetric"),
            ("enfermedad inflamatoria", "inflammatory bowel disease"),
            ("varices", "varicose veins"),
            ("várices", "varicose veins"),
            ("piernas hinchadas", "leg swelling"),
            ("edema", "swelling"),
            ("parálisis", "paralysis"),
            ("yeso", "cast"),
            ("férula", "splint"),
            ("molde", "cast"),
            ("miembros inferiores", "lower limbs"),
            ("cvc", "CVC"),
            ("picc", "PICC"),
            ("port", "Port"),
        ],
        "PT": [
            ("Antecedente de", "História de"),
            ("Historia de", "História de"),
            ("Actualmente", "Atualmente"),
            ("artroplastia", "artroplastia"),
            ("trauma mayor", "trauma maior"),
            ("no removible", "não removível"),
            ("ultimo mes", "último mês"),
            ("miocardio", "miocárdio"),
            # idem: no mapeamos “insuficiencia”
            ("cirugía", "cirurgia"),
            ("neumonía", "pneumonia"),
            ("infección", "infecção"),
            ("reposo", "repouso"),
            ("en cama", "no leito"),
            ("movilidad limitada", "mobilidade limitada"),
            ("gestación", "gestação"),
            ("embarazo", "gestação"),
            ("puerperio", "puerpério"),
            ("catéter", "cateter"),
            ("fractura", "fratura"),
            ("cadera", "quadril"),
            ("rodilla", "joelho"),
            ("pelvis", "pelve"),
            ("pierna", "perna"),
            ("enfermedad inflamatoria", "doença inflamatória"),
            ("varices", "varizes"),
            ("várices", "varizes"),
            ("piernas hinchadas", "edema em pernas"),
            ("edema", "edema"),
            ("parálisis", "paralisia"),
            ("yeso", "gesso"),
            ("férula", "tala"),
            ("molde", "gesso"),
            ("miembros inferiores", "membros inferiores"),
        ],
    }

    # --- Normalización y patrones para coincidencias no exactas
    import re as _re, unicodedata as _ud

    def _norm_txt(s: str) -> str:
        if not s: return ""
        s = _ud.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        s = s.lower().strip()
        s = s.replace("  ", " ")
        s = s.replace(" trh", " hrt")  # normalizar TRH↔HRT
        return s

    # Patrones EN: cubren híbridos y errores frecuentes
    _REGEX_EN = [
        # obstetric (incluye faltas y sin acento)
        (_re.compile(r"antecedentes?\s+obst[eé]tric\w*", _re.I),
         "History of unexplained stillborn infant, recurrent spontaneous abortion (>3), or preterm birth with toxemia or growth restriction"
         ),
        (_re.compile(r"c[aá]ncer\s+actual\s+o\s+previo",
                     _re.I), "Current or previous cancer"),
        (_re.compile(
            r"actualmente:?\s*tiene\s*cat[eé]ter\s+venoso\s+central\b.*",
            _re.I), "Currently has central venous catheter / PICC / Port"),
        (_re.compile(r"anticonceptiv.*(aco|hrt|trh)",
                     _re.I), "Oral contraceptives / HRT"),
        (_re.compile(r"lesi[oó]n\s+medular",
                     _re.I), "Spinal cord injury / paralysis"),
        (_re.compile(r"(infecci[oó]n\s+seria|neumon[ií]a)",
                     _re.I), "Pneumonia or respiratory infection"),
        (_re.compile(r"\breciente\b.*(acv|accidente\s+cerebrovascular)",
                     _re.I), "Recent cerebrovascular accident (stroke)"),
        (_re.compile(r"realizar[ée]\s+cirug[ií]a\s+mayor",
                     _re.I), "Planned major surgery (≥ 45 min)"),
        (_re.compile(r"realizar[ée]\s+cirug[ií]a\s+menor",
                     _re.I), "Planned minor surgery (< 45 min)"),
        (_re.compile(r"reposo\s*en\s*cama\s*o\s*movilidad\s*limitada",
                     _re.I), "Bed rest or limited mobility"),
        (_re.compile(
            r"(yeso|inmovilizaci[oó]n)\s+.*(no\s*removible|no\s*removibles|no\-removible).*(mes|último\s+mes)",
            _re.I), "Cast or non-removable immobilization in last month"),
        (_re.compile(r"infarto\s+de\s+miocardio",
                     _re.I), "History of myocardial infarction"),
        (_re.compile(r"trauma\s+mayor", _re.I), "History of major trauma"),
        (_re.compile(r"insuficiencia\s+card[ií]aca\s+congestiva",
                     _re.I), "Congestive heart failure"),
        (_re.compile(r"insuficiencia\s+card[ií]aca\b",
                     _re.I), "Heart failure"),
        (_re.compile(r"artroplastia.*(cadera|rodilla)",
                     _re.I), "History of elective hip/knee arthroplasty"),
    ]

    # Patrones PT
    _REGEX_PT = [
        # Obstétricos exacto (con/sin acento, singular/plural) -> texto largo
        (_re.compile(r"antecedentes?\s+obst[eé]tricos?$", _re.I),
         "Histórico de natimorto sem causa, abortos espontâneos recorrentes (>3) ou parto prematuro com toxemia/restrição de crescimento"
         ),

        # Variante que a veces queda “gesso o gesso … en el último mes” -> normalizar a PT final
        (_re.compile(
            r"(?:^|[\s,;])gesso\s*o\s*gesso.*(?:no\s*removible|n[aã]o\s*remov[ií]vel).*(?:en\s+el\s+)?(?:[úu]ltim[oa]\s+m[eê]s|ultimo\s+mes)\b",
            _re.I), "Gesso ou imobilização não removível no último mês"),

        # Infarto híbrido ("História de infarto de miocardio") -> PT final correcto
        (_re.compile(r"hist[óo]?ria\s+de\s+infarto\s+de\s+miocardio",
                     _re.I), "Infarto agudo do miocárdio (histórico)"),

        # Yeso/gesso + no removible + último mes (mixto ES/PT) -> PT final correcto
        (_re.compile(
            r"^(yeso|gesso)\s*o\s*(?:inmovilizaci[oó]n|imobiliza[cç][aã]o|gesso).*(no\s*removible|n[aã]o\s*remov[ií]vel).*(últim[oa]\s+m[eê]s|ultimo\s+mes)\b",
            _re.I), "Gesso ou imobilização não removível no último mês"),

        # Neumonía/infecção — fuerza "recente ou ... grave"
        (_re.compile(r"(neumonia|infec[cç][aã]o\s+respirat[óo]ria)", _re.I),
         "Pneumonia recente ou infecção respiratória grave"),

        # Yeso / imobilização no último mês — cubre variantes híbridas (gesso/no removible/etc.)
        (_re.compile(
            r"(yeso|gesso)\s*o\s*(inmovilizaci[oó]n|imobiliza[cç][aã]o|gesso).*(no\s*removible|n[aã]o\s*remov[ií]vel).*(últim[oa]\s+m[eê]s|ultimo\s+mes)\b",
            _re.I), "Gesso ou imobilização não removível no último mês"),

        # --- NUEVAS: cirugías planificadas ---
        (_re.compile(r"realizar[ée]\s+cirug[ií]a\s+mayor(?:\s*\([^)]*\))?",
                     _re.I), "Cirurgia maior planejada (≥ 45 min)"),
        (_re.compile(r"realizar[ée]\s+cirug[ií]a\s+menor(?:\s*\([^)]*\))?",
                     _re.I), "Cirurgia menor planejada (< 45 min)"),

        # (resto de reglas ya existentes)
        (_re.compile(r"c[aá]ncer\s+actual\s+o\s+previo",
                     _re.I), "Câncer atual ou prévio"),
        (_re.compile(r"hist[óo]?ria\s+de\s+infarto\s+de\s+miocardio",
                     _re.I), "Infarto agudo do miocárdio (histórico)"),
        (_re.compile(r"antecedentes?\s+obstetr\w*", _re.I),
         "Histórico de natimorto sem causa, abortos espontâneos recorrentes (>3) ou parto prematuro com toxemia/restrição de crescimento"
         ),
        (_re.compile(
            r"actualmente:?\s*tiene\s*cat[eé]ter\s+venoso\s+central\b.*",
            _re.I), "Atualmente com cateter venoso central / PICC / Port"),
        (_re.compile(r"^\s*en\s+reposo\s+en\s*cama\s*≥?\s*72\s*h?",
                     _re.I), "Em repouso no leito ≥ 72 h"),
        (_re.compile(r"antecedentes?\s+obstetr\w*", _re.I),
         "Histórico de natimorto sem causa, abortos espontâneos recorrentes (>3) ou parto prematuro com toxemia/restrição de crescimento"
         ),
        (_re.compile(r"anticoncep.*(aco|hrt|trh)",
                     _re.I), "Anticoncepcionais orais / TRH"),
        (_re.compile(r"les[aã]o\s+medular",
                     _re.I), "Lesão medular com paralisia"),
        (_re.compile(r"(neumonia|infec[cç][aã]o\s+respirat[óo]ria)", _re.I),
         "Pneumonia recente ou infecção respiratória grave"),
        (_re.compile(
            r"repous[ou]\s*(no)?\s*leito\s*ou\s*mobilidade\s*limitada",
            _re.I), "Repouso no leito ou mobilidade limitada"),
        (_re.compile(
            r"(gesso|imobiliza).*(n[aã]o\s*remov[ií]vel).*(m[eê]s|último\s+m[eê]s)",
            _re.I), "Gesso ou imobilização não removível no último mês"),
        (_re.compile(r"infarto\s+do\s+mioc[aá]rdio",
                     _re.I), "Infarto do miocárdio (histórico)"),
        (_re.compile(r"trauma\s+maior", _re.I), "Trauma maior (histórico)"),
        (_re.compile(r"insufici[eê]ncia\s+card[ií]aca\s+congestiva",
                     _re.I), "Insuficiência cardíaca congestiva"),
        (_re.compile(r"insufici[eê]ncia\s+card[ií]aca\b",
                     _re.I), "Insuficiência cardíaca"),
        (_re.compile(r"artroplastia.*(quadril|joelho).*(eletiva)?", _re.I),
         "Histórico de artroplastia eletiva de quadril/joelho"),
    ]

    # Mapas normalizados para coincidencias no exactas
    _NORM_MAP_EN = {_norm_txt(k): v for k, v in CAPRINI_T["EN"].items()}
    _NORM_MAP_PT = {_norm_txt(k): v for k, v in CAPRINI_T["PT"].items()}

    # === Helpers de presentación ===
    _ACRON_RE = _re.compile(r"\(([A-Z]{2,}|[A-Z]{2,}\s*/\s*[A-Z]{2,})\)")
    _PAREN_LONG = _re.compile(r"\(([^)]+)\)")
    _PREFIX_RE = _re.compile(r"^(Antecedente de|Historia de|Actualmente)\s*",
                             _re.I)

    def _abreviar_caprini(txt: str) -> str:
        if not txt: return ""
        kept = [m.group(0) for m in _ACRON_RE.finditer(txt)]
        t = _PREFIX_RE.sub("", txt).strip()

        def shrink(m):
            return m.group(0) if m.group(0) in kept else ""

        t = _PAREN_LONG.sub(shrink, t).strip()
        t = t.replace("últimos meses", "últ. meses")
        return t

    def _trad_caprini(label: str, idioma: str) -> str:
        if idioma == "ES":
            return label
        # 1) Exacto
        direct = CAPRINI_T.get(idioma, {}).get(label)
        if direct:
            return direct
        # 2) Normalizado + regex
        n = _norm_txt(label)
        if idioma == "EN":
            if n in _NORM_MAP_EN: return _NORM_MAP_EN[n]
            for pat, rep in _REGEX_EN:
                if pat.search(label): return rep
        elif idioma == "PT":
            if n in _NORM_MAP_PT: return _NORM_MAP_PT[n]
            for pat, rep in _REGEX_PT:
                if pat.search(label): return rep
        # 3) Fallback por tokens
        t = label
        for es, tr in _TOKEN_MAP.get(idioma, []):
            t = _re.sub(rf"\b{_re.escape(es)}\b", tr, t, flags=_re.IGNORECASE)
        return t

    def _label_caprini(x: str) -> str:
        lang = (st.session_state.get("idioma", "ES") or "ES").upper()
        return _abreviar_caprini(_trad_caprini(x, lang))

    def _es_actual(item: str) -> bool:
        s = (item or "")
        sl = s.lower()
        # ES
        es_hit = any(k in sl for k in [
            "actual", "catéter", "picc", "port", "neumon",
            "infección respiratoria", "inmovilización", "reposo", "en cama",
            "movilidad limitada", "gestación", "embarazo", "puerperio",
            "cirugía", "yeso", "férula", "molde", "cáncer actual",
            "cáncer previo"
        ])
        # EN
        en_hit = any(k in sl for k in [
            "currently", "catheter", "picc", "port", "pneumonia", "infection",
            "immobil", "bed rest", "limited mobility", "pregnancy",
            "postpartum", "surgery", "cast", "splint", "cancer"
        ])
        return es_hit or en_hit

    # ===== Fin Bloque 2 =====

    try:
        OPC_ACTUALES = [x for x in CAPRINI_TODOS if _es_actual(x)]
        OPC_ANTECEDENTES = [x for x in CAPRINI_TODOS if x not in OPC_ACTUALES]
    except NameError:
        OPC_ACTUALES, OPC_ANTECEDENTES = [], []

    antecedentes_previos: List[str] = st.multiselect(
        _sec["past_label"],
        OPC_ANTECEDENTES,
        format_func=_label_caprini,
        key="caprini_previos",
        placeholder=_sec.get("placeholder", "Choose options"),
    )

    condiciones_actuales: List[str] = st.multiselect(
        _sec["curr_label"],
        OPC_ACTUALES,
        format_func=_label_caprini,
        key="caprini_actuales",
        placeholder=_sec.get("placeholder", "Choose options"),
    )
    
    # Trigger autoscroll if antecedentes were just changed
    if st.session_state.get("autoscroll_target"):
        autoscroll_to(st.session_state["autoscroll_target"])
        st.session_state["autoscroll_target"] = None

    # --- Normalizaciones ---
    def _is_reposo_corto(txt: str) -> bool:
        s = (txt or "").lower()
        return ("reposo" in s or "inmov" in s) and ("<" in s and "72" in s)

    def _is_reposo_largo(txt: str) -> bool:
        s = (txt or "").lower()
        return ("reposo" in s or "inmov" in s) and (("≥" in s and "72" in s) or
                                                    (">=" in s and "72" in s))

    if any(_is_reposo_corto(x) for x in condiciones_actuales) and any(
            _is_reposo_largo(x) for x in condiciones_actuales):
        condiciones_actuales = [
            x for x in condiciones_actuales if _is_reposo_largo(x)
            or not (_is_reposo_corto(x) or _is_reposo_largo(x))
        ]

    if any("realizaré cirugía mayor" in x.lower() for x in condiciones_actuales) and \
       any("realizaré cirugía menor" in x.lower() for x in condiciones_actuales):
        condiciones_actuales = [
            x for x in condiciones_actuales
            if "cirugía mayor" in x.lower() or "cirugía" not in x.lower()
        ]

    antecedentes_todos: List[str] = antecedentes_previos + condiciones_actuales
    st.session_state["caprini_seleccion"] = antecedentes_todos

    if any(_is_reposo_corto(x) for x in antecedentes_todos) and any(
            _is_reposo_largo(x) for x in antecedentes_todos):
        antecedentes_todos = [
            x for x in antecedentes_todos if not _is_reposo_corto(x)
        ]

    has_mayor = any("realizaré cirugía mayor" in x.lower()
                    for x in antecedentes_todos)
    has_menor = any("realizaré cirugía menor" in x.lower()
                    for x in antecedentes_todos)
    if has_mayor and has_menor:
        antecedentes_todos = [
            x for x in antecedentes_todos if "cirugía menor" not in x.lower()
        ]

    # --- Cálculo Caprini (¡no mover de acá!) ---

    cap_score, cap_det = caprini_desde(antecedentes_todos)
    cap_cat = caprini_categoria(cap_score)
    f = factor_riesgo_fn(edad, bmi, tabaquismo, cap_score)
    nivel = nivel_por_factor(f)

    # === Helper for Yes/No labels ===
    def yn_labels(lang: str | None) -> tuple[str, str]:
        l = (lang or "ES").upper()
        if l == "EN": return ("No", "Yes")
        if l == "PT": return ("Não", "Sim")
        return ("No", "Sí")

    # === Helper for i18n labels ===
    def i18n_label(es: str, en: str, pt: str, fr: str = "") -> str:
        lang = (st.session_state.get("idioma", "ES") or "ES").upper()
        return {"ES": es, "EN": en, "PT": pt, "FR": fr or es}.get(lang, en)

    # === Centralized gating logic (removed local function to avoid shadowing) ===

    # === Screening Psicológico (i18n) ===
    expander_title = {
        "ES": "Preocupaciones psicológicas (opcional)",
        "EN": "Psychological concerns (optional)",
        "PT": "Preocupações psicológicas (opcional)",
    }.get(idioma, "Preocupaciones psicológicas (opcional)")

    with st.expander(f"💭 {expander_title}", expanded=False):
        info_txt = {
            "ES":
            "Estas preguntas son orientativas y no reemplazan una consulta profesional.",
            "EN":
            "These questions are for guidance and do not replace professional care.",
            "PT":
            "Estas perguntas são orientativas e não substituem uma consulta profissional.",
        }.get(idioma)
        st.info(info_txt)

        no_lbl, yes_lbl = yn_labels(idioma)

        q1_label: str = i18n_label(
            "¿Te preocupa mucho la apariencia de alguna parte de tu cuerpo?",
            "Are you very worried about the appearance of any body part?",
            "Você se preocupa muito com a aparência de alguma parte do seu corpo?"
        ) or "¿Te preocupa mucho la apariencia de alguna parte de tu cuerpo?"
        q1 = st.radio(
            label=q1_label,
            options=[no_lbl, yes_lbl],
            horizontal=True,
            key="q1_radio",
        )

        q2 = no_lbl
        q3 = no_lbl
        q4 = no_lbl
        if q1 == yes_lbl:
            q2_label: str = i18n_label(
                "¿Pensás mucho en eso y desearías poder pensar menos?",
                "Do you think about it a lot and wish you could think about it less?",
                "Você pensa muito nisso e gostaria de pensar menos?"
            ) or "¿Pensás mucho en eso y desearías poder pensar menos?"
            q2 = st.radio(
                label=q2_label,
                options=[no_lbl, yes_lbl],
                horizontal=True,
                key="q2_radio",
            )

            if q2 == yes_lbl:
                q3_label: str = i18n_label(
                    "¿Te causa angustia o malestar significativo?",
                    "Does it cause significant distress?",
                    "Isso causa angústia ou sofrimento significativo?",
                ) or "¿Te causa angustia o malestar significativo?"
                q3 = st.radio(
                    label=q3_label,
                    options=[no_lbl, yes_lbl],
                    horizontal=True,
                    key="q3_radio",
                )

            q4_label: str = i18n_label(
                "¿Tenés **dificultad para aumentar de peso** o **miedo intenso a engordar** (p. ej., evitás comer para no subir)?",
                "Do you have **difficulty gaining weight** or **intense fear of gaining weight** (e.g., avoid eating to avoid weight gain)?",
                "Você tem **dificuldade para ganhar peso** ou **medo intenso de engordar** (ex.: evita comer para não ganhar peso)?"
            ) or "¿Tenés **dificultad para aumentar de peso** o **miedo intenso a engordar** (p. ej., evitás comer para no subir)?"
            q4 = st.radio(
                label=q4_label,
                options=[no_lbl, yes_lbl],
                horizontal=True,
                key="q4_radio",
            )

        bdd_pos = (q1 == yes_lbl and q2 == yes_lbl and q3 == yes_lbl)
        if bdd_pos and q4 == yes_lbl:
            resultado_psico = "BDD negativo; posible trastorno alimentario"
        elif bdd_pos:
            resultado_psico = "BDD positivo (sugerir consulta psicológica)"
        elif q4 == yes_lbl:
            resultado_psico = "Posible trastorno alimentario (sin criterios de BDD)"
        else:
            resultado_psico = "Negativo"

        st.session_state["bdd_resultado"] = resultado_psico
        st.session_state["psico_resultado"] = resultado_psico
        st.session_state["bdd_respuestas"] = {
            "q1": q1,
            "q2": q2,
            "q3": q3,
            "q4": q4
        }
        st.session_state["tdc_positive"] = ("bdd positivo"
                                            in resultado_psico.lower())

# ---- Descarga / pago / compartir  (i18n ES/EN/PT) ----
    _lang = st.session_state.get("idioma", "ES")

    TXT = {
        "ES": {
            "section":
            "Elegí cómo querés recibir tu informe",
            "name":
            "Nombre (opcional)",
            "email":
            "Email",
            "email_ph":
            "tunombre@mail.com",
            "phone":
            "Teléfono",
            "phone_ph":
            "+54 9 …",
            "consent":
            "Acepto compartir estos datos para recibir mi informe y seguimiento.",
            "medico":
            "¿Querés compartirlo con alguien? Por ejemplo, tu médico.",
            "medico_ph":
            "Ingresá su email (opcional)",
            "gate_title":
            "Elegí cómo querés recibir tu informe",
            "gate_subtitle":
            "💎 Pagar reporte completo · 💬 Compartir y descargar gratis",
            "gate_pay":
            "💳 Pagar y descargar (Pesos Arg. $65500)",
            "gate_share":
            "👉 Compartí la app por WhatsApp y descargá gratis tu informe.",
            "pay_info":
            "Se abrirá Mercado Pago en una pestaña nueva. El informe final se habilitará cuando regreses con confirmación.",
            "pay_link":
            "Ir a pagar / revisar en Mercado Pago",
            "pay_done":
            "✅ Ya realicé el pago",
            "pay_code":
            "Pegá el código de pago (opcional)",
            "pay_code_help":
            "Se acepta cualquier comprobante alfanumérico de ≥6 caracteres.",
            "zelle_opt":
            "Pagar con Zelle",
            "zelle_info":
            "Paga con Zelle y pegá el código/nota de pago. Se acepta cualquier referencia alfanumérica.",
            "zelle_done":
            "✅ Ya pagué por Zelle",
            "zelle_amount_ph":
            "Monto en USD (opcional)",
            "zelle_code_ph":
            "Código/nota de Zelle (opcional)",
            "zelle_cta":
            "Ver datos de Zelle",
            "wa_cta":
            "📲 Compartir por WhatsApp",
            "wa_done":
            "✅ Ya compartí por WhatsApp",
            "need_fields":
            "Completá **email**, **teléfono** y el **consentimiento** para continuar.",
            "prev_btn":
            "📄 Descargar vista previa (PDF)",
            "locked":
            "El informe final se habilitará cuando confirmes pago o compartas por WhatsApp.",
            "final_btn":
            "⬇️ Descargar informe final (PDF)",
            "send_btn":
            "📧 Enviarme por email",
            "sent_ok":
            "Informe enviado a {email}. Revisá tu bandeja (y spam).",
            "sent_fail":
            "El servidor no confirmó el envío del informe.",
            "send_not_avail":
            "La función de envío de email no está disponible en este entorno.",
            "send_err":
            "No se pudo enviar: {etype}: {emsg}",
            "zelle_to":
            "Enviar para",
            "mail_sent":
            "📧 ¡Enviado a {email}! Revisá tu casilla (y la carpeta de spam/promociones).",  # ES
            "wa_text":
            "Conocé tu nivel de riesgo estético con AestheticSafe. Probalo en 1 minuto y compartilo con alguien que cuidás: {link} #AestheticSafe",
        },
        "EN": {
            "section":
            "Choose how to receive your report",
            "name":
            "Name (optional)",
            "email":
            "Email",
            "email_ph":
            "yourname@email.com",
            "phone":
            "Phone",
            "phone_ph":
            "+1 …",
            "consent":
            "I agree to share this information to receive my report and follow-up.",
            "medico":
            "Would you like to share it with someone? For example, your doctor.",
            "medico_ph":
            "Enter their email (optional)",
            "gate_title":
            "Choose how to receive your report",
            "gate_subtitle":
            "💎 Pay for complete report · 💬 Share and download free",
            "gate_pay":
            "💳 Pay and download (ARS $65500)",
            "gate_share":
            "👉 Share the app on WhatsApp and download your report for free.",
            "pay_info":
            "Mercado Pago will open in a new tab. The final report will unlock once you return with confirmation.",
            "pay_link":
            "Go to pay / review in Mercado Pago",
            "pay_done":
            "✅ I've already paid",
            "pay_code":
            "Paste your payment code (optional)",
            "pay_code_help":
            "Any alphanumeric receipt ≥6 chars is accepted.",
            "wa_cta":
            "📲 Share on WhatsApp",
            "wa_done":
            "✅ I already shared on WhatsApp",
            "need_fields":
            "Please fill **email**, **phone** and **consent** to continue.",
            "prev_btn":
            "📄 Download preview (PDF)",
            "locked":
            "The final report will be enabled after payment or WhatsApp share.",
            "final_btn":
            "⬇️ Download final report (PDF)",
            "send_btn":
            "📧 Send me by email",
            "sent_ok":
            "Report sent to {email}. Check your inbox (and spam).",
            "sent_fail":
            "The server didn't confirm the email send.",
            "send_not_avail":
            "Email send function is not available in this environment.",
            "send_err":
            "Could not send: {etype}: {emsg}",
            "zelle_to":
            "Send to",
            "mail_sent":
            "📧 Sent to {email}! Check your inbox (and the spam/promotions folder).",  # EN
            "wa_text":
            "Find out your aesthetic risk level with AestheticSafe and share it with someone you care about: {link}  #AestheticSafe",
        },
        "PT": {
            "section":
            "Escolha como receber seu relatório",
            "name":
            "Nome (opcional)",
            "email":
            "Email",
            "email_ph":
            "seunome@email.com",
            "phone":
            "Telefone",
            "phone_ph":
            "+55 …",
            "consent":
            "Concordo em compartilhar estes dados para receber meu relatório e acompanhamento.",
            "medico":
            "Quer compartilhar com alguém? Por exemplo, seu médico.",
            "medico_ph":
            "Digite o e-mail (opcional)",
            "gate_title":
            "Escolha como receber seu relatório",
            "gate_subtitle":
            "💎 Pagar relatório completo · 💬 Compartilhar e baixar grátis",
            "gate_pay":
            "💳 Pagar e baixar (ARS $65500)",
            "gate_share":
            "👉 Compartilhe o app no WhatsApp e baixe seu relatório grátis.",
            "pay_info":
            "O Mercado Pago abrirá em uma nova aba. O relatório final será liberado quando você retornar com a confirmação.",
            "pay_link":
            "Ir pagar / revisar no Mercado Pago",
            "pay_done":
            "✅ Já realizei o pagamento",
            "pay_code":
            "Cole o código do pagamento (opcional)",
            "pay_code_help":
            "Aceita-se qualquer comprovante alfanumérico com ≥6 caracteres.",
            "wa_cta":
            "📲 Compartilhar no WhatsApp",
            "wa_done":
            "✅ Já compartilhei no WhatsApp",
            "need_fields":
            "Preencha **email**, **telefone** e o **consentimento** para continuar.",
            "prev_btn":
            "📄 Baixar pré-via (PDF)",
            "locked":
            "O relatório final será habilitado após o pagamento ou o compartilhamento no WhatsApp.",
            "final_btn":
            "⬇️ Baixar relatório final (PDF)",
            "send_btn":
            "📧 Enviar para meu email",
            "sent_ok":
            "Relatório enviado para {email}. Verifique sua caixa de entrada (e spam).",
            "sent_fail":
            "O servidor não confirmou o envio do email.",
            "zelle_to":
            "Enviar para",
            "send_not_avail":
            "A função de envio de email não está disponível neste ambiente.",
            "send_err":
            "Não foi possível enviar: {etype}: {emsg}",
            "mail_sent":
            "📧 Enviado para {email}! Verifique sua caixa de entrada (e as pastas de spam/promoções).",  # PT
            "wa_text":
            "Conheça seu nível de risco estético com o AestheticSafe e compartilhe com alguém importante: {link}  #AestheticSafe",
        },
        "FR": {
            "section":
            "Choisissez comment recevoir votre rapport",
            "name":
            "Nom (optionnel)",
            "email":
            "Email",
            "email_ph":
            "votrenom@email.com",
            "phone":
            "Téléphone",
            "phone_ph":
            "+33 …",
            "consent":
            "J'accepte de partager ces informations pour recevoir mon rapport et le suivi.",
            "medico":
            "Voulez-vous le partager avec quelqu'un? Par exemple, votre médecin.",
            "medico_ph":
            "Entrez leur e-mail (optionnel)",
            "gate_title":
            "Choisissez comment recevoir votre rapport",
            "gate_subtitle":
            "💎 Payer le rapport complet · 💬 Partager et télécharger gratuitement",
            "gate_pay":
            "💳 Payer et télécharger (ARS $65500)",
            "gate_share":
            "👉 Partagez l'application sur WhatsApp et téléchargez votre rapport gratuitement.",
            "pay_info":
            "Mercado Pago s'ouvrira dans un nouvel onglet. Le rapport final sera débloqué une fois que vous reviendrez avec la confirmation.",
            "pay_link":
            "Aller payer / vérifier dans Mercado Pago",
            "pay_done":
            "✅ J'ai déjà payé",
            "pay_code":
            "Collez votre code de paiement (optionnel)",
            "pay_code_help":
            "Tout reçu alphanumérique ≥6 caractères est accepté.",
            "wa_cta":
            "📲 Partager sur WhatsApp",
            "wa_done":
            "✅ J'ai déjà partagé sur WhatsApp",
            "need_fields":
            "Veuillez remplir **email**, **téléphone** et le **consentement** pour continuer.",
            "prev_btn":
            "📄 Télécharger l'aperçu (PDF)",
            "locked":
            "Le rapport final sera activé après le paiement ou le partage WhatsApp.",
            "final_btn":
            "⬇️ Télécharger le rapport final (PDF)",
            "send_btn":
            "📧 M'envoyer par email",
            "sent_ok":
            "Rapport envoyé à {email}. Vérifiez votre boîte de réception (et spam).",
            "sent_fail":
            "Le serveur n'a pas confirmé l'envoi de l'email.",
            "send_not_avail":
            "La fonction d'envoi d'email n'est pas disponible dans cet environnement.",
            "send_err":
            "Impossible d'envoyer: {etype}: {emsg}",
            "zelle_to":
            "Envoyer à",
            "mail_sent":
            "📧 Envoyé à {email}! Vérifiez votre boîte de réception (et le dossier spam/promotions).",
            "wa_text":
            "Découvrez votre niveau de risque esthétique avec AestheticSafe et partagez-le avec quelqu'un que vous aimez: {link}  #AestheticSafe",
        },
    }.get(_lang, {})

    # ============ FEEDBACK BLOCK 1 (before download section) ============
    st.markdown('<div id="section-feedback-top"></div>', unsafe_allow_html=True)
    st.write("")
    
    # Global CSS for grayscale emoji buttons and smooth scroll (MUST BE BEFORE TEXT RENDERING)
    st.markdown("""
    <style>
    /* Scroll suave global */
    html {
        scroll-behavior: smooth;
    }
    
    .feedback-title {
        font-size: 18px !important;
        font-weight: 600;
        color: #e0e0e0;
        margin-bottom: 16px;
        text-align: center;
    }
    
    /* === EMOJI LAYOUT (CENTERED) === */
    /* Contenedor principal de emojis */
    .emoji-wrapper {
        display: flex !important;
        flex-direction: row !important;
        justify-content: center !important;
        align-items: center !important;
        flex-wrap: nowrap !important;
        gap: 0 !important;
        width: 100% !important;
        margin: 0 auto !important;
        padding: 0 !important;
    }

    /* Forzamos a Streamlit a no apilar botones */
    .emoji-wrapper div[data-testid="stVerticalBlock"] {
        display: inline-block !important;
        vertical-align: middle !important;
        margin: 0 4px !important;
    }

    /* Estilo base de los botones */
    .emoji-wrapper button {
        flex: 0 0 auto !important;
        width: 2.8rem !important;
        height: 2.8rem !important;
        font-size: 1.6rem !important;
        line-height: 1 !important;
        text-align: center !important;
        margin: 0 !important;
    }
    
    /* Emoji buttons: grayscale default, color + slight scale on hover */
    .emoji-wrapper .stButton > button {
      background: transparent !important;
      filter: grayscale(100%) !important;
      transition: transform 0.12s ease, filter 0.12s ease !important;
      border: none !important;
      box-shadow: none !important;
    }
    
    /* Hover opcional: emoji agrandado y color */
    .emoji-wrapper button:hover {
        transform: scale(1.15);
        filter: grayscale(0%);
        transition: 0.2s ease-in-out;
    }

    /* Kill any unwanted default theming */
    .emoji-wrapper .stButton > button span,
    .emoji-wrapper .stButton > button div {
      background: transparent !important;
      box-shadow: none !important;
    }

    /* Ajuste para móviles */
    @media (max-width: 480px) {
        .emoji-wrapper {
            justify-content: center !important;
        }
        .emoji-wrapper div[data-testid="stVerticalBlock"] {
            margin: 0 2px !important;
        }
        .emoji-wrapper button {
            width: 2.2rem !important;
            height: 2.2rem !important;
            font-size: 1.4rem !important;
        }
    }
    
    /* === BLOQUE DE PRUEBA (NUEVA LÍNEA DE BOTONES) === */
    .emoji-test-wrapper {
        display: flex !important;
        flex-direction: row !important;
        justify-content: center !important;
        align-items: center !important;
        flex-wrap: nowrap !important;
        gap: 6px !important;
        width: 100% !important;
        margin: 1rem auto !important;
        padding: 0 !important;
    }

    /* Corrige el div intermedio que Streamlit inserta */
    .emoji-test-wrapper div[data-testid="stVerticalBlock"] {
        display: inline-block !important;
        vertical-align: middle !important;
        margin: 0 4px !important;
    }

    /* Estilo del botón */
    .emoji-test-wrapper button {
        flex: 0 0 auto !important;
        width: 2.8rem !important;
        height: 2.8rem !important;
        font-size: 1.6rem !important;
        line-height: 1 !important;
        text-align: center !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* Responsive móvil */
    @media (max-width: 480px) {
        .emoji-test-wrapper {
            gap: 3px !important;
        }
        .emoji-test-wrapper button {
            width: 2.2rem !important;
            height: 2.2rem !important;
            font-size: 1.4rem !important;
        }
    }
    
    .fade-in-content {
        animation: fadeIn 0.3s ease-in-out;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Text utilities with adaptive colors */
    .text-sm {
      font-size: 0.95rem;
    }
    .font-semibold {
      font-weight: 600;
    }
    .text-gray-200 {
      color: #e0e0e0 !important; /* Default: light text for dark backgrounds */
    }
    
    /* Light mode: dark text */
    @media (prefers-color-scheme: light) {
        .text-gray-200 {
            color: #1a1a1a !important;
        }
    }
    
    /* Evitar dobles barras de scroll */
    [data-testid="stVerticalBlock"] {
        overflow-y: visible !important;
    }
    </style>
    
    <script>
    // Auto-scroll suave controlado
    (function() {
        let dropdownOpen = false;
        
        // Detectar cuando un dropdown está abierto
        document.addEventListener('focus', function(e) {
            if (e.target.tagName === 'SELECT' || e.target.tagName === 'INPUT') {
                dropdownOpen = true;
            }
        }, true);
        
        // Detectar cuando se cierra
        document.addEventListener('blur', function(e) {
            if (e.target.tagName === 'SELECT' || e.target.tagName === 'INPUT') {
                dropdownOpen = false;
            }
        }, true);
        
        // Función de scroll suave
        window.smoothScrollTo = function(targetY) {
            if (!dropdownOpen) {
                window.scrollTo({ top: targetY, behavior: 'smooth' });
            }
        };
    })();
    </script>
    """, unsafe_allow_html=True)
    
    feedback_title = i18n_label(
        "💬 ¿Cómo te sentiste completando esta evaluación?",
        "💬 How did you feel completing this assessment?",
        "💬 Como você se sentiu completando esta avaliação?",
        "💬 Comment vous êtes-vous senti en complétant cette évaluation?"
    )
    
    # Minimalist grayscale emoji feedback
    st.markdown(f"<p class='text-sm font-semibold text-gray-200'>{feedback_title}</p>", unsafe_allow_html=True)
    
    # Get evaluation ID and email for logging
    eval_id = st.session_state.get("sess_ref", "")
    user_email = st.session_state.get("email", "")
    
    # === EMOJI FEEDBACK (TOP) — TRES COLUMNAS PEQUEÑAS Y CENTRADAS ===
    def handle_feedback(choice):
        if st.session_state.get("feedback_top_choice") != choice:
            st.session_state["feedback_top_choice"] = choice
            st.session_state["feedback_top_timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            log_to_funnel_progress(satisfaction_step="step1", emoji=choice, comment="")

    # Emojis con st.columns para layout horizontal nativo (solución definitiva)
    col1, col2, col3 = st.columns([1, 1, 1], gap="small")
    with col1:
        st.button("😞", key="emoji_sad_top", help="Tuve dificultades", on_click=handle_feedback, args=("sad",), use_container_width=True)
    with col2:
        st.button("😐", key="emoji_neutral_top", help="Fue aceptable", on_click=handle_feedback, args=("neutral",), use_container_width=True)
    with col3:
        st.button("🙂", key="emoji_happy_top", help="Me sentí bien", on_click=handle_feedback, args=("happy",), use_container_width=True)
    
    # Show response only for neutral/sad (NOT for happy)
    if "feedback_top_choice" in st.session_state:
        choice = st.session_state["feedback_top_choice"]
        if choice in ["neutral", "sad"]:
            st.markdown('<div class="fade-in-content">', unsafe_allow_html=True)
            
            feedback_prompt = i18n_label(
                "💭 ¿Cómo podemos mejorar tu experiencia?",
                "💭 How can we improve your experience?",
                "💭 Como podemos melhorar sua experiência?",
                "💭 Comment pouvons-nous améliorer votre expérience?"
            )
            feedback_placeholder = i18n_label(
                "Escribí aquí tus sugerencias o comentarios...",
                "Write your suggestions or comments here...",
                "Escreva aqui suas sugestões ou comentários...",
                "Écrivez ici vos suggestions ou commentaires..."
            )
            feedback_text_top = st.text_area(
                feedback_prompt, 
                key="feedback_top_text_pre", 
                height=100,
                placeholder=feedback_placeholder
            )
            st.session_state["feedback_top_text_value"] = feedback_text_top
            
            # Log comment to Funnel_Progress if provided
            if feedback_text_top and feedback_text_top.strip():
                log_to_funnel_progress(
                    satisfaction_step="step1",
                    emoji=choice,
                    comment=feedback_text_top.strip()
                )
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.write("")
    # ============ /FEEDBACK BLOCK 1 ============

    st.markdown('<div id="section-contacto"></div>', unsafe_allow_html=True)
    # No mostrar título duplicado aquí - el título principal está en el gate
    cA, cB, cC = st.columns(3)
    with cA:
        nombre = st.text_input(
            str(TXT.get("name", "Nombre (opcional)")),
            key="nombre_input",
        )
    with cB:
        email = st.text_input(
            str(TXT.get("email_label", "Email")),
            value=st.session_state.get("email", ""),
            placeholder=TXT.get("email_ph", "tu@email.com"),
            key="email_input",
        )
    with cC:
        telefono = st.text_input(
            str(TXT.get("phone_label", "Teléfono (WhatsApp)")),
            value=st.session_state.get("telefono", ""),
            placeholder="+5491112345678",
            key="telefono_input",
        )

    consent_label = i18n_label(
        "Acepto compartir estos datos para recibir mi informe y seguimiento.",
        "I agree to share this information to receive my report and follow-up.",
        "Concordo em compartilhar estes dados para receber meu relatório e acompanhamento.",
        "J'accepte de partager ces informations pour recevoir mon rapport et le suivi."
    )
    consent = st.checkbox(consent_label, key="consent_checkbox")

    # Store consent for gating logic
    st.session_state["acepto_compartir"] = consent
    
    st.write("")  # Spacer
    
    # ==== COMPARTIR CON MÉDICO/STAFF (Multilingüe) ====
    perfil = st.session_state.get("perfil", "paciente")
    is_doctor = (perfil == "medico")
    
    # Textos dinámicos según perfil
    if is_doctor:
        share_label = i18n_label(
            "🩺 ¿Querés compartir esta evaluación con tu staff?",
            "🩺 Do you want to share this evaluation with your staff?",
            "🩺 Deseja compartilhar esta avaliação com sua equipe?",
            "🩺 Voulez-vous partager cette évaluation avec votre équipe?"
        )
        share_placeholder = i18n_label(
            "email del colega o asistente",
            "colleague or assistant email",
            "email do colega ou assistente",
            "email du collègue ou assistant"
        )
        share_help = i18n_label(
            "Podés enviar una copia a tu equipo para revisión.",
            "You can send a copy to your team for review.",
            "Você pode enviar uma cópia para sua equipe para revisão.",
            "Vous pouvez envoyer une copie à votre équipe pour examen."
        )
    else:
        share_label = i18n_label(
            "💬 ¿Te gustaría compartir tu informe con tu médico o alguien más?",
            "💬 Would you like to share your report with your doctor or someone else?",
            "💬 Gostaria de compartilhar seu relatório com seu médico ou outra pessoa?",
            "💬 Souhaitez-vous partager votre rapport avec votre médecin ou quelqu'un d'autre?"
        )
        share_placeholder = i18n_label(
            "Ingresa su email (opcional)",
            "Enter their email (optional)",
            "Digite o email deles (opcional)",
            "Entrez leur email (facultatif)"
        )
        share_help = i18n_label(
            "Le enviaremos una copia segura del informe.",
            "We will send a secure copy of the report.",
            "Enviaremos uma cópia segura do relatório.",
            "Nous enverrons une copie sécurisée du rapport."
        )
    
    # Campo de email con validación visual
    st.markdown(f"<p class='text-sm font-semibold text-gray-200'>{share_label}</p>", unsafe_allow_html=True)
    
    doctor_email = st.text_input(
        label="Email para compartir",
        value=st.session_state.get("doctor_shared_email", ""),
        placeholder=share_placeholder,
        key="doctor_shared_email_input",
        label_visibility="collapsed"
    )
    
    # Guardar en session state
    st.session_state["doctor_shared_email"] = doctor_email.strip()
    st.session_state["shared_role"] = "doctor_to_staff" if is_doctor else "patient_to_doctor"
    
    # Mensaje de ayuda
    st.caption(share_help)
    
    # Validación de email (solo si hay algo escrito)
    if doctor_email.strip():
        import re
        email_pattern = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        if not re.match(email_pattern, doctor_email.strip()):
            error_msg = i18n_label(
                "⚠️ Ingresá un email válido para compartir la información.",
                "⚠️ Enter a valid email to share the information.",
                "⚠️ Digite um email válido para compartilhar as informações.",
                "⚠️ Entrez un email valide pour partager les informations."
            )
            st.error(error_msg)

    # --- Cálculo Caprini (usa variables ya definidas arriba) ---
    cap_score, cap_det = caprini_desde(antecedentes_todos)
    cap_cat = caprini_categoria(cap_score)
    f = factor_riesgo_fn(edad, bmi, tabaquismo, cap_score)
    nivel = nivel_por_factor(f)

    payload = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "nombre": (nombre or '').strip(),
        "email": (email or '').strip(),
        "telefono": (telefono or '').strip(),
        "perfil": st.session_state.get("perfil", ""),
        "idioma": st.session_state.get("idioma", "ES"),
        "version": "v1.0",
        # Datos
        "edad": edad,
        "peso_kg": peso,
        "altura_cm": altura,
        "bmi": bmi,
        # Riesgo
        "tabaquismo": tabaquismo,
        "caprini_score": cap_score,
        "caprini_categoria": cap_cat,
        "caprini_factores":
        "; ".join([f"{k}(+{v})" for k, v in cap_det.items()]),
        "antecedentes": "; ".join(antecedentes_todos),
        "factor_riesgo": f,
        "nivel_riesgo": nivel,
        # Consent / origen
        "consentimiento": consent,
        "origen": BRAND,
        # Psico
        "bdd_resultado": st.session_state.get("bdd_resultado", ""),
    }

    def faltan():
        return not (consent and payload["email"] and payload["telefono"])

    # Flags pago/share
    paid_flag = _read_paid_flag_from_query()
    st.session_state.setdefault("mp_confirmado", False)
    st.session_state.setdefault("wa_confirmado", False)
    st.session_state.setdefault("mail_sent", False)

    if paid_flag:
        st.session_state.mp_confirmado = True

    ref = ""
    paid_code = ""
    
    # ==== GATE v2 — Dark themed buttons with progressive disclosure ====
    gate_title = TXT.get(
        "gate_title", "Elegí cómo querés recibir tu informe")
    gate_subtitle = TXT.get(
        "gate_subtitle", "💎 Pagar reporte completo · 💬 Compartir y descargar gratis")
    
    # Multi-language button labels (ES/EN/FR/PT)
    gate_pay = button_label(
        es="💳 Pagar y Descargar",
        en="💳 Pay & Download",
        fr="💳 Payer & Télécharger",
        pt="💳 Pagar e Baixar"
    )
    gate_share = button_label(
        es="📲 Compartir y Descargar",
        en="📲 Share & Download",
        fr="📲 Partager & Télécharger",
        pt="📲 Compartilhar e Baixar"
    )

    # Limpieza de restos de la V1
    for k in ("gate_opt", "opt_last"):
        st.session_state.pop(k, None)

    st.markdown(f"#### {gate_title}")
    st.markdown(f"<p style='text-align: center; color: #999; font-size: 0.9em; margin-top: -8px; margin-bottom: 16px;'>{gate_subtitle}</p>", unsafe_allow_html=True)
    
    # Adaptive themed horizontal buttons CSS (dark buttons in light mode, light buttons in dark mode)
    st.markdown("""
    <style>
    /* Light mode: dark buttons with white text */
    [data-testid="column"] button[kind="secondary"] {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border: 2px solid #444 !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        padding: 14px 28px !important;
        margin: 0 8px !important;
        transition: all 0.2s ease-in-out !important;
        cursor: pointer !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }
    [data-testid="column"] button[kind="secondary"]:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 6px 16px rgba(0,0,0,0.4) !important;
        background-color: #2d2d2d !important;
        border-color: #666 !important;
        opacity: 1 !important;
    }
    [data-testid="column"] button[kind="secondary"]:focus:not(:active) {
        background-color: #333 !important;
        box-shadow: 0 0 0 3px rgba(255,255,255,0.2) !important;
        border-color: #888 !important;
    }
    
    /* Dark mode: light buttons with dark text */
    @media (prefers-color-scheme: dark) {
        [data-testid="column"] button[kind="secondary"] {
            background-color: #f5f5f5 !important;
            color: #1a1a1a !important;
            border: 2px solid #ddd !important;
            box-shadow: 0 2px 8px rgba(255,255,255,0.1) !important;
        }
        [data-testid="column"] button[kind="secondary"]:hover {
            background-color: #ffffff !important;
            border-color: #aaa !important;
            box-shadow: 0 6px 16px rgba(255,255,255,0.2) !important;
        }
        [data-testid="column"] button[kind="secondary"]:focus:not(:active) {
            background-color: #e8e8e8 !important;
            box-shadow: 0 0 0 3px rgba(255,255,255,0.3) !important;
            border-color: #999 !important;
        }
        
        /* Link buttons (WhatsApp, MercadoPago) also adapt to dark mode */
        button[kind="primary"], a[data-testid="stLinkButton"] > button {
            background-color: #f5f5f5 !important;
            color: #1a1a1a !important;
            border: 2px solid #ddd !important;
        }
        button[kind="primary"]:hover, a[data-testid="stLinkButton"] > button:hover {
            background-color: #ffffff !important;
            border-color: #aaa !important;
        }
    }
    /* Fade-in animation for sub-options */
    .sub-options-container {
        animation: fadeIn 0.2s ease-in-out;
        opacity: 1;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-5px); }
        to { opacity: 1; transform: translateY(0); }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Horizontal buttons layout
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(gate_pay, key="btn_pay", use_container_width=True):
            st.session_state["gate_mode_v2"] = "pay"
    
    with col2:
        if st.button(gate_share, key="btn_share", use_container_width=True):
            st.session_state["gate_mode_v2"] = "share"
    
    # Get current mode from session state
    mode = st.session_state.get("gate_mode_v2", None)
    
    # Set session state based on selected mode
    if mode == "pay":
        st.session_state["pay_and_download"] = True
        st.session_state["share_and_download"] = False
    elif mode == "share":
        st.session_state["share_and_download"] = True
        st.session_state["pay_and_download"] = False

    # --------------------- MODO: PAGO ---------------------
    if mode == "pay":
        st.markdown('<div class="sub-options-container">', unsafe_allow_html=True)
        
        pay_method_label = i18n_label("Elegí método de pago:",
                                      "Choose a payment method:",
                                      "Escolha um método de pagamento:")

        pay_method = st.radio(
            pay_method_label,
            options=["mp", "zelle"],
            format_func=lambda v: ("Mercado Pago" if v == "mp" else "Zelle"),
            key="pay_method_v2",
        )

        if pay_method == "mp":
            info_text = i18n_label(
                "Se abrirá Mercado Pago en una pestaña nueva. El informe final se habilitará cuando regreses con confirmación.",
                "Mercado Pago will open in a new tab. The final report will unlock once you return with confirmation.",
                "O Mercado Pago abrirá em uma nova aba. O relatório final será liberado quando você retornar com a confirmação."
            )
            st.info(info_text)

            mp_url = st.session_state.get("mp_url") or MERCADOPAGO_LINK
            link_text = i18n_label("Ir a pagar / revisar en Mercado Pago",
                                   "Go to pay / review in Mercado Pago",
                                   "Ir pagar / revisar no Mercado Pago")
            st.link_button(link_text, sstr(mp_url), use_container_width=True)

            pay_done_label = i18n_label("✅ Ya realicé el pago",
                                        "✅ I've already paid",
                                        "✅ Já realizei o pagamento")
            st.session_state["pay_ok"] = st.checkbox(
                pay_done_label,
                key="pay_done_v2",
            )
            # Set pay_and_download flag for gating
            st.session_state["pay_and_download"] = st.session_state.get(
                "pay_ok", False)

            pay_code_label = i18n_label(
                "Pegá el código de pago (opcional)",
                "Paste your payment code (optional)",
                "Cole o código do pagamento (opcional)")
            st.session_state["paid_code"] = st.text_input(
                pay_code_label,
                value=st.session_state.get("paid_code", ""),
                key="pay_code_v2",
            ).strip()

        else:  # Zelle
            zelle_info_text = i18n_label(
                "Pagar con Zelle y pegar el memo/código de pago. Se acepta cualquier referencia alfanumérica.",
                "Pay with Zelle and paste the payment memo/code. Any alphanumeric reference is accepted.",
                "Pagar com Zelle e colar o código/nota de pagamento. Qualquer referência alfanumérica é aceita."
            )
            st.caption(zelle_info_text)

            # REF único de sesión: pedimos ponerlo en la nota/memo de Zelle
            ref = st.session_state.get("sess_ref") or _ensure_session_ref()
            zelle_memo_text = i18n_label(
                f"📝 En la nota/memo de Zelle escribí: REF-{ref}",
                f"📝 In the Zelle memo write: REF-{ref}",
                f"📝 No memo do Zelle escreva: REF-{ref}")
            st.caption(zelle_memo_text)

            send_to_label = i18n_label("Enviar para", "Send to", "Enviar para")
            st.markdown(f"**{send_to_label}** `{ZELLE_EMAIL}`")

            zelle_done_label = i18n_label("✅ Ya pagué por Zelle",
                                          "✅ I already paid with Zelle",
                                          "✅ Já paguei por Zelle")
            st.session_state["zelle_ok"] = st.checkbox(
                zelle_done_label,
                key="zelle_done_v2",
            )

            amount_label = i18n_label("Monto en USD (opcional)",
                                      "Amount in USD (optional)",
                                      "Valor em USD (opcional)")
            st.session_state["pago_monto_usd"] = st.text_input(
                amount_label,
                value=st.session_state.get("pago_monto_usd", ""),
                key="zelle_amount_v2",
            ).strip()

            zelle_code_label = i18n_label("Código/nota de Zelle (opcional)",
                                          "Zelle memo / code (optional)",
                                          "Código/nota do Zelle (opcional)")
            st.session_state["paid_code"] = st.text_input(
                zelle_code_label,
                value=st.session_state.get("paid_code", ""),
                key="zelle_code_v2",
            ).strip()
            # Store Zelle code separately for gating logic
            st.session_state["zelle_code"] = st.session_state["paid_code"]
        
        st.markdown('</div>', unsafe_allow_html=True)

    # --------------------- MODO: COMPARTIR POR WHATSAPP ---------------------
    elif mode == "share":
        st.markdown('<div class="sub-options-container">', unsafe_allow_html=True)
        
        # 1) Input de teléfono ANTES del CTA
        phone_label = i18n_label("Teléfono (WhatsApp)", "Phone (WhatsApp)",
                                 "Telefone (WhatsApp)")
        phone_input = st.text_input(
            phone_label,
            value=st.session_state.get("whatsapp_phone", ""),
            placeholder="+5491112345678",
            key="whatsapp_phone",
        ).strip()

        dest = (phone_input or st.session_state.get("whatsapp_phone")
                or "").strip()
        is_valid_phone = bool(regex.fullmatch(r"^\+?[1-9]\d{7,14}$", dest))

        # 2) Construir link de WhatsApp
        ref = st.session_state.get("sess_ref") or _ensure_session_ref()
        try:
            app_url = APP_PUBLIC_URL
        except NameError:
            app_url = (st.session_state.get("APP_PUBLIC_URL")
                       or st.session_state.get("app_url")
                       or TXT.get("app_link", ""))
        share_link = f"{app_url}?ref={ref}" if app_url else ref

        # 🎯 Sistema multiidioma para mensajes CTA de WhatsApp
        cta_messages = {
            "ES": "Hacé tu Autoevaluación sin cargo y preparate para una cirugía segura con app.aestheticsafe.com",
            "EN": "Do your free Self-Assessment and get ready for a safe surgery with app.aestheticsafe.com", 
            "PT": "Faça sua Autoavaliação gratuita e prepare-se para uma cirurgia segura com app.aestheticsafe.com"
        }
        
        # Obtener idioma actual (default: español)
        current_lang = st.session_state.get("idioma", "ES")
        cta_text = cta_messages.get(current_lang, cta_messages["ES"])
        
        # Codificar para URL y generar link de WhatsApp
        wa_url = f"https://wa.me/?text={urllib.parse.quote(cta_text)}"
        safe_log("WhatsApp CTA generado", lang=current_lang)

        # 3) Botón de WhatsApp (lo dejamos SIEMPRE clickable)
        wa_cta_label = i18n_label("📲 Compartir por WhatsApp",
                                  "📲 Share on WhatsApp",
                                  "📲 Compartilhar no WhatsApp")
        clicked = st.link_button(
            wa_cta_label,
            sstr(wa_url),
            use_container_width=True,
        )

        # Tip si el teléfono no es válido (no bloquea el click, solo info)
        if not is_valid_phone:
            tip_text = i18n_label(
                "ℹ️ Ingresá un número válido para registrar el share y desbloquear la descarga.",
                "ℹ️ Enter a valid number to register the share and unlock the download.",
                "ℹ️ Digite um número válido para registrar o compartilhamento e desbloquear o download."
            )
            st.caption(tip_text)

        # Si hubo click + teléfono válido, registramos destino
        if clicked and is_valid_phone:
            st.session_state["share_ref"] = dest
            st.session_state["wa_destino"] = dest

        # 4) Confirmación manual (al tildar, desbloquea)
        wa_done_label = i18n_label("✅ Ya compartí por WhatsApp",
                                   "✅ I already shared on WhatsApp",
                                   "✅ Já compartilhei no WhatsApp")
        shared_checkbox = st.checkbox(
            wa_done_label,
            key="whatsapp_shared",
            disabled=not is_valid_phone,
        )

        # Update session state for gating logic
        st.session_state["shared_whatsapp"] = shared_checkbox
        st.session_state["shared_ok"] = shared_checkbox

        if shared_checkbox and is_valid_phone:
            st.session_state["wa_phone_confirmed"] = dest
            st.session_state["share_ref"] = dest

        
        st.markdown("</div>", unsafe_allow_html=True)
    # -------- Unificación del “desbloqueo” (ambos modos) --------
    pay_ok = bool(st.session_state.get("pay_ok"))
    zelle_ok = bool(st.session_state.get("zelle_ok"))
    shared_ok = bool(st.session_state.get("shared_whatsapp"))

    st.session_state["can_unlock"] = bool(pay_ok or zelle_ok or shared_ok)
    
    # Mensajes dinámicos según acción del usuario
    if pay_ok or zelle_ok:
        success_msg = i18n_label(
            "💎 ¡Gracias por tu pago! Tu informe completo se enviará por email en unos momentos.",
            "💎 Thank you for your payment! Your complete report will be sent by email shortly.",
            "💎 Obrigado pelo seu pagamento! Seu relatório completo será enviado por e-mail em breve.",
            "💎 Merci pour votre paiement! Votre rapport complet sera envoyé par email sous peu."
        )
        st.success(success_msg)
    elif shared_ok:
        success_msg = i18n_label(
            "✅ ¡Gracias por compartir! Descargá tu vista previa gratuita a continuación.",
            "✅ Thanks for sharing! Download your free preview below.",
            "✅ Obrigado por compartilhar! Baixe sua prévia gratuita abaixo.",
            "✅ Merci d'avoir partagé! Téléchargez votre aperçu gratuit ci-dessous."
        )
        st.success(success_msg)

    if not st.session_state["can_unlock"]:
        st.info(
            TXT.get(
                "locked",
                "El informe final se habilitará cuando confirmes pago o compartas por WhatsApp."
            ))
        st.stop()

    # ================== /HOOK 2 ==================

    # ---------- Médico (opcional) ----------
    doctor_label = i18n_label(
        "¿Querés compartirlo con alguien? Por ejemplo, tu médico.",
        "Would you like to share it with someone? For example, your doctor.",
        "Quer compartilhar com alguém? Por exemplo, seu médico.",
        "Voulez-vous le partager avec quelqu'un? Par exemple, votre médecin."
    )

    doctor_placeholder = i18n_label(
        "Ingresá su email (opcional)",
        "Enter their email (optional)",
        "Digite o e-mail (opcional)",
        "Entrez leur e-mail (optionnel)"
    )
    
    medico_val = st.text_input(
        doctor_label,
        value=st.session_state.get("medico_input")
        or st.session_state.get("medico", ""),
        key="medico_input",
        placeholder=doctor_placeholder,
    ).strip()

    # Canonicalizar / alias (para usar en PDF/email)
    st.session_state["medico"] = medico_val
    st.session_state["medico_ui"] = medico_val

    # Requisitos mínimos
    # ===== Permiso para FINAL =====
    paid_code = (st.session_state.get("paid_code") or "").strip()

    # MP requiere código de 6+ alfanuméricos
    code_ok = bool(regex.fullmatch(r"[A-Za-z0-9]{6,}", paid_code))

    pay_ok = bool(st.session_state.get("pay_ok"))  # MP (checkbox)
    zelle_ok = bool(st.session_state.get("zelle_ok"))  # Zelle (checkbox)
    shared_ok = bool(
        st.session_state.get("shared_whatsapp")
        and st.session_state.get("wa_phone_confirmed"))

    # Compatibilidad con ?paid=1 si lo usás
    paid_flag = bool(_read_paid_flag_from_query())

    # Reglas rápidas:
    # - MP: requiere check + código válido
    # - Zelle: sólo check (no pedimos código en la opción rápida)
    # - Compartir: check + teléfono confirmado
    permiso = bool(paid_flag or (pay_ok and code_ok) or zelle_ok or shared_ok)

    # Esto controla el UI de “desbloqueado”
    st.session_state["can_unlock"] = permiso
    # Alias local para usar en los botones
    can_download = bool(st.session_state.get("can_download", False))

    if not permiso:
        st.info(
            TXT.get(
                "locked",
                "El informe final se habilitará cuando confirmes pago o compartas por WhatsApp."
            ))
        st.stop()

    # Recomendaciones y PDF FINAL
    recs = recomendaciones_txt(IMC=bmi,
                               edad=edad,
                               tabaquismo=tabaquismo,
                               hta_txt=hta_txt,
                               diabetes_txt=diabetes_txt,
                               tiroides_txt=tiroides_txt,
                               caprini_score=cap_score,
                               antecedentes=antecedentes_todos,
                               riesgo=nivel)
    final_data = {
        "rep_id":
        f"ESTH-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "paciente": {
            "nombre": nombre or "—",
            "edad": edad,
            "altura_cm": altura,
            "peso_kg": peso
        },
        "bmi": bmi,
        "caprini_score": cap_score,
        "caprini_categoria": cap_cat,
        "factor_riesgo": f,
        "nivel_riesgo": nivel,
        "bdd_evaluacion": st.session_state.get("bdd_respuestas", ""),
        "bdd_resultado": st.session_state.get("bdd_resultado", ""),
        "recomendaciones": recs,
        "conclusion":
        "Optimizar salud general y reevaluar antes de planificar procedimientos combinados.",
        "psico_resultado": st.session_state.get("psico_resultado", ""),
    }
    # --- cacheo de Caprini en session_state para logging/gsheets ---
    st.session_state["caprini_score"] = str(cap_score)
    st.session_state["caprini_categoria"] = cap_cat
    st.session_state.setdefault("caprini_factores_txt",
                                st.session_state.get("caprini_detalle", ""))
    st.session_state["factor_riesgo_val"] = str(f)
    st.session_state["nivel_riesgo_val"] = nivel
    # ---------------------------------------------------------------

    # Use new v3.1 PDF generator if available, otherwise fall back to legacy
    if generar_pdf_v3_1:
        pdf_final, verification_uuid = generar_pdf_v3_1(final_data, preview=False, full=True)
        st.session_state["verification_uuid"] = verification_uuid
    else:
        pdf_final = generar_pdf(final_data, preview=False, full=True)
        verification_uuid = None
        st.session_state["verification_uuid"] = None
    pdf_id = f"PDF-{payload['timestamp']}-{payload['email']}"
    st.session_state["pdf_id"] = pdf_id
    
    # Log PDF generation to V3_Interoperability_Log
    if not st.session_state.get("pdf_generation_logged"):
        import json
        log_to_interoperability(
            request_data=json.dumps({"BMI": payload.get("bmi", ""), "email": payload.get('email', ''), "risk_level": nivel}),
            response_data=json.dumps({"status": "PDF_GENERATED", "code": 200}),
            stage="pdf_generation",
            substage="created"
        )
        st.session_state["pdf_generation_logged"] = True
        # 🔥 Registro del funnel: FORM COMPLETED
        registro.registrar_evento_funnel(**st.session_state)

    # === Descargar informe final ===
    st.markdown('<div id="section-download"></div>', unsafe_allow_html=True)
    ready = can_release_report(cast(Mapping[Any, Any], st.session_state))

    final_btn_label = i18n_label("⬇️ Descargar informe final (PDF)",
                                 "⬇️ Download final report (PDF)",
                                 "⬇️ Baixar relatório final (PDF)")

    # Apply gating logic to download button
    ready = can_release_report(cast(Mapping[Any, Any], st.session_state))

    # Backend safeguard
    if not can_release_report(cast(Mapping[Any, Any], st.session_state)):
        warning_msg = i18n_label(
            "Por favor, completá el paso requerido para habilitar la descarga.",
            "Please complete the required step to enable the download.",
            "Por favor, complete o passo necessário para habilitar o download."
        )
        st.warning(warning_msg)
        st.stop()

    st.download_button(
        final_btn_label,
        data=pdf_final,
        file_name="AestheticSafe_Informe.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="download_final_button",
        disabled=not ready,
    )

    # === Mensaje persistente + Envío por email (drop-in) ===

    # Init seguro (idempotente)
    st.session_state.setdefault("mail_sent", False)
    st.session_state.setdefault("last_sent_email", "")

    # Email actual en la UI/payload
    current_email = (payload.get("email") or "").strip()

    # Si cambian el email, ocultar el mensaje de "Enviado"
    if st.session_state.get(
            "mail_sent"
    ) and current_email and current_email != st.session_state.get(
            "last_sent_email"):
        st.session_state["mail_sent"] = False

    # Mensaje persistente arriba del botón (estilo "globo" amarillo)
    if st.session_state.get("mail_sent", False):
        st.warning(
            TXT["mail_sent"].format(
                email=st.session_state.get("last_sent_email", "tu email")
            )
        )

    # === Envío del informe por email (SOLO al presionar el botón) ===
    send_btn_label = i18n_label("📧 Enviarme por email", "📧 Send me by email",
                                "📧 Enviar para meu email")
    
    safe_log("Botón email - ready", ready=ready)
    safe_log("Email en payload", email=mask_email(payload.get('email', 'NO_EMAIL')))
    safe_log("can_release_report check", result=can_release_report(cast(Mapping[Any, Any], st.session_state)))
    
    # ✅ Mostrar botón solo si pagó (no solo compartió WhatsApp)
    if st.session_state.get("pay_and_download", False):
        # Usuario pagó o compartió por WhatsApp → mostrar botón activo
        if st.button(send_btn_label,
                     use_container_width=True,
                     key="emailbtn"):
            
            safe_log("¡BOTÓN PRESIONADO!")
            safe_log("Email destino", email=mask_email(payload.get('email', 'VACÍO')))

            # Backend safeguard
            if not can_release_report(cast(Mapping[Any, Any], st.session_state)):
                warning_msg = i18n_label(
                    "Por favor, completá el paso requerido para habilitar la descarga.",
                    "Please complete the required step to enable the download.",
                    "Por favor, complete o passo necessário para habilitar o download."
                )
                st.warning(warning_msg)
                st.stop()

            ok = False
            try:
                lang_code = st.session_state.get("idioma", "ES")
                tpl = EMAIL_TPL.get(lang_code, EMAIL_TPL["ES"])

                to_email = (payload.get("email") or "").strip()
                if not to_email:
                    raise ValueError("Email del paciente vacío.")

                subject = tpl["subject"]
                content_text = tpl["body"].format(
                    name=(payload.get("nombre")
                          or ("Patient" if lang_code == "EN" else "Paciente")),
                    brand=BRAND,
                    mail=BRAND_MAIL,
                    tel=BRAND_TEL,
                    web1=BRAND_WEB1,
                )

                # Use imported email functions
                try:
                    ok = send_email_with_pdf(
                        to_email=to_email,
                        subject=subject,
                        content_text=content_text,
                        pdf_bytes=pdf_final,
                        pdf_filename="AestheticSafe_Informe.pdf",
                    )
                except Exception:
                    # Fallback to basic send_email if send_email_with_pdf fails
                    try:
                        result = send_email(
                            {
                                **payload, "subject": subject,
                                "body": content_text
                            }, pdf_final)
                        ok = result.get("ok", False) if isinstance(
                            result, dict) else bool(result)
                    except Exception:
                        st.warning(TXT["send_not_avail"])
                        ok = False

            except Exception as e:
                st.error(TXT["send_err"].format(etype=type(e).__name__, emsg=e))
                ok = False
            else:
                if ok:
                    # Log a Sheets (con tus campos)
                    mp_ok = bool(st.session_state.get("mp_confirmado")) and bool(
                        (code_ok if 'code_ok' in locals() else
                         st.session_state.get("code_ok", False)))
                    canal = "pago_email" if mp_ok else "share_email"

                    _append_row_extended(
                    payload if canal == "pago_email" else {
                        **payload, "ref":
                        (ref if 'ref' in locals() else st.session_state.get(
                            "share_ref", ""))
                    },
                    canal,
                    pdf_entregado="sí",
                    pdf_entrega_via="email",
                    pdf_ref=pdf_id,
                    share_ref=((ref if 'ref' in locals() else
                                st.session_state.get("share_ref", ""))
                               if canal == "share_email" else ""),
                    share_via=("whatsapp" if canal == "share_email" else ""),
                    tdc_positivo=("Sí" if st.session_state.get("tdc_positive")
                                  else "No"),
                )

                    # Log email delivery to V3_Interoperability_Log
                    import json
                    log_to_interoperability(
                        request_data=json.dumps({"email": to_email, "canal": canal}),
                        response_data=json.dumps({"status": "EMAIL_SENT", "code": 200}),
                        stage="email_delivery",
                        substage="sent"
                    )
                    
                    # Persistir y mostrar confirmación
                    st.session_state["last_sent_email"] = to_email
                    st.session_state["mail_sent"] = True
                    st.rerun()
                else:
                    # Log email failure to V3_Interoperability_Log
                    import json
                    log_to_interoperability(
                        request_data=json.dumps({"email": to_email, "canal": "failed"}),
                        response_data=json.dumps({"status": "EMAIL_FAILED", "code": 500, "error": "Email sending failed"}),
                        stage="email_delivery",
                        substage="failed"
                    )
                    st.session_state["mail_sent"] = False
                    st.error(
                        TXT.get("sent_fail",
                                "No se pudo enviar el email. Intentá nuevamente."))
    else:
        # ❌ Usuario no pagó ni compartió → mostrar aviso
        warning_msg = i18n_label(
            "Para enviarte el informe por email es necesario completar el pago.",
            "To send the report by email, you need to complete the payment.",
            "Para enviar o relatório por email, é necessário completar o pagamento."
        )
        st.warning(warning_msg)

    # ============ FEEDBACK BLOCK 2 (after download/email) ============
    st.markdown('<div id="section-feedback-bottom"></div>', unsafe_allow_html=True)
    st.write("")
    
    feedback_title_bottom = i18n_label(
        "💭 ¿Cómo fue tu experiencia general con AestheticSafe?",
        "💭 How was your overall experience with AestheticSafe?",
        "💭 Como foi sua experiência geral com o AestheticSafe?"
    )
    
    # Minimalist grayscale emoji feedback
    st.markdown(f"<p class='text-sm font-semibold text-gray-200'>{feedback_title_bottom}</p>", unsafe_allow_html=True)
    
    # Get evaluation ID and email for logging
    eval_id_bottom = st.session_state.get("sess_ref", "")
    user_email_bottom = st.session_state.get("email", "")
    
    # Get i18n tooltips
    happy_help = i18n_label("Me sentí bien", "I felt good", "Me senti bem")
    neutral_help = i18n_label("Fue aceptable", "It was acceptable", "Foi aceitável")
    sad_help = i18n_label("Tuve dificultades", "I had difficulties", "Tive dificuldades")
    
    # === EMOJI FEEDBACK (BOTTOM) — TRES COLUMNAS PEQUEÑAS Y CENTRADAS ===
    def handle_feedback_bottom(choice):
        if st.session_state.get("feedback_bottom_choice") != choice:
            st.session_state["feedback_bottom_choice"] = choice
            st.session_state["feedback_bottom_timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            log_to_funnel_progress(satisfaction_step="step2", emoji=choice, comment="")

    # Emojis con st.columns para layout horizontal nativo (solución definitiva)
    col1_b, col2_b, col3_b = st.columns([1, 1, 1], gap="small")
    with col1_b:
        st.button("😞", key="emoji_sad_bottom", help="Tuve dificultades", on_click=handle_feedback_bottom, args=("sad",), use_container_width=True)
    with col2_b:
        st.button("😐", key="emoji_neutral_bottom", help="Fue aceptable", on_click=handle_feedback_bottom, args=("neutral",), use_container_width=True)
    with col3_b:
        st.button("🙂", key="emoji_happy_bottom", help="Me sentí bien", on_click=handle_feedback_bottom, args=("happy",), use_container_width=True)
    
    # Show response only for neutral/sad (NOT for happy)
    if "feedback_bottom_choice" in st.session_state:
        choice_bottom = st.session_state["feedback_bottom_choice"]
        
        # Only show UI for neutral/sad - happy just logs silently
        if choice_bottom in ["neutral", "sad"]:
            st.markdown('<div class="fade-in-content">', unsafe_allow_html=True)
            
            feedback_prompt_bottom = i18n_label(
                "💭 ¿Cómo podemos mejorar tu experiencia?",
                "💭 How can we improve your experience?",
                "💭 Como podemos melhorar sua experiência?"
            )
            feedback_placeholder_bottom = i18n_label(
                "Escribí aquí tus sugerencias o comentarios...",
                "Write your suggestions or comments here...",
                "Escreva aqui suas sugestões ou comentários..."
            )
            feedback_text_bottom = st.text_area(
                feedback_prompt_bottom, 
                key="feedback_bottom_text", 
                height=100,
                placeholder=feedback_placeholder_bottom
            )
            st.session_state["feedback_bottom_text_value"] = feedback_text_bottom
            
            # Log comment to Funnel_Progress if provided
            if feedback_text_bottom and feedback_text_bottom.strip():
                log_to_funnel_progress(
                    satisfaction_step="step2",
                    emoji=choice_bottom,
                    comment=feedback_text_bottom.strip()
                )
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Feedback already logged via individual emoji/comment interactions above
    
    st.write("")
    # ============ /FEEDBACK BLOCK 2 ============

    # ---- FIN bloque i18n de descarga/envío ----


# ===== Función principal callable desde app.py =====
def vista_calculadora_pi():
    """Entry point para ser llamado desde app.py"""
    calculadora()

# ===== ENTRYPOINT DIRECTO PARA STREAMLIT =====
if __name__ == "__main__":
    # Cuando se ejecuta directamente `streamlit run calculadora.py`
    calculadora()
