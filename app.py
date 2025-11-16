# ruff: noqa
# pyright: reportUnusedExpression=false

# app.py — conexión robusta a Google Sheets (Secrets o credentials.json)
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
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def obtener_respuesta_ia(pregunta):
    response = client.responses.create(
        model="gpt-5.1-mini",
        input=pregunta
    )
    return response.output_text


def vista_calculadora_pi():
    calculadora()  # <-- solo llama a calculadora(), sin título duplicado


# Configuración de tu hoja
SHEET_KEY = "12PC1-vv-RIPDDs0O07Xg0ZoAFH7H6npJSnDDpUtPkJQ"  # <-- tu ID
WORKSHEET_TITLE = "Evaluación Estética - SAFE MD AI 25"  # <-- tu pestaña

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


# ==== LEER DATOS ====
def leer_datos():
    ws = get_sheet()
    datos = ws.get_all_values()  # Lista de listas
    return datos


# ==== AGREGAR FILA ====
def agregar_fila(nueva_fila):
    ws = get_sheet()
    ws.append_row(nueva_fila, value_input_option="USER_ENTERED")
    return True


# ==== EJEMPLOS DE USO ====
# (Código de ejemplo removido para evitar ejecución automática)

# ===== UI base =====

st.markdown("""
<style>
:root{
  --brand-primary:#38c694; /* Low */
  --brand-warn:#fcb960;    /* Moderate */
  --brand-danger:#fa5f45;  /* High */
}

.main { background-color: #f7f9fc; }

/* Botones */
.stButton>button{
  background:var(--brand-primary)!important;
  color:#fff!important;
  font-weight:700!important;
  border-radius:10px!important;
  padding:.55rem 1rem!important;
  border:0!important;
}
.stButton>button:hover{ filter:brightness(.95); }

/* Inputs */
.stTextInput>div>div>input,
.stNumberInput input, 
.stSelectbox div[data-baseweb="select"]{
  border-radius:10px!important;
}

/* Títulos / separadores */
h1, h2, h3{ color:#0f172a; }
hr{ border:none; border-top:1px solid #e5e7eb; margin:1rem 0; }

/* Badges */
.badge{
  display:inline-block; padding:.35rem .7rem; border-radius:999px;
  font-weight:700; font-size:.95rem;
}
.badge-low{ background:rgba(56,198,148,.12); color:#38c694; }
.badge-mod{ background:rgba(252,185,96,.15); color:#fcb960; }
.badge-high{ background:rgba(250,95,69,.15); color:#fa5f45; }

/* Multiselect chips */
[data-baseweb="tag"]{
  border-radius:999px!important;
  font-weight:600!important;
  padding:0 .6rem!important;
}
[data-baseweb="tag"]:has(span:contains("Low")){
  background:rgba(56,198,148,.12)!important; color:#38c694!important;
}
[data-baseweb="tag"]:has(span:contains("Moderate")){
  background:rgba(252,185,96,.15)!important; color:#fcb960!important;
}
[data-baseweb="tag"]:has(span:contains("High")){
  background:rgba(250,95,69,.15)!important; color:#fa5f45!important;
}
</style>
""",
            unsafe_allow_html=True)

# ===== Config Sheets =====
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# 🔒 Valores fijos (tu hoja)
SHEET_KEY = "12PC1-vv-RIPDDs0O07Xg0ZoAFH7H6npJSnDDpUtPkJQ"  # ID del doc
WORKSHEET_TITLE = "Evaluación Estética - SAFE MD AI 25"  # pestaña
SHEET_NAME_FALLB = os.getenv(
    "SHEET_NAME",
    "AestheticSafe_Respuestas").strip()  # abrir por nombre si falla el KEY


