import streamlit as st
import pandas as pd
from lib import queries

st.title("Stock de Cubas")
st.markdown("Estado actual de cada cuba/tanque")

try:
    tanks = queries.get_tanks()
    contents = queries.get_tank_contents()
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")
    st.stop()

# Crear mapa de contenidos por tank_id
content_map = {}
for c in contents:
    content_map[c["tank_id"]] = c

# Filtros
col_f1, col_f2 = st.columns(2)
with col_f1:
    filter_status = st.selectbox("Filtrar por estado:", ["Todos", "Ocupado", "Vacio", "En proceso", "Limpieza"])
with col_f2:
    search = st.text_input("Buscar cuba:", placeholder="Numero o nombre...")

# Metricas
occupied = sum(1 for c in contents if c.get("status") == "Ocupado")
total_tanks = len(tanks)
st.markdown("---")
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Total Cubas", total_tanks)
col_m2.metric("Ocupadas", occupied)
col_m3.metric("Disponibles", total_tanks - occupied)

# Grid de cubas
st.markdown("---")
if tanks:
    rows_data = []
    for t in tanks:
        content = content_map.get(t["id"], {})
        status = content.get("status", "Vacio") if content else "Vacio"
        liters = content.get("current_liters", 0) if content else 0
        capacity = t.get("capacity_liters", 0) or 0
        pct = (liters / capacity * 100) if capacity > 0 else 0

        wine_info = "-"
        if content and content.get("wines"):
            wine_info = content["wines"].get("code", "-")
        grape_info = "-"
        if content and content.get("grape_varieties"):
            grape_info = content["grape_varieties"].get("code", "-")

        row = {
            "Cuba": t["code"],
            "Nombre": t.get("name") or "-",
            "Capacidad (L)": capacity,
            "Litros": liters,
            "% Uso": round(pct, 1),
            "Estado": status,
            "Vino": wine_info,
            "Cepa": grape_info,
            "Ubicacion": t.get("location") or "-",
        }
        rows_data.append(row)

    df = pd.DataFrame(rows_data)

    if filter_status != "Todos":
        df = df[df["Estado"] == filter_status]
    if search:
        mask = (df["Cuba"].astype(str).str.contains(search, case=False, na=False) |
                df["Nombre"].str.contains(search, case=False, na=False))
        df = df[mask]

    def color_status(val):
        colors = {
            "Ocupado": "background-color: #d4edda",
            "Vacio": "background-color: #f8f9fa",
            "En proceso": "background-color: #fff3cd",
            "Limpieza": "background-color: #cce5ff",
        }
        return colors.get(val, "")

    st.dataframe(
        df.style.map(color_status, subset=["Estado"]),
        use_container_width=True,
        hide_index=True,
        height=600,
    )
    st.caption(f"Mostrando {len(df)} de {total_tanks} cubas")
else:
    st.info("No hay cubas registradas. Agreguelas en Configuracion.")
