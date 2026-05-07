import streamlit as st
from lib.database import get_supabase_client

st.title("Configuracion")
st.markdown("Administracion de datos maestros del sistema")

client = get_supabase_client()

# Tablas que referencian cada dato maestro (para validar eliminacion)
DEPENDENCY_MAP = {
    "supplies": [
        ("work_order_lines", "supply_id", "ordenes de trabajo"),
        ("purchase_order_lines", "supply_id", "ordenes de compra"),
        ("supply_lots", "supply_id", "lotes"),
    ],
    "suppliers": [
        ("purchase_orders", "supplier_id", "ordenes de compra"),
    ],
    "workers": [
        ("work_orders", "worker_id", "ordenes de trabajo"),
    ],
    "tanks": [
        ("work_orders", "source_tank_id", "ordenes de trabajo (cuba inicial)"),
        ("work_orders", "dest_tank_id", "ordenes de trabajo (cuba destino)"),
        ("tank_contents", "tank_id", "contenido de cubas"),
    ],
    "winemaking_processes": [
        ("work_orders", "process_id", "ordenes de trabajo"),
    ],
    "grape_varieties": [
        ("work_orders", "grape_variety_id", "ordenes de trabajo"),
        ("wines", "grape_variety_id", "vinos"),
    ],
    "product_lines": [
        ("work_orders", "product_line_id", "ordenes de trabajo"),
        ("wines", "product_line_id", "vinos"),
    ],
}


def check_dependencies(table_name: str, record_id: int) -> list[str]:
    deps = DEPENDENCY_MAP.get(table_name, [])
    found = []
    for ref_table, ref_column, desc in deps:
        try:
            result = (client.table(ref_table)
                      .select("id")
                      .eq(ref_column, record_id)
                      .limit(1)
                      .execute().data)
            if result:
                found.append(desc)
        except Exception:
            pass
    return found


def crud_table(tab, table_name, columns, display_name, id_field="id"):
    with tab:
        st.subheader(f"Gestionar {display_name}")

        try:
            data = client.table(table_name).select("*").order(columns[0]["field"]).execute().data
        except Exception as e:
            st.error(f"Error cargando {display_name}: {e}")
            return

        if not data:
            st.info(f"No hay {display_name.lower()} registrados")

        # --- TABLA CON EDICION Y ELIMINACION ---
        if data:
            # Buscador
            search = st.text_input(
                f"Buscar en {display_name.lower()}:",
                placeholder="Escriba para filtrar...",
                key=f"search_{table_name}"
            )

            filtered = data
            if search:
                search_lower = search.lower()
                filtered = [
                    row for row in data
                    if any(search_lower in str(row.get(col["field"], "")).lower() for col in columns)
                ]

            st.caption(f"Mostrando {len(filtered)} de {len(data)} registros")

            # Selector de registro para editar/eliminar
            record_options = {}
            for row in filtered:
                label_parts = []
                for col in columns[:2]:
                    val = row.get(col["field"], "")
                    if val:
                        label_parts.append(str(val))
                label = " - ".join(label_parts) if label_parts else f"ID {row[id_field]}"
                record_options[row[id_field]] = label

            col_table, col_actions = st.columns([3, 2])

            with col_table:
                display_rows = []
                for row in filtered:
                    display_row = {"ID": row[id_field]}
                    for col in columns:
                        display_row[col["label"]] = row.get(col["field"], "")
                    display_rows.append(display_row)

                st.dataframe(
                    display_rows,
                    use_container_width=True,
                    hide_index=True,
                    height=min(400, 40 + len(filtered) * 35),
                )

            with col_actions:
                st.markdown("**Editar / Eliminar registro:**")

                selected_id = st.selectbox(
                    "Seleccione registro:",
                    options=list(record_options.keys()),
                    format_func=lambda x: record_options[x],
                    index=None,
                    placeholder="Seleccione...",
                    key=f"select_{table_name}",
                )

                if selected_id:
                    selected_row = next(r for r in data if r[id_field] == selected_id)

                    # Campos editables
                    st.markdown("---")
                    updated = {}
                    for col in columns:
                        current_val = selected_row.get(col["field"], "")
                        if col.get("type") == "number":
                            updated[col["field"]] = st.number_input(
                                col["label"],
                                value=float(current_val) if current_val else 0.0,
                                key=f"edit_{table_name}_{col['field']}_{selected_id}",
                            )
                        else:
                            updated[col["field"]] = st.text_input(
                                col["label"],
                                value=str(current_val) if current_val else "",
                                key=f"edit_{table_name}_{col['field']}_{selected_id}",
                            )

                    col_save, col_delete = st.columns(2)

                    with col_save:
                        if st.button("Guardar cambios", key=f"save_{table_name}_{selected_id}",
                                     type="primary", use_container_width=True):
                            clean = {k: v for k, v in updated.items() if v != ""}
                            if clean:
                                try:
                                    client.table(table_name).update(clean).eq(id_field, selected_id).execute()
                                    st.success("Actualizado")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

                    with col_delete:
                        if st.button("Eliminar", key=f"del_{table_name}_{selected_id}",
                                     use_container_width=True):
                            deps = check_dependencies(table_name, selected_id)
                            if deps:
                                st.error(f"No se puede eliminar. Tiene movimientos en: {', '.join(deps)}")
                            else:
                                st.session_state[f"confirm_del_{table_name}_{selected_id}"] = True

                    # Confirmacion de eliminacion
                    if st.session_state.get(f"confirm_del_{table_name}_{selected_id}"):
                        st.warning(f"Confirma eliminar: **{record_options[selected_id]}**?")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Si, eliminar", key=f"yes_del_{table_name}_{selected_id}",
                                         use_container_width=True):
                                try:
                                    client.table(table_name).delete().eq(id_field, selected_id).execute()
                                    st.success("Eliminado")
                                    del st.session_state[f"confirm_del_{table_name}_{selected_id}"]
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        with col_no:
                            if st.button("Cancelar", key=f"no_del_{table_name}_{selected_id}",
                                         use_container_width=True):
                                del st.session_state[f"confirm_del_{table_name}_{selected_id}"]
                                st.rerun()

        # --- AGREGAR NUEVO ---
        st.markdown("---")
        singular = display_name.lower().rstrip("s") if display_name.lower().endswith("s") else display_name.lower()
        with st.expander(f"+ Agregar nuevo {singular}", expanded=False):
            new_data = {}
            cols = st.columns(min(len(columns), 4))
            for i, col_def in enumerate(columns):
                with cols[i % len(cols)]:
                    if col_def.get("type") == "number":
                        new_data[col_def["field"]] = st.number_input(
                            col_def["label"], value=0.0, key=f"new_{table_name}_{col_def['field']}"
                        )
                    else:
                        new_data[col_def["field"]] = st.text_input(
                            col_def["label"], key=f"new_{table_name}_{col_def['field']}"
                        )

            if st.button(f"Agregar {singular}", key=f"add_{table_name}", type="primary"):
                clean_data = {k: v for k, v in new_data.items() if v and v != 0.0}
                if clean_data:
                    try:
                        client.table(table_name).insert(clean_data).execute()
                        st.success("Registro agregado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Complete al menos un campo")


