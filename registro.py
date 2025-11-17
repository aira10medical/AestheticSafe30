# registro.py
# Módulo aislado para registrar actividad del FUNNEL V3 en Google Sheets.

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


# ----------------- HELPERS -----------------

def now_str():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def get_creds():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_json:
        return None, None
    try:
        info = json.loads(creds_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        svc = info.get("client_email", None)
        return creds, svc
    except:
        return None, None


def open_sheet():
    creds, svc = get_creds()
    if not creds:
        return None, svc
    try:
        gc = gspread.authorize(creds)
        ss = gc.open_by_key(SHEET_KEY)
        ws = ss.worksheet(TAB_FUNNEL)
        return ws, svc
    except:
        return None, svc


# ----------------- FUNCIÓN PRINCIPAL -----------------

def registrar_evento(session_id: str,
                     stage: str,
                     substage: str = "",
                     user_agent: str = "",
                     country: str = "",
                     extra: dict = None):

    ws, svc = open_sheet()
    if not ws:
        return False, svc

    fila = [
        now_str(),
        session_id,
        stage,
        substage,
        user_agent,
        country,
    ]

    try:
        fila.append(json.dumps(extra) if extra else "")
    except:
        fila.append("")

    try:
        ws.append_row(fila, value_input_option="USER_ENTERED")
        return True, svc
    except:
        return False, svc


# ----------------- ADAPTADOR PARA calculadora.py -----------------

def registrar_evento_funnel(**kwargs):

    session_id  = kwargs.get("sess_id", "")
    stage       = kwargs.get("stage", "")
    substage    = kwargs.get("substage", "")
    user_agent  = kwargs.get("user_agent", "")
    country     = kwargs.get("country", "")
    extra       = kwargs

    return registrar_evento(
        session_id=session_id,
        stage=stage,
        substage=substage,
        user_agent=user_agent,
        country=country,
        extra=extra,
    )
