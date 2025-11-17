# gsheets.py — utilidades robustas para Google Sheets (descarta eventos cortos)
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

# === TU SPREADSHEET ===
SHEET_KEY = "12PC1-vv-RIPDDs0O07Xg0ZoAFH7H6npJSnDDpUtPkJQ"

# Pestaña de envío final (la grande)
LOG_TAB_TITLE = "Calculadora_Evaluaciones"
LOG_TAB_GID = 1211408350  # gid de esa pestaña

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def _load_credentials() -> Tuple[Optional[Credentials], Optional[str]]:
    info: Optional[Dict[str, Any]] = None
    env = os.getenv("GOOGLE_CREDENTIALS")
    if env:
        try:
            info = json.loads(env)
        except Exception:
            info = None
    if not info:
        try:
            import streamlit as st  # opcional
            if "GOOGLE_CREDENTIALS" in st.secrets:
                info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        except Exception:
            info = None
    if not info and os.path.exists("credentials.json"):
        try:
            with open("credentials.json", "r", encoding="utf-8") as fh:
                info = json.load(fh)
        except Exception:
            info = None
    if not info:
        return None, None
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return creds, info.get("client_email")

def _open_sheet_and_tab(tab_title: str = LOG_TAB_TITLE, tab_gid: Optional[int] = LOG_TAB_GID) -> Tuple[Optional[gspread.Worksheet], Optional[str]]:
    creds, svc_email = _load_credentials()
    if not creds:
        return None, svc_email
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_KEY)

    ws: Optional[gspread.Worksheet] = None
    if tab_gid:
        try:
            ws = sh.get_worksheet_by_id(tab_gid)
        except Exception:
            ws = None
    if ws is None:
        try:
            ws = sh.worksheet(tab_title)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=tab_title, rows=2000, cols=50)
    return ws, svc_email

def append_row_safe(row: List[Any], tab: str = LOG_TAB_TITLE, tab_gid: Optional[int] = LOG_TAB_GID) -> Tuple[bool, Optional[str]]:
    """
    Agrega una fila a la pestaña indicada ajustando la longitud al header.
    - Si llega un dict: se mapea por nombre de columna (orden de headers).
    - Si llega una lista: se recortan vacíos a la izquierda y se ajusta al largo del header.
    Además: si el destino es la pestaña principal y la fila parece un EVENTO corto,
    se descarta silenciosamente (para que sólo queden filas de calculadora.py).
    """

    for attempt in range(3):
        try:
            ws, svc = _open_sheet_and_tab(tab, tab_gid)
            if not ws:
                return False, svc

            headers = ws.row_values(1)     # encabezados existentes en la Sheet
            n = len(headers)

            # --- detección de "evento corto" (solo etiquetas técnicas) ---
            def _is_short_event(_row: Any) -> bool:
                # Texto concatenado de la fila (soporta list o dict)
                if isinstance(_row, dict):
                    parts = [str(v) for v in _row.values()]
                else:
                    parts = ["" if v is None else str(v) for v in (_row or [])]
                text = " ".join(parts).lower()

                # Solo filtramos eventos técnicos explícitos
                tags = ("session_open", "share_click", "share_done")
                return any(t in text for t in tags)


            # Si estamos escribiendo en la pestaña grande y la fila luce "evento", NO escribir
            if tab == LOG_TAB_TITLE and _is_short_event(row):
                return True, svc  # éxito falso: no insertamos nada

            # --- normalización de valores para escritura ---
            if isinstance(row, dict):
                values = [row.get(h, "") for h in headers]
            else:
                values = list(row) if row is not None else []
                # Quitar vacíos a la izquierda (evita corrimientos)
                while values and (values[0] is None or str(values[0]).strip() == ""):
                    values.pop(0)
                # Ajustar al largo del header
                if len(values) < n:
                    values.extend([""] * (n - len(values)))
                elif len(values) > n:
                    values = values[:n]

            ws.append_row(values, value_input_option="USER_ENTERED")
            return True, svc

        except Exception:
            if attempt < 2:
                time.sleep(1.5 + attempt * 0.5)  # backoff
                continue

    return False, svc

# Aliases de compatibilidad
def append_row(row: List[Any], tab: Optional[str] = None, tab_gid: Optional[int] = None) -> Tuple[bool, Optional[str]]:
    return append_row_safe(row, tab if tab else LOG_TAB_TITLE, tab_gid if tab_gid is not None else LOG_TAB_GID)

def append_log_row(row: List[Any]) -> Tuple[bool, Optional[str]]:
    return append_row_safe(row, LOG_TAB_TITLE, LOG_TAB_GID)

def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def service_account_email() -> Optional[str]:
    _, svc = _load_credentials()
    return svc or ""