# --- TABS ---
tab_sup, tab_prov, tab_work, tab_tank, tab_proc, tab_grape, tab_line = st.tabs([
    "Insumos", "Proveedores", "Operarios", "Cubas", "Procesos", "Cepas", "Lineas"
])

crud_table(tab_sup, "supplies", [
    {"field": "name", "label": "Nombre"},
    {"field": "code", "label": "Codigo"},
    {"field": "unit", "label": "Unidad (Kg/Lts/Unidad)"},
    {"field": "min_stock", "label": "Stock Minimo", "type": "number"},
], "Insumos")

crud_table(tab_prov, "suppliers", [
    {"field": "name", "label": "Nombre"},
    {"field": "rut", "label": "RUT"},
    {"field": "phone", "label": "Telefono"},
    {"field": "email", "label": "Email"},
], "Proveedores")

crud_table(tab_work, "workers", [
    {"field": "full_name", "label": "Nombre Completo"},
    {"field": "role", "label": "Cargo"},
], "Operarios")

crud_table(tab_tank, "tanks", [
    {"field": "code", "label": "Numero/Codigo"},
    {"field": "name", "label": "Nombre"},
    {"field": "capacity_liters", "label": "Capacidad (L)", "type": "number"},
    {"field": "location", "label": "Ubicacion"},
], "Cubas")

crud_table(tab_proc, "winemaking_processes", [
    {"field": "name", "label": "Nombre del Proceso"},
    {"field": "description", "label": "Descripcion"},
], "Procesos Enologicos")

crud_table(tab_grape, "grape_varieties", [
    {"field": "code", "label": "Codigo (CS, MR, etc.)"},
    {"field": "name", "label": "Nombre Completo"},
    {"field": "wine_type", "label": "Tipo (Tinto/Blanco/Rosado)"},
], "Cepas")

crud_table(tab_line, "product_lines", [
    {"field": "name", "label": "Nombre de Linea"},
    {"field": "sort_order", "label": "Orden", "type": "number"},
], "Lineas de Producto")

# --- Estado del sistema ---
st.markdown("---")
st.subheader("Estado del Sistema")
from lib.database import test_connection
col_test, col_info = st.columns(2)
with col_test:
    if st.button("Probar conexion"):
        if test_connection():
            st.success("Conexion OK")
        else:
            st.error("Sin conexion")
with col_info:
    try:
        counts = {
            "Insumos": len(client.table("supplies").select("id").execute().data),
            "Proveedores": len(client.table("suppliers").select("id").execute().data),
            "Operarios": len(client.table("workers").select("id").execute().data),
            "Cubas": len(client.table("tanks").select("id").execute().data),
            "Cepas": len(client.table("grape_varieties").select("id").execute().data),
        }
        st.markdown(" | ".join([f"**{k}:** {v}" for k, v in counts.items()]))
    except Exception:
        pass
