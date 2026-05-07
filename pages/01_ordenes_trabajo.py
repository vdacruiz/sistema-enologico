import streamlit as st
import pandas as pd
from datetime import date
from lib import queries
from lib.stock_engine import get_lots_with_stock, check_availability

st.title("Ordenes de Trabajo")
st.markdown("Registro de egreso de insumos enologicos")

# Inicializar lineas en session_state
if "ot_lines" not in st.session_state:
    st.session_state.ot_lines = [{"supply_id": None, "lot_id": None, "quantity": 0.0}]

# --- Cargar datos de referencia ---
@st.cache_data(ttl=300)
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
    st.info("Verifica que las tablas existan en Supabase y que las credenciales sean correctas.")
    st.stop()

# --- Formulario de cabecera ---
st.subheader("Nueva Orden de Trabajo")

col1, col2, col3 = st.columns(3)
with col1:
    ot_date = st.date_input("Fecha", value=date.today())
    try:
        next_ot = queries.get_next_ot_number()
    except Exception:
        next_ot = 1
    ot_number = st.number_input("N° OT", value=next_ot, min_value=1, step=1)

with col2:
    grape_options = {g["id"]: f"{g['code']} - {g['name']}" for g in ref["grape_varieties"]}
    grape_id = st.selectbox("Cepa", options=list(grape_options.keys()),
                            format_func=lambda x: grape_options[x],
                            index=None, placeholder="Seleccione cepa...")

    line_options = {l["id"]: l["name"] for l in ref["product_lines"]}
    line_id = st.selectbox("Linea de Producto", options=list(line_options.keys()),
                           format_func=lambda x: line_options[x],
                           index=None, placeholder="Seleccione linea...")

with col3:
    process_options = {p["id"]: p["name"] for p in ref["processes"]}
    process_id = st.selectbox("Operacion", options=list(process_options.keys()),
                              format_func=lambda x: process_options[x],
                              index=None, placeholder="Seleccione operacion...")

    worker_options = {w["id"]: w["full_name"] for w in ref["workers"]}
    worker_id = st.selectbox("Operario", options=list(worker_options.keys()),
                             format_func=lambda x: worker_options[x],
                             index=None, placeholder="Seleccione operario...")

# Cubas
col_t1, col_t2, col_t3 = st.columns(3)
with col_t1:
    tank_options = {t["id"]: f"Cuba {t['code']}" + (f" ({t['capacity_liters']}L)" if t.get("capacity_liters") else "")
                    for t in ref["tanks"]}
    source_tank_id = st.selectbox("Cuba Inicial", options=list(tank_options.keys()),
                                  format_func=lambda x: tank_options[x],
                                  index=None, placeholder="Seleccione cuba...")
with col_t2:
    dest_tank_id = st.selectbox("Cuba Destino", options=list(tank_options.keys()),
                                format_func=lambda x: tank_options[x],
                                index=None, placeholder="Seleccione cuba...")
with col_t3:
    liters = st.number_input("Litros", value=0, min_value=0, step=100)

# --- Lineas de insumos ---
st.markdown("---")
st.subheader("Insumos Utilizados")

supply_options = {s["id"]: f"{s['name']} ({s['unit']})" for s in ref["supplies"]}

def add_line():
    st.session_state.ot_lines.append({"supply_id": None, "lot_id": None, "quantity": 0.0})

def remove_line(idx):
    if len(st.session_state.ot_lines) > 1:
        st.session_state.ot_lines.pop(idx)

