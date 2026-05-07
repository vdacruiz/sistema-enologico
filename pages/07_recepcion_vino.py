import streamlit as st
import pandas as pd
from datetime import date
from lib import queries

st.title("Recepcion de Vino")
st.markdown("Registro de ingreso de vino comprado o de vendimia")

@st.cache_data(ttl=300)
def load_ref():
    return {
        "grape_varieties": queries.get_grape_varieties(),
        "product_lines": queries.get_product_lines(),
        "suppliers": queries.get_suppliers(),
        "tanks": queries.get_tanks(),
    }

try:
    ref = load_ref()
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")
    st.stop()

tab_nueva, tab_historial = st.tabs(["Nueva Recepcion", "Historial"])

# =============================================================
# TAB: Nueva Recepcion
# =============================================================
with tab_nueva:
    # Tipo de recepcion
    reception_type = st.radio(
        "Tipo de recepcion:",
        ["Compra Vino", "Vendimia"],
        horizontal=True,
    )

    st.markdown("---")

    # --- Cabecera ---
    col1, col2, col3 = st.columns(3)
    with col1:
        rec_date = st.date_input("Fecha", value=date.today(), key="rv_date")
    with col2:
        cepa_options = {g["id"]: f"{g['code']} - {g['name']}" for g in ref["grape_varieties"]}
        cepa_id = st.selectbox(
            "Cepa", options=list(cepa_options.keys()),
            format_func=lambda x: cepa_options[x],
            index=None, placeholder="Seleccione cepa...", key="rv_cepa"
        )
    with col3:
        line_options = {p["id"]: p["name"] for p in ref["product_lines"]}
        line_id = st.selectbox(
            "Linea de Producto", options=list(line_options.keys()),
            format_func=lambda x: line_options[x],
            index=None, placeholder="Seleccione linea...", key="rv_line"
        )

    # Determinar tipo de vino segun cepa
    wine_type_val = None
    if cepa_id:
        cepa_data = next((g for g in ref["grape_varieties"] if g["id"] == cepa_id), None)
        if cepa_data:
            wine_type_val = cepa_data.get("wine_type", "Tinto")

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
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        liters = st.number_input("Litros", min_value=0, step=100, key="rv_liters")
    with col_v2:
        alcohol = st.number_input("Grado Alcoholico (%vol)", min_value=0.0, max_value=20.0, step=0.1, key="rv_alcohol")
    with col_v3:
        so2_total = st.number_input("SO2 Total (mg/L)", min_value=0.0, step=1.0, key="rv_so2")

    if reception_type == "Vendimia":
        col_vd1, col_vd2, col_vd3 = st.columns(3)
        with col_vd1:
            kilos = st.number_input("Kilos Uva", min_value=0.0, step=100.0, key="rv_kilos")
        with col_vd2:
            brix = st.number_input("Brix", min_value=0.0, max_value=35.0, step=0.1, key="rv_brix")
        with col_vd3:
            ph = st.number_input("pH", min_value=0.0, max_value=5.0, step=0.01, key="rv_ph")
    else:
        kilos = None
        brix = None
        ph = None

    # --- Cuba destino ---
    st.subheader("Destino")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        tank_options = {t["id"]: f"{t['code']} - {t.get('name') or ''} ({t.get('capacity_liters', 0)} L)"
                        for t in ref["tanks"]}
        dest_tank = st.selectbox(
            "Cuba Destino", options=list(tank_options.keys()),
            format_func=lambda x: tank_options[x],
            index=None, placeholder="Seleccione cuba...", key="rv_tank"
        )
    with col_d2:
        wine_code = st.text_input("Codigo de Vino (YY/YY-NNN)", key="rv_wine_code",
                                  placeholder="Ej: 24/25-001")

    notes = st.text_area("Observaciones", key="rv_notes", placeholder="Notas adicionales...")

    # --- Guardar ---
    st.markdown("---")
    if st.button("Registrar Recepcion", type="primary", use_container_width=True):
        if not cepa_id:
            st.error("Debe seleccionar una cepa")
        elif liters <= 0:
            st.error("Debe ingresar litros mayor a 0")
        elif reception_type == "Compra Vino" and not supplier_id:
            st.error("Debe seleccionar un proveedor para compras")
        else:
            try:
                data = {
                    "date": str(rec_date),
                    "grape_variety_id": cepa_id,
                    "reception_type": reception_type,
                    "liters": liters,
                    "status": "Recibido",
                }
                if line_id:
                    data["product_line_id"] = line_id
                if wine_type_val:
                    data["wine_type"] = wine_type_val
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
                if wine_code:
                    data["wine_code"] = wine_code
                if notes:
                    data["notes"] = notes
                if kilos and kilos > 0:
                    data["kilos"] = kilos
                if brix and brix > 0:
                    data["brix"] = brix
                if ph and ph > 0:
                    data["ph"] = ph

                result = queries.create_wine_reception(data)
                st.success(f"Recepcion registrada exitosamente (ID: {result[0]['id']})")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# =============================================================
# TAB: Historial
# =============================================================
with tab_historial:
    st.subheader("Recepciones Registradas")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filter_type = st.selectbox("Tipo:", ["Todos", "Compra Vino", "Vendimia"], key="rv_filter_type")
    with col_f2:
        filter_search = st.text_input("Buscar:", placeholder="Cepa, proveedor, codigo...", key="rv_filter_search")

    try:
        receptions = queries.get_wine_receptions(limit=100)
        if receptions:
            rows = []
            for r in receptions:
                cepa = r.get("grape_varieties")
                cepa_txt = cepa.get("code", "-") if cepa else "-"
                linea = r.get("product_lines")
                linea_txt = linea.get("name", "-") if linea else "-"

                rows.append({
                    "ID": r["id"],
                    "Fecha": r.get("date", "-"),
                    "Tipo": r.get("reception_type", "-"),
                    "Cepa": cepa_txt,
                    "Linea": linea_txt,
                    "Litros": r.get("liters", 0),
                    "Grado": r.get("alcohol_degree") or "-",
                    "SO2T": r.get("so2_total") or "-",
                    "Codigo Vino": r.get("wine_code") or "-",
                    "Estado": r.get("status", "-"),
                })

            df = pd.DataFrame(rows)

            if filter_type != "Todos":
                df = df[df["Tipo"] == filter_type]
            if filter_search:
                mask = df.astype(str).apply(lambda row: row.str.contains(filter_search, case=False).any(), axis=1)
                df = df[mask]

            def color_type(val):
                if val == "Compra Vino":
                    return "background-color: #d4edda"
                elif val == "Vendimia":
                    return "background-color: #fff3cd"
                return ""

            st.dataframe(
                df.style.map(color_type, subset=["Tipo"]),
                use_container_width=True,
                hide_index=True,
                height=500,
            )
            st.caption(f"Mostrando {len(df)} recepciones")
        else:
            st.info("No hay recepciones registradas")
    except Exception as e:
        st.warning(f"No se pudo cargar el historial: {e}")
