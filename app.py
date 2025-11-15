# ruff: noqa
# pyright: reportUnusedExpression=false

"""
app.py — Shell mínimo para AestheticSafe en Streamlit/Railway

- Mantiene toda la lógica actual en calculadora.calculadora()
- Agrega un panel de chat IA a la derecha (SAFE·MD Chat)
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
# 🧠 Lógica de chat IA
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


def render_safe_chat_sidebar():
    """
    Renderiza el módulo de chat en la columna derecha,
    estilo 'panel Copilot' / mensajería limpia.
    """
    _ensure_chat_state()

    st.markdown("### 🤖 SAFE·MD Chat")
    st.caption(
        "Asistente IA para dudas generales sobre cirugía plástica estética. "
        "No reemplaza una consulta médica presencial."
    )

    # ---- Archivos adjuntos ----
    uploaded_files = st.file_uploader(
        "Adjuntar estudios, fotos o documentos (opcional)",
        type=["pdf", "jpg", "jpeg", "png", "dcm", "dicom"],
        accept_multiple_files=True,
        key="safe_chat_files_uploader",
    )

    # Guardamos los archivos sólo en sesión (no en disco)
    if uploaded_files is not None:
        # streamlit devuelve una lista o [] — nos aseguramos de usarla tal cual
        st.session_state["safe_chat_files"] = uploaded_files

    files = st.session_state.get("safe_chat_files", [])
    if files:
        with st.expander("Archivos adjuntados", expanded=False):
            for f in files:
                st.markdown(f"- `{{f.name}}`")

    st.markdown("---")

    # ---- Historial de conversación ----
    history = st.session_state["safe_chat_history"]

    # Mostramos últimos turnos (para no llenar toda la pantalla)
    max_turns = 8
    history_to_show = history[-max_turns:]

    for turn in history_to_show:
        role = turn.get("role", "user")
        content = turn.get("content", "")

        if role == "user":
            st.markdown(f"**Tú:** {{content}}")
        else:
            # assistant
            st.markdown(f"**SAFE·MD:** {{content}}")

        st.markdown("---")

    # ---- Input de usuario ----
    st.markdown("#### Escribí tu pregunta")

    with st.form("safe_chat_form", clear_on_submit=True):
        question = st.text_area(
            "Pregunta para SAFE·MD",
            placeholder="Ej: ¿Qué significa tener riesgo moderado en mi caso?",
            height=90,
            label_visibility="collapsed",
        )
        send = st.form_submit_button("💬 Enviar")

    if send:
        question_stripped = question.strip()
        if not question_stripped:
            st.warning("Escribí una pregunta antes de enviar.")
            return

        # Registramos turno del usuario
        history.append({"role": "user", "content": question_stripped})

        # Construimos contexto de archivos (por ahora solo nombres)
        files = st.session_state.get("safe_chat_files", [])
        if files:
            files_context = "Archivos adjuntos del paciente:\n" + "\n".join(
                f"- {{f.name}}" for f in files
            )
        else:
            files_context = ""

        with st.spinner("SAFE·MD está analizando tu pregunta…"):
            answer = _call_safe_md_assistant(question_stripped, files_context)

        # Registramos respuesta
        history.append({"role": "assistant", "content": answer})
        st.session_state["safe_chat_history"] = history

        # Mostramos respuesta inmediatamente
        st.success("Respuesta de SAFE·MD:")
        st.write(answer)


# ==========================
# 🧱 Layout principal
# ==========================
def main():
    st.set_page_config(
        page_title="AestheticSafe · SAFE·MD",
        page_icon="💎",
        layout="wide",
    )

    # Layout tipo Copilot: izquierda app médica, derecha chat IA
    col_app, col_chat = st.columns([2.2, 1])

    with col_app:
        # ⬇️ Tu app actual, sin tocar calculadora.py
        calculadora()

    with col_chat:
        render_safe_chat_sidebar()


# Para ejecución con `python app.py` o herramientas que esperan entrypoint
if __name__ == "__main__":
    main()


from safe_chat_bottom import render_safe_chat
render_safe_chat()