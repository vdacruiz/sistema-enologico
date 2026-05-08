import streamlit as st
import pandas as pd
from datetime import date
from lib import queries

st.title("Recepcion de Vino")
st.markdown("Registro de ingreso de vino comprado o de vendimia")

STATUS_COLORS = {
    "Recibido": "#17a2b8",
    "Facturado": "#ffc107",
    "DO Liberada": "#fd7e14",
    "Aprobada": "#28a745",
}

@st.cache_data(ttl=300)
def load_ref():
    return {
        "grape_varieties": queries.get_grape_varieties(),
        "product_lines": queries.get_product_lines(),
        "suppliers": queries.get_suppliers(),
        "tanks": queries.get_tanks(),
        "wines": queries.get_wines(),
    }

try:
    ref = load_ref()
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")
    st.stop()

tab_nueva, tab_historial, tab_factura = st.tabs(["Nueva Recepcion", "Historial", "Factura y DO"])

# =============================================================
# TAB: Nueva Recepcion
# =============================================================
with tab_nueva:
    reception_type = st.radio(
        "Tipo de recepcion:",
        ["Compra Vino", "Vendimia"],
        horizontal=True,
    )

    st.markdown("---")

    # --- Codigo de vino ---
    st.subheader("Identificacion del Vino")
    col_w1, col_w2 = st.columns(2)
    with col_w1:
        wine_code = st.text_input("Codigo de Vino (YY/YY-NNN)", key="rv_wine_code",
                                  placeholder="Ej: 25/26-001")
    with col_w2:
        wine_exists = None
        if wine_code:
            wine_exists = next((w for w in ref["wines"] if w["code"] == wine_code), None)
            if wine_exists:
                cepa_w = wine_exists.get("grape_varieties") or {}
                linea_w = wine_exists.get("product_lines") or {}
                st.success(f"Vino existente: {cepa_w.get('code', '')} {cepa_w.get('name', '')} | "
                           f"{linea_w.get('name', '-')} | {wine_exists.get('wine_type', '-')}")
            else:
                st.info("Vino nuevo - se creara automaticamente al registrar")

    # --- Cepa, linea, tipo, cosecha ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        cepa_options = {g["id"]: f"{g['code']} - {g['name']}" for g in ref["grape_varieties"]}
        default_cepa = wine_exists.get("grape_variety_id") if wine_exists else None
        cepa_idx = list(cepa_options.keys()).index(default_cepa) if default_cepa and default_cepa in cepa_options else None
        cepa_id = st.selectbox(
            "Cepa", options=list(cepa_options.keys()),
            format_func=lambda x: cepa_options[x],
            index=cepa_idx, placeholder="Seleccione cepa...", key="rv_cepa"
        )
    with col2:
        line_options = {p["id"]: p["name"] for p in ref["product_lines"]}
        default_line = wine_exists.get("product_line_id") if wine_exists else None
        line_idx = list(line_options.keys()).index(default_line) if default_line and default_line in line_options else None
        line_id = st.selectbox(
            "Linea de Producto", options=list(line_options.keys()),
            format_func=lambda x: line_options[x],
            index=line_idx, placeholder="Seleccione linea...", key="rv_line"
        )
    with col3:
        wine_type_options = ["Tinto", "Blanco", "Rosado"]
        default_type = wine_exists.get("wine_type") if wine_exists else None
        type_idx = wine_type_options.index(default_type) if default_type and default_type in wine_type_options else 0
        wine_type_val = st.selectbox("Tipo", wine_type_options, index=type_idx, key="rv_type")
    with col4:
        default_vintage = wine_exists.get("vintage_year") if wine_exists else date.today().year
        vintage_year = st.number_input("Ano Cosecha", min_value=2000, max_value=2050,
                                       value=default_vintage or date.today().year, key="rv_vintage")

    # --- Proveedor (solo compra) ---
    supplier_id = None
    guia_despacho = None
    oc_number = None
    price_per_liter = None
    total_price = None
    currency = "CLP"

    if reception_type == "Compra Vino":
        st.subheader("Datos de Compra")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            supp_options = {s["id"]: s["name"] for s in ref["suppliers"]}
            supplier_id = st.selectbox(
                "Proveedor", options=list(supp_options.keys()),
                format_func=lambda x: supp_options[x],
                index=None, placeholder="Seleccione proveedor...", key="rv_supplier"
            )
        with col_s2:
            guia_despacho = st.text_input("Guia de Despacho", key="rv_guia")
        with col_s3:
            oc_number = st.text_input("N OC", key="rv_oc")

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            price_per_liter = st.number_input("Precio por Litro", min_value=0.0, step=0.01, key="rv_ppl")
        with col_p2:
            currency = st.selectbox("Moneda", ["CLP", "USD", "EUR"], key="rv_currency")
        with col_p3:
            total_price = st.number_input("Precio Total", min_value=0.0, step=100.0, key="rv_total")

    # --- Datos del vino ---
    st.subheader("Datos del Vino")
    col_v1, col_v2, col_v3, col_v4 = st.columns(4)
    with col_v1:
        litros_guia = st.number_input("Litros Guia", min_value=0, step=100, key="rv_litros_guia")
    with col_v2:
        liters = st.number_input("Litros Recepcionados", min_value=0, step=100, key="rv_liters")
    with col_v3:
        alcohol = st.number_input("Grado Alcoholico (%vol)", min_value=0.0, max_value=20.0, step=0.1, key="rv_alcohol")
    with col_v4:
        so2_total = st.number_input("SO2 Total (mg/L)", min_value=0.0, step=1.0, key="rv_so2")

    if reception_type == "Vendimia":
        col_vd1, col_vd2, col_vd3 = st.columns(3)
        with col_vd1:
            kilos = st.number_input("Kilos Uva", min_value=0.0, step=100.0, key="rv_kilos")
        with col_vd2:
            brix = st.number_input("Brix", min_value=0.0, max_value=35.0, step=0.1, key="rv_brix")
        with col_vd3:
            rv_ph = st.number_input("pH", min_value=0.0, max_value=5.0, step=0.01, key="rv_ph")
    else:
        kilos = None
        brix = None
        rv_ph = None

    # --- Cuba destino ---
    st.subheader("Destino")
    tank_options = {t["id"]: f"{t['code']} - {t.get('name') or ''} ({t.get('capacity_liters', 0)} L)"
                    for t in ref["tanks"]}
    dest_tank = st.selectbox(
        "Cuba Destino", options=list(tank_options.keys()),
        format_func=lambda x: tank_options[x],
        index=None, placeholder="Seleccione cuba...", key="rv_tank"
    )

    notes = st.text_area("Observaciones", key="rv_notes", placeholder="Notas adicionales...")

    # --- Guardar ---
    st.markdown("---")
    if st.button("Registrar Recepcion", type="primary", use_container_width=True):
        if not wine_code:
            st.error("Debe ingresar un codigo de vino")
        elif not cepa_id:
            st.error("Debe seleccionar una cepa")
        elif liters <= 0:
            st.error("Debe ingresar litros recepcionados mayor a 0")
        elif reception_type == "Compra Vino" and not supplier_id:
            st.error("Debe seleccionar un proveedor para compras")
        else:
            try:
                wine = queries.find_or_create_wine(
                    code=wine_code,
                    grape_variety_id=cepa_id,
                    product_line_id=line_id,
                    wine_type=wine_type_val,
                    vintage_year=vintage_year,
                )
                wine_id = wine["id"]

                data = {
                    "date": str(date.today()),
                    "grape_variety_id": cepa_id,
                    "wine_id": wine_id,
                    "reception_type": reception_type,
                    "liters": liters,
                    "wine_code": wine_code,
                    "wine_type": wine_type_val,
                    "status": "Recibido",
                }
                if line_id:
                    data["product_line_id"] = line_id
                if vintage_year:
                    data["vintage_year"] = vintage_year
                if litros_guia and litros_guia > 0:
                    data["litros_guia"] = litros_guia
                if supplier_id:
                    data["supplier_id"] = supplier_id
                if guia_despacho:
                    data["guia_despacho"] = guia_despacho
                if oc_number:
                    data["oc_number"] = oc_number
                if price_per_liter and price_per_liter > 0:
                    data["price_per_liter"] = price_per_liter
                if total_price and total_price > 0:
                    data["total_price"] = total_price
                if currency:
                    data["currency"] = currency
                if alcohol and alcohol > 0:
                    data["alcohol_degree"] = alcohol
                if so2_total and so2_total > 0:
                    data["so2_total"] = so2_total
                if dest_tank:
                    data["dest_tank_id"] = dest_tank
                if notes:
                    data["notes"] = notes
                if kilos and kilos > 0:
                    data["kilos"] = kilos
                if brix and brix > 0:
                    data["brix"] = brix
                if rv_ph and rv_ph > 0:
                    data["ph"] = rv_ph

                result = queries.create_wine_reception(data)

                if dest_tank:
                    queries.assign_wine_to_tank(
                        tank_id=dest_tank,
                        wine_id=wine_id,
                        liters=liters,
                        grape_variety_id=cepa_id,
                        product_line_id=line_id,
                        wine_type=wine_type_val,
                        vintage_year=vintage_year,
                        alcohol_degree=alcohol if alcohol and alcohol > 0 else None,
                        so2_total=so2_total if so2_total and so2_total > 0 else None,
                        ph=rv_ph if rv_ph and rv_ph > 0 else None,
                    )

                created = "nuevo" if not wine_exists else "existente"
                st.success(f"Recepcion registrada (ID: {result[0]['id']}). "
                           f"Vino {wine_code} ({created}) asignado a cuba.")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# =============================================================
