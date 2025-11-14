# risk_widget.py — versión stui

    try:
    import streamlit_astui as stui  # pyright: ignore[reportMissingImports] # Optional dependency
except ImportError:
    stui = None

    # ===== Colores de marca =====
    COLOR_BAJO     = "#38c694"
    COLOR_MODERADO = "#fcb960"
    COLOR_ALTO     = "#fa5f45"
    COLOR_BG       = "#0e0e10"

    def _badge(texto: str, color: str):
        html = (
            f'<div style="display:inline-block;padding:6px 10px;'
            f'border-radius:10px;font-weight:600;color:white;'
            f'background:{color};">{texto}</div>'
        )
        stui.markdown(html, unsafe_allow_html=True)

    def risk_widget() -> None:
        if stui is None:
            return

        stui.title("Vista para Médicos (ES)")
        stui.write("Aquí va tu código de cálculo o visualización")

        # Ejemplo mínimo (podés borrar)
        riesgo = stui.selectbox("Nivel de riesgo", ["Bajo", "Moderado", "Alto"], index=0)
        if riesgo == "Bajo":
            _badge("Riesgo Bajo", COLOR_BAJO)
        elif riesgo == "Moderado":
            _badge("Riesgo Moderado", COLOR_MODERADO)
        else:
            _badge("Riesgo Alto", COLOR_ALTO)