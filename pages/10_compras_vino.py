import streamlit as st
import pandas as pd
from datetime import date
from lib import queries
from lib.auth import require_permission, has_permission

require_permission("recepcion_vino", "ver")

st.title("Compras de Vino")
st.markdown("Gestion de compras con despachos, factura y DO")

STATUSES = ["Pedido", "En Despacho", "Despachado", "Facturado", "DO Recibida", "Aceptada"]
STATUS_COLORS = {
    "Pedido": "#6c757d",
    "En Despacho": "#007bff",
    "Despachado": "#17a2b8",
    "Facturado": "#ffc107",
    "DO Recibida": "#fd7e14",
    "Aceptada": "#28a745",
}

@st.cache_data(ttl=300)
def load_ref():
    return {
        "suppliers": queries.get_suppliers(),
        "grape_varieties": queries.get_grape_varieties(),
        "product_lines": queries.get_product_lines(),
        "tanks": queries.get_tanks(),
    }

try:
    ref = load_ref()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

tab_lista, tab_nueva, tab_detalle = st.tabs(["Compras", "Nueva Compra", "Detalle / Despachos"])

# =============================================================
# TAB: Lista de compras
# =============================================================
with tab_lista:
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_status = st.selectbox("Estado:", ["Todos"] + STATUSES, key="wpc_filter")
    with col_f2:
        filter_search = st.text_input("Buscar:", placeholder="Proveedor, OC, cepa...", key="wpc_search")

    try:
        purchases = queries.get_wine_purchases(limit=100)
    except Exception:
        purchases = []

    if filter_status != "Todos":
        purchases = [p for p in purchases if p.get("status") == filter_status]
    if filter_search:
        s = filter_search.lower()
        purchases = [p for p in purchases if
                     s in str(p.get("oc_number", "")).lower() or
                     s in str((p.get("suppliers") or {}).get("name", "")).lower() or
                     s in str((p.get("grape_varieties") or {}).get("code", "")).lower()]

    # Metricas
    pending = [p for p in purchases if p.get("status") not in ("Aceptada",)]
    total_expected = sum(p.get("expected_liters", 0) or 0 for p in pending)
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Compras activas", len(pending))
    col_m2.metric("Litros esperados", f"{total_expected:,.0f}")
    col_m3.metric("Total registradas", len(purchases))

    if purchases:
        rows = []
        for p in purchases:
            supplier = p.get("suppliers")
            cepa = p.get("grape_varieties")
            color = STATUS_COLORS.get(p.get("status", ""), "#999")
            rows.append({
                "ID": p["id"],
                "Fecha": p.get("date", "-"),
                "OC": p.get("oc_number") or "-",
                "Proveedor": supplier.get("name", "-") if supplier else "-",
                "Cepa": cepa.get("code", "-") if cepa else "-",
                "Litros Esper.": p.get("expected_liters") or "-",
                "Precio/L": p.get("price_per_liter") or "-",
                "Estado": p.get("status", "-"),
                "Factura": p.get("invoice_number") or "-",
                "DO": p.get("do_number") or "-",
            })

        df = pd.DataFrame(rows)

        def color_status(val):
            c = STATUS_COLORS.get(val, "")
            if c:
                return f"background-color: {c}; color: white"
            return ""

        st.dataframe(
            df.style.map(color_status, subset=["Estado"]),
            use_container_width=True, hide_index=True, height=500,
        )
    else:
        st.info("Sin compras registradas")