for i, line in enumerate(st.session_state.ot_lines):
    col_s, col_l, col_q, col_stock, col_del = st.columns([3, 2, 1.5, 1.5, 0.5])

    with col_s:
        selected_supply = st.selectbox(
            f"Insumo {i+1}", options=list(supply_options.keys()),
            format_func=lambda x: supply_options[x],
            index=None, placeholder="Seleccione insumo...",
            key=f"supply_{i}"
        )
        st.session_state.ot_lines[i]["supply_id"] = selected_supply

    with col_l:
        if selected_supply:
            lots = get_lots_with_stock(selected_supply)
            lot_options = {}
            for lt in lots:
                expiry = lt.get("expiry_date") or "S/V"
                status = lt.get("expiry_status", "")
                label = f"Lote {lt['lot_number']} - Stock: {lt['current_stock']:.1f}"
                if status == "VENCIDO":
                    label += " [VENCIDO]"
                elif status == "POR VENCER":
                    label += " [POR VENCER]"
                lot_options[lt["lot_id"]] = label

            if lot_options:
                selected_lot = st.selectbox(
                    f"Lote {i+1}", options=list(lot_options.keys()),
                    format_func=lambda x: lot_options[x],
                    index=None, placeholder="Seleccione lote...",
                    key=f"lot_{i}"
                )
                st.session_state.ot_lines[i]["lot_id"] = selected_lot
            else:
                st.warning("Sin stock")
                st.session_state.ot_lines[i]["lot_id"] = None
        else:
            st.selectbox(f"Lote {i+1}", options=[], placeholder="Primero seleccione insumo...",
                        key=f"lot_{i}")

    with col_q:
        qty = st.number_input(f"Cantidad {i+1}", value=0.0, min_value=0.0, step=0.1,
                              key=f"qty_{i}")
        st.session_state.ot_lines[i]["quantity"] = qty

    with col_stock:
        if selected_supply and st.session_state.ot_lines[i].get("lot_id") and qty > 0:
            ok, msg = check_availability(selected_supply, st.session_state.ot_lines[i]["lot_id"], qty)
            if ok:
                st.success("OK")
            else:
                st.error(msg)
        else:
            st.empty()

    with col_del:
        st.markdown("<br>", unsafe_allow_html=True)
        if len(st.session_state.ot_lines) > 1:
            st.button("X", key=f"del_{i}", on_click=remove_line, args=(i,))

st.button("+ Agregar Insumo", on_click=add_line)

# --- Guardar OT ---
st.markdown("---")
if st.button("Guardar Orden de Trabajo", type="primary"):
    valid_lines = [l for l in st.session_state.ot_lines if l["supply_id"] and l["quantity"] > 0]

    if not valid_lines:
        st.error("Debe agregar al menos un insumo con cantidad mayor a 0")
    else:
        errors = []
        for l in valid_lines:
            if l["lot_id"]:
                ok, msg = check_availability(l["supply_id"], l["lot_id"], l["quantity"])
                if not ok:
                    supply_name = supply_options.get(l["supply_id"], "?")
                    errors.append(f"{supply_name}: {msg}")

        if errors:
            for err in errors:
                st.error(err)
        else:
            try:
                wo_data = {
                    "ot_number": int(ot_number),
                    "date": str(ot_date),
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
                        "lot_id": l["lot_id"],
                        "quantity": l["quantity"],
                    })
                queries.create_work_order_lines(wo_lines)

                st.success(f"Orden de Trabajo N° {ot_number} guardada exitosamente")
                st.session_state.ot_lines = [{"supply_id": None, "lot_id": None, "quantity": 0.0}]
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# --- Historial de OTs ---
st.markdown("---")
st.subheader("Ultimas Ordenes de Trabajo")

try:
    recent_ots = queries.get_work_orders(limit=20)
    if recent_ots:
        df = pd.DataFrame(recent_ots)
        display_cols = {
            "ot_number": "N° OT",
            "date": "Fecha",
        }
        if "grape_varieties" in df.columns:
            df["cepa"] = df["grape_varieties"].apply(lambda x: x["code"] if x else "-")
            display_cols["cepa"] = "Cepa"
        if "winemaking_processes" in df.columns:
            df["operacion"] = df["winemaking_processes"].apply(lambda x: x["name"] if x else "-")
            display_cols["operacion"] = "Operacion"
        if "workers" in df.columns:
            df["operario"] = df["workers"].apply(lambda x: x["full_name"] if x else "-")
            display_cols["operario"] = "Operario"
        if "liters" in df.columns:
            display_cols["liters"] = "Litros"

        st.dataframe(
            df[list(display_cols.keys())].rename(columns=display_cols),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No hay ordenes de trabajo registradas")
except Exception as e:
    st.warning(f"No se pudo cargar el historial: {e}")
