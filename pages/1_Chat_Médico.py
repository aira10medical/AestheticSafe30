# pages/1_Chat_Médico.py
# Streamlit page isolated from core; stores chat history in st.session_state and
# uses services.openai_client.chat_medic(prompt) to obtain assistant responses.
import streamlit as st
from services.openai_client import chat_medic

st.set_page_config(page_title="1 — Chat Médico (SAFE • IA)", layout="wide")

st.title("1 — Chat Médico (SAFE • IA)")
st.markdown("Página de chat aislada. Esta página no modifica ni importa el core.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # list of dicts {"role": "user"|"assistant", "text": str}

# Display chat
for m in st.session_state.chat_history:
    if m.get("role") == "user":
        st.markdown(f"<div style='text-align:right;background:#7a5cff;color:white;padding:8px;border-radius:8px;margin:6px 0'>{m.get('text')}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='text-align:left;background:#222;color:#e8e8e8;padding:8px;border-radius:8px;margin:6px 0'>{m.get('text')}</div>", unsafe_allow_html=True)

# Input
prompt = st.text_area("Escribí tu consulta médica (no compartas datos sensibles):", key="chat_prompt", height=140)
if st.button("Enviar") and prompt and prompt.strip():
    user_text = prompt.strip()
    st.session_state.chat_history.append({"role": "user", "text": user_text})
    # Call isolated service
    assistant = chat_medic(user_text)
    st.session_state.chat_history.append({"role": "assistant", "text": assistant})
    # Clear input
    st.session_state.chat_prompt = ""
    st.experimental_rerun()