# =============================================================
# TAB: Nueva Compra
# =============================================================
with tab_nueva:
    if not has_permission("recepcion_vino", "crear"):
        st.warning("No tiene permisos para crear compras")
    else:
        st.subheader("Registrar Nueva Compra de Vino")

        col1, col2, col3 = st.columns(3)
        with col1:
            wp_date = st.date_input("Fecha", value=date.today(), key="wp_date")
            supp_options = {s["id"]: s["name"] for s in ref["suppliers"]}
            wp_supplier = st.selectbox("Proveedor", options=list(supp_options.keys()),
                                        format_func=lambda x: supp_options[x],
                                        index=None, placeholder="Seleccione...", key="wp_supplier")
        with col2:
            wp_oc = st.text_input("N OC", key="wp_oc")
            cepa_options = {g["id"]: f"{g['code']} - {g['name']}" for g in ref["grape_varieties"]}
            wp_cepa = st.selectbox("Cepa", options=list(cepa_options.keys()),
                                    format_func=lambda x: cepa_options[x],
                                    index=None, placeholder="Seleccione...", key="wp_cepa")
        with col3:
            line_options = {p["id"]: p["name"] for p in ref["product_lines"]}
            wp_line = st.selectbox("Linea", options=list(line_options.keys()),
                                    format_func=lambda x: line_options[x],
                                    index=None, placeholder="Seleccione...", key="wp_line")
            wp_wine_type = st.selectbox("Tipo", ["Tinto", "Blanco", "Rosado"], key="wp_type")

        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            wp_liters = st.number_input("Litros esperados", min_value=0, step=100, key="wp_liters")
        with col_p2:
            wp_ppl = st.number_input("Precio por litro", min_value=0.0, step=0.01, key="wp_ppl")
        with col_p3:
            wp_total = st.number_input("Precio total", min_value=0.0, step=100.0, key="wp_total")
        with col_p4:
            wp_currency = st.selectbox("Moneda", ["CLP", "USD", "EUR"], key="wp_currency")

        wp_notes = st.text_area("Notas", key="wp_notes", placeholder="Observaciones de la compra...")

        if st.button("Registrar Compra", type="primary", use_container_width=True):
            if not wp_supplier:
                st.error("Debe seleccionar un proveedor")
            elif not wp_cepa:
                st.error("Debe seleccionar una cepa")
            elif wp_liters <= 0:
                st.error("Debe ingresar litros esperados")
            else:
                try:
                    data = {
                        "date": str(wp_date),
                        "supplier_id": wp_supplier,
                        "grape_variety_id": wp_cepa,
                        "expected_liters": wp_liters,
                        "status": "Pedido",
                    }
                    if wp_oc:
                        data["oc_number"] = wp_oc
                    if wp_line:
                        data["product_line_id"] = wp_line
                    if wp_wine_type:
                        data["wine_type"] = wp_wine_type
                    if wp_ppl > 0:
                        data["price_per_liter"] = wp_ppl
                    if wp_total > 0:
                        data["total_price"] = wp_total
                    if wp_currency:
                        data["currency"] = wp_currency
                    if wp_notes:
                        data["notes"] = wp_notes

                    result = queries.create_wine_purchase(data)
                    st.success(f"Compra registrada (ID: {result[0]['id']})")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# =============================================================