# TAB: Historial
# =============================================================
with tab_historial:
    st.subheader("Recepciones Registradas")

    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        filter_type = st.selectbox("Tipo:", ["Todos", "Compra Vino", "Vendimia"], key="rv_filter_type")
    with col_f2:
        filter_status = st.selectbox("Estado:", ["Todos", "Recibido", "Facturado", "DO Liberada", "Aprobada"], key="rv_filter_status")
    with col_f3:
        filter_search = st.text_input("Buscar:", placeholder="Cepa, proveedor, codigo, guia...", key="rv_filter_search")

    try:
        receptions = queries.get_wine_receptions(limit=200)
        if receptions:
            rows = []
            for r in receptions:
                cepa = r.get("grape_varieties")
                cepa_txt = cepa.get("code", "-") if cepa else "-"
                supplier = r.get("suppliers")
                supplier_txt = supplier.get("name", "-") if supplier else "-"
                tank = r.get("tanks")
                tank_txt = tank.get("code", "-") if tank else "-"

                rows.append({
                    "ID": r["id"],
                    "Fecha": r.get("date", "-"),
                    "Tipo": r.get("reception_type", "-"),
                    "Codigo": r.get("wine_code") or "-",
                    "Cepa": cepa_txt,
                    "Proveedor": supplier_txt,
                    "Guia": r.get("guia_despacho") or "-",
                    "L.Guia": r.get("litros_guia") or "-",
                    "L.Recep": r.get("liters", 0),
                    "Cuba": tank_txt,
                    "Cosecha": r.get("vintage_year") or "-",
                    "Factura": r.get("invoice_number") or "-",
                    "DO": r.get("do_number") or "-",
                    "Estado": r.get("status", "-"),
                })

            df = pd.DataFrame(rows)

            if filter_type != "Todos":
                df = df[df["Tipo"] == filter_type]
            if filter_status != "Todos":
                df = df[df["Estado"] == filter_status]
            if filter_search:
                mask = df.astype(str).apply(lambda row: row.str.contains(filter_search, case=False).any(), axis=1)
                df = df[mask]

            def color_status(val):
                c = STATUS_COLORS.get(val, "")
                if c:
                    return f"background-color: {c}; color: white"
                return ""

            st.dataframe(
                df.style.map(color_status, subset=["Estado"]),
                use_container_width=True,
                hide_index=True,
                height=500,
            )
            st.caption(f"Mostrando {len(df)} recepciones")
        else:
            st.info("No hay recepciones registradas")
    except Exception as e:
        st.warning(f"No se pudo cargar el historial: {e}")

