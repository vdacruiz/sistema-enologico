import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from lib import queries

st.set_page_config(layout="wide") if not hasattr(st, "_page_config_set") else None

st.title("Stock de Cubas")

try:
    tanks = queries.get_tanks()
    contents = queries.get_tank_contents()
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

content_map = {c["tank_id"]: c for c in contents}

tank_data = []
for t in tanks:
    c = content_map.get(t["id"], {})
    status = c.get("status", "Vacio") if c else "Vacio"
    liters = c.get("current_liters", 0) or 0
    capacity = t.get("capacity_liters", 0) or 0
    pct = (liters / capacity * 100) if capacity > 0 else 0

    wine = c.get("wines") if c else None
    wine_code = wine.get("code", "") if wine and isinstance(wine, dict) else ""
    grape = c.get("grape_varieties") if c else None
    grape_code = grape.get("code", "") if grape and isinstance(grape, dict) else ""
    grape_name = grape.get("name", "") if grape and isinstance(grape, dict) else ""
    wine_type = c.get("wine_type", "") if c else ""

    tank_data.append({
        "id": t["id"],
        "code": t["code"],
        "capacity": capacity,
        "liters": liters,
        "pct": round(pct, 1),
        "status": status,
        "wine_code": wine_code,
        "grape_code": grape_code,
        "grape_name": grape_name,
        "wine_type": wine_type or "",
    })

TYPE_COLORS = {
    "Tinto": {"bg": "#8B0000", "fill": "#DC143C", "light": "#f8d7da", "text": "#721c24"},
    "Blanco": {"bg": "#B8860B", "fill": "#FFD700", "light": "#fff3cd", "text": "#856404"},
    "Rosado": {"bg": "#C71585", "fill": "#FF69B4", "light": "#f5c6d0", "text": "#8B0A50"},
    "": {"bg": "#6c757d", "fill": "#adb5bd", "light": "#e2e3e5", "text": "#383d41"},
}

STATUS_ICONS = {"Ocupado": "🟢", "Vacio": "⚪", "En proceso": "🟡", "Limpieza": "🔵"}

# === METRICAS PRINCIPALES ===
total = len(tank_data)
ocupadas = sum(1 for t in tank_data if t["status"] == "Ocupado")
vacias = sum(1 for t in tank_data if t["status"] == "Vacio")
total_liters = sum(t["liters"] for t in tank_data)
tanks_with_cap = [t for t in tank_data if t["capacity"] > 0]
total_capacity = sum(t["capacity"] for t in tanks_with_cap)
liters_with_cap = sum(t["liters"] for t in tanks_with_cap)
occupancy_pct = (liters_with_cap / total_capacity * 100) if total_capacity > 0 else 0

col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
col_m1.metric("Total Cubas", total)
col_m2.metric("Ocupadas", ocupadas)
col_m3.metric("Vacias", vacias)
col_m4.metric("Litros Totales", f"{total_liters:,.0f}")
col_m5.metric("Capacidad Total", f"{total_capacity:,.0f}")

# === FILTROS ===
st.markdown("---")
col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.5, 1.5, 2])

with col_f1:
    filter_status = st.selectbox("Estado:", ["Todos", "Ocupado", "Vacio", "En proceso", "Limpieza"], key="tc_status")

with col_f2:
    wine_types = sorted(set(t["wine_type"] for t in tank_data if t["wine_type"]))
    filter_type = st.selectbox("Tipo vino:", ["Todos"] + wine_types, key="tc_type")

with col_f3:
    grape_codes = sorted(set(t["grape_code"] for t in tank_data if t["grape_code"]))
    filter_grape = st.selectbox("Cepa:", ["Todas"] + grape_codes, key="tc_grape")

with col_f4:
    search = st.text_input("Buscar:", placeholder="Cuba, vino, cepa...", key="tc_search")

filtered = tank_data
if filter_status != "Todos":
    filtered = [t for t in filtered if t["status"] == filter_status]
if filter_type != "Todos":
    filtered = [t for t in filtered if t["wine_type"] == filter_type]
if filter_grape != "Todas":
    filtered = [t for t in filtered if t["grape_code"] == filter_grape]
if search:
    s = search.lower()
    filtered = [t for t in filtered if
                s in t["code"].lower() or s in t["wine_code"].lower() or
                s in t["grape_code"].lower() or s in t["grape_name"].lower()]