def _load_credentials():
    """Busca credenciales en env, luego st.secrets, luego credentials.json."""
    creds_env = os.getenv("GOOGLE_CREDENTIALS")
    if creds_env:
        try:
            info = json.loads(creds_env)
            return Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            st.error(
                f"❌ GOOGLE_CREDENTIALS inválido en env: {type(e).__name__}: {e}"
            )
            return None

    try:
        if "GOOGLE_CREDENTIALS" in st.secrets:
            info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
            return Credentials.from_service_account_info(info, scopes=SCOPES)
    except Exception as e:
        st.error(
            f"❌ GOOGLE_CREDENTIALS inválido en st.secrets: {type(e).__name__}: {e}"
        )
        return None

    if os.path.exists("credentials.json"):
        try:
            return Credentials.from_service_account_file("credentials.json",
                                                         scopes=SCOPES)
        except Exception as e:
            st.error(
                f"❌ Error leyendo credentials.json: {type(e).__name__}: {e}")
            return None

    return None


def get_sheet():
    creds = _load_credentials()
    if not creds:
        return None

    try:
        gc = gspread.authorize(creds)
    except Exception as e:
        st.error(
            f"❌ Error de autorización con Google Sheets: {type(e).__name__}: {e}"
        )
        return None

    # Abrimos por KEY (preferido)
    try:
        ss = gc.open_by_key(SHEET_KEY)
    except Exception:
        # Fallback por nombre del documento
        try:
            ss = gc.open(SHEET_NAME_FALLB)
        except Exception as e2:
            st.error(
                f"❌ No pude abrir el Spreadsheet por KEY ni por nombre ('{SHEET_NAME_FALLB}'): {type(e2).__name__}: {e2}"
            )
            return None

    # Worksheet (pestaña)
    try:
        ws = ss.worksheet(WORKSHEET_TITLE)
        return ws
    except gspread.WorksheetNotFound:
        # Ayuda: listar pestañas existentes
        try:
            tabs = [w.title for w in ss.worksheets()]
        except Exception:
            tabs = []
        st.error(
            f"❌ No encuentro la pestaña '{WORKSHEET_TITLE}'.\n"
            f"👉 Pestañas disponibles: {tabs if tabs else '(no pude listarlas)'}"
        )
        return None
    except Exception as e:
        st.error(f"❌ Error abriendo la pestaña: {type(e).__name__}: {e}")
        return None


# ===== Conexión =====
#st.write("Conectando con Google Sheets…")
#sheet = get_sheet()
#if sheet:
 #   st.success("✅ Conexión exitosa con Google Sheets")
#else:
 #   st.warning(
  #      "⚠️ Google Sheets no está disponible. La app #funcionará sin guardar datos."
 #   )
  #  st.info(
   #     "💡 Para habilitar Google Sheets, cargá #GOOGLE_CREDENTIALS y compartí el doc con el email de la #cuenta de servicio."
#)


# ============== VISTAS ==============

APP_VERSION = "v1.1"
LOG_TAB = "Calculadora_Evaluaciones"

