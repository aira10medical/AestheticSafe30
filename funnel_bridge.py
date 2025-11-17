# funnel_bridge.py
from gsheets import append_row_safe, utc_now_str
import streamlit as st

def registrar_funnel(
    stage="unknown",
    email="",
    doctor="",
    session_id="",
    country="",
    user_agent=""
):
    try:
        payload = [
            utc_now_str(),            # Timestamp
            email,                    # email
            doctor,                   # doctor_email
            session_id,               # session_id
            country,                  # country
            stage,                    # stage
            user_agent,               # user_agent
        ]

        ok, svc = append_row_safe(
            payload,
            tab="V3_Funnel_Progress",
            tab_gid=404698208   # LO VALIDAMOS MAÑANA
        )

        return ok

    except Exception:
        return False
