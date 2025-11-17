# logger_bridge.py
# Módulo PUENTE ultra-seguro que envía registros a Google Sheets
# No modifica nada del proyecto ni requiere cambios internos

from gsheets import append_row_safe, utc_now_str
import streamlit as st

def registrar_evento_bridge(
    stage="unknown",
    substage="",
    session_id="",
    user_agent="",
    country="",
    extra=None
):
    """
    NO CRASHEA. Si algo falla → devuelve False sin romper la UI.
    Es un puente aislado a append_row_safe().
    """

    try:
        payload = [
            utc_now_str(),                                # Timestamp
            str(extra) if extra else "",                  # Request_Data
            "",                                           # Response_Data
            st.session_state.get("app_version", ""),      # App_Version
            st.session_state.get("browser_lang", ""),     # Browser_Lang
            st.session_state.get("idioma", ""),           # Idioma_Detected
            session_id,                                   # Session_ID
            user_agent,                                   # User_Agent
            country,                                      # Country
            stage,                                        # Stage
            substage                                      # Substage
        ]

        ok, svc = append_row_safe(
            payload,
            tab="V3_Interoperability_Log",
            tab_gid=831016227
        )

        return ok

    except Exception:
        return False
