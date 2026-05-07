import streamlit as st

st.set_page_config(
    page_title="Sistema Enologico VDA",
    page_icon="🍷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Password simple para proteger acceso
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Sistema Enologico VDA")
    st.markdown("---")
    password = st.text_input("Contraseña de acceso:", type="password")
    if st.button("Ingresar"):
        if password == "vda2024":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")
    st.stop()

# Navegacion principal
pg = st.navigation(
    {
        "Operaciones": [
            st.Page("pages/01_ordenes_trabajo.py", title="Ordenes de Trabajo", icon="📋"),
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
