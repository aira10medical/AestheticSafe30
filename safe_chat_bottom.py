import streamlit as st
from openai import OpenAI
import base64
import time

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==============================
# 🔧 Estado del Chat
# ==============================
def _init_chat_state():
    if "safe_chat_messages" not in st.session_state:
        st.session_state.safe_chat_messages = []

    if "safe_chat_files" not in st.session_state:
        st.session_state.safe_chat_files = []


# ==============================
# 🤖 Llamada al modelo SAFE-MD
# ==============================
def _call_safe_md(text, files):
    vision_files = []

    for f in files:
        b64 = base64.b64encode(f.read()).decode()
        vision_files.append({
            "type": "input_image",
            "image_url": f"data:image/jpeg;base64,{b64}"
        })

    # Mensaje para el modelo
    formatted = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text}
            ]
        }
    ]

    if vision_files:
        formatted[0]["content"] += vision_files

    resp = client.responses.create(
        model="gpt-4.1",
        input=formatted,
    )

    return resp.output_text


# ==============================
# 💬 Render del Chat SAFE-MD
# ==============================
def render_safe_chat():
    _init_chat_state()

    st.markdown("""
        <style>
            .safe-chat-box {
                position: fixed;
                bottom: 0;
                left: 0;
                width: 100%;
                padding: 10px;
                background: #111;
                border-top: 1px solid #444;
                z-index: 999999;
            }
            .safe-chat-input input {
                border-radius: 6px !important;
                padding: 8px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="safe-chat-box">', unsafe_allow_html=True)

    text = st.text_input("Preguntar a SAFE-MD", key="safe_chat_input", label_visibility="collapsed")
    files = st.file_uploader("Subir imágenes opcionales", type=["jpg","jpeg","png"], accept_multiple_files=True)

    send = st.button("Enviar", key="safe_chat_send")

    if send and text.strip() != "":
        # Guardar mensaje del usuario
        st.session_state.safe_chat_messages.append({
            "role": "user",
            "text": text,
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "attachments": files or [],
        })

        # Llamar SAFE-MD
        reply = _call_safe_md(text, files or [])

        # Guardar respuesta
        st.session_state.safe_chat_messages.append({
            "role": "assistant",
            "text": reply,
            "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
            "attachments": [],
        })

        st.experimental_rerun()

    # Render mensajes
    for msg in st.session_state.safe_chat_messages:
        if msg["role"] == "user":
            st.markdown(f"🧑 **Vos:** {msg['text']}")
        else:
            st.markdown(f"🤖 **SAFE-MD:** {msg['text']}")

    st.markdown("</div>", unsafe_allow_html=True)

