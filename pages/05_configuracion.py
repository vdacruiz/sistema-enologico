import streamlit as st
from lib.database import get_supabase_client

st.title("Configuracion")
st.markdown("Administracion de datos maestros del sistema")

client = get_supabase_client()

tab_sup, tab_prov, tab_work, tab_tank, tab_proc, tab_grape, tab_line = st.tabs([
    "Insumos", "Proveedores", "Operarios", "Cubas", "Procesos", "Cepas", "Lineas"
])


def crud_table(tab, table_name, columns, display_name):
    with tab:
        st.subheader(f"Gestionar {display_name}")

        try:
            data = client.table(table_name).select("*").order(columns[0]["field"]).execute().data
        except Exception as e:
            st.error(f"Error cargando {display_name}: {e}")
            st.info("Verifique que la tabla exista en Supabase.")
            return

        if data:
            st.dataframe(
                [{col["label"]: row.get(col["field"], "") for col in columns} for row in data],
                use_container_width=True,
                hide_index=True,
                height=300,
            )
            st.caption(f"Total: {len(data)} registros")

        st.markdown("---")
        st.markdown(f"**Agregar nuevo {display_name.lower()[:-1] if display_name.endswith('s') else display_name.lower()}:**")

        new_data = {}
        cols = st.columns(len(columns))
        for i, col_def in enumerate(columns):
            if col_def.get("editable", True):
                with cols[i]:
                    if col_def.get("type") == "number":
                        new_data[col_def["field"]] = st.number_input(
                            col_def["label"], value=0, key=f"new_{table_name}_{col_def['field']}"
                        )
                    else:
                        new_data[col_def["field"]] = st.text_input(
                            col_def["label"], key=f"new_{table_name}_{col_def['field']}"
                        )

        if st.button(f"Agregar", key=f"add_{table_name}"):
            clean_data = {k: v for k, v in new_data.items() if v}
            if clean_data:
                try:
                    client.table(table_name).insert(clean_data).execute()
                    st.success(f"Registro agregado exitosamente")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Complete al menos un campo")


# Insumos
crud_table(tab_sup, "supplies", [
    {"field": "name", "label": "Nombre"},
    {"field": "code", "label": "Codigo"},
    {"field": "unit", "label": "Unidad (Kg/Lts/Unidad)"},
    {"field": "min_stock", "label": "Stock Minimo", "type": "number"},
], "Insumos")

# Proveedores
crud_table(tab_prov, "suppliers", [
    {"field": "name", "label": "Nombre"},
    {"field": "rut", "label": "RUT"},
    {"field": "phone", "label": "Telefono"},
    {"field": "email", "label": "Email"},
], "Proveedores")

# Operarios
crud_table(tab_work, "workers", [
    {"field": "full_name", "label": "Nombre Completo"},
    {"field": "role", "label": "Cargo"},
], "Operarios")

# Cubas
crud_table(tab_tank, "tanks", [
    {"field": "code", "label": "Numero/Codigo"},
    {"field": "name", "label": "Nombre"},
    {"field": "capacity_liters", "label": "Capacidad (L)", "type": "number"},
    {"field": "location", "label": "Ubicacion"},
], "Cubas")

# Procesos
crud_table(tab_proc, "winemaking_processes", [
    {"field": "name", "label": "Nombre del Proceso"},
    {"field": "description", "label": "Descripcion"},
], "Procesos Enologicos")

# Cepas
crud_table(tab_grape, "grape_varieties", [
    {"field": "code", "label": "Codigo (CS, MR, etc.)"},
    {"field": "name", "label": "Nombre Completo"},
    {"field": "wine_type", "label": "Tipo (Tinto/Blanco/Rosado)"},
], "Cepas")

# Lineas de Producto
crud_table(tab_line, "product_lines", [
    {"field": "name", "label": "Nombre de Linea"},
    {"field": "sort_order", "label": "Orden", "type": "number"},
], "Lineas de Producto")


# --- Test de conexion ---
st.markdown("---")
st.subheader("Estado del Sistema")
from lib.database import test_connection
if st.button("Probar conexion a base de datos"):
    if test_connection():
        st.success("Conexion exitosa a Supabase")
    else:
        st.error("No se pudo conectar. Verifique las credenciales en .streamlit/secrets.toml")