# === GRAFICOS RESUMEN ===
tab_visual, tab_tabla, tab_graficos = st.tabs(["Vista Cubas", "Tabla", "Graficos"])

with tab_visual:
    st.markdown(f"**{len(filtered)}** cubas" + (f" (filtradas de {total})" if len(filtered) != total else ""))

    cols_per_row = 6
    for i in range(0, len(filtered), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(filtered):
                break
            t = filtered[idx]
            tc = TYPE_COLORS.get(t["wine_type"], TYPE_COLORS[""])
            fill_color = tc["fill"]
            status_icon = STATUS_ICONS.get(t["status"], "⚪")
            pct = min(t["pct"], 100)
            bar_height = max(int(pct * 0.6), 2) if pct > 0 else 0

            label_line1 = t["wine_code"][:18] if t["wine_code"] else t["status"]
            label_line2 = f"{t['grape_code']}" if t["grape_code"] else ""

            with col:
                st.markdown(f"""
                <div style="background:#fff;border-radius:8px;padding:8px;margin-bottom:8px;
                            box-shadow:0 1px 3px rgba(0,0,0,0.12);border:1px solid #e0e0e0;
                            min-height:160px;position:relative;">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <strong style="font-size:1.1em;">{t['code']}</strong>
                        <span style="font-size:0.7em;">{status_icon}</span>
                    </div>
                    <div style="background:#f0f0f0;border-radius:4px;height:60px;margin:6px 0;
                                position:relative;overflow:hidden;">
                        <div style="position:absolute;bottom:0;width:100%;height:{bar_height}px;
                                    background:{fill_color};border-radius:0 0 4px 4px;
                                    transition:height 0.3s;opacity:0.8;"></div>
                        <div style="position:absolute;width:100%;text-align:center;top:50%;
                                    transform:translateY(-50%);font-size:0.85em;font-weight:bold;
                                    color:#333;">{t['pct']}%</div>
                    </div>
                    <div style="font-size:0.75em;color:#555;line-height:1.3;">
                        <div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                             title="{t['wine_code']}">{label_line1}</div>
                        <div>{label_line2}</div>
                        <div style="color:#888;">{t['liters']:,.0f} / {t['capacity']:,.0f} L</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # Detalle al seleccionar cuba
    st.markdown("---")
    if filtered:
        detail_options = {t["id"]: f"Cuba {t['code']} - {t['wine_code'] or t['status']}" for t in filtered}
        sel_tank = st.selectbox("Detalle de cuba:", options=list(detail_options.keys()),
                                format_func=lambda x: detail_options[x], index=None,
                                placeholder="Seleccione cuba...", key="tc_detail")
        if sel_tank:
            t = next(x for x in filtered if x["id"] == sel_tank)
            tc = TYPE_COLORS.get(t["wine_type"], TYPE_COLORS[""])
            pct = min(t["pct"], 100)

            col_d1, col_d2, col_d3 = st.columns([1, 2, 1])
            with col_d1:
                st.markdown(f"""
                <div style="background:{tc['light']};border-radius:12px;padding:20px;text-align:center;">
                    <div style="font-size:2.5em;font-weight:bold;color:{tc['text']};">
                        {t['code']}
                    </div>
                    <div style="background:#e0e0e0;border-radius:8px;height:120px;margin:15px auto;
                                width:80px;position:relative;overflow:hidden;">
                        <div style="position:absolute;bottom:0;width:100%;height:{pct*1.2:.0f}px;
                                    background:{tc['fill']};border-radius:0 0 8px 8px;opacity:0.85;"></div>
                        <div style="position:absolute;width:100%;text-align:center;top:45%;
                                    font-size:1.2em;font-weight:bold;color:#333;">{pct:.0f}%</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_d2:
                st.markdown(f"""
                | Campo | Valor |
                |-------|-------|
                | **Codigo Vino** | {t['wine_code'] or '-'} |
                | **Cepa** | {t['grape_code']} {t['grape_name']} |
                | **Tipo** | {t['wine_type'] or '-'} |
                | **Estado** | {STATUS_ICONS.get(t['status'], '')} {t['status']} |
                | **Litros** | {t['liters']:,.0f} |
                | **Capacidad** | {t['capacity']:,.0f} L |
                | **Ocupacion** | {t['pct']}% |
                """)

            with col_d3:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=pct,
                    number={"suffix": "%"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": tc["fill"]},
                        "bgcolor": "#f0f0f0",
                        "steps": [
                            {"range": [0, 30], "color": "#f8f9fa"},
                            {"range": [30, 70], "color": "#e9ecef"},
                            {"range": [70, 100], "color": "#dee2e6"},
                        ],
                    },
                ))
                fig.update_layout(height=200, margin=dict(t=30, b=10, l=30, r=30))
                st.plotly_chart(fig, use_container_width=True)

