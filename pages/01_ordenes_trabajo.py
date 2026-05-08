import streamlit as st
import pandas as pd
from datetime import date
from lib import queries
from lib.auth import get_current_user
from lib.pdf_generator import generate_ot_pdf

st.title("Ordenes de Trabajo")
st.markdown("Creacion y seguimiento de ordenes de trabajo")

tab_kanban, tab_crear, tab_buscar = st.tabs(["Tablero", "Crear Nueva OT", "Buscar / Eliminar"])

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
        "wines": queries.get_wines(),
    }

try:
    ref = load_reference_data()
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")
    st.stop()


def get_tank_code(tank_id):
    if not tank_id:
        return "-"
    tank = next((t for t in ref["tanks"] if t["id"] == tank_id), None)
    return tank["code"] if tank else str(tank_id)


def get_wine_code(ot):
    wine = ot.get("wines") or {}
    return wine.get("code", "-") if isinstance(wine, dict) else "-"


def build_ot_pdf(ot, lines=None):
    ot_for_pdf = dict(ot)
    ot_for_pdf["source_tank_code"] = get_tank_code(ot.get("source_tank_id"))
    ot_for_pdf["dest_tank_code"] = get_tank_code(ot.get("dest_tank_id"))
    worker = ot.get("workers") or {}
    worker_name = worker.get("full_name", "-") if worker else "-"
    user = get_current_user()
    creator_name = user["full_name"] if user else "-"
    return generate_ot_pdf(ot_for_pdf, lines or [], worker_name, creator_name, logo_path="logo_vda.png")


