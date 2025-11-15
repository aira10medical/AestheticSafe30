# ruff: noqa
# pyright: reportUnusedExpression=false

"""
app.py — Shell mínimo para AestheticSafe en Streamlit/Railway

- Mantiene toda la lógica actual en calculadora.calculadora()
- No incluye el chat en el sidebar; SAFE-MD se renderiza como chat flotante fijo abajo.
- No toca la implementación interna de calculadora.py
"""

import os
import streamlit as st
from openai import OpenAI
from calculadora import calculadora  # ⬅️ tu app original, intacta

# ==========================
# 🔑 Cliente OpenAI
# ==========================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ==========================
# 🧠 (Helper functions preserved — no UI sidebar)
# ==========================
def _ensure_chat_state():
    """Inicializa el historial de chat en sesión."""
    if "safe_chat_history" not in st.session_state:
        st.session_state["safe_chat_history"] = []  # lista de dicts {role, content}
    if "safe_chat_files" not in st.session_state:
        st.session_state["safe_chat_files"] = []


def _call_safe_md_assistant(question: str, files_context: str = "") -> str:
    """
    Llama a GPT-5.1-mini con un prompt médico controlado.
    No da órdenes médicas directas, responde en lenguaje claro y prudente.
    """
    base_prompt = (
        "Actuás como un asistente médico virtual especializado en cirugía plástica estética. "
        "Respondé en español, con lenguaje claro, empático y profesional. "
        "No realices diagnósticos definitivos ni indiqués tratamientos concretos; "
        "enfatizá siempre que la evaluación final requiere consulta presencial con el cirujano.\n\n"
    )

    if files_context:
        base_prompt += f"Información sobre archivos adjuntos del paciente:\n{files_context}\n\n"

    full_input = (
        base_prompt
        + "Pregunta actual del paciente:\n"
        + question
    )

    try:
        response = client.responses.create(
            model="gpt-5.1-mini",
            input=full_input,
        )
        return response.output_text
    except Exception as e:
        # Falla segura: no rompe la app, solo informa el error genérico
        return (
            "Hubo un problema al consultar el asistente de IA. "
            "Por favor, intentá de nuevo más tarde. Detalle técnico: "
            f"{type(e).__name__}"
        )


# ==========================
# 🧱 Layout principal
# ==========================
def main():
    st.set_page_config(
        page_title="AestheticSafe · SAFE·MD",
        page_icon="💎",
        layout="wide",
    )

    # Layout tipo Copilot: izquierda app médica, derecha (removed sidebar chat)
    col_app, col_chat = st.columns([2.2, 1])

    with col_app:
        # ⬇️ Tu app actual, sin tocar calculadora.py
        calculadora()

    # Nota: el sidebar de chat fue eliminado intencionalmente.


# Para ejecución con `python app.py` o herramientas que esperan entrypoint
if __name__ == "__main__":
    main()


from safe_chat_bottom import render_safe_chat
render_safe_chat()