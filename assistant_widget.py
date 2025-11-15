import streamlit as st
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def render_assistant():
    """Renderiza un botón flotante + ventana de chat sin interferir con la UI principal."""
    
    # === ESTILO DEL BOTÓN + PANEL ===
    st.markdown("""
    <style>
      .floating-btn {
          position: fixed;
          bottom: 28px;
          right: 28px;
          background: #38c694;
          color: white;
          font-size: 22px;
          padding: 14px 20px;
          border-radius: 50%;
          cursor: pointer;
          box-shadow: 0px 4px 14px rgba(0,0,0,0.25);
          z-index: 9999;
          text-align: center;
      }
      .chat-box {
          position: fixed;
          bottom: 90px;
          right: 28px;
          width: 340px;
          padding: 18px;
          background: #ffffff;
          border-radius: 14px;
          box-shadow: 0px 5px 18px rgba(0,0,0,0.15);
          z-index: 9999;
      }
    </style>
    ", unsafe_allow_html=True)

    # Estado persistente
    if "assistant_open" not in st.session_state:
        st.session_state["assistant_open"] = False

    # Botón flotante (toggle)
    if st.button("💬", key="fab_btn", help="Asistente IA", use_container_width=False):
        st.session_state["assistant_open"] = not st.session_state["assistant_open"]

    # Panel del chat
    if st.session_state["assistant_open"]:
        with st.container():
            st.markdown('<div class="chat-box">', unsafe_allow_html=True)

            st.markdown('### 🤖 Asistente IA')
            pregunta = st.text_area("Escribí tu pregunta:", key="assistant_q")

            if st.button("Enviar", key="assistant_send"):
                if pregunta.strip():
                    try:
                        r = client.responses.create(
                            model="gpt-5.1-mini",
                            input=pregunta
                        )
                        st.success(r.output_text)
                    except Exception as e:
                        st.error("Error al consultar la IA")
                        st.code(str(e))
                else:
                    st.warning("Escribí algo primero.")

            st.markdown("</div>", unsafe_allow_html=True)