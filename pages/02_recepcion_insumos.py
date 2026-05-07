import streamlit as st
import pandas as pd
from datetime import date
from lib import queries
from lib.auth import require_permission, has_permission

require_permission("recepcion_insumos", "ver")

st.title("Recepcion de Insumos")

@st.cache_data(ttl=300)
def load_data():
    return {
        "supplies": queries.get_supplies(),
        "suppliers": queries.get_suppliers(),
    }

try:
    ref = load_data()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

tab_con_oc, tab_sin_oc, tab_historial = st.tabs(["Recepcionar OC", "Sin OC (Directa)", "Historial"])

# =============================================================
# TAB: Recepcionar contra OC existente
# =============================================================
with tab_con_oc:
    st.subheader("Recepcionar contra Orden de Compra")

    try:
        ocs_insumos = queries.get_purchase_orders_unified(purchase_type="Insumos")
        ocs_pendientes = [o for o in ocs_insumos if o.get("status") in ("Aprobada", "Pedido", "Recibido Parcial")]
    except Exception:
        ocs_pendientes = []
        ocs_insumos = []

    if not ocs_pendientes:
        st.info("No hay OCs de insumos pendientes de recepcion. Cree una en Ordenes de Compra o use recepcion directa.")
    else:
        oc_options = {}
        for o in ocs_pendientes:
            supplier = (o.get("suppliers") or {}).get("name", "?")
            oc_options[o["id"]] = f"OC {o.get('oc_number') or o['id']} - {supplier} - {o.get('date', '')} ({o.get('status', '?')})"

        sel_oc = st.selectbox("Seleccione OC:", options=list(oc_options.keys()),
                               format_func=lambda x: oc_options[x],
                               index=None, placeholder="Seleccione...", key="rec_oc")

        if sel_oc:
            oc_data = next(o for o in ocs_pendientes if o["id"] == sel_oc)
            supplier = oc_data.get("suppliers")

            st.markdown(
                f'<div style="background:#f8f9fa;border-radius:8px;padding:12px;margin:10px 0;'
                f'border-left:4px solid #007bff;">'
                f'<strong>OC {oc_data.get("oc_number") or oc_data["id"]}</strong> | '
                f'Proveedor: {supplier.get("name", "-") if supplier else "-"} | '
                f'Fecha: {oc_data.get("date", "-")} | '
                f'Estado: {oc_data.get("status", "-")}'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Cargar lineas de la OC
            try:
                oc_lines = queries.get_po_supply_lines(sel_oc)
            except Exception:
                oc_lines = []

            if not oc_lines:
                st.warning("Esta OC no tiene lineas de insumos. Puede registrar la recepcion directamente abajo.")

            st.markdown("---")

            # Factura
            col_fac1, col_fac2 = st.columns(2)
            with col_fac1:
                rec_invoice = st.text_input("N Factura (si llega con factura)", key="rec_inv")
            with col_fac2:
                rec_invoice_date = st.date_input("Fecha Factura", value=date.today(), key="rec_inv_date")

            rec_date = st.date_input("Fecha Recepcion", value=date.today(), key="rec_date")

            # Lineas: mostrar lo pedido y pedir lo recibido
            st.subheader("Detalle de Recepcion")

            if oc_lines:
                st.markdown("**Insumos pedidos en la OC:**")

                reception_lines = []
                for idx, line in enumerate(oc_lines):
                    supply = line.get("supplies", {})
                    supply_name = supply.get("name", "?") if supply else "?"
                    supply_code = supply.get("code", "") if supply else ""
                    supply_unit = supply.get("unit", "") if supply else ""
                    ordered_qty = line.get("quantity", 0)

                    st.markdown(f"**{supply_code} - {supply_name}** | Pedido: **{ordered_qty} {supply_unit}**")

                    col_q, col_lot, col_exp = st.columns([2, 2, 2])
                    with col_q:
                        real_qty = st.number_input(
                            f"Cantidad recibida", value=float(ordered_qty),
                            min_value=0.0, step=0.1, key=f"rec_qty_{idx}"
                        )
                    with col_lot:
                        lot_num = st.text_input(f"N Lote", key=f"rec_lot_{idx}")
                    with col_exp:
                        exp_date = st.date_input(f"Vencimiento", value=None, key=f"rec_exp_{idx}")

                    reception_lines.append({
                        "supply_id": line.get("supply_id"),
                        "quantity": real_qty,
                        "lot_number": lot_num,
                        "expiry_date": exp_date,
                        "ordered_qty": ordered_qty,
                    })

            else:
                # OC sin lineas: permitir agregar insumos manualmente
                st.info("Agregue los insumos recibidos manualmente:")

                if "rec_manual_lines" not in st.session_state:
                    st.session_state.rec_manual_lines = [{"supply_id": None, "quantity": 0.0, "lot_number": "", "expiry_date": None}]

                supply_options = {s["id"]: f"{s['code']} - {s['name']} ({s['unit']})" for s in ref["supplies"]}

                def add_manual_line():
                    st.session_state.rec_manual_lines.append({"supply_id": None, "quantity": 0.0, "lot_number": "", "expiry_date": None})

                def remove_manual_line(idx):
                    if len(st.session_state.rec_manual_lines) > 1:
                        st.session_state.rec_manual_lines.pop(idx)

                reception_lines = []
                for i, ml in enumerate(st.session_state.rec_manual_lines):
                    col_s, col_q, col_l, col_e, col_d = st.columns([3, 1.5, 2, 2, 0.5])
                    with col_s:
                        sel = st.selectbox(f"Insumo {i+1}", options=list(supply_options.keys()),
                                            format_func=lambda x: supply_options[x],
                                            index=None, placeholder="Seleccione...", key=f"rec_ms_{i}")
                    with col_q:
                        qty = st.number_input(f"Cantidad", min_value=0.0, step=0.1, key=f"rec_mq_{i}")
                    with col_l:
                        lot = st.text_input(f"Lote", key=f"rec_ml_{i}")
                    with col_e:
                        exp = st.date_input(f"Vencimiento", value=None, key=f"rec_me_{i}")
                    with col_d:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if len(st.session_state.rec_manual_lines) > 1:
                            st.button("X", key=f"rec_mdel_{i}", on_click=remove_manual_line, args=(i,))

                    reception_lines.append({
                        "supply_id": sel,
                        "quantity": qty,
                        "lot_number": lot,
                        "expiry_date": exp,
                        "ordered_qty": 0,
                    })

                st.button("+ Agregar Insumo", on_click=add_manual_line, key="rec_add_manual")

            rec_notes = st.text_area("Observaciones", key="rec_notes", placeholder="Notas de la recepcion...")

            st.markdown("---")
            if st.button("Confirmar Recepcion", type="primary", use_container_width=True, key="save_rec_oc"):
                valid_lines = [l for l in reception_lines if l.get("supply_id") and l["quantity"] > 0]
                if not valid_lines:
                    st.error("Debe tener al menos un insumo con cantidad mayor a 0")
                else:
                    try:
                        # Crear lineas de recepcion (purchase_order_lines con movement_type Ingreso)
                        po_lines = []
                        for l in valid_lines:
                            lot_id = None
                            if l["lot_number"]:
                                try:
                                    lot_result = queries.create_lot(
                                        l["supply_id"], l["lot_number"],
                                        l["expiry_date"], initial_stock=0,
                                    )
                                    lot_id = lot_result[0]["id"]
                                except Exception:
                                    existing = queries.get_lots_by_supply(l["supply_id"])
                                    for ex in existing:
                                        if ex["lot_number"] == l["lot_number"]:
                                            lot_id = ex["id"]
                                            break

                            po_lines.append({
                                "purchase_order_id": sel_oc,
                                "supply_id": l["supply_id"],
                                "lot_id": lot_id,
                                "quantity": l["quantity"],
                                "movement_type": "Ingreso",
                            })

                        queries.create_purchase_order_lines(po_lines)

                        # Actualizar factura si se ingreso
                        update_data = {}
                        if rec_invoice:
                            update_data["invoice_number"] = rec_invoice
                            update_data["invoice_date"] = str(rec_invoice_date)

                        # Determinar estado
                        all_received = all(
                            l["quantity"] >= l["ordered_qty"]
                            for l in valid_lines if l["ordered_qty"] > 0
                        )
                        if all_received and oc_lines:
                            update_data["status"] = "Recibido"
                            if rec_invoice:
                                update_data["status"] = "Facturado"
                        else:
                            update_data["status"] = "Recibido Parcial"

                        if update_data:
                            queries.update_purchase_order(sel_oc, update_data)

                        st.success(f"Recepcion registrada ({len(valid_lines)} insumos)")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")


# =============================================================
# TAB: Recepcion directa (sin OC)
# =============================================================
with tab_sin_oc:
    if not has_permission("recepcion_insumos", "crear"):
        st.warning("No tiene permisos para crear recepciones")
    else:
        st.subheader("Recepcion Directa (sin OC)")
        st.caption("Para compras chicas o urgentes que no tienen OC previa")

        if "oc_lines_direct" not in st.session_state:
            st.session_state.oc_lines_direct = [{"supply_id": None, "lot_number": "", "expiry_date": None, "quantity": 0.0}]

        col1, col2, col3 = st.columns(3)
        with col1:
            d_date = st.date_input("Fecha", value=date.today(), key="d_date")
        with col2:
            d_oc = st.text_input("N OC (opcional)", key="d_oc")
        with col3:
            supp_options = {s["id"]: s["name"] for s in ref["suppliers"]}
            d_supplier = st.selectbox("Proveedor", options=list(supp_options.keys()),
                                       format_func=lambda x: supp_options[x],
                                       index=None, placeholder="Seleccione...", key="d_supplier")

        col_fi1, col_fi2 = st.columns(2)
        with col_fi1:
            d_invoice = st.text_input("N Factura (opcional)", key="d_invoice")
        with col_fi2:
            d_inv_date = st.date_input("Fecha Factura", value=date.today(), key="d_inv_date")

        st.markdown("---")
        st.subheader("Detalle de Insumos")

        supply_options = {s["id"]: f"{s['name']} ({s['unit']})" for s in ref["supplies"]}

        def add_direct_line():
            st.session_state.oc_lines_direct.append({"supply_id": None, "lot_number": "", "expiry_date": None, "quantity": 0.0})

        def remove_direct_line(idx):
            if len(st.session_state.oc_lines_direct) > 1:
                st.session_state.oc_lines_direct.pop(idx)

        for i, line in enumerate(st.session_state.oc_lines_direct):
            col_s, col_lot, col_exp, col_q, col_del = st.columns([3, 2, 2, 1.5, 0.5])

            with col_s:
                selected = st.selectbox(
                    f"Insumo {i+1}", options=list(supply_options.keys()),
                    format_func=lambda x: supply_options[x],
                    index=None, placeholder="Seleccione...", key=f"d_supply_{i}"
                )
                st.session_state.oc_lines_direct[i]["supply_id"] = selected

            with col_lot:
                lot_num = st.text_input(f"N Lote", key=f"d_lot_{i}")
                st.session_state.oc_lines_direct[i]["lot_number"] = lot_num

            with col_exp:
                exp_date = st.date_input(f"Vencimiento", value=None, key=f"d_exp_{i}")
                st.session_state.oc_lines_direct[i]["expiry_date"] = exp_date

            with col_q:
                qty = st.number_input(f"Cantidad", value=0.0, min_value=0.0, step=0.1, key=f"d_qty_{i}")
                st.session_state.oc_lines_direct[i]["quantity"] = qty

            with col_del:
                st.markdown("<br>", unsafe_allow_html=True)
                if len(st.session_state.oc_lines_direct) > 1:
                    st.button("X", key=f"d_del_{i}", on_click=remove_direct_line, args=(i,))

        st.button("+ Agregar Insumo", on_click=add_direct_line, key="d_add")

        st.markdown("---")
        if st.button("Guardar Recepcion", type="primary", use_container_width=True, key="save_direct"):
            valid_lines = [l for l in st.session_state.oc_lines_direct if l["supply_id"] and l["quantity"] > 0]

            if not valid_lines:
                st.error("Debe agregar al menos un insumo con cantidad mayor a 0")
            else:
                try:
                    po_data = {
                        "date": str(d_date),
                        "purchase_type": "Insumos",
                        "status": "Recibido",
                    }
                    if d_oc:
                        po_data["oc_number"] = d_oc
                    if d_supplier:
                        po_data["supplier_id"] = d_supplier
                    if d_invoice:
                        po_data["invoice_number"] = d_invoice
                        po_data["invoice_date"] = str(d_inv_date)
                        po_data["status"] = "Facturado"

                    result = queries.create_purchase_order(po_data)
                    po_id = result[0]["id"]

                    po_lines = []
                    for l in valid_lines:
                        lot_id = None
                        if l["lot_number"]:
                            try:
                                lot_result = queries.create_lot(
                                    l["supply_id"], l["lot_number"],
                                    l["expiry_date"], initial_stock=0,
                                )
                                lot_id = lot_result[0]["id"]
                            except Exception:
                                existing = queries.get_lots_by_supply(l["supply_id"])
                                for ex in existing:
                                    if ex["lot_number"] == l["lot_number"]:
                                        lot_id = ex["id"]
                                        break

                        po_lines.append({
                            "purchase_order_id": po_id,
                            "supply_id": l["supply_id"],
                            "lot_id": lot_id,
                            "quantity": l["quantity"],
                            "movement_type": "Ingreso",
                        })

                    queries.create_purchase_order_lines(po_lines)

                    st.success(f"Recepcion registrada ({len(valid_lines)} insumos)")
                    st.session_state.oc_lines_direct = [{"supply_id": None, "lot_number": "", "expiry_date": None, "quantity": 0.0}]
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")


# =============================================================
# TAB: Historial
# =============================================================
with tab_historial:
    st.subheader("Historial de Recepciones")

    try:
        recent = queries.get_purchase_orders_unified(purchase_type="Insumos", limit=50)
        received = [o for o in recent if o.get("status") in ("Recibido", "Recibido Parcial", "Facturado", "Cerrada")]
    except Exception:
        received = []

    if received:
        rows = []
        for o in received:
            supplier = o.get("suppliers")
            rows.append({
                "ID": o["id"],
                "Fecha": o.get("date", "-"),
                "N OC": o.get("oc_number") or "-",
                "Proveedor": supplier.get("name", "-") if supplier else "-",
                "Factura": o.get("invoice_number") or "-",
                "Estado": o.get("status", "-"),
            })

        df = pd.DataFrame(rows)

        def color_status(val):
            colors = {
                "Recibido": "background-color: #d4edda",
                "Recibido Parcial": "background-color: #fff3cd",
                "Facturado": "background-color: #cce5ff",
                "Cerrada": "background-color: #e2e3e5",
            }
            return colors.get(val, "")

        st.dataframe(
            df.style.map(color_status, subset=["Estado"]),
            use_container_width=True, hide_index=True, height=400,
        )

        # Ver detalle de una recepcion
        rec_options = {o["id"]: f"OC {o.get('oc_number') or o['id']} - {o.get('date', '')}" for o in received}
        sel_rec = st.selectbox("Ver detalle:", options=list(rec_options.keys()),
                                format_func=lambda x: rec_options[x],
                                index=None, placeholder="Seleccione...", key="hist_detail")

        if sel_rec:
            try:
                lines = queries.get_po_supply_lines(sel_rec)
                if lines:
                    detail_rows = []
                    for l in lines:
                        supply = l.get("supplies")
                        detail_rows.append({
                            "Insumo": supply.get("name", "?") if supply else "?",
                            "Codigo": supply.get("code", "-") if supply else "-",
                            "Cantidad": l.get("quantity", 0),
                            "Unidad": supply.get("unit", "") if supply else "",
                        })
                    st.dataframe(pd.DataFrame(detail_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("Sin detalle de insumos")
            except Exception as e:
                st.warning(f"Error: {e}")
    else:
        st.info("No hay recepciones registradas")