def vista_paciente_es():
    
    # Log funnel step1
    registrar_evento_bridge(
    session_id=st.session_state.get("session_id", "no-session"),
    stage="step1",
    substage="start",
    user_agent=st.session_state.get("user_agent", ""),
    country=st.session_state.get("country", "")
    )

    st.header("Evaluación Estética - SAFE MD 25")
    st.markdown(
        "Por favor, completá el siguiente formulario de evaluación médica. Los campos se ajustarán según el tipo de procedimiento seleccionado."
    )
    st.markdown("---")

    # --- Sección 1: Motivación y expectativas ---
    medico = st.selectbox("¿Con qué médico estás haciendo tu consulta?",
                          ["drbukret@drbukret.com", "Otro"])
    motivacion = st.text_input("Motivación y objetivos del procedimiento")
    valores_servicio = st.text_input(
        "¿Qué es lo que más valoras en un servicio médico?")
    preocupacion = st.text_input(
        "¿Cuál es tu principal preocupación sobre la cirugía?")
    resultado_deseado = st.text_input(
        "¿Cómo te gustaría sentirte después del procedimiento?")
    experiencia_perfecta = st.text_input(
        "¿Qué crees que haría esta experiencia perfecta para ti?")

    # --- Sección 2: Datos demográficos y personales ---
    edad = st.number_input("Edad", min_value=10, max_value=100)
    peso = st.number_input("Peso en kilos", min_value=30, max_value=250)
    altura = st.number_input("Altura en centímetros",
                             min_value=120,
                             max_value=230)
    genero = st.selectbox("Seleccione su género",
                          ["Femenino", "Masculino", "Otro"])
    anticonceptivo = st.text_input("Anticonceptivos (píldoras o parches)")
    ultima_menstruacion = st.date_input("Fecha de última menstruación",
                                        value=None)
    embarazos = st.number_input("Embarazos", min_value=0)
    cesareas = st.number_input("Cesareas", min_value=0)
    abortos = st.number_input("Abortos espontáneos (no provocados)",
                              min_value=0)

    # --- Sección 3: Antecedentes y hábitos ---
    opciones_medicas = st.multiselect(
        "Selecciona las opciones que correspondan:", [
            "Diabetes", "Hipertensión arterial", "Arritmia cardiaca",
            "Hernia abdominal", "Ulcera gástrica o duodenal",
            "Hepatitis B o C", "HIV"
        ])
    fuma = st.selectbox("¿Fuma?", ["Sí", "No"])
    fuma_cantidad = st.number_input("¿Cuánto fuma por semana?", min_value=0)
    alcohol = st.selectbox("¿Toma bebidas alcohólicas?", ["Sí", "No"])
    alcohol_cantidad = st.text_input("¿Cuánto bebe actualmente?")
    medicamentos = st.text_area("Medicamentos que toma habitualmente")
    sustancias = st.text_input("¿Consume sustancias recreativas?")

    # --- Sección 4: Patologías ---
    pulmonar = st.selectbox("Patología pulmonar crónica", ["Sí", "No"])
    tiroides = st.selectbox("¿Problemas de tiroides?", ["Sí", "No"])
    alergias = st.text_input("Alergias (indique a qué medicación o sustancia)")
    condiciones_extra = st.text_area(
        "Marca si tienes o has tenido alguna de estas condiciones")
    cirugias_previas = st.selectbox("Cirugías previas", ["Sí", "No"])

    # --- Sección 5: Dismorfia corporal ---
    dismorfia_1 = st.radio(
        "¿Le preocupa mucho la apariencia de alguna parte de su cuerpo?",
        ["Sí", "No"])
    dismorfia_2 = st.radio(
        "¿Piensa mucho en eso y desearía poder pensar menos?", ["Sí", "No"])
    dismorfia_3 = st.radio("¿Le ha causado mucha angustia o dolor?",
                           ["Sí", "No"])
    dismorfia_4 = st.radio(
        "¿Su principal preocupación es no ser lo suficientemente delgado?",
        ["Sí", "No"])
    dismorfia_5 = st.radio("¿Interfiere con su vida social?", ["Sí", "No"])
    dismorfia_6 = st.radio("¿Interfiere con su trabajo o estudios?",
                           ["Sí", "No"])
    dismorfia_7 = st.radio("¿Evita cosas por estos defectos?", ["Sí", "No"])
    dismorfia_8 = st.radio("¿Piensa en sus defectos más de 1 hora al día?",
                           ["Sí", "No"])

    # --- Sección 6: Procedimientos ---
    fecha_cirugia = st.date_input(
        "¿En qué fecha aproximada le gustaría operarse?")
    tipo_procedimiento = st.selectbox(
        "¿Qué tipo de procedimiento te interesa?",
        ["Facial", "Mamario", "Corporal"])

    # Inicialización para evitar NameError
    facial = nariz_preocupacion = nariz_dorso = nariz_punta = respiracion = ""
    nariz_previas = 0
    mama_tipo = mama_objetivo = implantes = ""
    lactancia = mama_previas = 0
    corporal_tipo = ""
    zonas = []
    circ_ombligo = circ_pubis = circ_gluteo = 0

    if tipo_procedimiento == "Facial":
        facial = st.text_input("¿Qué procedimiento facial estás considerando?")
        nariz_preocupacion = st.text_input("¿Qué le preocupa de su nariz?")
        nariz_dorso = st.text_input(
            "¿Qué le gustaría cambiar en el dorso nasal?")
        nariz_punta = st.text_input(
            "¿Qué le gustaría cambiar en la punta nasal?")
        respiracion = st.selectbox("¿Tiene dificultad para respirar?",
                                   ["Sí", "No"])
        nariz_previas = st.number_input("¿Cuántas veces se operó la nariz?",
                                        min_value=0)
        st.file_uploader("Facial de frente", type=['jpg', 'png'], key="f1")
        st.file_uploader("Facial perfil izquierdo",
                         type=['jpg', 'png'],
                         key="f2")
        st.file_uploader("Facial perfil derecho",
                         type=['jpg', 'png'],
                         key="f3")

    elif tipo_procedimiento == "Mamario":
        mama_tipo = st.text_input(
            "¿Qué procedimiento mamario estás considerando?")
        mama_objetivo = st.text_input("¿Qué resultado le gustaría lograr?")
        lactancia = st.number_input("Veces que dio de mamar", min_value=0)
        mama_previas = st.number_input("¿Veces que se operó las mamas?",
                                       min_value=0)
        implantes = st.text_input("Tamaño de los implantes actuales")
        st.file_uploader("Mamas frente", type=['jpg', 'png'], key="m1")
        st.file_uploader("Mamas perfil derecho", type=['jpg', 'png'], key="m2")
        st.file_uploader("Mamas perfil izquierdo",
                         type=['jpg', 'png'],
                         key="m3")

    elif tipo_procedimiento == "Corporal":
        corporal_tipo = st.text_input(
            "¿Qué procedimiento corporal estás considerando?")
        zonas = st.multiselect(
            "Zonas a tratar",
            ["Abdomen", "Cintura", "Espalda", "Muslos", "Glúteos"])
        circ_ombligo = st.number_input("Circunferencia del abdomen (ombligo)",
                                       min_value=50)
        circ_pubis = st.number_input("Circunferencia del abdomen (pubis)",
                                     min_value=50)
        circ_gluteo = st.number_input("Circunferencia subglútea", min_value=50)
        st.file_uploader("Cuerpo anterior", type=['jpg', 'png'], key="c1")
        st.file_uploader("Cuerpo perfil derecho",
                         type=['jpg', 'png'],
                         key="c2")
        st.file_uploader("Cuerpo perfil izquierdo",
                         type=['jpg', 'png'],
                         key="c3")
        st.file_uploader("Cuerpo posterior", type=['jpg', 'png'], key="c4")

    # --- Sección 7: Contacto ---
    email = st.text_input("¿Cuál es su dirección de correo electrónico?")
    telefono = st.text_input("Ingrese su número de teléfono")
    claridad_formulario = st.slider(
        "¿Qué tan clara y fácil de seguir te pareció esta evaluación de riesgo?",
        1, 5)
    # --- Envío final ---
    if st.button("Enviar evaluación", key="submit_btn"):
        errores = []
        if not email or email.count('@') != 1:
            errores.append("📧 Ingresá un email válido.")
        if not telefono or len(telefono) < 6:
            errores.append("📞 Ingresá un número de teléfono válido.")
        if not motivacion:
            errores.append("📝 Completá el campo de motivación.")
        if not tipo_procedimiento:
            errores.append("💉 Seleccioná el tipo de procedimiento.")
        if not fecha_cirugia:
            errores.append("📅 Ingresá la fecha estimada de cirugía.")
        if claridad_formulario < 2:
            errores.append("📋 Asegurate de evaluar la claridad del formulario.")
        if tipo_procedimiento == "Facial" and not facial:
            errores.append("👤 Especificá qué procedimiento facial deseas.")
        if tipo_procedimiento == "Mamario" and not mama_tipo:
            errores.append("👙 Especificá qué procedimiento mamario deseas.")
        if tipo_procedimiento == "Corporal" and not corporal_tipo:
            errores.append("🏋️ Especificá qué procedimiento corporal deseas.")

        if errores:
            for err in errores:
                st.error(err)
            st.stop()  # detiene la ejecución del submit

        try:
            # ---- 1) Resumen a pestaña de PRUEBA (_test_envios) ----
            try:
                bmi = round(peso / ((altura / 100) ** 2), 1) if altura else ""
            except Exception:
                bmi = ""

            # Definir LANG si no existe
            LANG = "ES"  # idioma por defecto

            fila_resumen = [
                utc_now_str(),   # timestamp UTC
                "app",           # canal
                email,
                telefono,
                "",              # nombre (si no lo pedís acá)
                "",              # perfil (si no lo pedís acá)
                LANG,            # idioma de UI
                APP_VERSION,     # versión de la app
                edad,
                peso,
                altura,
                bmi,
                fuma,
            ]
            ok_test, svc = append_row_safe(fila_resumen, tab="_test_envios")

            # ---- 2) Fila COMPLETA a pestaña de PRODUCCIÓN ----
            fila = [
                # Sección 1
                medico,
                motivacion,
                valores_servicio,
                preocupacion,
                resultado_deseado,
                experiencia_perfecta,
                # Sección 2
                edad,
                peso,
                altura,
                genero,
                anticonceptivo,
                str(ultima_menstruacion),
                embarazos,
                cesareas,
                abortos,
                # Sección 3
                ", ".join(opciones_medicas),
                fuma,
                fuma_cantidad,
                alcohol,
                alcohol_cantidad,
                medicamentos,
                sustancias,
                # Sección 4
                pulmonar,
                tiroides,
                alergias,
                condiciones_extra,
                cirugias_previas,
                # Sección 5
                dismorfia_1,
                dismorfia_2,
                dismorfia_3,
                dismorfia_4,
                dismorfia_5,
                dismorfia_6,
                dismorfia_7,
                dismorfia_8,
                # Sección 6
                str(fecha_cirugia),
                tipo_procedimiento,
                (facial if tipo_procedimiento == "Facial" else ""),
                (nariz_preocupacion if tipo_procedimiento == "Facial" else ""),
                (nariz_dorso if tipo_procedimiento == "Facial" else ""),
                (nariz_punta if tipo_procedimiento == "Facial" else ""),
                (respiracion if tipo_procedimiento == "Facial" else ""),
                (nariz_previas if tipo_procedimiento == "Facial" else ""),
                (mama_tipo if tipo_procedimiento == "Mamario" else ""),
                (mama_objetivo if tipo_procedimiento == "Mamario" else ""),
                (lactancia if tipo_procedimiento == "Mamario" else ""),
                (mama_previas if tipo_procedimiento == "Mamario" else ""),
                (implantes if tipo_procedimiento == "Mamario" else ""),
                (corporal_tipo if tipo_procedimiento == "Corporal" else ""),
                (", ".join(zonas) if tipo_procedimiento == "Corporal" else ""),
                (circ_ombligo if tipo_procedimiento == "Corporal" else ""),
                (circ_pubis if tipo_procedimiento == "Corporal" else ""),
                (circ_gluteo if tipo_procedimiento == "Corporal" else ""),
                # Sección 7
                email,
                telefono,
                claridad_formulario,
            ]

            # 👉 Si querés operar SOLO en modo prueba, comentá la línea de abajo.
            ok_prod, _ = append_row_safe(fila, tab="Calculadora_Evaluaciones")

            # ---- 3) Mensajes al usuario ----
            if ok_prod:
                st.success("✅ Evaluación enviada correctamente. ¡Gracias!")
            elif ok_test:
                st.success("✅ Evaluación enviada (modo prueba: _test_envios).")
                if svc:
                    # st.info(f"Para guardar en producción, compartí la hoja con: **{svc}**")
                    pass
            else:
                st.warning("⚠️ No se pudo guardar en Google Sheets.")
                if svc:
                    st.info(f"Revisá permisos. Compartí el Spreadsheet con: **{svc}**")

        except Exception as e:
            st.error(f"❌ Error inesperado al guardar: {type(e).__name__}: {e}")
            
    # =========================================================
    # 🧠 ASISTENTE IA – GPT-5.1-mini
    # =========================================================
    st.markdown("---")
    st.subheader("Asistente IA — Consultas Médicas Generales")

    st.markdown(
        "Podés hacer preguntas sobre el procedimiento, riesgos, preparación "
        "y cualquier duda relacionada. Este asistente **no reemplaza** una consulta médica presencial."
    )

    with st.form("form_asistente_ia"):
        pregunta_ia = st.text_area(
            "Escribí tu pregunta:",
            placeholder="Ejemplo: ¿Qué significa tener riesgo moderado en cirugía estética?",
            height=130
        )
        enviar_ia = st.form_submit_button("💬 Preguntar al Asistente IA")

    if enviar_ia:
        if not pregunta_ia.strip():
            st.warning("Por favor escribí una pregunta antes de continuar.")
        else:
            with st.spinner("Consultando a GPT-5.1-mini..."):
                try:
                    respuesta = client.responses.create(
                        model="gpt-5.1-mini",
                        input=(
                            "Actúa como un asistente médico experto en cirugía plástica estética. "
                            "Proporciona respuestas claras, concisas, en español, "
                            "y evita cualquier acto médico directo.\n\n"
                            f"Pregunta del usuario: {pregunta_ia}"
                        )
                    )
                    st.success("Respuesta del asistente:")
                    st.write(respuesta.output_text)

                except Exception as e:
                    st.error(
                        "Ocurrió un error al consultar el modelo de OpenAI. "
                        "Por favor intentá de nuevo más tarde."
                    )

