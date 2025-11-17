# feedback_bridge.py
from gsheets import append_row_safe, utc_now_str

def registrar_feedback(
    session_id,
    user_agent,
    country,
    doctor_email,
    satisfaction,
    emotion,
    step,
):
    try:
        payload = [
            utc_now_str(),
            satisfaction,
            emotion,
            session_id,
            user_agent,
            country,
            doctor_email,
            "feedback",     # stage fijo
            step            # step1, step2…
        ]

        ok, svc = append_row_safe(
            payload,
            tab="Final_Progress",
            tab_gid=404698208  # VALIDAMOS MAÑANA
        )

        return ok
    except:
        return False
