# registro.py
# Módulo oficial y definitivo para registrar eventos del FUNNEL V3 y de interoperabilidad.
# 100% compatible con tus Google Sheets reales. No toca calculadora.py.

import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_KEY = "12PC1-vv-RIPDDs0O07Xg0ZoAFH7H6npJSnDDpUtPkJQ"

TAB_FUNNEL = "V3_Funnel_Progress"
TAB_INTEROP = "V3_Interoperability_Log"


def _utc():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _creds():
    raw = os.getenv("GOOGLE_CREDENTIALS")
    if not raw:
        return None, None
    try:
        info = json.loads(raw)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        return creds, info.get("client_email", None)
    except:
        return None, None


def _open(tab_name):
    creds, svc = _creds()
    if not creds:
        return None, svc
    try:
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_KEY)
        return sh.worksheet(tab_name), svc
    except:
        return None, svc


# -------------------------------------------------------------------
# 🔵 1. REGISTRO EN V3_Funnel_Progress
# -------------------------------------------------------------------
FUNNEL_HEADERS = [
    "Timestamp",
    "satisfaction_step1",
    "satisfaction_step1_comment",
    "satisfaction_step2",
    "satisfaction_step2_comment",
    "session_id",
    "user_agent",
    "country",
    "doctor_email",
    "stage",
    "substage",
    "last_contact_at",
    "next_contact_at",
    "contact_attempts",
    "sequence_name",
    "wa_template",
    "app_version",
    "idioma_ui",
    "logo_fade_triggered",
    "scroll_events",
]


def registrar_evento_funnel(**data):
    """
    Recibe TODA la session_state de calculadora.py como **kwargs.
    Extrae solo lo que existe en el sheet.
    No crashea nunca.
    """

    ws, svc = _open(TAB_FUNNEL)
    if not ws:
        return False, svc

    row = [_utc()]  # Timestamp

    for h in FUNNEL_HEADERS[1:]:
        row.append(data.get(h, ""))

    try:
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True, svc
    except:
        return False, svc


# -------------------------------------------------------------------
# 🔵 2. REGISTRO EN V3_Interoperability_Log
# -------------------------------------------------------------------
INTEROP_HEADERS = [
    "Timestamp",
    "Request_Data",
    "Response_Data",
    "App_Version",
    "Browser_Lang",
    "Idioma_Detected",
    "Session_ID",
    "User_Agent",
    "Country",
    "Stage",
    "Substage",
]


def registrar_evento_interop(
    request_data: dict,
    response_data: dict,
    app_version: str,
    browser_lang: str,
    idioma_detected: bool,
    session_id: str,
    user_agent: str,
    country: str,
    stage: str,
    substage: str,
):
    """
    Inserta EXACTAMENTE en el sheet V3_Interoperability_Log siguiendo tus columnas reales.
    """

    ws, svc = _open(TAB_INTEROP)
    if not ws:
        return False, svc

    row = [
        _utc(),
        json.dumps(request_data),
        json.dumps(response_data),
        app_version,
        browser_lang,
        idioma_detected,
        session_id,
        user_agent,
        country,
        stage,
        substage,
    ]

    try:
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True, svc
    except:
        return False, svc