# TAB: Detalle / Despachos
# =============================================================
with tab_detalle:
    try:
        all_purchases = queries.get_wine_purchases(limit=200)
    except Exception:
        all_purchases = []

    active_purchases = [p for p in all_purchases if p.get("status") != "Aceptada"]
    if not active_purchases:
        active_purchases = all_purchases

    if not active_purchases:
        st.info("Sin compras registradas")
    else:
        purchase_options = {}
        for p in active_purchases:
            supplier = (p.get("suppliers") or {}).get("name", "?")
            cepa = (p.get("grape_varieties") or {}).get("code", "?")
            purchase_options[p["id"]] = f"OC {p.get('oc_number') or p['id']} - {supplier} - {cepa} ({p.get('status', '?')})"

        selected_id = st.selectbox(
            "Seleccione compra:",
            options=list(purchase_options.keys()),
            format_func=lambda x: purchase_options[x],
            index=None, placeholder="Seleccione...",
            key="wp_detail"
        )

        if selected_id:
            purchase = next(p for p in active_purchases if p["id"] == selected_id)
            supplier = purchase.get("suppliers")
            cepa = purchase.get("grape_varieties")
            linea = purchase.get("product_lines")

            # Info de la compra
            status = purchase.get("status", "?")
            color = STATUS_COLORS.get(status, "#999")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:15px;">'
                f'<span style="background:{color};color:white;padding:6px 16px;border-radius:4px;'
                f'font-weight:bold;font-size:1.1em;">{status}</span>'
                f'<span style="font-size:1.1em;">OC: {purchase.get("oc_number") or "-"} | '
                f'{supplier.get("name", "-") if supplier else "-"} | '
                f'{cepa.get("code", "-") if cepa else "-"}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            col_i1, col_i2, col_i3, col_i4 = st.columns(4)
            col_i1.metric("Litros esperados", f"{purchase.get('expected_liters', 0):,.0f}")

            # Cargar despachos
            try:
                deliveries = queries.get_wine_deliveries(selected_id)
            except Exception:
                deliveries = []

            delivered_liters = sum(d.get("liters", 0) or 0 for d in deliveries)
            remaining = (purchase.get("expected_liters", 0) or 0) - delivered_liters
            col_i2.metric("Litros recibidos", f"{delivered_liters:,.0f}")
            col_i3.metric("Litros pendientes", f"{max(remaining, 0):,.0f}")
            col_i4.metric("Despachos", len(deliveries))

            # Barra de progreso
            expected = purchase.get("expected_liters", 0) or 1
            pct = min(delivered_liters / expected * 100, 100)
            st.markdown(
                f'<div style="background:#eee;border-radius:6px;height:12px;margin:10px 0;">'
                f'<div style="background:#28a745;border-radius:6px;height:12px;width:{pct}%;"></div>'
                f'</div>'
                f'<div style="text-align:center;color:#666;font-size:0.85em;">{pct:.1f}% recibido</div>',
                unsafe_allow_html=True,
            )

            st.markdown("---")

            # --- Lista de despachos ---
            if deliveries:
                st.subheader(f"Despachos ({len(deliveries)})")
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
                        "Codigo Vino": d.get("wine_code") or "-",
                    })
                st.dataframe(pd.DataFrame(del_rows), use_container_width=True, hide_index=True)

            # --- Agregar despacho ---
            if has_permission("recepcion_vino", "crear") and status not in ("Aceptada",):
                st.subheader("Registrar Despacho")

                col_d1, col_d2, col_d3 = st.columns(3)
                with col_d1:
                    del_date = st.date_input("Fecha despacho", value=date.today(), key="del_date")
                    del_guia = st.text_input("Guia de Despacho", key="del_guia")
                with col_d2:
                    del_liters = st.number_input("Litros", min_value=0, step=100, key="del_liters")
                    tank_options = {t["id"]: f"{t['code']} ({t.get('capacity_liters', 0)} L)"
                                    for t in ref["tanks"]}
                    del_tank = st.selectbox("Cuba destino", options=list(tank_options.keys()),
                                             format_func=lambda x: tank_options[x],
                                             index=None, placeholder="Seleccione...", key="del_tank")
                with col_d3:
                    del_alcohol = st.number_input("Grado (%vol)", min_value=0.0, step=0.1, key="del_alcohol")
                    del_so2 = st.number_input("SO2 Total (mg/L)", min_value=0.0, step=1.0, key="del_so2")

                col_d4, col_d5 = st.columns(2)
                with col_d4:
                    del_ph = st.number_input("pH", min_value=0.0, max_value=5.0, step=0.01, key="del_ph")
                with col_d5:
                    del_wine_code = st.text_input("Codigo de Vino", key="del_wine_code", placeholder="YY/YY-NNN")

                del_notes = st.text_input("Notas del despacho", key="del_notes")

                if st.button("Registrar Despacho", type="primary", use_container_width=True, key="save_del"):
                    if del_liters <= 0:
                        st.error("Debe ingresar litros")
                    elif not del_guia:
                        st.error("Debe ingresar guia de despacho")
                    else:
                        try:
                            del_data = {
                                "wine_purchase_id": selected_id,
                                "date": str(del_date),
                                "guia_despacho": del_guia,
                                "liters": del_liters,
                            }
                            if del_tank:
                                del_data["dest_tank_id"] = del_tank
                            if del_alcohol > 0:
                                del_data["alcohol_degree"] = del_alcohol
                            if del_so2 > 0:
                                del_data["so2_total"] = del_so2
                            if del_ph > 0:
                                del_data["ph"] = del_ph
                            if del_wine_code:
                                del_data["wine_code"] = del_wine_code
                            if del_notes:
                                del_data["notes"] = del_notes

                            queries.create_wine_delivery(del_data)

                            new_total = delivered_liters + del_liters
                            if new_total >= (purchase.get("expected_liters", 0) or 0):
                                queries.update_wine_purchase(selected_id, {"status": "Despachado"})
                            elif status == "Pedido":
                                queries.update_wine_purchase(selected_id, {"status": "En Despacho"})

                            st.success(f"Despacho registrado ({del_liters:,.0f} L)")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

            # --- Avanzar estado ---
            st.markdown("---")
            st.subheader("Avanzar Estado")

            if status == "Despachado":
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    inv_number = st.text_input("N Factura", key="inv_number")
                with col_f2:
                    inv_date = st.date_input("Fecha Factura", value=date.today(), key="inv_date")
                if st.button("Registrar Factura", type="primary", key="save_inv"):
                    if not inv_number:
                        st.error("Ingrese numero de factura")
                    else:
                        try:
                            queries.update_wine_purchase(selected_id, {
                                "invoice_number": inv_number,
                                "invoice_date": str(inv_date),
                                "status": "Facturado",
                            })
                            st.success("Factura registrada")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

            elif status == "Facturado":
                col_do1, col_do2 = st.columns(2)
                with col_do1:
                    do_number = st.text_input("N DO", key="do_number")
                with col_do2:
                    do_date = st.date_input("Fecha DO", value=date.today(), key="do_date")
                if st.button("Registrar DO", type="primary", key="save_do"):
                    if not do_number:
                        st.error("Ingrese numero de DO")
                    else:
                        try:
                            queries.update_wine_purchase(selected_id, {
                                "do_number": do_number,
                                "do_date": str(do_date),
                                "status": "DO Recibida",
                            })
                            st.success("DO registrada")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

            elif status == "DO Recibida":
                if st.button("Aceptar Factura y Cerrar Compra", type="primary", key="accept"):
                    try:
                        queries.update_wine_purchase(selected_id, {
                            "acceptance_date": str(date.today()),
                            "status": "Aceptada",
                        })
                        st.success("Compra aceptada y cerrada")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

            elif status == "Aceptada":
                st.success("Compra cerrada y aceptada")

            elif status in ("Pedido", "En Despacho"):
                st.info("Registre despachos arriba para avanzar el estado")
