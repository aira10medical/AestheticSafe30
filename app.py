# ruff: noqa
# pyright: reportUnusedExpression=false

"""
app.py — Shell mínimo para AestheticSafe en Streamlit/Railway

- Mantiene toda la lógica actual en calculadora.calculadora()
- SAFE-MD se renderiza como chat flotante fijo abajo (safe_chat_bottom.py)
- No toca calculadora.py
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
# 🧠 Helper functions (se conservan para compatibilidad)
# ==========================
def _ensure_chat_state():
    if "safe_chat_history" not in st.session_state:
        st.session_state["safe_chat_history"] = []
    if "safe_chat_files" not in st.session_state:
        st.session_state["safe_chat_files"] = []


def _call_safe_md_assistant(question: str, files_context: str = "") -> str:
    base_prompt = (
        "Actuás como un asistente médico virtual especializado en cirugía plástica estética. "
        "Respondé en español, con lenguaje claro, empático y profesional. "
        "No realices diagnósticos definitivos ni indiqués tratamientos concretos; "
        "enfatizá siempre que la evaluación final requiere consulta presencial con el cirujano.\n\n"
    )

    if files_context:
        base_prompt += f"Información sobre archivos adjuntos del paciente:\n{files_context}\n\n"

    full_input = base_prompt + "Pregunta actual del paciente:\n" + question

    try:
        response = client.responses.create(
            model="gpt-5.1-mini",
            input=full_input,
        )
        return response.output_text
    except Exception as e:
        return (
            "Hubo un problema al consultar el asistente de IA. "
            "Intentá más tarde. Detalle: " + type(e).__name__
        )


# ==========================
# 🧱 Layout principal
# ==========================
def main():
    st.set_page_config(
        page_title="AestheticSafe · SAFE-MD",
        page_icon="💎",
        layout="wide",
    )

    col_app, col_empty = st.columns([2.2, 1])

    with col_app:
        calculadora()

    # --- importar y renderizar el chat flotante ---
    from safe_chat_bottom import render_safe_chat
    render_safe_chat()


# Entry point
if __name__ == "__main__":
    main()
