import streamlit as st
from openai import OpenAI
import base64

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def _init_chat_state():
    if "safe_chat_messages" not in st.session_state:
        st.session_state.safe_chat_messages = []
    if "safe_chat_files" not in st.session_state:
        st.session_state.safe_chat_files = []

def _call_llm(messages, files):
    vision_files = []
    for f in files:
        b64 = base64.b64encode(f.read()).decode()
        vision_files.append({"type": "input_image", "image_url": f"data:image/jpeg;base64,{b64}"})

    formatted = []
    for m in messages:
        formatted.append({"role": m["role"], "content": [{"type": "text", "text": m["content"]}]})

    if vision_files:
        formatted[-1]["content"] += vision_files

    resp = client.responses.create(
        model="gpt-4.1",
        input=formatted,
    )
    return resp.output_text

def render_safe_chat():
    _init_chat_state()

    st.markdown(
        '''
        <style>
        .safe-chat-box {
            position: fixed;
            bottom: 0;
            width: 100%;
            background: #0E1117;
            padding: 12px;
            border-top: 1px solid #333;
            z-index: 999999;
        }
        .safe-chat-messages {
            position: fixed;
            bottom: 80px;
            left: 0;
            width: 100%;
            max-height: 40%;
            overflow-y: auto;
            padding: 10px;
            z-index: 99999;
        }
        .safe-chat-bubble-user {
            background: #444;
            padding: 10px;
            margin: 6px;
            border-radius: 10px;
            color: white;
            max-width: 80%;
        }
        .safe-chat-bubble-ai {
            background: #1E3A8A;
            padding: 10px;
            margin: 6px;
            border-radius: 10px;
            color: white;
            max-width: 80%;
        }
        </style>
        ''',
        unsafe_allow_html=True,
    )

    # mensajes arriba
    msg_zone = st.container()
    with msg_zone:
        st.markdown('<div class="safe-chat-messages">', unsafe_allow_html=True)
        for m in st.session_state.safe_chat_messages:
            if m["role"] == "user":
                st.markdown(f"<div class='safe-chat-bubble-user'>{m['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='safe-chat-bubble-ai'>{m['content']}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # caja abajo
    with st.container():
        st.markdown('<div class="safe-chat-box">', unsafe_allow_html=True)

        files = st.file_uploader("Enviar archivos (PDF, JPG, PNG, DICOM, etc.)", accept_multiple_files=True, label_visibility="collapsed")

        user_input = st.text_input("Escribe aquí…", label_visibility="collapsed")

        if st.button("Enviar"):
            if user_input or files:
                st.session_state.safe_chat_messages.append({"role": "user", "content": user_input})
                if files:
                    st.session_state.safe_chat_files = files

                ai_msg = _call_llm(st.session_state.safe_chat_messages, files or [])
                st.session_state.safe_chat_messages.append({"role": "assistant", "content": ai_msg})

        st.markdown('</div>', unsafe_allow_html=True)