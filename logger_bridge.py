# logger_bridge.py
# Módulo PUENTE ultra-seguro que envía registros a Google Sheets
# No modifica nada del proyecto ni requiere cambios internos

from gsheets import append_row_safe, utc_now_str

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
            utc_now_str(),
            stage,
            substage,
            session_id,
            user_agent,
            country,
            str(extra) if extra else "",
        ]

        ok, svc = append_row_safe(payload, tab="Calculadora_Evaluaciones", tab_gid=1211408350)
        return ok
    except Exception:
        return False
