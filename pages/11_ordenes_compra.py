import streamlit as st
import pandas as pd
from datetime import date
from lib import queries
from lib.auth import require_permission, has_permission, get_current_user
from lib.pdf_generator import generate_oc_pdf

require_permission("recepcion_insumos", "ver")

st.title("Ordenes de Compra")

PURCHASE_TYPES = ["Insumos", "Vino", "Uva"]
STATUSES_INSUMOS = ["Borrador", "Aprobada Enologia", "Aprobada", "Pedido", "Recibido Parcial", "Recibido", "Facturado", "Cerrada"]
STATUSES_VINO = ["Borrador", "Aprobada Enologia", "Aprobada", "Pedido", "En Despacho", "Despachado", "Facturado", "DO Recibida", "Aceptada"]
STATUSES_UVA = ["Borrador", "Aprobada Enologia", "Aprobada", "Pedido", "En Despacho", "Despachado", "Facturado", "Cerrada"]

STATUS_COLORS = {
    "Borrador": "#adb5bd",
    "Aprobada Enologia": "#6f42c1",
    "Aprobada": "#20c997",
    "Rechazada": "#dc3545",
    "Pedido": "#6c757d",
    "En Despacho": "#007bff",
    "Recibido Parcial": "#17a2b8",
    "Despachado": "#17a2b8",
    "Recibido": "#28a745",
    "Facturado": "#ffc107",
    "DO Recibida": "#fd7e14",
    "Aceptada": "#28a745",
    "Cerrada": "#28a745",
    "Anulada": "#6c757d",
}

@st.cache_data(ttl=300)
def load_ref():
    return {
        "suppliers": queries.get_suppliers(),
        "grape_varieties": queries.get_grape_varieties(),
        "product_lines": queries.get_product_lines(),
        "tanks": queries.get_tanks(),
        "supplies": queries.get_supplies(),
    }

try:
    ref = load_ref()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

tab_lista, tab_nueva, tab_aprobar, tab_detalle = st.tabs(["Listado", "Nueva OC", "Aprobaciones", "Detalle / Recepciones"])

# =============================================================
# TAB: Listado
# =============================================================
with tab_lista:
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_type = st.selectbox("Tipo:", ["Todos"] + PURCHASE_TYPES, key="oc_ftype")
    with col_f2:
        all_statuses = list(set(STATUSES_INSUMOS + STATUSES_VINO + STATUSES_UVA))
        filter_status = st.selectbox("Estado:", ["Todos"] + sorted(all_statuses), key="oc_fstatus")
    with col_f3:
        filter_search = st.text_input("Buscar:", placeholder="Proveedor, OC...", key="oc_fsearch")

    try:
        ocs = queries.get_purchase_orders_unified(
            purchase_type=filter_type if filter_type != "Todos" else None,
            status=filter_status if filter_status != "Todos" else None,
        )
    except Exception:
        ocs = []

    if filter_search:
        s = filter_search.lower()
        ocs = [o for o in ocs if
               s in str(o.get("oc_number", "")).lower() or
               s in str((o.get("suppliers") or {}).get("name", "")).lower()]

    # Metricas
    active = [o for o in ocs if o.get("status") not in ("Cerrada", "Aceptada")]
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("OCs activas", len(active))
    col_m2.metric("Total", len(ocs))
    col_m3.metric("Tipos", ", ".join(set(o.get("purchase_type", "?") for o in ocs)) if ocs else "-")

    if ocs:
        rows = []
        for o in ocs:
            supplier = o.get("suppliers")
            cepa = o.get("grape_varieties")
            rows.append({
                "ID": o["id"],
                "Fecha": o.get("date", "-"),
                "N OC": o.get("oc_number") or "-",
                "Tipo": o.get("purchase_type", "-"),
                "Proveedor": supplier.get("name", "-") if supplier else "-",
                "Cepa": cepa.get("code", "-") if cepa else "-",
                "Estado": o.get("status", "-"),
                "Factura": o.get("invoice_number") or "-",
            })

        df = pd.DataFrame(rows)

        def color_status(val):
            c = STATUS_COLORS.get(val, "")
            return f"background-color: {c}; color: white" if c else ""

        st.dataframe(
            df.style.map(color_status, subset=["Estado"]),
            use_container_width=True, hide_index=True, height=500,
        )
    else:
        st.info("Sin ordenes de compra")

