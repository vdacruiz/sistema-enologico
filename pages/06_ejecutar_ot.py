import streamlit as st
import pandas as pd
from datetime import datetime
from lib import queries
from lib.stock_engine import get_lots_with_stock, check_availability

st.title("Ejecutar Orden de Trabajo")
st.markdown("Vista del operario para ejecutar OTs asignadas")

# --- Seleccion de operario ---
@st.cache_data(ttl=120)
def load_workers():
    return queries.get_workers()

try:
    workers = load_workers()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

worker_options = {w["id"]: w["full_name"] for w in workers}

if "operator_id" not in st.session_state:
    st.session_state.operator_id = None

# Login del operario (simple)
if not st.session_state.operator_id:
    st.markdown("### Identificacion del Operario")
    selected_worker = st.selectbox(
        "Seleccione su nombre:",
        options=list(worker_options.keys()),
        format_func=lambda x: worker_options[x],
        index=None,
        placeholder="Seleccione operario..."
    )
    if st.button("Ingresar", type="primary"):
        if selected_worker:
            st.session_state.operator_id = selected_worker
            st.rerun()
        else:
            st.warning("Seleccione su nombre")
    st.stop()

# Header del operario
operator_name = worker_options.get(st.session_state.operator_id, "?")
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown(f"**Operario:** {operator_name}")
with col_h2:
    if st.button("Cambiar operario"):
        st.session_state.operator_id = None
        st.rerun()

st.markdown("---")

# --- Cargar OTs asignadas ---
try:
    my_ots = queries.get_work_orders_by_worker(st.session_state.operator_id)
except Exception as e:
    st.error(f"Error: {e}")
    my_ots = []

pendientes = [ot for ot in my_ots if ot.get("status") == "Pendiente"]
en_proceso = [ot for ot in my_ots if ot.get("status") == "En Proceso"]
completadas = [ot for ot in my_ots if ot.get("status") == "Completada"]

# Metricas
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Pendientes", len(pendientes))
col_m2.metric("En Proceso", len(en_proceso))
col_m3.metric("Completadas hoy", len([ot for ot in completadas
              if ot.get("completed_at", "")[:10] == str(datetime.now().date())]))

# --- OTs EN PROCESO (prioridad visual) ---
if en_proceso:
    st.subheader("En Proceso")
    for ot in en_proceso:
        render_execution_card(ot, "en_proceso")

# --- OTs PENDIENTES ---
st.subheader("Pendientes")
if not pendientes:
    st.success("No tiene OTs pendientes")
