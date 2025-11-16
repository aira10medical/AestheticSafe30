# pages/1_Chat_Médico.py
# Streamlit page isolated from core; stores chat history in st.session_state and
# uses services.openai_client.chat_medic(prompt) to obtain assistant responses.
# This page does NOT import or modify any core modules (calculadora, gsheets, app, pdf_generator, etc.)
import streamlit as st
from services.openai_client import chat_medic, is_available

st.set_page_config(page_title="1 — Chat Médico (SAFE • IA)", layout="wide")

st.title("1 — Chat Médico (SAFE • IA)")
st.markdown("Página de chat aislada. Esta página no modifica ni importa el core.")

if "chat_history" not in st.session_state:
    # list of dicts: {"role": "user"|"assistant", "text": str}
    st.session_state.chat_history = []

# Render chat messages
for msg in st.session_state.chat_history:
    role = msg.get("role")
    text = msg.get("text", "")
    if role == "user":
        st.markdown(
            f"",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"",
            unsafe_allow_html=True,
        )

# Sidebar/status
with st.sidebar:
    st.header("Estado")
    st.write("OpenAI disponible:", is_available())
    st.markdown("Variables de entorno requeridas: OPENAI_API_KEY (en Railway).")

# Input area
prompt = st.text_area("Escribí tu consulta médica (no compartas datos sensibles):", key="chat_prompt", height=140)

if st.button("Enviar") and prompt and prompt.strip():
    user_text = prompt.strip()
    st.session_state.chat_history.append({"role": "user", "text": user_text})

    # Call the isolated service (synchronous)
    assistant_text = chat_medic(user_text)

    st.session_state.chat_history.append({"role": "assistant", "text": assistant_text})

    # Clear input and rerun to show updated history
    st.session_state.chat_prompt = ""
    st.experimental_rerun()
