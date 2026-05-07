import streamlit as st
import pandas as pd
from lib import queries

st.title("Stock de Insumos Enologicos")

tab_total, tab_lotes, tab_alertas = st.tabs(["Por Insumo", "Por Lote", "Alertas"])

# --- Tab 1: Stock por insumo ---
with tab_total:
    st.subheader("Stock Total por Insumo")
    try:
        data = queries.get_stock_total()
        if data:
            df = pd.DataFrame(data)
            df = df.rename(columns={
                "supply_name": "Insumo",
                "supply_code": "Codigo",
                "unit": "Unidad",
                "total_initial": "Inicial",
                "total_entries": "Entradas",
                "total_exits": "Salidas",
                "total_stock": "Stock Actual",
                "active_lots": "Lotes Activos",
            })

            search = st.text_input("Buscar insumo:", placeholder="Escriba para filtrar...")
            if search:
                df = df[df["Insumo"].str.contains(search, case=False, na=False)]

            def highlight_stock(row):
                if row["Stock Actual"] <= 0:
                    return ["background-color: #ffcccc"] * len(row)
                elif row["Stock Actual"] < 10:
                    return ["background-color: #fff3cd"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df[["Codigo", "Insumo", "Unidad", "Stock Actual", "Entradas", "Salidas", "Lotes Activos"]]
                .sort_values("Insumo")
                .style.apply(highlight_stock, axis=1),
                use_container_width=True,
                hide_index=True,
                height=600,
            )
            st.caption(f"Total: {len(df)} insumos")
        else:
            st.info("No hay datos de stock. Registre recepciones o cargue inventario inicial.")
    except Exception as e:
        st.error(f"Error al cargar stock: {e}")

# --- Tab 2: Stock por lote ---
with tab_lotes:
    st.subheader("Stock Detallado por Lote")
    try:
        data = queries.get_stock_by_lot()
        if data:
            df = pd.DataFrame(data)
            df = df.rename(columns={
                "supply_name": "Insumo",
                "supply_code": "Codigo",
                "lot_number": "Lote",
                "expiry_date": "Vencimiento",
                "current_stock": "Stock",
                "expiry_status": "Estado",
                "unit": "Unidad",
            })

            search = st.text_input("Buscar:", placeholder="Filtrar por insumo o lote...", key="search_lot")
            if search:
                mask = (df["Insumo"].str.contains(search, case=False, na=False) |
                        df["Lote"].astype(str).str.contains(search, case=False, na=False))
                df = df[mask]

            def highlight_expiry(row):
                if row["Estado"] == "VENCIDO":
                    return ["background-color: #ffcccc"] * len(row)
                elif row["Estado"] == "POR VENCER":
                    return ["background-color: #fff3cd"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df[["Codigo", "Insumo", "Lote", "Vencimiento", "Stock", "Unidad", "Estado"]]
                .sort_values(["Insumo", "Vencimiento"])
                .style.apply(highlight_expiry, axis=1),
                use_container_width=True,
                hide_index=True,
                height=600,
            )
        else:
            st.info("No hay lotes registrados")
    except Exception as e:
        st.error(f"Error al cargar lotes: {e}")

# --- Tab 3: Alertas ---
with tab_alertas:
    col_low, col_exp = st.columns(2)

    with col_low:
        st.subheader("Stock Bajo Minimo")
        try:
            alerts = queries.get_low_stock_alerts()
            if alerts:
                df = pd.DataFrame(alerts)
                df = df.rename(columns={
                    "name": "Insumo",
                    "code": "Codigo",
                    "unit": "Unidad",
                    "min_stock": "Stock Minimo",
                    "current_stock": "Stock Actual",
                    "deficit": "Deficit",
                })
                st.dataframe(
                    df[["Insumo", "Unidad", "Stock Minimo", "Stock Actual", "Deficit"]]
                    .style.background_gradient(subset=["Deficit"], cmap="Reds"),
                    use_container_width=True,
                    hide_index=True,
                )
                st.warning(f"{len(alerts)} insumos bajo stock minimo")
            else:
                st.success("Todos los insumos sobre stock minimo")
        except Exception as e:
            st.error(f"Error: {e}")

    with col_exp:
        st.subheader("Lotes Vencidos / Por Vencer")
        try:
            alerts = queries.get_expiry_alerts()
            if alerts:
                df = pd.DataFrame(alerts)
                df = df.rename(columns={
                    "supply_name": "Insumo",
                    "lot_number": "Lote",
                    "expiry_date": "Vencimiento",
                    "current_stock": "Stock",
                    "expiry_status": "Estado",
                })

                vencidos = df[df["Estado"] == "VENCIDO"]
                por_vencer = df[df["Estado"] == "POR VENCER"]

                if not vencidos.empty:
                    st.error(f"{len(vencidos)} lotes VENCIDOS con stock")
                    st.dataframe(vencidos[["Insumo", "Lote", "Vencimiento", "Stock"]],
                                use_container_width=True, hide_index=True)

                if not por_vencer.empty:
                    st.warning(f"{len(por_vencer)} lotes por vencer (< 90 dias)")
                    st.dataframe(por_vencer[["Insumo", "Lote", "Vencimiento", "Stock"]],
                                use_container_width=True, hide_index=True)

                if vencidos.empty and por_vencer.empty:
                    st.success("Sin alertas de vencimiento")
            else:
                st.success("Sin alertas de vencimiento")
        except Exception as e:
            st.error(f"Error: {e}")
