import streamlit as st
import pandas as pd
from datetime import datetime
from lib import queries
from lib.auth import get_current_user, has_permission
from lib.stock_engine import get_lots_with_stock, check_availability

st.title("Ejecutar Orden de Trabajo")

user = get_current_user()
worker_id = user.get("worker_id") if user else None
is_supervisor = has_permission("ordenes_trabajo", "crear")

@st.cache_data(ttl=120)
def load_workers():
    return queries.get_workers()

@st.cache_data(ttl=60)
def load_tanks():
    return {t["id"]: t["code"] for t in queries.get_tanks()}

try:
    workers = load_workers()
    tank_codes = load_tanks()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

worker_options = {w["id"]: w["full_name"] for w in workers}


def get_tank(tank_id):
    return tank_codes.get(tank_id, "-") if tank_id else "-"


if worker_id:
    selected_worker_id = worker_id
    operator_name = worker_options.get(worker_id, user.get("full_name", "?"))
    st.markdown(f"**Operario:** {operator_name}")
elif is_supervisor:
    st.markdown("**Vista supervisor** - Seleccione operario para ver sus OTs")
    selected_worker_id = st.selectbox(
        "Operario:",
        options=list(worker_options.keys()),
        format_func=lambda x: worker_options[x],
        index=None,
        placeholder="Seleccione operario..."
    )
    if not selected_worker_id:
        st.info("Seleccione un operario para ver sus OTs asignadas")
        st.stop()
    operator_name = worker_options.get(selected_worker_id, "?")
else:
    st.warning("Su usuario no esta vinculado a un operario. Contacte al administrador.")
    st.stop()

st.markdown("---")

try:
    my_ots = queries.get_work_orders_by_worker(selected_worker_id)
except Exception as e:
    st.error(f"Error: {e}")
    my_ots = []

pendientes = [ot for ot in my_ots if ot.get("status") == "Pendiente"]
en_proceso = [ot for ot in my_ots if ot.get("status") == "En Proceso"]
completadas = [ot for ot in my_ots if ot.get("status") == "Completada"]

col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Pendientes", len(pendientes))
col_m2.metric("En Proceso", len(en_proceso))
col_m3.metric("Completadas hoy", len([ot for ot in completadas
              if ot.get("completed_at", "")[:10] == str(datetime.now().date())]))