with tab_tabla:
    if filtered:
        rows = []
        for t in filtered:
            rows.append({
                "Cuba": t["code"],
                "Vino": t["wine_code"] or "-",
                "Cepa": t["grape_code"] or "-",
                "Tipo": t["wine_type"] or "-",
                "Litros": t["liters"],
                "Capacidad": t["capacity"],
                "% Uso": t["pct"],
                "Estado": t["status"],
            })
        df = pd.DataFrame(rows)

        def color_tipo(val):
            m = {"Tinto": "background-color:#f8d7da;color:#721c24",
                 "Blanco": "background-color:#fff3cd;color:#856404",
                 "Rosado": "background-color:#f5c6d0;color:#8B0A50"}
            return m.get(val, "")

        def color_pct(val):
            if val >= 90:
                return "background-color:#d4edda"
            elif val >= 50:
                return "background-color:#fff3cd"
            elif val > 0:
                return "background-color:#f8d7da"
            return ""

        st.dataframe(
            df.style.map(color_tipo, subset=["Tipo"]).map(color_pct, subset=["% Uso"]),
            use_container_width=True, hide_index=True, height=600,
        )
        st.caption(f"{len(df)} cubas")
    else:
        st.info("Sin cubas para mostrar")

with tab_graficos:
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("Litros por Cepa")
        cepa_data = {}
        for t in tank_data:
            if t["liters"] > 0 and t["grape_code"]:
                key = t["grape_code"]
                cepa_data[key] = cepa_data.get(key, 0) + t["liters"]
        if cepa_data:
            df_cepa = pd.DataFrame([{"Cepa": k, "Litros": v} for k, v in cepa_data.items()])
            df_cepa = df_cepa.sort_values("Litros", ascending=True)
            fig = px.bar(df_cepa, x="Litros", y="Cepa", orientation="h",
                         color="Litros", color_continuous_scale="Reds")
            fig.update_layout(height=400, showlegend=False, margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with col_g2:
        st.subheader("Litros por Tipo")
        type_data = {}
        type_colors_chart = {"Tinto": "#DC143C", "Blanco": "#FFD700", "Rosado": "#FF69B4"}
        for t in tank_data:
            if t["liters"] > 0 and t["wine_type"]:
                type_data[t["wine_type"]] = type_data.get(t["wine_type"], 0) + t["liters"]
        if type_data:
            df_type = pd.DataFrame([{"Tipo": k, "Litros": v} for k, v in type_data.items()])
            colors = [type_colors_chart.get(t, "#adb5bd") for t in df_type["Tipo"]]
            fig = px.pie(df_type, names="Tipo", values="Litros",
                         color="Tipo", color_discrete_map=type_colors_chart)
            fig.update_layout(height=400, margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

    col_g3, col_g4 = st.columns(2)

    with col_g3:
        st.subheader("Ocupacion por Estado")
        status_data = {}
        for t in tank_data:
            status_data[t["status"]] = status_data.get(t["status"], 0) + 1
        if status_data:
            df_status = pd.DataFrame([{"Estado": k, "Cubas": v} for k, v in status_data.items()])
            status_colors = {"Ocupado": "#28a745", "Vacio": "#dee2e6", "En proceso": "#ffc107", "Limpieza": "#17a2b8"}
            fig = px.pie(df_status, names="Estado", values="Cubas",
                         color="Estado", color_discrete_map=status_colors)
            fig.update_layout(height=350, margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with col_g4:
        st.subheader("Top 15 Cubas por Litros")
        top = sorted([t for t in tank_data if t["liters"] > 0], key=lambda x: -x["liters"])[:15]
        if top:
            df_top = pd.DataFrame([{"Cuba": t["code"], "Litros": t["liters"], "Tipo": t["wine_type"] or "-"} for t in top])
            fig = px.bar(df_top, x="Cuba", y="Litros", color="Tipo",
                         color_discrete_map={"Tinto": "#DC143C", "Blanco": "#FFD700", "Rosado": "#FF69B4", "-": "#adb5bd"})
            fig.update_layout(height=350, margin=dict(t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
