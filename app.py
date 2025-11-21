# ============================================================
# DIAGNOSTIC: detect which openai_client.py is being loaded
# ============================================================
import importlib, importlib.util, sys, os, traceback

def _diag_openai_client():
    try:
        spec = importlib.util.find_spec("services.openai_client")
        if spec:
            print(">>> USING OPENAI_CLIENT (spec.origin):", spec.origin)
        else:
            print(">>> services.openai_client spec not found")

        try:
            oc = importlib.import_module("services.openai_client")
            print(">>> USING OPENAI_CLIENT (module.__file__):", getattr(oc, "__file__", None))
        except Exception as ie:
            print(">>> IMPORT ERROR importing services.openai_client:", repr(ie))
            traceback.print_exc()

        found = set()
        for p in sys.path:
            try:
                candidate = os.path.join(p, "services", "openai_client.py")
                if os.path.isfile(candidate):
                    found.add(os.path.abspath(candidate))
            except Exception:
                pass

        for root, dirs, files in os.walk(os.getcwd()):
            if "openai_client.py" in files:
                found.add(os.path.abspath(os.path.join(root, "openai_client.py")))

        if found:
            for f in sorted(found):
                print(">>> FOUND openai_client.py at:", f)
        else:
            print(">>> No openai_client.py files discovered")
    except Exception:
        traceback.print_exc()

_diag_openai_client()

# ============================================================
# ruff: noqa
# pyright: reportUnusedExpression=false
# ============================================================

# app.py — conexión robusta a Google Sheets (Secrets o credentials.json)
from services.chat_widget import render_chat_widget

import os
import json
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from calculadora import calculadora
from logger_bridge import registrar_evento_bridge
from gsheets import append_row_safe, utc_now_str, service_account_email
APP_VERSION = "v1.1"
LOG_TAB = "Calculadora_Evaluaciones"
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def obtener_respuesta_ia(pregunta):
    response = client.responses.create(
        model="gpt-5.1-mini",
        input=pregunta
    )
    return response.output_text

def vista_calculadora_pi():
    calculadora()


# ------- Google Sheets Config --------
SHEET_KEY = "12PC1-vv-RIPDDs0O07Xg0ZoAFH7H6npJSnDDpUtPkJQ"
WORKSHEET_TITLE = "Evaluación Estética - SAFE MD AI 25"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_sheet():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise RuntimeError("Falta el secret GOOGLE_CREDENTIALS en Replit")

    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_KEY)
    worksheet = sh.worksheet(WORKSHEET_TITLE)
    return worksheet

def leer_datos():
    ws = get_sheet()
    return ws.get_all_values()

def agregar_fila(nueva_fila):
    ws = get_sheet()
    ws.append_row(nueva_fila, value_input_option="USER_ENTERED")
    return True


# ------- CSS UI -------

st.markdown("""
<style>
:root{
  --brand-primary:#38c694;
  --brand-warn:#fcb960;
  --brand-danger:#fa5f45;
}

.main { background-color: #f7f9fc; }
.stButton>button{
  background:var(--brand-primary)!important;
  color:#fff!important;
  font-weight:700!important;
  border-radius:10px!important;
  padding:.55rem 1rem!important;
  border:0!important;
}
.stButton>button:hover{ filter:brightness(.95); }

.stTextInput>div>div>input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"]{
  border-radius:10px!important;
}
h1, h2, h3{ color:#0f172a; }
hr{ border:none; border-top:1px solid #e5e7eb; margin:1rem 0; }
.badge{ display:inline-block; padding:.35rem .7rem; border-radius:999px;
        font-weight:700; font-size:.95rem; }
.badge-low{ background:rgba(56,198,148,.12); color:#38c694; }
.badge-mod{ background:rgba(252,185,96,.15); color:#fcb960; }
.badge-high{ background:rgba(250,95,69,.15); color:#fa5f45; }
</style>
""", unsafe_allow_html=True)

# ============================================
# Vista Paciente (NO MODIFICADA)
# ============================================

APP_VERSION = "v1.1"
LOG_TAB = "Calculadora_Evaluaciones"

# ------ función enorme de UI mantenida intacta ------
# (NO LA REPITO AQUÍ PARA AHORRAR ESPACIO, pero debes pegar tu versión completa)
# PEGA COMPLETA LA FUNCIÓN vista_paciente_es AQUÍ
# ----------------------------------------------------

# (Tu código completo de vista_paciente_es ya lo pegaste, mantenelo sin tocar)

# ============================================
# Asistente IA (NO MODIFICADO)
# ============================================

# (Aquí va todo tu bloque actual tal cual sobre preguntas IA. No cambia nada)

# ============================================
# Router + cálculo
# ============================================

st.markdown("""
<style>
section[data-testid="stSidebar"] {display: none !important;}
div[data-testid="collapsedControl"] {display: none !important;}
</style>
""", unsafe_allow_html=True)

def _render_main():
    try:
        vista_calculadora_pi()
    except Exception as e:
        import traceback
        st.error(f"❌ calculadora() lanzó: {type(e).__name__}: {e}")
        st.code("".join(traceback.format_exception(e)))

def start_streamlit_server():
    port = int(os.environ.get("PORT", 5000))

    print("="*60)
    print("🚀 INICIANDO AestheticSafe")
    print(f"📍 Puerto detectado: {port}")
    print(f"🌐 Dominio Replit: {os.environ.get('REPLIT_DEV_DOMAIN','localhost')}")
    print("="*60)

    cmd = [
        "streamlit","run","app.py",
        "--server.port",str(port),
        "--server.address","0.0.0.0",
        "--server.headless","true",
        "--server.enableCORS","false",
        "--server.enableXsrfProtection","false"
    ]

    os.system(" ".join(cmd))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("="*60)
    print(f"🚀 Iniciando AestheticSafe en puerto {port}")
    print("="*60)

    os.system(
        f"streamlit run calculadora.py --server.port {port} "
        f"--server.address 0.0.0.0 --server.headless true"
    )
else:
    _render_main()

render_chat_widget()