# ============================================================
# OTs EN PROCESO — INSTRUCCIONES CLARAS PARA COMPLETAR
# ============================================================
if en_proceso:
    st.markdown("---")
    for ot in en_proceso:
        ot_num = ot.get("ot_number", "?")
        ot_type = ot.get("ot_type", "Insumos")
        ot_date = ot.get("date", "-")
        cepa = (ot.get("grape_varieties") or {})
        cepa_code = cepa.get("code", "-") if cepa else "-"
        cepa_name = cepa.get("name", "") if cepa else ""
        process = (ot.get("winemaking_processes") or {})
        process_name = process.get("name", "-") if process else "-"
        wine = (ot.get("wines") or {})
        wine_code = wine.get("code", "-") if wine else "-"
        linea = (ot.get("product_lines") or {})
        linea_name = linea.get("name", "-") if linea else "-"
        liters = ot.get("liters") or "-"
        src_tank = get_tank(ot.get("source_tank_id"))
        dst_tank = get_tank(ot.get("dest_tank_id"))
        observations = ot.get("observations") or ""

        type_color = "#2563eb" if ot_type == "Insumos" else "#059669"
        type_icon = "&#128230;" if ot_type == "Insumos" else "&#127858;"

        # --- CABECERA DE LA OT ---
        st.markdown(f"""
        <div style="background:linear-gradient(135deg, #eff6ff, #ffffff);border-radius:12px;
                    padding:20px 24px;border:2px solid {type_color};margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <div>
                    <span style="font-size:1.4rem;font-weight:700;color:#1e1e2f;">OT #{ot_num}</span>
                    <span style="background:{type_color};color:white;padding:4px 12px;border-radius:20px;
                          font-size:0.8rem;font-weight:600;margin-left:10px;">{type_icon} {ot_type.upper()}</span>
                    <span style="background:#dbeafe;color:#1e40af;padding:4px 10px;border-radius:20px;
                          font-size:0.8rem;font-weight:600;margin-left:6px;">EN PROCESO</span>
                </div>
                <span style="color:#6b7280;font-size:0.9rem;">{ot_date}</span>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;
                        background:white;border-radius:8px;padding:14px;border:1px solid #e5e7eb;">
                <div>
                    <div style="color:#6b7280;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;">Vino</div>
                    <div style="font-weight:700;font-size:1rem;color:#1e1e2f;">{wine_code}</div>
                </div>
                <div>
                    <div style="color:#6b7280;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;">Cepa</div>
                    <div style="font-weight:600;color:#1e1e2f;">{cepa_code} - {cepa_name}</div>
                </div>
                <div>
                    <div style="color:#6b7280;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.05em;">Linea</div>
                    <div style="font-weight:600;color:#1e1e2f;">{linea_name}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- INSTRUCCIONES SEGUN TIPO ---
        if ot_type == "Movimiento":
            st.markdown(f"""
            <div style="background:#f0fdf4;border-radius:10px;padding:20px;border:1px solid #bbf7d0;margin-bottom:16px;">
                <div style="font-weight:700;font-size:1.1rem;color:#166534;margin-bottom:12px;">
                    INSTRUCCIONES DE MOVIMIENTO
                </div>
                <div style="display:flex;align-items:center;gap:20px;margin-bottom:16px;">
                    <div style="background:white;border-radius:10px;padding:16px 24px;text-align:center;
                                border:2px solid #059669;flex:1;">
                        <div style="color:#6b7280;font-size:0.75rem;text-transform:uppercase;">DESDE</div>
                        <div style="font-size:1.6rem;font-weight:800;color:#059669;">Cuba {src_tank}</div>
                    </div>
                    <div style="font-size:2rem;color:#059669;">&#10132;</div>
                    <div style="background:white;border-radius:10px;padding:16px 24px;text-align:center;
                                border:2px solid #2563eb;flex:1;">
                        <div style="color:#6b7280;font-size:0.75rem;text-transform:uppercase;">HACIA</div>
                        <div style="font-size:1.6rem;font-weight:800;color:#2563eb;">Cuba {dst_tank}</div>
                    </div>
                </div>
                <div style="background:white;border-radius:8px;padding:12px 16px;text-align:center;
                            border:1px solid #bbf7d0;">
                    <span style="color:#6b7280;font-size:0.75rem;text-transform:uppercase;">LITROS A TRASPASAR</span><br>
                    <span style="font-size:2rem;font-weight:800;color:#1e1e2f;">{liters} L</span>
                </div>
                <div style="margin-top:14px;padding:10px 14px;background:#fefce8;border-radius:6px;border:1px solid #fde68a;">
                    <div style="font-weight:600;color:#92400e;font-size:0.85rem;">PASOS:</div>
                    <ol style="margin:6px 0 0 0;padding-left:20px;color:#1e1e2f;font-size:0.9rem;line-height:1.8;">
                        <li>Dirigirse a <strong>Cuba {src_tank}</strong></li>
                        <li>Conectar manguera hacia <strong>Cuba {dst_tank}</strong></li>
                        <li>Traspasar <strong>{liters} litros</strong></li>
                        <li>Verificar niveles en ambas cubas</li>
                        <li>Volver aqui y presionar <strong>"Completar OT"</strong></li>
                    </ol>
                </div>
                {"<div style='margin-top:10px;padding:8px 12px;background:#fef2f2;border-radius:6px;border:1px solid #fecaca;font-size:0.88rem;'><strong>Nota:</strong> " + observations + "</div>" if observations else ""}
            </div>
            """, unsafe_allow_html=True)

        else:
            st.markdown(f"""
            <div style="background:#eff6ff;border-radius:10px;padding:20px;border:1px solid #bfdbfe;margin-bottom:4px;">
                <div style="font-weight:700;font-size:1.1rem;color:#1e40af;margin-bottom:12px;">
                    INSTRUCCIONES DE APLICACION DE INSUMOS
                </div>
                <div style="display:flex;gap:16px;margin-bottom:14px;">
                    <div style="background:white;border-radius:8px;padding:14px 20px;text-align:center;
                                border:2px solid #2563eb;flex:1;">
                        <div style="color:#6b7280;font-size:0.75rem;text-transform:uppercase;">Operacion</div>
                        <div style="font-size:1.2rem;font-weight:700;color:#2563eb;">{process_name}</div>
                    </div>
                    {"<div style='background:white;border-radius:8px;padding:14px 20px;text-align:center;border:2px solid #059669;flex:1;'><div style=color:#6b7280;font-size:0.75rem;text-transform:uppercase;>Cuba</div><div style=font-size:1.4rem;font-weight:800;color:#059669;>Cuba " + src_tank + "</div></div>" if src_tank != "-" else ""}
                    {"<div style='background:white;border-radius:8px;padding:14px 20px;text-align:center;border:1px solid #e5e7eb;flex:1;'><div style=color:#6b7280;font-size:0.75rem;text-transform:uppercase;>Litros</div><div style=font-size:1.4rem;font-weight:700;color:#1e1e2f;>" + str(liters) + " L</div></div>" if liters != "-" else ""}
                </div>
                <div style="padding:10px 14px;background:#fefce8;border-radius:6px;border:1px solid #fde68a;">
                    <div style="font-weight:600;color:#92400e;font-size:0.85rem;">PASOS:</div>
                    <ol style="margin:6px 0 0 0;padding-left:20px;color:#1e1e2f;font-size:0.9rem;line-height:1.8;">
                        <li>Buscar los insumos indicados abajo en bodega</li>
                        <li>Verificar los lotes y cantidades</li>
                        <li>{"Dirigirse a <strong>Cuba " + src_tank + "</strong> y aplicar" if src_tank != "-" else "Aplicar los insumos segun la operacion"}</li>
                        <li>Registrar las cantidades reales utilizadas abajo</li>
                        <li>Seleccionar el lote de cada insumo</li>
                        <li>Presionar <strong>"Completar OT"</strong></li>
                    </ol>
                </div>
                {"<div style='margin-top:10px;padding:8px 12px;background:#fef2f2;border-radius:6px;border:1px solid #fecaca;font-size:0.88rem;'><strong>Nota:</strong> " + observations + "</div>" if observations else ""}
            </div>
            """, unsafe_allow_html=True)

        # --- FORMULARIO DE INSUMOS ---
        try:
            lines = queries.get_work_order_lines(ot["id"])
        except Exception:
            lines = []

        updated_lines = []
        if lines:
            st.markdown(f"""
            <div style="background:#fff;border-radius:8px;padding:12px 16px;border:1px solid #e5e7eb;margin-bottom:8px;">
                <div style="font-weight:600;color:#1e1e2f;font-size:0.95rem;">
                    Insumos a utilizar ({len(lines)})
                </div>
            </div>
            """, unsafe_allow_html=True)

            for idx, line in enumerate(lines):
                supply = line.get("supplies") or {}
                supply_name = supply.get("name", "?")
                supply_unit = supply.get("unit", "")
                planned = line.get("planned_quantity") or line.get("quantity", 0)

                st.markdown(f"""
                <div style="background:#f9fafb;border-radius:8px;padding:10px 14px;margin:6px 0;
                            border-left:3px solid #2563eb;">
                    <span style="font-weight:700;color:#1e1e2f;font-size:1rem;">{idx+1}. {supply_name}</span>
                    <span style="color:#6b7280;font-size:0.85rem;margin-left:8px;">
                        Usar <strong style="color:#2563eb;">{planned} {supply_unit}</strong>
                    </span>
                </div>
                """, unsafe_allow_html=True)

                col_real, col_lot = st.columns([1, 2])

                with col_real:
                    real_qty = st.number_input(
                        f"Cantidad real ({supply_unit})",
                        value=float(planned) if planned else 0.0,
                        min_value=0.0, step=0.1,
                        key=f"exec_qty_{ot['id']}_{line['id']}"
                    )

                with col_lot:
                    supply_id = line.get("supply_id")
                    selected_lot = None
                    if supply_id:
                        lots = get_lots_with_stock(supply_id)
                        lot_opts = {}
                        for lt in lots:
                            stock = lt.get("current_stock", 0)
                            status_txt = ""
                            if lt.get("expiry_status") == "VENCIDO":
                                status_txt = " [VENCIDO]"
                            elif lt.get("expiry_status") == "POR VENCER":
                                status_txt = " [POR VENCER]"
                            lot_opts[lt["lot_id"]] = f"Lote {lt['lot_number']} — Stock: {stock:.1f} {supply_unit}{status_txt}"

                        if lot_opts:
                            selected_lot = st.selectbox(
                                "Seleccionar lote",
                                options=list(lot_opts.keys()),
                                format_func=lambda x, lo=lot_opts: lo[x],
                                index=None, placeholder="Seleccione el lote a utilizar...",
                                key=f"exec_lot_{ot['id']}_{line['id']}"
                            )
                        else:
                            st.error(f"SIN STOCK de {supply_name}")

                updated_lines.append({
                    "line_id": line["id"],
                    "supply_id": supply_id,
                    "quantity": real_qty,
                    "lot_id": selected_lot,
                    "planned_quantity": planned,
                })

        st.markdown("")
        obs = st.text_area("Observaciones del operario:",
                          key=f"exec_obs_{ot['id']}",
                          placeholder="Ej: Se ajusto dosis, se derramo un poco, cuba tenia sedimento...")

        st.markdown("")
        col_complete, col_cancel = st.columns(2)

        with col_complete:
            if st.button(f"Completar OT #{ot_num}", type="primary", key=f"complete_{ot['id']}",
                        use_container_width=True):
                errors = []

                if ot_type == "Insumos" and updated_lines:
                    for ul in updated_lines:
                        if ul["quantity"] > 0 and not ul["lot_id"]:
                            sup = next((l.get("supplies", {}).get("name", "?") for l in lines
                                       if l["id"] == ul["line_id"]), "?")
                            errors.append(f"Debe seleccionar lote para: {sup}")
                        elif ul["quantity"] > 0 and ul["lot_id"]:
                            ok, msg = check_availability(ul["supply_id"], ul["lot_id"], ul["quantity"])
                            if not ok:
                                errors.append(msg)

                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    try:
                        for ul in updated_lines:
                            update_data = {"quantity": ul["quantity"]}
                            if ul["lot_id"]:
                                update_data["lot_id"] = ul["lot_id"]
                            if ul["planned_quantity"]:
                                update_data["planned_quantity"] = ul["planned_quantity"]
                            queries.update_work_order_line(ul["line_id"], update_data)

                        queries.update_work_order_status(ot["id"], "Completada", obs)
                        st.success(f"OT #{ot_num} completada exitosamente")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

        with col_cancel:
            if st.button("Devolver a Pendiente", key=f"return_{ot['id']}",
                        use_container_width=True):
                try:
                    queries.update_work_order_status(ot["id"], "Pendiente")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("---")


# ============================================================
# OTs PENDIENTES — TARJETAS CON RESUMEN CLARO
# ============================================================
st.subheader("Pendientes")
if not pendientes:
    st.success("No tiene OTs pendientes")
else:
    pendientes.sort(key=lambda x: (0 if x.get("priority") == "Urgente" else 1, x.get("date", "")))

    for ot in pendientes:
        ot_num = ot.get("ot_number", "?")
        ot_type = ot.get("ot_type", "Insumos")
        cepa = (ot.get("grape_varieties") or {})
        cepa_code = cepa.get("code", "-") if cepa else "-"
        process = (ot.get("winemaking_processes") or {})
        process_name = process.get("name", "-") if process else "-"
        wine = (ot.get("wines") or {})
        wine_code = wine.get("code", "-") if wine else "-"
        is_urgent = ot.get("priority") == "Urgente"
        liters = ot.get("liters") or "-"
        src_tank = get_tank(ot.get("source_tank_id"))
        dst_tank = get_tank(ot.get("dest_tank_id"))
        type_color = "#2563eb" if ot_type == "Insumos" else "#059669"

        border = "border-left: 4px solid #dc2626;" if is_urgent else f"border-left: 4px solid {type_color};"

        if ot_type == "Movimiento":
            task_desc = f"Traspasar <strong>{liters} L</strong> de <strong>Cuba {src_tank}</strong> a <strong>Cuba {dst_tank}</strong>"
        else:
            task_desc = f"Aplicar <strong>{process_name}</strong> en <strong>Cuba {src_tank}</strong>" if src_tank != "-" else f"Aplicar <strong>{process_name}</strong>"

        with st.container():
            st.markdown(f"""
            <div style="background:#fff;border-radius:10px;padding:16px 20px;margin-bottom:10px;
                        box-shadow:0 1px 3px rgba(0,0,0,0.08);{border}">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span style="font-size:1.1rem;font-weight:700;color:#1e1e2f;">OT #{ot_num}</span>
                        <span style="background:{type_color};color:white;padding:3px 10px;border-radius:20px;
                              font-size:0.75rem;font-weight:600;margin-left:8px;">{ot_type.upper()}</span>
                        {'<span style="background:#dc2626;color:white;padding:3px 10px;border-radius:20px;font-size:0.75rem;font-weight:600;margin-left:4px;">URGENTE</span>' if is_urgent else ''}
                    </div>
                    <span style="color:#6b7280;font-size:0.85rem;">{ot.get('date', '-')}</span>
                </div>
                <div style="margin-top:10px;font-size:0.92rem;color:#374151;">
                    <div><strong>Vino:</strong> {wine_code} | <strong>Cepa:</strong> {cepa_code}</div>
                    <div style="margin-top:4px;padding:6px 10px;background:#f5f6fa;border-radius:6px;">
                        {task_desc}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            can_execute = worker_id or has_permission("ejecutar_ot", "ejecutar")
            if can_execute:
                if st.button(f"Iniciar OT #{ot_num}", key=f"start_{ot['id']}", type="primary"):
                    try:
                        queries.update_work_order_status(ot["id"], "En Proceso")
                        st.success(f"OT #{ot_num} iniciada")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# ============================================================
# HISTORIAL COMPLETADAS
# ============================================================
if completadas:
    st.markdown("---")
    with st.expander(f"Historial completadas ({len(completadas)})"):
        for ot in completadas[:10]:
            ot_type = ot.get("ot_type", "Insumos")
            completed = ot.get("completed_at", "-")[:10] if ot.get("completed_at") else "-"
            process = (ot.get("winemaking_processes") or {}).get("name", "-")
            wine = (ot.get("wines") or {}).get("code", "-")
            st.markdown(
                f"- **OT #{ot.get('ot_number')}** [{ot_type}] — {wine} — {process} — Completada: {completed}"
            )
