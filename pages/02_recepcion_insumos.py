import streamlit as st
import pandas as pd
from datetime import date
from lib import queries

st.title("Recepcion de Insumos")
st.markdown("Registro de ingreso de insumos enologicos (Ordenes de Compra)")

if "oc_lines" not in st.session_state:
    st.session_state.oc_lines = [{"supply_id": None, "lot_number": "", "expiry_date": None, "quantity": 0.0}]

@st.cache_data(ttl=300)
def load_data():
    return {
        "supplies": queries.get_supplies(),
        "suppliers": queries.get_suppliers(),
    }

try:
    ref = load_data()
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")
    st.stop()

# --- Cabecera OC ---
st.subheader("Nueva Orden de Compra")

col1, col2, col3 = st.columns(3)
with col1:
    oc_date = st.date_input("Fecha", value=date.today())
with col2:
    oc_number = st.text_input("N° Orden de Compra")
with col3:
    supplier_options = {s["id"]: s["name"] for s in ref["suppliers"]}
    supplier_id = st.selectbox("Proveedor", options=list(supplier_options.keys()),
                               format_func=lambda x: supplier_options[x],
                               index=None, placeholder="Seleccione proveedor...")

# --- Lineas ---
st.markdown("---")
st.subheader("Detalle de Insumos")

supply_options = {s["id"]: f"{s['name']} ({s['unit']})" for s in ref["supplies"]}

def add_oc_line():
    st.session_state.oc_lines.append({"supply_id": None, "lot_number": "", "expiry_date": None, "quantity": 0.0})

def remove_oc_line(idx):
    if len(st.session_state.oc_lines) > 1:
        st.session_state.oc_lines.pop(idx)

for i, line in enumerate(st.session_state.oc_lines):
    col_s, col_lot, col_exp, col_q, col_del = st.columns([3, 2, 2, 1.5, 0.5])

    with col_s:
        selected = st.selectbox(
            f"Insumo {i+1}", options=list(supply_options.keys()),
            format_func=lambda x: supply_options[x],
            index=None, placeholder="Seleccione insumo...",
            key=f"oc_supply_{i}"
        )
        st.session_state.oc_lines[i]["supply_id"] = selected

    with col_lot:
        lot_num = st.text_input(f"N° Lote {i+1}", key=f"oc_lot_{i}")
        st.session_state.oc_lines[i]["lot_number"] = lot_num

    with col_exp:
        exp_date = st.date_input(f"Vencimiento {i+1}", value=None, key=f"oc_exp_{i}")
        st.session_state.oc_lines[i]["expiry_date"] = exp_date

    with col_q:
        qty = st.number_input(f"Cantidad {i+1}", value=0.0, min_value=0.0, step=0.1, key=f"oc_qty_{i}")
        st.session_state.oc_lines[i]["quantity"] = qty

    with col_del:
        st.markdown("<br>", unsafe_allow_html=True)
        if len(st.session_state.oc_lines) > 1:
            st.button("X", key=f"oc_del_{i}", on_click=remove_oc_line, args=(i,))

st.button("+ Agregar Insumo", on_click=add_oc_line)

# --- Guardar ---
st.markdown("---")
if st.button("Guardar Recepcion", type="primary"):
    valid_lines = [l for l in st.session_state.oc_lines if l["supply_id"] and l["quantity"] > 0]

    if not valid_lines:
        st.error("Debe agregar al menos un insumo con cantidad mayor a 0")
    else:
        try:
            po_data = {
                "date": str(oc_date),
                "oc_number": oc_number or None,
            }
            if supplier_id:
                po_data["supplier_id"] = supplier_id

            result = queries.create_purchase_order(po_data)
            po_id = result[0]["id"]

            po_lines = []
            for l in valid_lines:
                lot_id = None
                if l["lot_number"]:
                    try:
                        lot_result = queries.create_lot(
                            l["supply_id"],
                            l["lot_number"],
                            l["expiry_date"],
                            initial_stock=0,
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

            st.success(f"Orden de Compra registrada exitosamente ({len(valid_lines)} insumos)")
            st.session_state.oc_lines = [{"supply_id": None, "lot_number": "", "expiry_date": None, "quantity": 0.0}]
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")

# --- Historial ---
st.markdown("---")
st.subheader("Ultimas Recepciones")

try:
    recent_pos = queries.get_purchase_orders(limit=20)
    if recent_pos:
        df = pd.DataFrame(recent_pos)
        df["proveedor"] = df["suppliers"].apply(lambda x: x["name"] if x else "-")
        st.dataframe(
            df[["date", "oc_number", "proveedor"]].rename(columns={
                "date": "Fecha",
                "oc_number": "N° OC",
                "proveedor": "Proveedor",
            }),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No hay recepciones registradas")
except Exception as e:
    st.warning(f"No se pudo cargar el historial: {e}")