# =============================================================
# TAB: Nueva OC
# =============================================================
with tab_nueva:
    # PDF de OC recien creada
    if "last_created_oc" in st.session_state:
        _oc_id = st.session_state.last_created_oc
        try:
            _oc_data = queries.get_purchase_order_by_id(_oc_id)
            _oc_lines = []
            if _oc_data.get("purchase_type") == "Insumos":
                _oc_lines = queries.get_po_supply_lines(_oc_id)
            _pdf = generate_oc_pdf(_oc_data, lines=_oc_lines, logo_path="logo_vda.png")
            st.success(f"OC {_oc_data.get('oc_number') or _oc_id} creada exitosamente")
            col_ocpdf, col_ocnew = st.columns(2)
            with col_ocpdf:
                st.download_button(
                    "Descargar PDF",
                    data=_pdf,
                    file_name=f"OC_{_oc_data.get('oc_number') or _oc_id}.pdf",
                    mime="application/pdf",
                    key="new_oc_pdf",
                )
            with col_ocnew:
                if st.button("Crear otra OC", key="close_oc_success"):
                    del st.session_state["last_created_oc"]
                    st.rerun()
        except Exception:
            del st.session_state["last_created_oc"]
        st.markdown("---")

    can_create = has_permission("recepcion_insumos", "crear") or has_permission("recepcion_vino", "crear")
    if not can_create:
        st.warning("No tiene permisos para crear OC")
    else:
        oc_type = st.radio("Tipo de compra:", PURCHASE_TYPES, horizontal=True, key="oc_type")

        st.markdown("---")

        # Cabecera comun
        col1, col2, col3 = st.columns(3)
        with col1:
            oc_date = st.date_input("Fecha", value=date.today(), key="oc_date")
        with col2:
            oc_number = st.text_input("N OC", key="oc_number")
        with col3:
            supp_options = {s["id"]: s["name"] for s in ref["suppliers"]}
            oc_supplier = st.selectbox("Proveedor", options=list(supp_options.keys()),
                                        format_func=lambda x: supp_options[x],
                                        index=None, placeholder="Seleccione...", key="oc_supplier")

        # Campos segun tipo
        if oc_type == "Vino":
            st.subheader("Datos del Vino")
            col_v1, col_v2, col_v3 = st.columns(3)
            with col_v1:
                cepa_options = {g["id"]: f"{g['code']} - {g['name']}" for g in ref["grape_varieties"]}
                oc_cepa = st.selectbox("Cepa", options=list(cepa_options.keys()),
                                        format_func=lambda x: cepa_options[x],
                                        index=None, placeholder="Seleccione...", key="oc_cepa")
            with col_v2:
                line_options = {p["id"]: p["name"] for p in ref["product_lines"]}
                oc_line = st.selectbox("Linea", options=list(line_options.keys()),
                                        format_func=lambda x: line_options[x],
                                        index=None, placeholder="Seleccione...", key="oc_line")
            with col_v3:
                oc_wine_type = st.selectbox("Tipo vino", ["Tinto", "Blanco", "Rosado"], key="oc_wtype")

            col_p1, col_p2, col_p3, col_p4 = st.columns(4)
            with col_p1:
                oc_liters = st.number_input("Litros esperados", min_value=0, step=100, key="oc_liters")
            with col_p2:
                oc_ppl = st.number_input("Precio/litro", min_value=0.0, step=0.01, key="oc_ppl")
            with col_p3:
                oc_total = st.number_input("Precio total", min_value=0.0, step=100.0, key="oc_total")
            with col_p4:
                oc_currency = st.selectbox("Moneda", ["CLP", "USD", "EUR"], key="oc_currency")

        elif oc_type == "Uva":
            st.subheader("Datos de la Uva")
            col_u1, col_u2, col_u3 = st.columns(3)
            with col_u1:
                cepa_options = {g["id"]: f"{g['code']} - {g['name']}" for g in ref["grape_varieties"]}
                oc_cepa = st.selectbox("Cepa", options=list(cepa_options.keys()),
                                        format_func=lambda x: cepa_options[x],
                                        index=None, placeholder="Seleccione...", key="oc_cepa_u")
            with col_u2:
                oc_kilos = st.number_input("Kilos esperados", min_value=0.0, step=100.0, key="oc_kilos")
            with col_u3:
                oc_currency = st.selectbox("Moneda", ["CLP", "USD", "EUR"], key="oc_currency_u")

            col_pu1, col_pu2 = st.columns(2)
            with col_pu1:
                oc_ppk = st.number_input("Precio/kilo", min_value=0.0, step=0.01, key="oc_ppk")
            with col_pu2:
                oc_total = st.number_input("Precio total", min_value=0.0, step=100.0, key="oc_total_u")

        elif oc_type == "Insumos":
            st.subheader("Insumos a Comprar")

            if "oc_insumo_lines" not in st.session_state:
                st.session_state.oc_insumo_lines = [{"supply_id": None, "quantity": 0.0}]

            supply_options = {s["id"]: f"{s['code']} - {s['name']} ({s['unit']})" for s in ref["supplies"]}

            def add_insumo_line():
                st.session_state.oc_insumo_lines.append({"supply_id": None, "quantity": 0.0})

            def remove_insumo_line(idx):
                if len(st.session_state.oc_insumo_lines) > 1:
                    st.session_state.oc_insumo_lines.pop(idx)

            for i, line in enumerate(st.session_state.oc_insumo_lines):
                col_s, col_q, col_del = st.columns([4, 2, 0.5])
                with col_s:
                    sel = st.selectbox(f"Insumo {i+1}", options=list(supply_options.keys()),
                                        format_func=lambda x: supply_options[x],
                                        index=None, placeholder="Seleccione...",
                                        key=f"oc_ins_{i}")
                    st.session_state.oc_insumo_lines[i]["supply_id"] = sel
                with col_q:
                    qty = st.number_input(f"Cantidad {i+1}", min_value=0.0, step=0.1, key=f"oc_insq_{i}")
                    st.session_state.oc_insumo_lines[i]["quantity"] = qty
                with col_del:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if len(st.session_state.oc_insumo_lines) > 1:
                        st.button("X", key=f"oc_insdel_{i}", on_click=remove_insumo_line, args=(i,))

            st.button("+ Agregar Insumo", on_click=add_insumo_line)

            col_pi1, col_pi2 = st.columns(2)
            with col_pi1:
                oc_total = st.number_input("Precio total OC", min_value=0.0, step=100.0, key="oc_total_i")
            with col_pi2:
                oc_currency = st.selectbox("Moneda", ["CLP", "USD", "EUR"], key="oc_currency_i")

        oc_notes = st.text_area("Notas", key="oc_notes")

        st.markdown("---")
        if st.button("Crear Orden de Compra", type="primary", use_container_width=True):
            if not oc_supplier:
                st.error("Debe seleccionar un proveedor")
            else:
                try:
                    user = get_current_user()
                    can_approve = has_permission("aprobar_oc", "aprobar_admin")
                    initial_status = "Aprobada" if can_approve else "Borrador"

                    data = {
                        "date": str(oc_date),
                        "supplier_id": oc_supplier,
                        "purchase_type": oc_type,
                        "status": initial_status,
                        "created_by": user["id"] if user else None,
                    }
                    if oc_number:
                        data["oc_number"] = oc_number
                    if oc_notes:
                        data["notes"] = oc_notes

                    if oc_type == "Vino":
                        if oc_cepa:
                            data["grape_variety_id"] = oc_cepa
                        if oc_line:
                            data["product_line_id"] = oc_line
                        if oc_wine_type:
                            data["wine_type"] = oc_wine_type
                        if oc_liters > 0:
                            data["expected_liters"] = oc_liters
                        if oc_ppl > 0:
                            data["price_per_liter"] = oc_ppl
                        if oc_total > 0:
                            data["total_price"] = oc_total
                        data["currency"] = oc_currency

                    elif oc_type == "Uva":
                        if oc_cepa:
                            data["grape_variety_id"] = oc_cepa
                        if oc_kilos > 0:
                            data["expected_kilos"] = oc_kilos
                        if oc_ppk > 0:
                            data["price_per_kilo"] = oc_ppk
                        if oc_total > 0:
                            data["total_price"] = oc_total
                        data["currency"] = oc_currency

                    elif oc_type == "Insumos":
                        if oc_total > 0:
                            data["total_price"] = oc_total
                        data["currency"] = oc_currency

                    result = queries.create_purchase_order(data)
                    po_id = result[0]["id"]

                    if oc_type == "Insumos":
                        valid_lines = [l for l in st.session_state.oc_insumo_lines
                                       if l["supply_id"] and l["quantity"] > 0]
                        if valid_lines:
                            lines = [{
                                "purchase_order_id": po_id,
                                "supply_id": l["supply_id"],
                                "quantity": l["quantity"],
                                "movement_type": "Ingreso",
                            } for l in valid_lines]
                            queries.create_purchase_order_lines(lines)

                    st.session_state.last_created_oc = po_id
                    st.session_state.oc_insumo_lines = [{"supply_id": None, "quantity": 0.0}]
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# =============================================================
# TAB: Aprobaciones
# =============================================================
with tab_aprobar:
    can_approve_eno = has_permission("aprobar_oc", "aprobar_enologia")
    can_approve_admin = has_permission("aprobar_oc", "aprobar_admin")

    if not can_approve_eno and not can_approve_admin:
        st.info("No tiene permisos de aprobacion. Las OC que cree pasaran por el flujo de aprobacion.")
    else:
        st.subheader("OC Pendientes de Aprobacion")

        try:
            all_for_approval = queries.get_purchase_orders_unified(limit=200)
        except Exception:
            all_for_approval = []

        # Filtrar segun rol
        pending_approval = []
        for o in all_for_approval:
            s = o.get("status", "")
            if s == "Borrador" and can_approve_eno:
                pending_approval.append(o)
            elif s == "Aprobada Enologia" and can_approve_admin:
                pending_approval.append(o)

        if not pending_approval:
            st.success("No hay OC pendientes de su aprobacion")
        else:
            for oc in pending_approval:
                supplier = (oc.get("suppliers") or {}).get("name", "?")
                cepa = oc.get("grape_varieties")
                cepa_txt = cepa.get("code", "") if cepa else ""
                status = oc.get("status", "?")
                color = STATUS_COLORS.get(status, "#999")

                oc_label = f"OC {oc.get('oc_number') or oc['id']}"
                type_label = oc.get("purchase_type", "?")

                st.markdown(
                    f'<div style="background:#fff;border-radius:8px;padding:15px;margin-bottom:10px;'
                    f'box-shadow:0 1px 3px rgba(0,0,0,0.1);border-left:4px solid {color};">'
                    f'<div style="display:flex;justify-content:space-between;">'
                    f'<strong>{oc_label}</strong>'
                    f'<span style="background:{color};color:white;padding:2px 10px;border-radius:3px;'
                    f'font-size:0.8em;">{status}</span></div>'
                    f'<div style="margin-top:8px;color:#555;">'
                    f'Tipo: {type_label} | Proveedor: {supplier} '
                    f'{"| Cepa: " + cepa_txt if cepa_txt else ""} | '
                    f'Fecha: {oc.get("date", "-")}</div>'
                    f'<div style="margin-top:4px;color:#555;">'
                    f'{"Litros: " + str(oc.get("expected_liters", "")) + " | " if oc.get("expected_liters") else ""}'
                    f'{"Kilos: " + str(oc.get("expected_kilos", "")) + " | " if oc.get("expected_kilos") else ""}'
                    f'{"Total: $" + str(oc.get("total_price", "")) + " " + str(oc.get("currency", "")) if oc.get("total_price") else ""}'
                    f'</div>'
                    f'{"<div style=margin-top:4px;color:#666;font-style:italic;>" + oc.get("notes", "") + "</div>" if oc.get("notes") else ""}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Mostrar lineas si es insumos
                if oc.get("purchase_type") == "Insumos":
                    try:
                        oc_lines = queries.get_po_supply_lines(oc["id"])
                        if oc_lines:
                            line_texts = []
                            for l in oc_lines:
                                supply = l.get("supplies", {})
                                line_texts.append(f"  - {supply.get('name', '?')}: {l.get('quantity', 0)} {supply.get('unit', '')}")
                            st.markdown("\n".join(line_texts))
                    except Exception:
                        pass

                col_apr, col_rej = st.columns(2)

                with col_apr:
                    if status == "Borrador" and can_approve_eno:
                        if st.button(f"Aprobar (Enologia)", key=f"apr_eno_{oc['id']}", type="primary",
                                     use_container_width=True):
                            user = get_current_user()
                            queries.update_purchase_order(oc["id"], {
                                "status": "Aprobada Enologia",
                                "approved_by_enology": user["id"],
                                "approved_by_enology_at": "now()",
                            })
                            st.success(f"{oc_label} aprobada por Enologia")
                            st.cache_data.clear()
                            st.rerun()

                    elif status == "Aprobada Enologia" and can_approve_admin:
                        if st.button(f"Aprobar (V°B°)", key=f"apr_admin_{oc['id']}", type="primary",
                                     use_container_width=True):
                            user = get_current_user()
                            queries.update_purchase_order(oc["id"], {
                                "status": "Aprobada",
                                "approved_by_admin": user["id"],
                                "approved_by_admin_at": "now()",
                            })
                            st.success(f"{oc_label} aprobada con V°B°")
                            st.cache_data.clear()
                            st.rerun()

                with col_rej:
                    if st.button(f"Rechazar", key=f"rej_{oc['id']}", use_container_width=True):
                        st.session_state[f"reject_oc_{oc['id']}"] = True

                    if st.session_state.get(f"reject_oc_{oc['id']}"):
                        rej_notes = st.text_input("Motivo del rechazo:", key=f"rej_notes_{oc['id']}")
                        if st.button("Confirmar Rechazo", key=f"rej_confirm_{oc['id']}"):
                            if not rej_notes:
                                st.error("Debe indicar el motivo")
                            else:
                                user = get_current_user()
                                queries.update_purchase_order(oc["id"], {
                                    "status": "Rechazada",
                                    "rejected_by": user["id"],
                                    "rejected_at": "now()",
                                    "rejection_notes": rej_notes,
                                })
                                st.success(f"{oc_label} rechazada")
                                del st.session_state[f"reject_oc_{oc['id']}"]
                                st.cache_data.clear()
                                st.rerun()

                st.markdown("---")

# =============================================================
# TAB: Detalle / Recepciones
# =============================================================
with tab_detalle:
    try:
        all_ocs = queries.get_purchase_orders_unified(limit=200)
    except Exception:
        all_ocs = []

    if not all_ocs:
        st.info("Sin ordenes de compra")
    else:
        oc_options = {}
        for o in all_ocs:
            supplier = (o.get("suppliers") or {}).get("name", "?")
            oc_options[o["id"]] = f"[{o.get('purchase_type', '?')}] OC {o.get('oc_number') or o['id']} - {supplier} ({o.get('status', '?')})"

        sel_oc_id = st.selectbox("Seleccione OC:", options=list(oc_options.keys()),
                                  format_func=lambda x: oc_options[x],
                                  index=None, placeholder="Seleccione...", key="oc_detail")

        if sel_oc_id:
            oc = next(o for o in all_ocs if o["id"] == sel_oc_id)
            oc_type = oc.get("purchase_type", "Insumos")
            status = oc.get("status", "?")
            supplier = oc.get("suppliers")
            cepa = oc.get("grape_varieties")
            color = STATUS_COLORS.get(status, "#999")

            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin:10px 0;">'
                f'<span style="background:{color};color:white;padding:6px 16px;border-radius:4px;'
                f'font-weight:bold;">{status}</span>'
                f'<span style="font-size:1.1em;"><strong>{oc_type}</strong> | '
                f'OC: {oc.get("oc_number") or "-"} | '
                f'{supplier.get("name", "-") if supplier else "-"}'
                f'{" | " + cepa.get("code", "") if cepa else ""}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # PDF Download
            _oc_lines_for_pdf = []
            if oc_type == "Insumos":
                try:
                    _oc_lines_for_pdf = queries.get_po_supply_lines(sel_oc_id)
                except Exception:
                    pass
            try:
                pdf_bytes = generate_oc_pdf(oc, lines=_oc_lines_for_pdf, logo_path="logo_vda.png")
                st.download_button(
                    "Descargar PDF OC",
                    data=pdf_bytes,
                    file_name=f"OC_{oc.get('oc_number') or oc['id']}.pdf",
                    mime="application/pdf",
                    key="oc_detail_pdf",
                )
            except Exception as e:
                st.warning(f"Error generando PDF: {e}")

            # ---- DETALLE SEGUN TIPO ----

            if oc_type == "Vino":
                # Metricas
                try:
                    deliveries = queries.get_po_wine_deliveries(sel_oc_id)
                except Exception:
                    deliveries = []

                expected = oc.get("expected_liters", 0) or 0
                delivered = sum(d.get("liters", 0) or 0 for d in deliveries)
                remaining = max(expected - delivered, 0)
                pct = min(delivered / expected * 100, 100) if expected > 0 else 0

                col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                col_i1.metric("Litros esperados", f"{expected:,.0f}")
                col_i2.metric("Recibidos", f"{delivered:,.0f}")
                col_i3.metric("Pendientes", f"{remaining:,.0f}")
                col_i4.metric("Despachos", len(deliveries))

                st.markdown(
                    f'<div style="background:#eee;border-radius:6px;height:12px;margin:10px 0;">'
                    f'<div style="background:#28a745;border-radius:6px;height:12px;width:{pct}%;"></div>'
                    f'</div><div style="text-align:center;color:#666;font-size:0.85em;">{pct:.1f}% recibido</div>',
                    unsafe_allow_html=True,
                )

                if deliveries:
                    del_rows = []
                    for d in deliveries:
                        tank = d.get("tanks")
                        del_rows.append({
                            "Fecha": d.get("date", "-"),
                            "Guia": d.get("guia_despacho") or "-",
                            "Litros": d.get("liters", 0),
                            "Cuba": tank.get("code", "-") if tank else "-",
                            "Grado": d.get("alcohol_degree") or "-",
                            "SO2": d.get("so2_total") or "-",
                            "pH": d.get("ph") or "-",
                        })
                    st.dataframe(pd.DataFrame(del_rows), use_container_width=True, hide_index=True)

                # Agregar despacho
                if has_permission("recepcion_vino", "crear") and status not in ("Aceptada",):
                    st.markdown("---")
                    st.subheader("Registrar Despacho")
                    col_d1, col_d2, col_d3 = st.columns(3)
                    with col_d1:
                        d_date = st.date_input("Fecha", value=date.today(), key="vd_date")
                        d_guia = st.text_input("Guia de Despacho", key="vd_guia")
                    with col_d2:
                        d_liters = st.number_input("Litros", min_value=0, step=100, key="vd_liters")
                        tank_opts = {t["id"]: f"{t['code']} ({t.get('capacity_liters', 0)} L)" for t in ref["tanks"]}
                        d_tank = st.selectbox("Cuba destino", options=list(tank_opts.keys()),
                                               format_func=lambda x: tank_opts[x],
                                               index=None, placeholder="Seleccione...", key="vd_tank")
                    with col_d3:
                        d_alcohol = st.number_input("Grado (%vol)", min_value=0.0, step=0.1, key="vd_alcohol")
                        d_so2 = st.number_input("SO2 Total", min_value=0.0, step=1.0, key="vd_so2")

                    d_ph = st.number_input("pH", min_value=0.0, max_value=5.0, step=0.01, key="vd_ph")
                    d_wine_code = st.text_input("Codigo Vino", key="vd_wcode", placeholder="YY/YY-NNN")
                    d_notes = st.text_input("Notas", key="vd_notes")

                    if st.button("Registrar Despacho", type="primary", use_container_width=True, key="save_vd"):
                        if d_liters <= 0:
                            st.error("Ingrese litros")
                        elif not d_guia:
                            st.error("Ingrese guia de despacho")
                        else:
                            try:
                                dd = {
                                    "purchase_order_id": sel_oc_id,
                                    "date": str(d_date),
                                    "guia_despacho": d_guia,
                                    "liters": d_liters,
                                }
                                if d_tank:
                                    dd["dest_tank_id"] = d_tank
                                if d_alcohol > 0:
                                    dd["alcohol_degree"] = d_alcohol
                                if d_so2 > 0:
                                    dd["so2_total"] = d_so2
                                if d_ph > 0:
                                    dd["ph"] = d_ph
                                if d_wine_code:
                                    dd["wine_code"] = d_wine_code
                                if d_notes:
                                    dd["notes"] = d_notes

                                queries.create_po_wine_delivery(dd)

                                new_total = delivered + d_liters
                                if expected > 0 and new_total >= expected:
                                    queries.update_purchase_order(sel_oc_id, {"status": "Despachado"})
                                elif status == "Pedido":
                                    queries.update_purchase_order(sel_oc_id, {"status": "En Despacho"})

                                st.success(f"Despacho registrado ({d_liters:,.0f} L)")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

            elif oc_type == "Uva":
                try:
                    deliveries = queries.get_po_grape_deliveries(sel_oc_id)
                except Exception:
                    deliveries = []

                expected_k = oc.get("expected_kilos", 0) or 0
                delivered_k = sum(d.get("kilos", 0) or 0 for d in deliveries)
                remaining_k = max(expected_k - delivered_k, 0)
                pct_k = min(delivered_k / expected_k * 100, 100) if expected_k > 0 else 0

                col_i1, col_i2, col_i3, col_i4 = st.columns(4)
                col_i1.metric("Kilos esperados", f"{expected_k:,.0f}")
                col_i2.metric("Recibidos", f"{delivered_k:,.0f}")
                col_i3.metric("Pendientes", f"{remaining_k:,.0f}")
                col_i4.metric("Despachos", len(deliveries))

                st.markdown(
                    f'<div style="background:#eee;border-radius:6px;height:12px;margin:10px 0;">'
                    f'<div style="background:#28a745;border-radius:6px;height:12px;width:{pct_k}%;"></div>'
                    f'</div><div style="text-align:center;color:#666;font-size:0.85em;">{pct_k:.1f}% recibido</div>',
                    unsafe_allow_html=True,
                )

                if deliveries:
                    del_rows = []
                    for d in deliveries:
                        tank = d.get("tanks")
                        del_rows.append({
                            "Fecha": d.get("date", "-"),
                            "Guia": d.get("guia_despacho") or "-",
                            "Kilos": d.get("kilos", 0),
                            "Brix": d.get("brix") or "-",
                            "pH": d.get("ph") or "-",
                            "Acidez": d.get("acidity") or "-",
                            "Cuba": tank.get("code", "-") if tank else "-",
                        })
                    st.dataframe(pd.DataFrame(del_rows), use_container_width=True, hide_index=True)

                if has_permission("recepcion_vino", "crear") and status not in ("Cerrada",):
                    st.markdown("---")
                    st.subheader("Registrar Recepcion de Uva")
                    col_g1, col_g2, col_g3 = st.columns(3)
                    with col_g1:
                        g_date = st.date_input("Fecha", value=date.today(), key="gd_date")
                        g_guia = st.text_input("Guia de Despacho", key="gd_guia")
                    with col_g2:
                        g_kilos = st.number_input("Kilos", min_value=0.0, step=100.0, key="gd_kilos")
                        g_brix = st.number_input("Brix", min_value=0.0, max_value=35.0, step=0.1, key="gd_brix")
                    with col_g3:
                        g_ph = st.number_input("pH", min_value=0.0, max_value=5.0, step=0.01, key="gd_ph")
                        g_acidity = st.number_input("Acidez (g/L)", min_value=0.0, step=0.1, key="gd_acid")

                    tank_opts = {t["id"]: f"{t['code']} ({t.get('capacity_liters', 0)} L)" for t in ref["tanks"]}
                    g_tank = st.selectbox("Cuba destino", options=list(tank_opts.keys()),
                                           format_func=lambda x: tank_opts[x],
                                           index=None, placeholder="Seleccione...", key="gd_tank")
                    g_notes = st.text_input("Notas", key="gd_notes")

                    if st.button("Registrar Recepcion", type="primary", use_container_width=True, key="save_gd"):
                        if g_kilos <= 0:
                            st.error("Ingrese kilos")
                        else:
                            try:
                                gd = {
                                    "purchase_order_id": sel_oc_id,
                                    "date": str(g_date),
                                    "kilos": g_kilos,
                                }
                                if g_guia:
                                    gd["guia_despacho"] = g_guia
                                if g_brix > 0:
                                    gd["brix"] = g_brix
                                if g_ph > 0:
                                    gd["ph"] = g_ph
                                if g_acidity > 0:
                                    gd["acidity"] = g_acidity
                                if g_tank:
                                    gd["dest_tank_id"] = g_tank
                                if g_notes:
                                    gd["notes"] = g_notes

                                queries.create_po_grape_delivery(gd)

                                new_total_k = delivered_k + g_kilos
                                if expected_k > 0 and new_total_k >= expected_k:
                                    queries.update_purchase_order(sel_oc_id, {"status": "Despachado"})
                                elif status == "Pedido":
                                    queries.update_purchase_order(sel_oc_id, {"status": "En Despacho"})

                                st.success(f"Recepcion registrada ({g_kilos:,.0f} kg)")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

            elif oc_type == "Insumos":
                try:
                    po_lines = queries.get_po_supply_lines(sel_oc_id)
                except Exception:
                    po_lines = []

                if po_lines:
                    st.subheader("Insumos pedidos")
                    line_rows = []
                    for l in po_lines:
                        supply = l.get("supplies")
                        line_rows.append({
                            "Insumo": supply.get("name", "?") if supply else "?",
                            "Codigo": supply.get("code", "-") if supply else "-",
                            "Cantidad": l.get("quantity", 0),
                            "Unidad": supply.get("unit", "") if supply else "",
                        })
                    st.dataframe(pd.DataFrame(line_rows), use_container_width=True, hide_index=True)

                if has_permission("recepcion_insumos", "crear") and status not in ("Cerrada",):
                    st.markdown("---")
                    st.subheader("Registrar Recepcion de Insumos")
                    st.info("Para registrar la recepcion con lotes, use el modulo **Recepcion de Insumos** vinculando esta OC")

            # ---- AVANZAR ESTADO (comun) ----
            st.markdown("---")
            st.subheader("Documentos y Estado")

            if oc_type == "Vino":
                if status == "Despachado":
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        inv_num = st.text_input("N Factura", key="doc_inv")
                    with col_f2:
                        inv_date = st.date_input("Fecha Factura", value=date.today(), key="doc_inv_date")
                    if st.button("Registrar Factura", type="primary", key="doc_save_inv"):
                        if inv_num:
                            queries.update_purchase_order(sel_oc_id, {
                                "invoice_number": inv_num, "invoice_date": str(inv_date), "status": "Facturado"})
                            st.success("Factura registrada")
                            st.cache_data.clear()
                            st.rerun()

                elif status == "Facturado":
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        do_num = st.text_input("N DO", key="doc_do")
                    with col_d2:
                        do_date = st.date_input("Fecha DO", value=date.today(), key="doc_do_date")
                    if st.button("Registrar DO", type="primary", key="doc_save_do"):
                        if do_num:
                            queries.update_purchase_order(sel_oc_id, {
                                "do_number": do_num, "do_date": str(do_date), "status": "DO Recibida"})
                            st.success("DO registrada")
                            st.cache_data.clear()
                            st.rerun()

                elif status == "DO Recibida":
                    if st.button("Aceptar Factura y Cerrar", type="primary", key="doc_accept"):
                        queries.update_purchase_order(sel_oc_id, {
                            "acceptance_date": str(date.today()), "status": "Aceptada"})
                        st.success("Compra aceptada y cerrada")
                        st.cache_data.clear()
                        st.rerun()

                elif status == "Aceptada":
                    st.success("Compra cerrada")

            else:
                if status in ("Despachado", "Recibido"):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        inv_num = st.text_input("N Factura", key="doc_inv2")
                    with col_f2:
                        inv_date = st.date_input("Fecha Factura", value=date.today(), key="doc_inv_date2")
                    if st.button("Registrar Factura", type="primary", key="doc_save_inv2"):
                        if inv_num:
                            queries.update_purchase_order(sel_oc_id, {
                                "invoice_number": inv_num, "invoice_date": str(inv_date), "status": "Facturado"})
                            st.success("Factura registrada")
                            st.cache_data.clear()
                            st.rerun()

                elif status == "Facturado":
                    if st.button("Cerrar OC", type="primary", key="doc_close"):
                        queries.update_purchase_order(sel_oc_id, {"status": "Cerrada"})
                        st.success("OC cerrada")
                        st.cache_data.clear()
                        st.rerun()

                elif status in ("Cerrada", "Aceptada"):
                    st.success("OC cerrada")

            # ---- ELIMINAR / ANULAR ----
            if status in ("Borrador", "Rechazada"):
                st.markdown("---")
                if st.button("Eliminar OC", key="oc_delete", use_container_width=True):
                    st.session_state[f"confirm_del_oc_{sel_oc_id}"] = True

                if st.session_state.get(f"confirm_del_oc_{sel_oc_id}"):
                    st.warning(f"Confirma eliminar OC {oc.get('oc_number') or sel_oc_id}? Esta accion no se puede deshacer.")
                    col_dy, col_dn = st.columns(2)
                    with col_dy:
                        if st.button("Si, eliminar", key="oc_del_yes", use_container_width=True):
                            try:
                                queries.delete_purchase_order(sel_oc_id)
                                st.success("OC eliminada")
                                del st.session_state[f"confirm_del_oc_{sel_oc_id}"]
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with col_dn:
                        if st.button("Cancelar", key="oc_del_no", use_container_width=True):
                            del st.session_state[f"confirm_del_oc_{sel_oc_id}"]
                            st.rerun()

            elif status in ("Aprobada Enologia", "Aprobada", "Pedido"):
                st.markdown("---")
                if st.button("Anular OC", key="oc_annul", use_container_width=True):
                    st.session_state[f"confirm_annul_oc_{sel_oc_id}"] = True

                if st.session_state.get(f"confirm_annul_oc_{sel_oc_id}"):
                    annul_reason = st.text_input("Motivo de anulacion:", key="oc_annul_reason")
                    col_ay, col_an = st.columns(2)
                    with col_ay:
                        if st.button("Confirmar Anulacion", key="oc_annul_yes", use_container_width=True):
                            if not annul_reason:
                                st.error("Debe indicar el motivo")
                            else:
                                try:
                                    queries.update_purchase_order(sel_oc_id, {
                                        "status": "Anulada",
                                        "notes": f"ANULADA: {annul_reason}",
                                    })
                                    st.success("OC anulada")
                                    del st.session_state[f"confirm_annul_oc_{sel_oc_id}"]
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    with col_an:
                        if st.button("Cancelar", key="oc_annul_no", use_container_width=True):
                            del st.session_state[f"confirm_annul_oc_{sel_oc_id}"]
                            st.rerun()

            elif status == "Anulada":
                st.warning("Esta OC fue anulada")