# =============================================================
# TAB: Factura y DO
# =============================================================
with tab_factura:
    st.subheader("Gestion de Factura y DO")
    st.markdown("Registre factura y liberacion de DO para aprobar contablemente")

    try:
        all_receptions = queries.get_wine_receptions_pending_invoice(limit=200)
    except Exception as e:
        st.error(f"Error: {e}")
        all_receptions = []

    if not all_receptions:
        st.info("No hay recepciones de compra registradas")
    else:
        col_fs, col_ff = st.columns([2, 1])
        with col_fs:
            fact_search = st.text_input("Buscar:", placeholder="Codigo vino, cepa, proveedor, guia...", key="fact_search")
        with col_ff:
            fact_filter = st.radio("Mostrar:", ["Pendientes", "Todos", "Aprobadas"], horizontal=True, key="fact_filter")

        filtered_rec = all_receptions
        if fact_filter == "Pendientes":
            filtered_rec = [r for r in filtered_rec if r.get("status") != "Aprobada"]
        elif fact_filter == "Aprobadas":
            filtered_rec = [r for r in filtered_rec if r.get("status") == "Aprobada"]

        if fact_search:
            s = fact_search.lower()
            filtered_rec = [r for r in filtered_rec if
                            s in (r.get("wine_code") or "").lower() or
                            s in ((r.get("grape_varieties") or {}).get("code", "")).lower() or
                            s in ((r.get("grape_varieties") or {}).get("name", "")).lower() or
                            s in ((r.get("suppliers") or {}).get("name", "")).lower() or
                            s in (r.get("guia_despacho") or "").lower() or
                            s in (r.get("invoice_number") or "").lower()]

        st.caption(f"{len(filtered_rec)} recepciones")

        if not filtered_rec:
            st.info("Sin resultados")
        else:
            rec_options = {}
            for r in filtered_rec:
                cepa = (r.get("grape_varieties") or {}).get("code", "?")
                supplier = (r.get("suppliers") or {}).get("name", "?")
                status = r.get("status", "?")
                color = STATUS_COLORS.get(status, "#999")
                rec_options[r["id"]] = (
                    f"{r.get('wine_code') or '?'} | {cepa} | {supplier} | "
                    f"{r.get('liters', 0):,.0f}L | Guia: {r.get('guia_despacho') or '-'} | {status}"
                )

            selected_id = st.selectbox(
                "Seleccione recepcion:",
                options=list(rec_options.keys()),
                format_func=lambda x: rec_options[x],
                index=None, placeholder="Seleccione...",
                key="fact_select"
            )

            if selected_id:
                rec = next(r for r in filtered_rec if r["id"] == selected_id)
                status = rec.get("status", "Recibido")
                color = STATUS_COLORS.get(status, "#999")

                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;margin:10px 0;">'
                    f'<span style="background:{color};color:white;padding:6px 16px;border-radius:4px;'
                    f'font-weight:bold;">{status}</span>'
                    f'<span>Vino: {rec.get("wine_code") or "-"} | '
                    f'Cepa: {(rec.get("grape_varieties") or {}).get("code", "-")} | '
                    f'Proveedor: {(rec.get("suppliers") or {}).get("name", "-")}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                col_r1.metric("Litros Guia", f"{rec.get('litros_guia', 0) or 0:,.0f}")
                col_r2.metric("Litros Recep.", f"{rec.get('liters', 0):,.0f}")
                col_r3.metric("Guia Despacho", rec.get("guia_despacho") or "-")
                col_r4.metric("N OC", rec.get("oc_number") or "-")

                st.markdown("---")

                # --- Estado: Recibido → agregar factura ---
                if status == "Recibido":
                    st.subheader("Registrar Factura")
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        inv_number = st.text_input("N Factura", key="inv_number")
                    with col_f2:
                        inv_date = st.date_input("Fecha Factura", value=date.today(), key="inv_date")
                    with col_f3:
                        inv_amount = st.number_input("Monto Factura", min_value=0.0, step=1000.0, key="inv_amount")

                    if st.button("Registrar Factura", type="primary", use_container_width=True, key="save_inv"):
                        if not inv_number:
                            st.error("Ingrese numero de factura")
                        else:
                            try:
                                update = {
                                    "invoice_number": inv_number,
                                    "invoice_date": str(inv_date),
                                    "status": "Facturado",
                                }
                                if inv_amount > 0:
                                    update["invoice_amount"] = inv_amount
                                queries.update_wine_reception(selected_id, update)
                                st.success("Factura registrada")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

                # --- Estado: Facturado → registrar DO ---
                elif status == "Facturado":
                    st.markdown(f"**Factura:** {rec.get('invoice_number')} | "
                                f"Fecha: {rec.get('invoice_date') or '-'} | "
                                f"Monto: ${rec.get('invoice_amount') or 0:,.0f}")
                    st.subheader("Registrar Liberacion DO")
                    col_do1, col_do2 = st.columns(2)
                    with col_do1:
                        do_number = st.text_input("N DO", key="do_number")
                    with col_do2:
                        do_date = st.date_input("Fecha DO", value=date.today(), key="do_date")

                    if st.button("Registrar DO Liberada", type="primary", use_container_width=True, key="save_do"):
                        if not do_number:
                            st.error("Ingrese numero de DO")
                        else:
                            try:
                                queries.update_wine_reception(selected_id, {
                                    "do_number": do_number,
                                    "do_date": str(do_date),
                                    "do_released": True,
                                    "status": "DO Liberada",
                                })
                                st.success("DO registrada como liberada")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")

                # --- Estado: DO Liberada → aprobar contablemente ---
                elif status == "DO Liberada":
                    st.markdown(f"**Factura:** {rec.get('invoice_number')} | "
                                f"Fecha: {rec.get('invoice_date') or '-'} | "
                                f"Monto: ${rec.get('invoice_amount') or 0:,.0f}")
                    st.markdown(f"**DO:** {rec.get('do_number')} | Fecha: {rec.get('do_date') or '-'}")

                    if st.button("Aprobar para Contabilidad", type="primary", use_container_width=True, key="approve"):
                        try:
                            queries.update_wine_reception(selected_id, {
                                "approved_date": str(date.today()),
                                "approved_by": st.session_state.get("username", "admin"),
                                "status": "Aprobada",
                            })
                            st.success("Recepcion aprobada contablemente")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

                # --- Estado: Aprobada ---
                elif status == "Aprobada":
                    st.markdown(f"**Factura:** {rec.get('invoice_number')} | "
                                f"Fecha: {rec.get('invoice_date') or '-'} | "
                                f"Monto: ${rec.get('invoice_amount') or 0:,.0f}")
                    st.markdown(f"**DO:** {rec.get('do_number')} | Fecha: {rec.get('do_date') or '-'}")
                    st.markdown(f"**Aprobada:** {rec.get('approved_date') or '-'} por {rec.get('approved_by') or '-'}")
                    st.success("Esta recepcion ya fue aprobada contablemente")