else:
    # Ordenar urgentes primero
    pendientes.sort(key=lambda x: (0 if x.get("priority") == "Urgente" else 1, x.get("date", "")))

    for ot in pendientes:
        cepa = ot.get("grape_varieties", {})
        cepa_code = cepa.get("code", "-") if cepa else "-"
        process = ot.get("winemaking_processes", {})
        process_name = process.get("name", "-") if process else "-"
        is_urgent = ot.get("priority") == "Urgente"

        border = "border-left: 4px solid #dc3545;" if is_urgent else "border-left: 4px solid #ffc107;"

        with st.container():
            st.markdown(f"""
            <div style="background:#fff;border-radius:8px;padding:15px;margin-bottom:10px;
                        box-shadow:0 1px 3px rgba(0,0,0,0.1);{border}">
                <div style="display:flex;justify-content:space-between;">
                    <strong style="font-size:1.1em;">OT #{ot.get('ot_number', '?')}</strong>
                    <span style="color:#666;">{ot.get('date', '-')}</span>
                </div>
                <div style="margin-top:8px;color:#555;">
                    Cepa: {cepa_code} | Operacion: {process_name} | Litros: {ot.get('liters', '-') or '-'}
                </div>
                {'<div style="margin-top:4px;"><span style="background:#dc3545;color:white;padding:2px 8px;border-radius:3px;font-size:0.8em;">URGENTE</span></div>' if is_urgent else ''}
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Iniciar OT #{ot.get('ot_number', '?')}", key=f"start_{ot['id']}", type="primary"):
                try:
                    queries.update_work_order_status(ot["id"], "En Proceso")
                    st.success(f"OT #{ot.get('ot_number')} iniciada")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# --- EJECUTAR OT EN PROCESO ---
if en_proceso:
    st.markdown("---")
    st.subheader("Completar OT en Proceso")

    for ot in en_proceso:
        ot_num = ot.get("ot_number", "?")
        cepa = ot.get("grape_varieties", {})
        cepa_code = cepa.get("code", "-") if cepa else "-"
        process = ot.get("winemaking_processes", {})
        process_name = process.get("name", "-") if process else "-"

        st.markdown(f"### OT #{ot_num} - {cepa_code} - {process_name}")

        # Cargar lineas
        try:
            lines = queries.get_work_order_lines(ot["id"])
        except Exception:
            lines = []

        if lines:
            st.markdown("**Insumos a utilizar:**")

            updated_lines = []
            for idx, line in enumerate(lines):
                supply_name = line.get("supplies", {}).get("name", "?") if line.get("supplies") else "?"
                supply_unit = line.get("supplies", {}).get("unit", "") if line.get("supplies") else ""
                planned = line.get("planned_quantity") or line.get("quantity", 0)

                col_ins, col_plan, col_real, col_lot = st.columns([3, 1.5, 1.5, 2.5])

                with col_ins:
                    st.markdown(f"**{supply_name}** ({supply_unit})")

                with col_plan:
                    st.markdown(f"Planificado: **{planned}**")

                with col_real:
                    real_qty = st.number_input(
                        f"Real", value=float(planned) if planned else 0.0,
                        min_value=0.0, step=0.1,
                        key=f"exec_qty_{ot['id']}_{line['id']}"
                    )

                with col_lot:
                    supply_id = line.get("supply_id")
                    if supply_id:
                        lots = get_lots_with_stock(supply_id)
                        lot_opts = {}
                        for lt in lots:
                            status_txt = ""
                            if lt.get("expiry_status") == "VENCIDO":
                                status_txt = " [VENCIDO]"
                            elif lt.get("expiry_status") == "POR VENCER":
                                status_txt = " [POR VENCER]"
                            lot_opts[lt["lot_id"]] = f"Lote {lt['lot_number']} ({lt['current_stock']:.1f}){status_txt}"

                        if lot_opts:
                            selected_lot = st.selectbox(
                                f"Lote", options=list(lot_opts.keys()),
                                format_func=lambda x: lot_opts[x],
                                index=None, placeholder="Seleccione lote...",
                                key=f"exec_lot_{ot['id']}_{line['id']}"
                            )
                        else:
                            selected_lot = None
                            st.warning("Sin stock")
                    else:
                        selected_lot = None

                updated_lines.append({
                    "line_id": line["id"],
                    "supply_id": supply_id,
                    "quantity": real_qty,
                    "lot_id": selected_lot,
                    "planned_quantity": planned,
                })

            # Observaciones
            obs = st.text_area(f"Observaciones (opcional):", key=f"exec_obs_{ot['id']}",
                              placeholder="Ej: Se ajusto dosis por alta turbidez...")

            col_complete, col_cancel = st.columns(2)

            with col_complete:
                if st.button(f"Completar OT #{ot_num}", type="primary", key=f"complete_{ot['id']}",
                            use_container_width=True):
                    # Validar stock
                    errors = []
                    for ul in updated_lines:
                        if ul["quantity"] > 0 and ul["lot_id"]:
                            ok, msg = check_availability(ul["supply_id"], ul["lot_id"], ul["quantity"])
                            if not ok:
                                errors.append(f"{ul['supply_id']}: {msg}")

                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        try:
                            # Actualizar cada linea con cantidad real y lote
                            for ul in updated_lines:
                                update_data = {"quantity": ul["quantity"]}
                                if ul["lot_id"]:
                                    update_data["lot_id"] = ul["lot_id"]
                                if ul["planned_quantity"]:
                                    update_data["planned_quantity"] = ul["planned_quantity"]
                                queries.update_work_order_line(ul["line_id"], update_data)

                            # Actualizar estado de la OT
                            queries.update_work_order_status(ot["id"], "Completada", obs)
                            st.success(f"OT #{ot_num} completada. Stock actualizado.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

            with col_cancel:
                if st.button(f"Devolver a Pendiente", key=f"return_{ot['id']}",
                            use_container_width=True):
                    try:
                        queries.update_work_order_status(ot["id"], "Pendiente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.info("Esta OT no tiene insumos asignados")

# --- Historial completadas ---
if completadas:
    st.markdown("---")
    with st.expander(f"Historial completadas ({len(completadas)})"):
        for ot in completadas[:10]:
            st.markdown(f"- **OT #{ot.get('ot_number')}** - {ot.get('date')} - Completada: {ot.get('completed_at', '-')[:10] if ot.get('completed_at') else '-'}")


def render_execution_card(ot, prefix):
    """Helper para renderizar cards - definida para evitar error"""
    pass
