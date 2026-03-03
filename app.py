import streamlit as st

st.set_page_config(page_title="Diagnóstico", page_icon="🔧")
st.title("🔧 Diagnóstico de arranque")

# TEST 1 - Secrets
st.subheader("1. Verificando Secrets...")
try:
    usuarios = st.secrets["AUTH_USERS"]
    st.success(f"✅ AUTH_USERS: {usuarios}")
except Exception as e:
    st.error(f"❌ AUTH_USERS falta o tiene error: {e}")

try:
    ph = st.secrets["AUTH_PASSWORD_HASH"]
    st.success(f"✅ AUTH_PASSWORD_HASH: {ph[:10]}...")
except Exception as e:
    st.error(f"❌ AUTH_PASSWORD_HASH falta o tiene error: {e}")

try:
    fid = st.secrets["DRIVE_FILE_ID"]
    st.success(f"✅ DRIVE_FILE_ID: {fid}")
except Exception as e:
    st.error(f"❌ DRIVE_FILE_ID falta o tiene error: {e}")

try:
    import json
    gsaj = st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]
    parsed = json.loads(gsaj)
    st.success(f"✅ GOOGLE_SERVICE_ACCOUNT_JSON OK — project: {parsed.get('project_id')}, email: {parsed.get('client_email')}")
except Exception as e:
    st.error(f"❌ GOOGLE_SERVICE_ACCOUNT_JSON error: {e}")

# TEST 2 - Google Drive
st.subheader("2. Verificando conexión a Google Drive...")
try:
    import json
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    service = build("drive", "v3", credentials=creds)
    file_id = st.secrets["DRIVE_FILE_ID"]
    meta = service.files().get(fileId=file_id, fields="name,size").execute()
    st.success(f"✅ Archivo encontrado en Drive: {meta.get('name')} ({int(meta.get('size',0))//1024//1024} MB)")
except Exception as e:
    st.error(f"❌ Error al conectar con Drive: {e}")

# TEST 3 - Imports
st.subheader("3. Verificando librerías...")
for lib in ["pandas", "pyarrow", "xlsxwriter", "google.oauth2", "googleapiclient"]:
    try:
        __import__(lib.replace(".", ".").split(".")[0])
        st.success(f"✅ {lib}")
    except Exception as e:
        st.error(f"❌ {lib}: {e}")

st.info("Compartí esta pantalla para diagnosticar el problema.")