# ============ ROUTER (sin sidebar, con diagnóstico) ============
# Ocultar sidebar y botón de colapso
st.markdown("""
<style>
section[data-testid="stSidebar"] {display: none !important;}
div[data-testid="collapsedControl"] {display: none !important;}
</style>
""", unsafe_allow_html=True)

def _render_main():
    """Render normal de Streamlit (cuando ejecuta `streamlit run app.py`)."""
    try:
        vista_calculadora_pi()   # <-- tu calculadora real
    except Exception as e:
        import traceback
        st.error(f"❌ calculadora() lanzó: {type(e).__name__}: {e}")
        st.code("".join(traceback.format_exception(e)), language="text")

# ===== CONFIGURACIÓN PARA REPLIT PREVIEW =====
def start_streamlit_server():
    """Inicia servidor Streamlit con configuración automática de puerto para Replit"""
    import os
    
    # 🎯 Puerto: usar PORT de Replit o fallback a 5000
    port = int(os.environ.get("PORT", 5000))
    
    # 🐞 Debug info
    print("=" * 60)
    print("🚀 INICIANDO AestheticSafe")
    print(f"📍 Puerto detectado: {port}")
    print(f"🌐 Dominio Replit: {os.environ.get('REPLIT_DEV_DOMAIN', 'localhost')}")
    print(f"🔧 Variables de entorno PORT: {os.environ.get('PORT', 'NO DEFINIDA')}")
    print("=" * 60)
    
    # 🖥️ Comando Streamlit optimizado para Replit
    cmd = [
        "streamlit", "run", "app.py",
        "--server.port", str(port),
        "--server.address", "0.0.0.0", 
        "--server.headless", "true",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false"
    ]
    
    print(f"📦 Ejecutando: {' '.join(cmd)}")
    print("✅ Preview habilitado en Replit")
    print("=" * 60)
    
    # 🚀 Ejecutar Streamlit
    os.system(' '.join(cmd))

# ===== ENTRYPOINT PARA REPLIT PREVIEW =====
if __name__ == "__main__":
    # 🎯 Configuración automática de puerto para Replit
    import os
    port = int(os.environ.get("PORT", 5000))
    
    print("=" * 60)
    print(f"🚀 Iniciando AestheticSafe en puerto {port}")
    print(f"🌐 Dominio: {os.environ.get('REPLIT_DEV_DOMAIN', 'localhost')}")
    print(f"🔧 Puerto detectado: {port} ({'PORT env' if os.environ.get('PORT') else 'default 5000'})")
    print("=" * 60)
    
    # 🚀 Ejecutar Streamlit con configuración para Replit
    cmd = f"streamlit run calculadora.py --server.port {port} --server.address 0.0.0.0 --server.headless true"
    print(f"📦 Ejecutando: {cmd}")
    print("✅ Preview habilitado en Replit")
    print("=" * 60)
    
    os.system(cmd)
else:
    # Si se importa desde otro módulo, renderizar normal
    _render_main()
