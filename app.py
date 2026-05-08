import streamlit as st
import extra_streamlit_components as stx
import json, base64
from datetime import datetime, timedelta
from lib.auth import login, get_current_user, has_permission, logout

st.set_page_config(
    page_title="Sistema Enologico VDA",
    page_icon="logo_vda.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Estilos profesionales tipo ERP ---
st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
        color: #b0b0b0 !important;
    }

    /* Header */
    .main-header {
        display: flex;
        align-items: center;
        gap: 15px;
        padding: 10px 0;
        border-bottom: 2px solid #722F37;
        margin-bottom: 20px;
    }
    .main-header img {
        height: 50px;
    }
    .main-header h2 {
        color: #722F37;
        margin: 0;
        font-weight: 600;
    }

    /* Cards */
    .metric-card {
        background: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        border-left: 4px solid #722F37;
    }
    .metric-card h3 {
        color: #666;
        font-size: 0.85em;
        margin: 0 0 5px 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-card .value {
        color: #1a1a2e;
        font-size: 1.8em;
        font-weight: 700;
        margin: 0;
    }

    /* Buttons */
    .stButton > button[kind="primary"] {
        background-color: #722F37;
        border-color: #722F37;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #5a252c;
        border-color: #5a252c;
    }

    /* Tables */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        border-bottom-color: #722F37 !important;
        color: #722F37 !important;
    }

    /* Form inputs */
    .stSelectbox > div > div, .stTextInput > div > div, .stNumberInput > div > div {
        border-radius: 6px;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- Cookie manager ---
cookie_manager = stx.CookieManager(key="vda_cm")

# --- Login ---
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    if not st.session_state.get("_logged_out"):
        saved = cookie_manager.get("vda_auth")
        if saved:
            try:
                creds = json.loads(base64.b64decode(saved))
                user_data = login(creds["u"], creds["p"])
                if user_data:
                    st.session_state.user = user_data
                    st.rerun()
                else:
                    cookie_manager.delete("vda_auth")
            except Exception:
                cookie_manager.delete("vda_auth")
    else:
        st.session_state._logged_out = False

    col_empty1, col_login, col_empty2 = st.columns([1, 1, 1])
    with col_login:
        st.image("logo_vda.png", width=200)
        st.markdown("### Sistema de Gestion Enologica")
        st.markdown("---")
        username = st.text_input("Usuario:", placeholder="Ingrese su usuario")
        password = st.text_input("Clave:", type="password")
        remember = st.checkbox("Recordarme")
        if st.button("Ingresar", type="primary", use_container_width=True):
            if username and password:
                user = login(username, password)
                if user:
                    st.session_state.user = user
                    if remember:
                        token = base64.b64encode(
                            json.dumps({"u": username, "p": password}).encode()
                        ).decode()
                        cookie_manager.set("vda_auth", token,
                                           expires_at=datetime.now() + timedelta(days=30))
                    st.rerun()
                else:
                    st.error("Usuario o clave incorrectos")
            else:
                st.warning("Ingrese usuario y clave")
    st.stop()

# --- Sidebar con logo e info de usuario ---
user = get_current_user()
with st.sidebar:
    st.image("logo_vda.png", width=160)
    st.markdown(f"**{user['full_name']}**")
    st.caption(f"Rol: {user['role_name']}")
    if st.button("Cerrar Sesion", use_container_width=True):
        cookie_manager.delete("vda_auth")
        st.session_state._logged_out = True
        logout()
        st.rerun()
    st.markdown("---")

# --- Navegacion segun permisos ---
pages = {}

# Dashboard (pagina de inicio)
if has_permission("dashboard", "ver"):
    pages["Inicio"] = [
        st.Page("pages/00_dashboard.py", title="Centro de Control", icon="🏠", default=True),
    ]

# Operaciones
op_pages = []
if has_permission("ordenes_trabajo", "ver"):
    op_pages.append(st.Page("pages/01_ordenes_trabajo.py", title="Ordenes de Trabajo", icon="📋"))
if has_permission("ejecutar_ot", "ver"):
    op_pages.append(st.Page("pages/06_ejecutar_ot.py", title="Ejecutar OT (Operario)", icon="🔧"))
if has_permission("recepcion_insumos", "ver"):
    op_pages.append(st.Page("pages/11_ordenes_compra.py", title="Ordenes de Compra", icon="🛒"))
    op_pages.append(st.Page("pages/02_recepcion_insumos.py", title="Recepcion de Insumos", icon="📦"))
if op_pages:
    pages["Operaciones"] = op_pages

# Inventario
inv_pages = []
if has_permission("stock_insumos", "ver"):
    inv_pages.append(st.Page("pages/03_stock_insumos.py", title="Stock de Insumos", icon="📊"))
if has_permission("stock_cubas", "ver"):
    inv_pages.append(st.Page("pages/04_stock_cubas.py", title="Stock de Cubas", icon="🏗️"))
if inv_pages:
    pages["Inventario"] = inv_pages

# Laboratorio
if has_permission("laboratorio", "ver"):
    pages["Laboratorio"] = [
        st.Page("pages/08_laboratorio.py", title="Analisis de Laboratorio", icon="🔬"),
    ]

# Administracion
admin_pages = []
if has_permission("configuracion", "ver"):
    admin_pages.append(st.Page("pages/05_configuracion.py", title="Configuracion", icon="⚙️"))
if has_permission("admin", "ver"):
    admin_pages.append(st.Page("pages/09_admin.py", title="Usuarios y Roles", icon="🔐"))
if admin_pages:
    pages["Administracion"] = admin_pages

pg = st.navigation(pages)
pg.run()
