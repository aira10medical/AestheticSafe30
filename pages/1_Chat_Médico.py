import streamlit as st
from services.openai_client import chat_medic, is_available

st.set_page_config(page_title="1 — Chat Médico (SAFE • IA)", layout="wide")

st.title("1 — Chat Médico (SAFE • IA)")
st.markdown("Página de chat aislada. Esta página no modifica ni importa el core.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

for msg in st.session_state.chat_history:
    role = msg.get("role")
    text = msg.get("text", "")
    if role == "user":
        st.markdown(
            f"<div style='text-align:right;background:#7a5cff;color:white;padding:10px;border-radius:10px;margin:8px 0'>{text}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='text-align:left;background:#222;color:#e8e8e8;padding:10px;border-radius:10px;margin:8px 0'>{text}</div>",
            unsafe_allow_html=True,
        )

with st.sidebar:
    st.header("Estado")
    st.write("OpenAI disponible:", is_available())
    st.markdown("Variables requeridas: OPENAI_API_KEY (en Railway).")

prompt = st.text_area("Escribí tu consulta médica (no compartas datos sensibles):", key="chat_prompt", height=140)

if st.button("Enviar") and prompt and prompt.strip():
    user_text = prompt.strip()
    st.session_state.chat_history.append({"role": "user", "text": user_text})
    assistant_text = chat_medic(user_text)
    st.session_state.chat_history.append({"role": "assistant", "text": assistant_text})
    st.session_state.chat_prompt = ""
    st.experimental_rerun()


