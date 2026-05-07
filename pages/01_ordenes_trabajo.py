import streamlit as st
import pandas as pd
from datetime import date
from lib import queries

st.title("Ordenes de Trabajo")
st.markdown("Creacion y seguimiento de ordenes de trabajo")

tab_kanban, tab_crear = st.tabs(["Tablero", "Crear Nueva OT"])

# --- Cargar datos de referencia ---
@st.cache_data(ttl=120)
def load_reference_data():
    return {
        "supplies": queries.get_supplies(),
        "grape_varieties": queries.get_grape_varieties(),
        "product_lines": queries.get_product_lines(),
        "workers": queries.get_workers(),
        "processes": queries.get_processes(),
        "tanks": queries.get_tanks(),
    }

try:
    ref = load_reference_data()
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")
    st.stop()

# =================================================================
# TAB 1: TABLERO KANBAN
# =================================================================
with tab_kanban:
    # Filtros
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_date = st.date_input("Desde fecha:", value=date(date.today().year, date.today().month, 1))
    with col_f2:
        worker_filter_opts = {"": "Todos"} | {str(w["id"]): w["full_name"] for w in ref["workers"]}
        worker_filter = st.selectbox("Operario:", options=list(worker_filter_opts.keys()),
                                     format_func=lambda x: worker_filter_opts[x])
    with col_f3:
        status_filter = st.selectbox("Estado:", ["Todos", "Pendiente", "En Proceso", "Completada", "Anulada"])

    # Cargar OTs
    try:
        all_ots = queries.get_work_orders_with_status(str(filter_date))
    except Exception as e:
        st.error(f"Error: {e}")
        all_ots = []

    if worker_filter:
        all_ots = [ot for ot in all_ots if str(ot.get("worker_id", "")) == worker_filter]
    if status_filter != "Todos":
        all_ots = [ot for ot in all_ots if ot.get("status") == status_filter]

    # Kanban columns
    pendientes = [ot for ot in all_ots if ot.get("status") == "Pendiente"]
    en_proceso = [ot for ot in all_ots if ot.get("status") == "En Proceso"]
    completadas = [ot for ot in all_ots if ot.get("status") == "Completada"]

    col_p, col_e, col_c = st.columns(3)

    def render_ot_card(ot, container):
        with container:
            status = ot.get("status", "Pendiente")
            priority = ot.get("priority", "Normal")
            colors = {"Pendiente": "#fff3cd", "En Proceso": "#cce5ff", "Completada": "#d4edda", "Anulada": "#f8d7da"}
            border_color = "#dc3545" if priority == "Urgente" else "#dee2e6"
            bg = colors.get(status, "#f8f9fa")

            cepa = ot.get("grape_varieties", {})
            cepa_code = cepa.get("code", "-") if cepa else "-"
            worker = ot.get("workers", {})
            worker_name = worker.get("full_name", "-") if worker else "-"
            process = ot.get("winemaking_processes", {})
            process_name = process.get("name", "-") if process else "-"

            urgente_badge = ' <span style="background:#dc3545;color:white;padding:2px 6px;border-radius:3px;font-size:0.7em;">URGENTE</span>' if priority == "Urgente" else ""

            st.markdown(f"""
            <div style="background:{bg};border:1px solid {border_color};border-radius:8px;padding:12px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <strong>OT #{ot.get('ot_number', '?')}</strong>{urgente_badge}
                </div>
                <div style="font-size:0.85em;color:#555;margin-top:4px;">
                    <div>{ot.get('date', '-')}</div>
                    <div>Cepa: {cepa_code} | {process_name}</div>
                    <div>Operario: {worker_name}</div>
                    <div>Litros: {ot.get('liters', '-') or '-'}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_p:
        st.markdown(f"### Pendientes ({len(pendientes)})")
        st.markdown('<div style="border-top:3px solid #ffc107;"></div>', unsafe_allow_html=True)
        if pendientes:
            for ot in pendientes:
                render_ot_card(ot, col_p)
        else:
            st.caption("Sin OTs pendientes")

    with col_e:
        st.markdown(f"### En Proceso ({len(en_proceso)})")
        st.markdown('<div style="border-top:3px solid #007bff;"></div>', unsafe_allow_html=True)
        if en_proceso:
            for ot in en_proceso:
                render_ot_card(ot, col_e)
        else:
            st.caption("Sin OTs en proceso")

    with col_c:
        st.markdown(f"### Completadas ({len(completadas)})")
        st.markdown('<div style="border-top:3px solid #28a745;"></div>', unsafe_allow_html=True)
        if completadas:
            for ot in completadas:
                render_ot_card(ot, col_c)
        else:
            st.caption("Sin OTs completadas")

    # Detalle de OT seleccionada
    if all_ots:
        st.markdown("---")
        st.subheader("Detalle de OT")
        ot_options = {ot["id"]: f"OT #{ot.get('ot_number', '?')} - {ot.get('date', '')} - {ot.get('status', '')}"
                      for ot in all_ots}
        selected_ot_id = st.selectbox("Seleccione OT:", options=list(ot_options.keys()),
                                      format_func=lambda x: ot_options[x], index=None)
        if selected_ot_id:
            try:
                lines = queries.get_work_order_lines(selected_ot_id)
                if lines:
                    df_lines = pd.DataFrame(lines)
                    df_lines["insumo"] = df_lines["supplies"].apply(lambda x: x["name"] if x else "-")
                    df_lines["unidad"] = df_lines["supplies"].apply(lambda x: x.get("unit", "") if x else "")
                    display_cols = {"insumo": "Insumo", "unidad": "Unidad"}
                    if "planned_quantity" in df_lines.columns:
                        display_cols["planned_quantity"] = "Planificado"
                    display_cols["quantity"] = "Real"
                    if "observations" in df_lines.columns:
                        display_cols["observations"] = "Observaciones"
                    st.dataframe(
                        df_lines[list(display_cols.keys())].rename(columns=display_cols),
                        use_container_width=True, hide_index=True,
                    )
                else:
                    st.info("Sin insumos registrados")
            except Exception as e:
                st.warning(f"Error cargando detalle: {e}")

            # Boton para anular
            selected_ot = next(ot for ot in all_ots if ot["id"] == selected_ot_id)
            if selected_ot.get("status") == "Pendiente":
                if st.button("Anular OT", key="anular_ot"):
                    try:
                        queries.update_work_order_status(selected_ot_id, "Anulada")
                        st.success("OT anulada")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# =================================================================
# TAB 2: CREAR NUEVA OT
# =================================================================
with tab_crear:
    if "ot_lines" not in st.session_state:
        st.session_state.ot_lines = [{"supply_id": None, "lot_id": None, "quantity": 0.0}]

    st.subheader("Nueva Orden de Trabajo")

    col1, col2, col3 = st.columns(3)
    with col1:
        ot_date = st.date_input("Fecha", value=date.today(), key="new_ot_date")
        try:
            next_ot = queries.get_next_ot_number()
        except Exception:
            next_ot = 1
        ot_number = st.number_input("N° OT", value=next_ot, min_value=1, step=1)

    with col2:
        grape_options = {g["id"]: f"{g['code']} - {g['name']}" for g in ref["grape_varieties"]}
        grape_id = st.selectbox("Cepa", options=list(grape_options.keys()),
                                format_func=lambda x: grape_options[x],
                                index=None, placeholder="Seleccione cepa...", key="new_grape")

        line_options = {l["id"]: l["name"] for l in ref["product_lines"]}
        line_id = st.selectbox("Linea de Producto", options=list(line_options.keys()),
                               format_func=lambda x: line_options[x],
                               index=None, placeholder="Seleccione linea...", key="new_line")

    with col3:
        process_options = {p["id"]: p["name"] for p in ref["processes"]}
        process_id = st.selectbox("Operacion", options=list(process_options.keys()),
                                  format_func=lambda x: process_options[x],
                                  index=None, placeholder="Seleccione operacion...", key="new_proc")

        worker_options = {w["id"]: w["full_name"] for w in ref["workers"]}
        worker_id = st.selectbox("Operario Asignado", options=list(worker_options.keys()),
                                 format_func=lambda x: worker_options[x],
                                 index=None, placeholder="Seleccione operario...", key="new_worker")

    # Cubas y prioridad
    col_t1, col_t2, col_t3, col_t4 = st.columns([2, 2, 2, 1])
    with col_t1:
        tank_options = {t["id"]: f"Cuba {t['code']}" for t in ref["tanks"]}
        source_tank_id = st.selectbox("Cuba Inicial", options=list(tank_options.keys()),
                                      format_func=lambda x: tank_options[x],
                                      index=None, placeholder="Seleccione...", key="new_src_tank")
    with col_t2:
        dest_tank_id = st.selectbox("Cuba Destino", options=list(tank_options.keys()),
                                    format_func=lambda x: tank_options[x],
                                    index=None, placeholder="Seleccione...", key="new_dst_tank")
    with col_t3:
        liters = st.number_input("Litros", value=0, min_value=0, step=100, key="new_liters")
    with col_t4:
        priority = st.selectbox("Prioridad", ["Normal", "Urgente"], key="new_priority")

    # Insumos planificados
    st.markdown("---")
    st.subheader("Insumos Planificados")

    supply_options = {s["id"]: f"{s['name']} ({s['unit']})" for s in ref["supplies"]}

    def add_line():
        st.session_state.ot_lines.append({"supply_id": None, "lot_id": None, "quantity": 0.0})

    def remove_line(idx):
        if len(st.session_state.ot_lines) > 1:
            st.session_state.ot_lines.pop(idx)

    for i, line in enumerate(st.session_state.ot_lines):
        col_s, col_q, col_del = st.columns([4, 2, 0.5])

        with col_s:
            selected_supply = st.selectbox(
                f"Insumo {i+1}", options=list(supply_options.keys()),
                format_func=lambda x: supply_options[x],
                index=None, placeholder="Seleccione insumo...",
                key=f"create_supply_{i}"
            )
            st.session_state.ot_lines[i]["supply_id"] = selected_supply

        with col_q:
            qty = st.number_input(f"Cantidad planificada {i+1}", value=0.0, min_value=0.0, step=0.1,
                                  key=f"create_qty_{i}")
            st.session_state.ot_lines[i]["quantity"] = qty

        with col_del:
            st.markdown("<br>", unsafe_allow_html=True)
            if len(st.session_state.ot_lines) > 1:
                st.button("X", key=f"create_del_{i}", on_click=remove_line, args=(i,))

    st.button("+ Agregar Insumo", on_click=add_line, key="create_add_line")

    # Guardar
    st.markdown("---")
    if st.button("Crear Orden de Trabajo", type="primary", key="create_ot_btn"):
        valid_lines = [l for l in st.session_state.ot_lines if l["supply_id"] and l["quantity"] > 0]

        if not worker_id:
            st.error("Debe asignar un operario")
        elif not valid_lines:
            st.error("Debe agregar al menos un insumo con cantidad mayor a 0")
        else:
            try:
                wo_data = {
                    "ot_number": int(ot_number),
                    "date": str(ot_date),
                    "status": "Pendiente",
                    "priority": priority,
                }
                if grape_id:
                    wo_data["grape_variety_id"] = grape_id
                if line_id:
                    wo_data["product_line_id"] = line_id
                if process_id:
                    wo_data["process_id"] = process_id
                if worker_id:
                    wo_data["worker_id"] = worker_id
                if source_tank_id:
                    wo_data["source_tank_id"] = source_tank_id
                if dest_tank_id:
                    wo_data["dest_tank_id"] = dest_tank_id
                if liters > 0:
                    wo_data["liters"] = liters

                result = queries.create_work_order(wo_data)
                wo_id = result[0]["id"]

                wo_lines = []
                for l in valid_lines:
                    wo_lines.append({
                        "work_order_id": wo_id,
                        "supply_id": l["supply_id"],
                        "planned_quantity": l["quantity"],
                        "quantity": 0,
                    })
                queries.create_work_order_lines(wo_lines)

                st.success(f"OT #{ot_number} creada como PENDIENTE y asignada al operario")
                st.session_state.ot_lines = [{"supply_id": None, "lot_id": None, "quantity": 0.0}]
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
