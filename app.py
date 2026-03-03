import streamlit as st
import pandas as pd
import io
import json
import hashlib
from datetime import datetime

st.set_page_config(
    page_title="Buscador de Históricos",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .main > div { padding: 1rem; }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        padding: 0.6rem;
        font-size: 1rem;
        font-weight: 600;
    }
    .metric-card {
        background: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .user-badge {
        background: #f0f4ff;
        border-radius: 8px;
        padding: 0.3rem 0.8rem;
        font-size: 0.85rem;
        color: #4f6ef7;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

ORDEN_PERIODOS = {
    "ENERO": 1, "ENERO_FEBRERO": 2, "FEBRERO": 2, "MARZO": 3,
    "MARZO_ABRIL": 4, "ABRIL": 4, "MAYO": 5, "MAYO_JUNIO": 6,
    "JUNIO": 6, "JULIO": 7, "JULIO_AGOSTO": 8, "AGOSTO": 8,
    "SETIEMBRE": 9, "SETIEMBRE_OCTUBRE": 10, "OCTUBRE": 10,
    "NOVIEMBRE": 11, "NOVIEMBRE_DICIEMBRE": 12, "DICIEMBRE": 12
}
COLUMNAS_CLAVE = ["RUB", "CI TIT", "CI SEC"]

# ── AUTH ──────────────────────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_credenciales(usuario, password):
    try:
        usuarios_validos = [u.strip() for u in st.secrets["AUTH_USERS"].split(",")]
        return usuario.strip() in usuarios_validos and hash_password(password) == st.secrets["AUTH_PASSWORD_HASH"]
    except Exception:
        return False

def mostrar_login():
    st.markdown("""
        <div style='text-align:center; margin-top:3rem;'>
            <h1>🔍</h1>
            <h2>Buscador de Históricos</h2>
            <p style='color:#888;'>Pagos e Impagos 2025</p>
        </div>
    """, unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("#### 🔐 Iniciar sesión")
        usuario = st.text_input("Usuario", placeholder="tu_usuario", key="login_user")
        password = st.text_input("Contraseña", type="password", placeholder="••••••••", key="login_pass")
        if st.button("Ingresar", type="primary"):
            if verificar_credenciales(usuario, password):
                st.session_state["autenticado"] = True
                st.session_state["usuario_actual"] = usuario.strip()
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos.")

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_actual"] = ""

if not st.session_state["autenticado"]:
    mostrar_login()
    st.stop()

# ── HELPERS ───────────────────────────────────────────────────
def transformar_periodo(valor):
    if pd.isna(valor):
        return ""
    valor = str(valor).strip().replace("__", "_").replace(" _", "_").replace("_ ", "_")
    valor = " ".join(valor.split())
    partes = valor.split("_")
    if partes[-1].isdigit():
        año = partes[-1]
        periodo = "_".join(partes[:-1])
    elif partes[0].isdigit():
        año = partes[0]
        periodo = "_".join(partes[1:])
    else:
        return valor
    return f"{año}_{periodo.upper()}"

def clave_orden(periodo):
    if isinstance(periodo, str):
        partes = periodo.strip().split("_")
        if len(partes) >= 2 and partes[0].isdigit():
            año = int(partes[0])
            periodo_texto = "_".join(partes[1:]).upper()
            orden = ORDEN_PERIODOS.get(periodo_texto, 99)
            return año * 100 + orden
    return float("inf")

def cargar_desde_drive():
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload

        creds_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
        file_id = st.secrets["DRIVE_FILE_ID"]
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        service = build("drive", "v3", credentials=creds)
        request = service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        buffer.seek(0)
        return pd.read_parquet(buffer)
    except Exception as e:
        st.error(f"❌ Error al cargar desde Drive: {e}")
        return None

@st.cache_data(show_spinner="⚡ Cargando datos...")
def cargar_datos():
    df = cargar_desde_drive()
    if df is None:
        return None
    for col in COLUMNAS_CLAVE:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    if "Periodo de Pago" in df.columns:
        if not df["Periodo de Pago"].astype(str).str.match(r"^\d{4}_").any():
            df["Periodo de Pago"] = df["Periodo de Pago"].apply(transformar_periodo)
    return df

def crear_excel(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dataframe.to_excel(writer, index=False, sheet_name='Resultados')
        workbook = writer.book
        worksheet = writer.sheets['Resultados']
        header_format = workbook.add_format({'bold': True, 'bg_color': '#4f6ef7', 'font_color': 'white', 'border': 1})
        for col_num, value in enumerate(dataframe.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, max(len(str(value)) + 4, 12))
    output.seek(0)
    return output

# ── INTERFAZ ──────────────────────────────────────────────────
col_titulo, col_usuario = st.columns([3, 1])
with col_titulo:
    st.title("🔍 Buscador de Históricos")
    st.caption("Pagos e Impagos 2025")
with col_usuario:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"<div class='user-badge'>👤 {st.session_state['usuario_actual']}</div>", unsafe_allow_html=True)
    if st.button("🚪 Salir", key="logout"):
        st.session_state["autenticado"] = False
        st.session_state["usuario_actual"] = ""
        st.rerun()

df = cargar_datos()

if df is None:
    st.warning("⚠️ No se pudieron cargar los datos.")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""<div class="metric-card"><h3>📋 {len(df):,}</h3><p>Registros totales</p></div>""", unsafe_allow_html=True)
with col2:
    periodos = df["Periodo de Pago"].nunique() if "Periodo de Pago" in df.columns else 0
    st.markdown(f"""<div class="metric-card"><h3>📅 {periodos}</h3><p>Períodos distintos</p></div>""", unsafe_allow_html=True)

st.divider()
st.subheader("🔎 Buscar registro")

campo = st.selectbox(
    "Buscar por:",
    options=["RUB", "CI TIT", "CI SEC"],
    format_func=lambda x: {"RUB": "🏠 RUB — Código de rubro", "CI TIT": "👤 CI TIT — Cédula del titular", "CI SEC": "👥 CI SEC — Cédula del secundario"}[x]
)
valor_input = st.text_input(f"Ingresá el valor de {campo}:", placeholder="Ej: 123456", max_chars=20)
buscar = st.button("🔍 Buscar", type="primary")

if buscar:
    if not valor_input.strip():
        st.warning("⚠️ Por favor ingresá un valor.")
    else:
        try:
            valor = str(int(valor_input.strip()))
        except ValueError:
            st.error("❌ Ingresá solo números.")
            st.stop()

        with st.spinner("Buscando..."):
            resultados = df[df[campo] == valor].copy() if campo in df.columns else pd.DataFrame()

        if len(resultados) > 0:
            resultados["__ORDEN__"] = resultados["Periodo de Pago"].apply(clave_orden)
            resultados = resultados.sort_values("__ORDEN__").drop(columns="__ORDEN__")
            st.success(f"✅ {len(resultados)} registro(s) encontrado(s) para **{campo} = {valor}**")
            st.dataframe(resultados, use_container_width=True, hide_index=True)

            excel_data = crear_excel(resultados)
            nombre_archivo = f"Resultados_{campo}_{valor}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            st.download_button(
                label="📥 Descargar Excel",
                data=excel_data,
                file_name=nombre_archivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="secondary"
            )
        else:
            st.warning(f"⚠️ No se encontraron registros para **{campo} = {valor}**.")
