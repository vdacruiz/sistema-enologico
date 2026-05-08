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

# --- Design System VDA ---
st.markdown("""
<style>
    :root {
        --vda-burdeo: #722F37;
        --vda-burdeo-dark: #5a252c;
        --vda-burdeo-light: #8c3a44;
        --vda-navy: #1a1a2e;
        --vda-navy-mid: #16213e;
        --vda-navy-light: #0f3460;
        --vda-gold: #c9a84c;
        --vda-gold-light: #e8d5a0;
        --vda-bg: #f5f6fa;
        --vda-card: #ffffff;
        --vda-text: #1e1e2f;
        --vda-text-secondary: #6b7280;
        --vda-border: #e5e7eb;
        --vda-success: #059669;
        --vda-warning: #d97706;
        --vda-danger: #dc2626;
        --vda-info: #2563eb;
        --vda-radius: 10px;
        --vda-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
        --vda-shadow-md: 0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06);
        --vda-shadow-lg: 0 10px 25px rgba(0,0,0,0.1), 0 4px 10px rgba(0,0,0,0.06);
    }

    /* ===== Global ===== */
    .main .block-container {
        padding-top: 1.5rem;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background: rgba(255,255,255,0.95);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--vda-border);
    }

    /* ===== Sidebar ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 40%, #0f3460 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    [data-testid="stSidebar"] * {
        color: #d1d5db !important;
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {
        color: #9ca3af !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.08) !important;
    }
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.1);
        color: #d1d5db !important;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(220,38,38,0.15);
        border-color: rgba(220,38,38,0.3);
        color: #fca5a5 !important;
    }

    /* ===== Typography ===== */
    h1 {
        color: var(--vda-navy) !important;
        font-weight: 700 !important;
        font-size: 1.75rem !important;
        letter-spacing: -0.02em;
    }
    h2 {
        color: var(--vda-navy) !important;
        font-weight: 600 !important;
        font-size: 1.35rem !important;
    }
    h3 {
        color: var(--vda-text) !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
    }

    /* ===== Buttons ===== */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--vda-burdeo) 0%, var(--vda-burdeo-dark) 100%);
        border: none;
        border-radius: 8px;
        font-weight: 600;
        letter-spacing: 0.02em;
        transition: all 0.2s ease;
        box-shadow: 0 2px 4px rgba(114,47,55,0.3);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, var(--vda-burdeo-light) 0%, var(--vda-burdeo) 100%);
        box-shadow: 0 4px 8px rgba(114,47,55,0.4);
        transform: translateY(-1px);
    }
    .stButton > button[kind="secondary"] {
        border-radius: 8px;
        font-weight: 500;
        border: 1px solid var(--vda-border);
        transition: all 0.2s ease;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: var(--vda-burdeo);
        color: var(--vda-burdeo);
    }

    /* ===== Form Inputs ===== */
    .stSelectbox > div > div, .stTextInput > div > div,
    .stNumberInput > div > div, .stDateInput > div > div,
    .stTextArea > div > div {
        border-radius: 8px;
        border-color: var(--vda-border);
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .stSelectbox > div > div:focus-within, .stTextInput > div > div:focus-within,
    .stNumberInput > div > div:focus-within, .stTextArea > div > div:focus-within {
        border-color: var(--vda-burdeo) !important;
        box-shadow: 0 0 0 3px rgba(114,47,55,0.1) !important;
    }

    /* ===== Tabs ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: var(--vda-bg);
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        border-radius: 8px;
        padding: 8px 16px;
        border-bottom: none !important;
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: var(--vda-burdeo) !important;
        box-shadow: var(--vda-shadow);
        border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none;
    }

    /* ===== DataFrames ===== */
    .stDataFrame {
        border-radius: var(--vda-radius);
        overflow: hidden;
        box-shadow: var(--vda-shadow);
    }

    /* ===== Expanders ===== */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: var(--vda-text);
        border-radius: var(--vda-radius);
    }

    /* ===== Metrics ===== */
    [data-testid="stMetric"] {
        background: var(--vda-card);
        border-radius: var(--vda-radius);
        padding: 16px;
        box-shadow: var(--vda-shadow);
        border: 1px solid var(--vda-border);
    }
    [data-testid="stMetricLabel"] {
        color: var(--vda-text-secondary) !important;
        text-transform: uppercase;
        font-size: 0.75rem !important;
        letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] {
        color: var(--vda-navy) !important;
        font-weight: 700 !important;
    }

    /* ===== Reusable Components ===== */
    .vda-card {
        background: var(--vda-card);
        border-radius: var(--vda-radius);
        padding: 20px;
        box-shadow: var(--vda-shadow);
        border: 1px solid var(--vda-border);
        transition: box-shadow 0.2s ease;
    }
    .vda-card:hover {
        box-shadow: var(--vda-shadow-md);
    }
    .vda-card-accent {
        background: var(--vda-card);
        border-radius: var(--vda-radius);
        padding: 20px;
        box-shadow: var(--vda-shadow);
        border-left: 4px solid var(--vda-burdeo);
    }
    .vda-section-title {
        color: var(--vda-navy);
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--vda-bg);
    }
    .vda-kpi {
        text-align: center;
        padding: 20px 16px;
    }
    .vda-kpi-label {
        color: var(--vda-text-secondary);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 500;
        margin-bottom: 4px;
    }
    .vda-kpi-value {
        color: var(--vda-navy);
        font-size: 1.85rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .vda-kpi-sub {
        color: var(--vda-text-secondary);
        font-size: 0.75rem;
        margin-top: 2px;
    }
    .vda-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .vda-badge-success { background: #d1fae5; color: #065f46; }
    .vda-badge-warning { background: #fef3c7; color: #92400e; }
    .vda-badge-danger { background: #fee2e2; color: #991b1b; }
    .vda-badge-info { background: #dbeafe; color: #1e40af; }
    .vda-badge-neutral { background: #f3f4f6; color: #4b5563; }
    .vda-divider {
        height: 1px;
        background: var(--vda-border);
        margin: 24px 0;
        border: none;
    }

    /* ===== Alerts refinement ===== */
    .stAlert > div {
        border-radius: 8px;
    }
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

    st.markdown("""
    <style>
        /* Login page overrides */
        .main .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        [data-testid="stSidebar"] { display: none; }
        header[data-testid="stHeader"] { display: none; }
        .login-bg {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(135deg, #1a1a2e 0%, #2d1b30 25%, #4a2035 50%, #722F37 75%, #5a252c 100%);
            z-index: -1;
        }
        .login-bg::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: radial-gradient(ellipse at 30% 20%, rgba(201,168,76,0.08) 0%, transparent 50%),
                        radial-gradient(ellipse at 70% 80%, rgba(114,47,55,0.15) 0%, transparent 50%);
        }
        .login-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .login-card {
            background: rgba(255,255,255,0.97);
            border-radius: 16px;
            padding: 48px 40px 36px;
            width: 100%;
            max-width: 400px;
            box-shadow: 0 25px 60px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.1);
        }
        .login-logo {
            text-align: center;
            margin-bottom: 8px;
        }
        .login-logo img {
            height: 80px;
            opacity: 0.95;
        }
        .login-subtitle {
            text-align: center;
            color: #6b7280;
            font-size: 0.85rem;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            margin-bottom: 32px;
            font-weight: 500;
        }
        .login-footer {
            text-align: center;
            margin-top: 28px;
            padding-top: 20px;
            border-top: 1px solid #f0f0f0;
        }
        .login-footer span {
            color: #9ca3af;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }
    </style>
    <div class="login-bg"></div>
    """, unsafe_allow_html=True)

    col_empty1, col_login, col_empty2 = st.columns([1.2, 1, 1.2])
    with col_login:
        st.markdown('<div class="login-logo">', unsafe_allow_html=True)
        st.image("logo_vda.png", width=200)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Sistema de Gestion Enologica</div>', unsafe_allow_html=True)

        username = st.text_input("Usuario", placeholder="Ingrese su usuario", label_visibility="collapsed")
        password = st.text_input("Clave", type="password", placeholder="Ingrese su clave", label_visibility="collapsed")
        remember = st.checkbox("Recordarme", value=True)
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

        st.markdown("""
        <div class="login-footer">
            <span>VIÑA DE AGUIRRE &middot; SISTEMA ENOLOGICO</span>
        </div>
        """, unsafe_allow_html=True)
    st.stop()

# --- Sidebar con logo e info de usuario ---
user = get_current_user()
with st.sidebar:
    st.image("logo_vda.png", width=140)
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.06);border-radius:10px;padding:14px 16px;margin:8px 0 4px;">
        <div style="font-size:0.95rem;font-weight:600;color:#e5e7eb !important;margin-bottom:2px;">
            {user['full_name']}
        </div>
        <div style="font-size:0.75rem;color:#9ca3af !important;letter-spacing:0.04em;">
            {user['role_name']}
        </div>
    </div>
    """, unsafe_allow_html=True)
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
lab_pages = []
if has_permission("laboratorio", "ver"):
    lab_pages.append(st.Page("pages/08_laboratorio.py", title="Analisis de Laboratorio", icon="🔬"))
if has_permission("stock_cubas", "ver"):
    lab_pages.append(st.Page("pages/12_embotellado.py", title="Embotellado y Lotes", icon="🍾"))
if lab_pages:
    pages["Laboratorio"] = lab_pages

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
