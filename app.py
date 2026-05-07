import streamlit as st

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

# --- Login ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col_empty1, col_login, col_empty2 = st.columns([1, 1, 1])
    with col_login:
        st.image("logo_vda.png", width=200)
        st.markdown("### Sistema de Gestion Enologica")
        st.markdown("---")
        password = st.text_input("Clave de acceso:", type="password")
        if st.button("Ingresar", type="primary", use_container_width=True):
            if password == "vda2024":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Clave incorrecta")
    st.stop()

# --- Sidebar con logo ---
with st.sidebar:
    st.image("logo_vda.png", width=160)
    st.markdown("---")

# --- Navegacion ---
pg = st.navigation(
    {
        "Operaciones": [
            st.Page("pages/01_ordenes_trabajo.py", title="Ordenes de Trabajo", icon="📋"),
            st.Page("pages/06_ejecutar_ot.py", title="Ejecutar OT (Operario)", icon="🔧"),
            st.Page("pages/02_recepcion_insumos.py", title="Recepcion de Insumos", icon="📦"),
        ],
        "Inventario": [
            st.Page("pages/03_stock_insumos.py", title="Stock de Insumos", icon="📊"),
            st.Page("pages/04_stock_cubas.py", title="Stock de Cubas", icon="🏗️"),
        ],
        "Administracion": [
            st.Page("pages/05_configuracion.py", title="Configuracion", icon="⚙️"),
        ],
    }
)

pg.run()
