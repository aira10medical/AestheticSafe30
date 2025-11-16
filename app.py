import streamlit as st
from calculadora import calculadora
from safe_chat_bottom import render_safe_chat

def main():
    st.set_page_config(
        page_title="AestheticSafe • SAFE-MD",
        page_icon="🛡️",
        layout="wide",
    )

    col_app, _ = st.columns([2.2, 1])
    with col_app:
        calculadora()

    st.markdown(
        "<style>html, body, .stApp { overflow: visible !important; }</style>",
        unsafe_allow_html=True,
    )

    render_safe_chat()


if __name__ == "__main__":
    main()