# =================================================================
# TAB 1: TABLERO KANBAN
# =================================================================
with tab_kanban:
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_date = st.date_input("Desde fecha:", value=date(date.today().year, date.today().month, 1))
    with col_f2:
        worker_filter_opts = {"": "Todos"} | {str(w["id"]): w["full_name"] for w in ref["workers"]}
        worker_filter = st.selectbox("Operario:", options=list(worker_filter_opts.keys()),
                                     format_func=lambda x: worker_filter_opts[x])
    with col_f3:
        status_filter = st.selectbox("Estado:", ["Todos", "Pendiente", "En Proceso", "Completada", "Anulada"])

    try:
        all_ots = queries.get_work_orders_with_status(str(filter_date))
    except Exception as e:
        st.error(f"Error: {e}")
        all_ots = []

    if worker_filter:
        all_ots = [ot for ot in all_ots if str(ot.get("worker_id", "")) == worker_filter]
    if status_filter != "Todos":
        all_ots = [ot for ot in all_ots if ot.get("status") == status_filter]

    pendientes = [ot for ot in all_ots if ot.get("status") == "Pendiente"]
    en_proceso = [ot for ot in all_ots if ot.get("status") == "En Proceso"]
    completadas = [ot for ot in all_ots if ot.get("status") == "Completada"]

    col_p, col_e, col_c = st.columns(3)

    def render_ot_card(ot, container):
        with container:
            status = ot.get("status", "Pendiente")
            priority = ot.get("priority", "Normal")
            ot_type = ot.get("ot_type", "Insumos")
            colors = {"Pendiente": "#fff3cd", "En Proceso": "#cce5ff", "Completada": "#d4edda", "Anulada": "#f8d7da"}
            border_color = "#dc3545" if priority == "Urgente" else "#dee2e6"
            bg = colors.get(status, "#f8f9fa")

            wine_code = get_wine_code(ot)
            cepa = ot.get("grape_varieties", {})
            cepa_code = cepa.get("code", "-") if cepa else "-"
            worker = ot.get("workers", {})
            worker_name = worker.get("full_name", "-") if worker else "-"
            process = ot.get("winemaking_processes", {})
            process_name = process.get("name", "-") if process else "-"

            urgente_badge = ' <span style="background:#dc3545;color:white;padding:2px 6px;border-radius:3px;font-size:0.7em;">URGENTE</span>' if priority == "Urgente" else ""
            type_color = "#17a2b8" if ot_type == "Insumos" else "#28a745"
            type_badge = f' <span style="background:{type_color};color:white;padding:1px 5px;border-radius:3px;font-size:0.65em;">{ot_type.upper()}</span>'

            st.markdown(f"""
            <div style="background:{bg};border:1px solid {border_color};border-radius:8px;padding:12px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <strong>OT #{ot.get('ot_number', '?')}</strong>{type_badge}{urgente_badge}
                </div>
                <div style="font-size:0.85em;color:#555;margin-top:4px;">
                    <div>{ot.get('date', '-')}</div>
                    <div>Vino: {wine_code} | Cepa: {cepa_code}</div>
                    <div>{process_name} | {worker_name}</div>
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
        ot_options = {ot["id"]: f"OT #{ot.get('ot_number', '?')} - {get_wine_code(ot)} - {ot.get('status', '')} [{ot.get('ot_type', 'Insumos')}]"
                      for ot in all_ots}
        selected_ot_id = st.selectbox("Seleccione OT:", options=list(ot_options.keys()),
                                      format_func=lambda x: ot_options[x], index=None)
        if selected_ot_id:
            selected_ot = next(ot for ot in all_ots if ot["id"] == selected_ot_id)
            ot_lines = []

            wine_code = get_wine_code(selected_ot)
            cepa = (selected_ot.get("grape_varieties") or {}).get("code", "-")
            process = (selected_ot.get("winemaking_processes") or {}).get("name", "-")
            st.markdown(f"**Vino:** {wine_code} | **Cepa:** {cepa} | **Operacion:** {process}")

            if selected_ot.get("ot_type") == "Movimiento":
                st.info(f"Movimiento de Vino: {get_tank_code(selected_ot.get('source_tank_id'))} → {get_tank_code(selected_ot.get('dest_tank_id'))} | {selected_ot.get('liters', '-')} L")
            else:
                try:
                    ot_lines = queries.get_work_order_lines(selected_ot_id)
                    if ot_lines:
                        df_lines = pd.DataFrame(ot_lines)
                        df_lines["insumo"] = df_lines["supplies"].apply(lambda x: x["name"] if x else "-")
                        df_lines["unidad"] = df_lines["supplies"].apply(lambda x: x.get("unit", "") if x else "")
                        display_cols = {"insumo": "Insumo", "unidad": "Unidad"}
                        if "planned_quantity" in df_lines.columns:
                            display_cols["planned_quantity"] = "Planificado"
                        display_cols["quantity"] = "Real"
                        st.dataframe(
                            df_lines[list(display_cols.keys())].rename(columns=display_cols),
                            use_container_width=True, hide_index=True,
                        )
                    else:
                        st.info("Sin insumos registrados")
                except Exception as e:
                    st.warning(f"Error cargando detalle: {e}")

            col_pdf, col_anular = st.columns(2)
            with col_pdf:
                try:
                    pdf_bytes = build_ot_pdf(selected_ot, ot_lines)
                    st.download_button(
                        "Descargar PDF",
                        data=pdf_bytes,
                        file_name=f"OT_{selected_ot.get('ot_number', selected_ot_id)}.pdf",
                        mime="application/pdf",
                        key="kanban_pdf",
                    )
                except Exception as e:
                    st.warning(f"Error generando PDF: {e}")

            with col_anular:
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
    if "last_created_ot" in st.session_state:
        _ot_id = st.session_state.last_created_ot
        try:
            _ot_data = queries.get_work_order_by_id(_ot_id)
            _ot_lines = queries.get_work_order_lines(_ot_id)
            _pdf = build_ot_pdf(_ot_data, _ot_lines)
            st.success(f"OT #{_ot_data.get('ot_number', '?')} creada exitosamente")
            st.warning("Debe descargar el PDF antes de continuar")
            col_otpdf, col_otnew = st.columns(2)
            with col_otpdf:
                downloaded = st.download_button(
                    "Descargar PDF",
                    data=_pdf,
                    file_name=f"OT_{_ot_data.get('ot_number', _ot_id)}.pdf",
                    mime="application/pdf",
                    key="new_ot_pdf",
                    type="primary",
                )
                if downloaded:
                    st.session_state[f"ot_pdf_downloaded_{_ot_id}"] = True
            with col_otnew:
                if st.session_state.get(f"ot_pdf_downloaded_{_ot_id}"):
                    if st.button("Crear otra OT", key="close_ot_success"):
                        del st.session_state["last_created_ot"]
                        del st.session_state[f"ot_pdf_downloaded_{_ot_id}"]
                        st.rerun()
                else:
                    st.button("Crear otra OT", key="close_ot_success", disabled=True,
                              help="Primero descargue el PDF")
        except Exception:
            del st.session_state["last_created_ot"]
        st.stop()

    if "ot_lines" not in st.session_state:
        st.session_state.ot_lines = [{"supply_id": None, "lot_id": None, "quantity": 0.0}]

    st.subheader("Nueva Orden de Trabajo")

    ot_type = st.radio("Tipo de OT:", ["Insumos", "Movimiento de Vino"], horizontal=True, key="new_ot_type")

    col1, col2, col3 = st.columns(3)
    with col1:
        ot_date = st.date_input("Fecha", value=date.today(), key="new_ot_date")
        try:
            next_ot = queries.get_next_ot_number()
        except Exception:
            next_ot = 1
        ot_number = st.number_input("N OT", value=next_ot, min_value=1, step=1)

    with col2:
        wine_options = {}
        for w in ref["wines"]:
            cepa = w.get("grape_varieties") or {}
            linea = w.get("product_lines") or {}
            wine_options[w["id"]] = f"{w['code']} - {cepa.get('code', '')} {linea.get('name', '')}"

        wine_id = st.selectbox("Codigo Vino", options=list(wine_options.keys()),
                               format_func=lambda x: wine_options[x],
                               index=None, placeholder="Seleccione vino...", key="new_wine")

        grape_id = None
        line_id = None
        if wine_id:
            selected_wine = next(w for w in ref["wines"] if w["id"] == wine_id)
            cepa_info = selected_wine.get("grape_varieties") or {}
            linea_info = selected_wine.get("product_lines") or {}
            grape_id = selected_wine.get("grape_variety_id")
            line_id = selected_wine.get("product_line_id")
            st.markdown(f"**Cepa:** {cepa_info.get('code', '-')} - {cepa_info.get('name', '-')}")
            st.markdown(f"**Linea:** {linea_info.get('name', '-')}")

    with col3:
        process_options = {p["id"]: p["name"] for p in ref["processes"]}
        process_id = st.selectbox("Operacion", options=list(process_options.keys()),
                                  format_func=lambda x: process_options[x],
                                  index=None, placeholder="Seleccione operacion...", key="new_proc")

        worker_options = {w["id"]: w["full_name"] for w in ref["workers"]}
        worker_id = st.selectbox("Operario Asignado", options=list(worker_options.keys()),
                                 format_func=lambda x: worker_options[x],
                                 index=None, placeholder="Seleccione operario...", key="new_worker")

    try:
        tank_contents = queries.get_tank_contents()
    except Exception:
        tank_contents = []
    content_by_tank = {c["tank_id"]: c for c in tank_contents}

    is_movement = ot_type == "Movimiento de Vino"

    if wine_id:
        source_tanks = [t for t in ref["tanks"]
                        if content_by_tank.get(t["id"], {}).get("wine_id") == wine_id
                        and (content_by_tank.get(t["id"], {}).get("current_liters", 0) or 0) > 0]
        total_wine_liters = sum(
            content_by_tank.get(t["id"], {}).get("current_liters", 0) or 0
            for t in source_tanks
        )
        if source_tanks:
            st.info(f"Este vino tiene **{total_wine_liters:,.0f} L** en **{len(source_tanks)} cuba{'s' if len(source_tanks) > 1 else ''}**")
        else:
            st.warning("No hay cubas con este vino. Verifique el codigo de vino seleccionado.")
    else:
        source_tanks = ref["tanks"]

    col_t1, col_t2, col_t3, col_t4 = st.columns([2, 2, 2, 1])
    with col_t1:
        source_options = {}
        for t in source_tanks:
            c = content_by_tank.get(t["id"], {})
            lts = c.get("current_liters", 0) or 0
            cepa_c = (c.get("grape_varieties") or {}).get("code", "")
            if wine_id:
                source_options[t["id"]] = f"Cuba {t['code']} — {lts:,.0f} L {cepa_c}"
            else:
                source_options[t["id"]] = f"Cuba {t['code']}"
        source_tank_id = st.selectbox("Cuba Inicial", options=list(source_options.keys()),
                                      format_func=lambda x: source_options[x],
                                      index=None, placeholder="Seleccione...", key="new_src_tank")

    with col_t2:
        if is_movement:
            dest_empty = []
            dest_occupied = []
            for t in ref["tanks"]:
                if t["id"] == source_tank_id:
                    continue
                c = content_by_tank.get(t["id"], {})
                status = c.get("status", "Vacio")
                if status == "Vacio" or not c.get("current_liters"):
                    dest_empty.append(t)
                else:
                    dest_occupied.append(t)
            dest_tanks_sorted = dest_empty + dest_occupied
            dest_options = {}
            for t in dest_tanks_sorted:
                c = content_by_tank.get(t["id"], {})
                status = c.get("status", "Vacio")
                lts = c.get("current_liters", 0) or 0
                wine_c = (c.get("wines") or {}).get("code", "")
                cap = next((tk.get("capacity_liters", 0) or 0 for tk in ref["tanks"] if tk["id"] == t["id"]), 0)
                if status == "Vacio" or not lts:
                    tag = f"Vacia — Cap. {cap:,.0f} L" if cap else "Vacia"
                else:
                    tag = f"{lts:,.0f} L — {wine_c}" if wine_c else f"{lts:,.0f} L"
                dest_options[t["id"]] = f"Cuba {t['code']} — {tag}"
        else:
            dest_options = {t["id"]: f"Cuba {t['code']}" for t in ref["tanks"]}
        dest_tank_id = st.selectbox("Cuba Destino", options=list(dest_options.keys()),
                                    format_func=lambda x: dest_options[x],
                                    index=None, placeholder="Seleccione...", key="new_dst_tank")

    with col_t3:
        if source_tank_id:
            src_content = content_by_tank.get(source_tank_id, {})
            max_liters = int(src_content.get("current_liters", 0) or 0)
            if max_liters > 0:
                st.caption(f"Disponible en cuba: {max_liters:,} L")
        liters = st.number_input("Litros a traspasar" if is_movement else "Litros",
                                 value=0, min_value=0, step=100, key="new_liters")
    with col_t4:
        priority = st.selectbox("Prioridad", ["Normal", "Urgente"], key="new_priority")

    if ot_type == "Insumos":
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

    is_blend = False
    blend_wine_id = None
    if ot_type == "Movimiento de Vino":
        st.markdown("---")

        if dest_tank_id and wine_id:
            dest_content = content_by_tank.get(dest_tank_id, {})
            dest_wine_id = dest_content.get("wine_id")
            dest_wine_code = (dest_content.get("wines") or {}).get("code", "")
            dest_liters = dest_content.get("current_liters", 0) or 0
            dest_status = dest_content.get("status", "Vacio")

            if dest_status != "Vacio" and dest_wine_id and dest_wine_id != wine_id:
                is_blend = True
                src_wine_code = wine_options.get(wine_id, "?")
                st.warning(f"**Mezcla detectada:** {src_wine_code.split(' - ')[0]} + {dest_wine_code} ({dest_liters:,.0f} L en destino)")
                st.markdown("Esta operacion requiere un nuevo codigo de vino para la mezcla resultante.")

                col_b1, col_b2, col_b3 = st.columns(3)
                with col_b1:
                    blend_code = st.text_input("Codigo del nuevo vino", placeholder="Ej: 103-CS/MR 26/26-200",
                                               key="blend_code")
                with col_b2:
                    grape_opts = {g["id"]: f"{g['code']} - {g['name']}" for g in ref["grape_varieties"]}
                    blend_grape_id = st.selectbox("Cepa principal", options=list(grape_opts.keys()),
                                                  format_func=lambda x: grape_opts[x],
                                                  index=None, placeholder="Seleccione...", key="blend_grape")
                with col_b3:
                    line_opts = {l["id"]: l["name"] for l in ref["product_lines"]}
                    blend_line_id = st.selectbox("Linea de producto", options=list(line_opts.keys()),
                                                 format_func=lambda x: line_opts[x],
                                                 index=None, placeholder="Seleccione...", key="blend_line")

                blend_wine_type = st.selectbox("Tipo de vino", ["Tinto", "Blanco", "Rosado"],
                                               key="blend_wine_type")

        ot_observations = st.text_area("Observaciones", key="new_ot_obs", placeholder="Notas sobre el movimiento...")
    else:
        ot_observations = None

    st.markdown("---")
    if st.button("Crear Orden de Trabajo", type="primary", key="create_ot_btn"):
        if not wine_id:
            st.error("Debe seleccionar un Codigo de Vino")
        elif ot_type == "Insumos":
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
                        "ot_type": "Insumos",
                        "wine_id": wine_id,
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

                    st.session_state.last_created_ot = wo_id
                    st.session_state.ot_lines = [{"supply_id": None, "lot_id": None, "quantity": 0.0}]
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        elif ot_type == "Movimiento de Vino":
            src_content = content_by_tank.get(source_tank_id, {}) if source_tank_id else {}
            src_liters = int(src_content.get("current_liters", 0) or 0)
            src_wine = src_content.get("wine_id")
            if not worker_id:
                st.error("Debe asignar un operario")
            elif not source_tank_id:
                st.error("Debe seleccionar Cuba Inicial")
            elif not dest_tank_id:
                st.error("Debe seleccionar Cuba Destino")
            elif source_tank_id == dest_tank_id:
                st.error("Cuba Inicial y Destino deben ser diferentes")
            elif liters <= 0:
                st.error("Debe indicar los litros a mover")
            elif src_wine != wine_id:
                st.error("La Cuba Inicial no contiene el vino seleccionado")
            elif liters > src_liters:
                st.error(f"La Cuba Inicial solo tiene {src_liters:,} litros disponibles")
            elif is_blend and not blend_code:
                st.error("Debe ingresar el codigo del nuevo vino para la mezcla")
            elif is_blend and not blend_grape_id:
                st.error("Debe seleccionar la cepa principal de la mezcla")
            elif is_blend and not blend_line_id:
                st.error("Debe seleccionar la linea de producto de la mezcla")
            else:
                try:
                    final_wine_id = wine_id
                    final_grape_id = grape_id
                    final_line_id = line_id

                    if is_blend:
                        new_wine = queries.create_wine({
                            "code": blend_code,
                            "grape_variety_id": blend_grape_id,
                            "product_line_id": blend_line_id,
                            "wine_type": blend_wine_type,
                            "notes": f"Mezcla: {wine_options.get(wine_id, '?').split(' - ')[0]} + {dest_wine_code}",
                            "is_active": True,
                        })
                        final_wine_id = new_wine[0]["id"]
                        final_grape_id = blend_grape_id
                        final_line_id = blend_line_id
                        obs_blend = f"MEZCLA: {wine_options.get(wine_id, '?').split(' - ')[0]} + {dest_wine_code} → {blend_code}"
                        ot_observations = f"{obs_blend}\n{ot_observations}" if ot_observations else obs_blend

                    wo_data = {
                        "ot_number": int(ot_number),
                        "date": str(ot_date),
                        "status": "Pendiente",
                        "priority": priority,
                        "ot_type": "Movimiento",
                        "wine_id": final_wine_id,
                        "source_tank_id": source_tank_id,
                        "dest_tank_id": dest_tank_id,
                        "liters": liters,
                    }
                    if final_grape_id:
                        wo_data["grape_variety_id"] = final_grape_id
                    if final_line_id:
                        wo_data["product_line_id"] = final_line_id
                    if process_id:
                        wo_data["process_id"] = process_id
                    if worker_id:
                        wo_data["worker_id"] = worker_id
                    if ot_observations:
                        wo_data["observations"] = ot_observations

                    result = queries.create_work_order(wo_data)
                    st.session_state.last_created_ot = result[0]["id"]
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# =================================================================
# TAB 3: BUSCAR / ELIMINAR
# =================================================================
with tab_buscar:
    st.subheader("Buscar Ordenes de Trabajo")

    col_s1, col_s2, col_s3, col_s4 = st.columns([2, 1.5, 1.5, 1])
    with col_s1:
        search_term = st.text_input("Buscar:", placeholder="N OT, vino, cepa, operario...",
                                    key="search_ot_term")
    with col_s2:
        search_from = st.date_input("Desde:", value=date(date.today().year, 1, 1), key="search_from")
    with col_s3:
        search_to = st.date_input("Hasta:", value=date.today(), key="search_to")
    with col_s4:
        search_status = st.selectbox("Estado:", ["Todos", "Pendiente", "En Proceso", "Completada", "Anulada"],
                                     key="search_status")

    try:
        results = queries.search_work_orders(
            search_term=search_term if search_term else None,
            from_date=str(search_from),
            to_date=str(search_to),
            status=search_status,
        )
    except Exception as e:
        st.error(f"Error: {e}")
        results = []

    if results:
        rows = []
        for ot in results:
            cepa = (ot.get("grape_varieties") or {}).get("code", "-")
            worker = (ot.get("workers") or {}).get("full_name", "-")
            process = (ot.get("winemaking_processes") or {}).get("name", "-")
            wine_code = get_wine_code(ot)
            rows.append({
                "id": ot["id"],
                "N OT": ot.get("ot_number", "?"),
                "Fecha": ot.get("date", "-"),
                "Vino": wine_code,
                "Cepa": cepa,
                "Tipo": ot.get("ot_type", "Insumos"),
                "Estado": ot.get("status", "-"),
                "Operacion": process,
                "Operario": worker,
                "Litros": ot.get("liters", "-") or "-",
            })

        df = pd.DataFrame(rows)

        def color_estado(val):
            colors = {
                "Pendiente": "background-color: #fff3cd",
                "En Proceso": "background-color: #cce5ff",
                "Completada": "background-color: #d4edda",
                "Anulada": "background-color: #f8d7da",
            }
            return colors.get(val, "")

        st.dataframe(
            df[["N OT", "Fecha", "Vino", "Cepa", "Tipo", "Estado", "Operacion", "Operario", "Litros"]]
            .style.map(color_estado, subset=["Estado"]),
            use_container_width=True,
            hide_index=True,
            height=400,
        )
        st.caption(f"{len(results)} resultados")

        st.markdown("---")
        ot_select_opts = {ot["id"]: f"OT #{ot.get('ot_number', '?')} - {get_wine_code(ot)} [{ot.get('ot_type', 'Insumos')}] ({ot.get('status', '')})"
                         for ot in results}
        selected_id = st.selectbox("Seleccione OT para ver detalle o eliminar:",
                                   options=list(ot_select_opts.keys()),
                                   format_func=lambda x: ot_select_opts[x],
                                   index=None, key="search_select_ot")

        if selected_id:
            selected = next(ot for ot in results if ot["id"] == selected_id)

            col_det1, col_det2 = st.columns(2)
            with col_det1:
                st.markdown(f"""
                **OT #{selected.get('ot_number')}** | Tipo: **{selected.get('ot_type', 'Insumos')}** | Estado: **{selected.get('status')}**

                Vino: **{get_wine_code(selected)}** | Cepa: {(selected.get('grape_varieties') or {}).get('code', '-')}

                Fecha: {selected.get('date')} | Litros: {selected.get('liters', '-') or '-'}

                Cuba: {get_tank_code(selected.get('source_tank_id'))} → {get_tank_code(selected.get('dest_tank_id'))}

                Observaciones: {selected.get('observations', '-') or '-'}
                """)

            search_ot_lines = []
            with col_det2:
                try:
                    search_ot_lines = queries.get_work_order_lines(selected_id)
                    if search_ot_lines:
                        for ln in search_ot_lines:
                            sup = (ln.get("supplies") or {})
                            name = sup.get("name", "?")
                            unit = sup.get("unit", "")
                            planned = ln.get("planned_quantity", "-")
                            real = ln.get("quantity", "-")
                            st.markdown(f"- **{name}** ({unit}): planificado {planned} / real {real}")
                    elif selected.get("ot_type") == "Movimiento":
                        st.caption("OT de Movimiento de Vino (sin insumos)")
                    else:
                        st.caption("Sin insumos")
                except Exception:
                    st.caption("Error cargando insumos")

            try:
                pdf_bytes = build_ot_pdf(selected, search_ot_lines)
                st.download_button(
                    "Descargar PDF",
                    data=pdf_bytes,
                    file_name=f"OT_{selected.get('ot_number', selected_id)}.pdf",
                    mime="application/pdf",
                    key="search_pdf",
                )
            except Exception as e:
                st.warning(f"Error generando PDF: {e}")

            st.markdown("---")
            status = selected.get("status", "")

            col_a1, col_a2, col_a3 = st.columns(3)

            with col_a1:
                if status == "Completada":
                    st.info("Las OTs completadas no se pueden eliminar (ya descontaron stock)")
                elif status == "En Proceso":
                    st.warning("Primero devuelva la OT a Pendiente antes de eliminar")
                    if st.button("Devolver a Pendiente", key="search_return_pending"):
                        try:
                            queries.update_work_order_status(selected_id, "Pendiente")
                            st.success("OT devuelta a Pendiente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

            with col_a2:
                if status in ("Pendiente", "Anulada"):
                    if st.button("Eliminar OT", key="search_delete_ot"):
                        st.session_state[f"confirm_delete_ot_{selected_id}"] = True

                    if st.session_state.get(f"confirm_delete_ot_{selected_id}"):
                        st.warning(f"Confirma eliminar OT #{selected.get('ot_number')}?")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Si, eliminar", key=f"yes_del_ot_{selected_id}",
                                        use_container_width=True):
                                try:
                                    queries.delete_work_order(selected_id)
                                    st.success(f"OT #{selected.get('ot_number')} eliminada")
                                    del st.session_state[f"confirm_delete_ot_{selected_id}"]
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                        with col_no:
                            if st.button("Cancelar", key=f"no_del_ot_{selected_id}",
                                        use_container_width=True):
                                del st.session_state[f"confirm_delete_ot_{selected_id}"]
                                st.rerun()

            with col_a3:
                if status == "Pendiente":
                    if st.button("Anular OT", key="search_anular_ot"):
                        try:
                            queries.update_work_order_status(selected_id, "Anulada")
                            st.success("OT anulada")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
    else:
        st.info("No se encontraron ordenes de trabajo")
