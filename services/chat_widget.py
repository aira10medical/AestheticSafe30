# services/chat_widget.py
import streamlit as st
from services.openai_client import ask_openai

def render_chat_widget():
    """Floating bottom chat widget, isolated from the app."""
    
    # --- Widget container fixed at the bottom ---
    widget_css = """
    <style>
        .floating-chat {
            position: fixed;
            bottom: 0;
            left: 0;
            width: 100%;
            background: #111;
            padding: 12px;
            border-top: 1px solid #333;
            z-index: 999999;
        }
        .floating-chat textarea {
            height: 60px !important;
        }
    </style>
    """

    st.markdown(widget_css, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="floating-chat">', unsafe_allow_html=True)
        
        user_msg = st.text_area("🧠 Consultá lo que quieras:", key="chat_input")

        send = st.button("Enviar", key="chat_send")

        if send and user_msg.strip():
            response = ask_openai(user_msg)
            st.markdown(f"**Respuesta:** {response}")

        st.markdown("</div>", unsafe_allow_html=True)
