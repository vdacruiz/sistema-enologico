import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from lib import queries

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
    pct = min((liters / capacity * 100) if capacity > 0 else 0, 100)

    wine = c.get("wines") if c else None
    wine_code = wine.get("code", "") if wine and isinstance(wine, dict) else ""
    grape = c.get("grape_varieties") if c else None
    grape_code = grape.get("code", "") if grape and isinstance(grape, dict) else ""
    grape_name = grape.get("name", "") if grape and isinstance(grape, dict) else ""
    pl = c.get("product_lines") if c else None
    pl_name = pl.get("name", "") if pl and isinstance(pl, dict) else ""
    wine_type = c.get("wine_type", "") if c else ""
    wine_state = c.get("wine_state", "") if c else ""

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
        "product_line": pl_name,
        "wine_type": wine_type or "",
        "wine_state": wine_state or "",
        "vintage_year": c.get("vintage_year") if c else None,
        "ph": c.get("ph") if c else None,
        "total_acidity": c.get("total_acidity") if c else None,
        "volatile_acidity": c.get("volatile_acidity") if c else None,
        "free_so2": c.get("free_so2") if c else None,
        "total_so2": c.get("total_so2") if c else None,
        "residual_sugar": c.get("residual_sugar") if c else None,
        "so2_molecular": c.get("so2_molecular") if c else None,
        "alcohol_degree": c.get("alcohol_degree") if c else None,
        "ntu": c.get("ntu") if c else None,
        "color": c.get("color") if c else None,
        "co2": c.get("co2") if c else None,
        "fml": c.get("fml") if c else None,
        "last_analysis_date": c.get("last_analysis_date") if c else None,
    })

TYPE_COLORS = {
    "Tinto": {"fill": "#DC143C", "light": "#f8d7da", "text": "#721c24", "border": "#c62828"},
    "Blanco": {"fill": "#FFD700", "light": "#fff8e1", "text": "#856404", "border": "#f9a825"},
    "Rosado": {"fill": "#FF69B4", "light": "#fce4ec", "text": "#8B0A50", "border": "#d81b60"},
    "": {"fill": "#adb5bd", "light": "#e2e3e5", "text": "#383d41", "border": "#6c757d"},
}

STATE_COLORS = {
    "Sulfitado": "#2196F3",
    "Estabilizado": "#4CAF50",
    "VENDIMIA": "#FF9800",
    "Trasegada": "#9C27B0",
}

# === METRICAS ===
total = len(tank_data)
ocupadas = sum(1 for t in tank_data if t["liters"] > 0)
vacias = total - ocupadas
total_liters = sum(t["liters"] for t in tank_data)
tanks_cap = [t for t in tank_data if t["capacity"] > 0]
total_capacity = sum(t["capacity"] for t in tanks_cap)

states = {}
for t in tank_data:
    if t["wine_state"]:
        states[t["wine_state"]] = states.get(t["wine_state"], 0) + 1

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Total Cubas", total)
col_m2.metric("Con Vino", ocupadas)
col_m3.metric("Vacias", vacias)
col_m4.metric("Litros Totales", f"{total_liters:,.0f}")

# Estado badges
if states:
    state_html = " ".join(
        f'<span style="background:{STATE_COLORS.get(s, "#607D8B")};color:white;'
        f'padding:3px 10px;border-radius:12px;font-size:0.8em;margin-right:4px;">'
        f'{s}: {c}</span>'
        for s, c in sorted(states.items(), key=lambda x: -x[1])
    )
    st.markdown(f'<div style="margin:8px 0;">{state_html}</div>', unsafe_allow_html=True)

# === FILTROS ===
st.markdown("---")
col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns([1.5, 1, 1, 1, 2])

with col_f1:
    filter_state = st.selectbox("Estado Vino:", ["Todos"] + sorted(states.keys()), key="tc_state")
with col_f2:
    wine_types = sorted(set(t["wine_type"] for t in tank_data if t["wine_type"]))
    filter_type = st.selectbox("Tipo:", ["Todos"] + wine_types, key="tc_type")
with col_f3:
    grape_codes = sorted(set(t["grape_code"] for t in tank_data if t["grape_code"]))
    filter_grape = st.selectbox("Cepa:", ["Todas"] + grape_codes, key="tc_grape")
with col_f4:
    plines = sorted(set(t["product_line"] for t in tank_data if t["product_line"]))
    filter_pl = st.selectbox("Linea:", ["Todas"] + plines, key="tc_pl")
with col_f5:
    search = st.text_input("Buscar:", placeholder="Cuba, vino, cepa...", key="tc_search")

filtered = tank_data
if filter_state != "Todos":
    filtered = [t for t in filtered if t["wine_state"] == filter_state]
if filter_type != "Todos":
    filtered = [t for t in filtered if t["wine_type"] == filter_type]
if filter_grape != "Todas":
    filtered = [t for t in filtered if t["grape_code"] == filter_grape]
if filter_pl != "Todas":
    filtered = [t for t in filtered if t["product_line"] == filter_pl]
if search:
    s = search.lower()
    filtered = [t for t in filtered if
                s in t["code"].lower() or s in t["wine_code"].lower() or
                s in t["grape_code"].lower() or s in t["grape_name"].lower()]

# === GRILLA DE CUBAS ===
st.markdown(f"**{len(filtered)}** cubas" + (f" (de {total})" if len(filtered) != total else ""))

cols_per_row = 8
for i in range(0, len(filtered), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, col in enumerate(cols):
        idx = i + j
        if idx >= len(filtered):
            break
        t = filtered[idx]
        tc = TYPE_COLORS.get(t["wine_type"], TYPE_COLORS[""])
        pct = t["pct"]
        bar_h = max(int(pct * 0.4), 1) if pct > 0 else 0
        sc = STATE_COLORS.get(t["wine_state"], "#999")

        with col:
            st.markdown(f"""
            <div style="background:#fff;border-radius:6px;padding:5px;margin-bottom:4px;
                        box-shadow:0 1px 2px rgba(0,0,0,0.1);border-top:3px solid {tc['border']};
                        min-height:100px;font-size:0.7em;">
                <div style="display:flex;justify-content:space-between;">
                    <strong style="font-size:1.2em;">{t['code']}</strong>
                    <span style="background:{sc};color:white;padding:1px 4px;border-radius:3px;
                          font-size:0.7em;">{t['wine_state'][:4] if t['wine_state'] else ''}</span>
                </div>
                <div style="background:#f0f0f0;border-radius:3px;height:28px;margin:3px 0;
                            position:relative;overflow:hidden;">
                    <div style="position:absolute;bottom:0;width:100%;height:{bar_h}px;
                                background:{tc['fill']};opacity:0.7;"></div>
                    <div style="position:absolute;width:100%;text-align:center;top:50%;
                                transform:translateY(-50%);font-size:0.9em;font-weight:bold;">{pct:.0f}%</div>
                </div>
                <div style="color:#555;line-height:1.2;">
                    <div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
                         title="{t['wine_code']}">{t['wine_code'][:14] or '-'}</div>
                    <div>{t['grape_code']} | {t['liters']:,.0f}L</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# === PANEL DETALLE ===
st.markdown("---")
if filtered:
    detail_opts = {}
    for t in filtered:
        label = f"Cuba {t['code']}"
        if t["wine_code"]:
            label += f" - {t['wine_code']}"
        if t["wine_state"]:
            label += f" [{t['wine_state']}]"
        detail_opts[t["id"]] = label

    sel_id = st.selectbox("Seleccione cuba para ver detalle:",
                          options=list(detail_opts.keys()),
                          format_func=lambda x: detail_opts[x],
                          index=None, placeholder="Seleccione...", key="tc_sel")

    if sel_id:
        t = next(x for x in filtered if x["id"] == sel_id)
        tc = TYPE_COLORS.get(t["wine_type"], TYPE_COLORS[""])
        sc = STATE_COLORS.get(t["wine_state"], "#607D8B")

        # --- IDENTIFICACION ---
        st.markdown(f"""
        <div style="background:linear-gradient(135deg, {tc['light']}, #fff);border-radius:10px;
                    padding:20px;border:1px solid {tc['border']}33;">
            <h3 style="margin:0 0 12px 0;color:{tc['text']};">Cuba {t['code']}</h3>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
                <div><small style="color:#888;">CODIGO</small><br><strong>{t['wine_code'] or '-'}</strong></div>
                <div><small style="color:#888;">CAPACIDAD</small><br><strong>{t['capacity']:,.0f} L</strong></div>
                <div><small style="color:#888;">LT REALES</small><br><strong>{t['liters']:,.0f} L</strong></div>
                <div><small style="color:#888;">OCUPACION</small><br><strong>{t['pct']}%</strong></div>
                <div><small style="color:#888;">TIPO</small><br>
                    <span style="background:{tc['fill']};color:white;padding:2px 8px;border-radius:4px;
                          font-size:0.85em;">{t['wine_type'] or '-'}</span></div>
                <div><small style="color:#888;">CEPA</small><br><strong>{t['grape_code']} {t['grape_name']}</strong></div>
                <div><small style="color:#888;">LINEA</small><br><strong>{t['product_line'] or '-'}</strong></div>
                <div><small style="color:#888;">COSECHA</small><br><strong>{t['vintage_year'] or '-'}</strong></div>
                <div><small style="color:#888;">ESTADO</small><br>
                    <span style="background:{sc};color:white;padding:2px 8px;border-radius:4px;
                          font-size:0.85em;">{t['wine_state'] or 'Sin especificar'}</span></div>
                <div><small style="color:#888;">ULTIMO ANALISIS</small><br><strong>{t['last_analysis_date'] or '-'}</strong></div>
                <div><small style="color:#888;">FML</small><br><strong>{t['fml'] or '-'}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("")

        # --- ANALISIS DE LABORATORIO ---
        def eval_param(name, value, wine_type):
            if value is None:
                return "-", "", "#f5f5f5"
            wt = wine_type or "Tinto"
            ranges = {
                "pH": {"Tinto": (3.40, 3.80, 3.30, 3.90), "Blanco": (3.10, 3.40, 3.00, 3.50), "Rosado": (3.10, 3.40, 3.00, 3.50)},
                "A.T.": {"Tinto": (3.50, 6.00, 3.00, 7.00), "Blanco": (5.00, 7.50, 4.50, 8.00), "Rosado": (5.00, 7.50, 4.50, 8.00)},
                "A.V.": {"Tinto": (0.00, 0.60, 0.00, 0.80), "Blanco": (0.00, 0.50, 0.00, 0.65), "Rosado": (0.00, 0.50, 0.00, 0.65)},
                "SO2 L": {"Tinto": (25.0, 50.0, 15.0, 60.0), "Blanco": (25.0, 50.0, 15.0, 60.0), "Rosado": (25.0, 50.0, 15.0, 60.0)},
                "SO2 T": {"Tinto": (50.0, 150.0, 30.0, 200.0), "Blanco": (80.0, 200.0, 50.0, 250.0), "Rosado": (80.0, 200.0, 50.0, 250.0)},
                "MR": {"Tinto": (0.0, 2.5, 0.0, 4.0), "Blanco": (0.0, 4.0, 0.0, 8.0), "Rosado": (0.0, 4.0, 0.0, 8.0)},
                "NTU": {"Tinto": (0.0, 2.0, 0.0, 5.0), "Blanco": (0.0, 1.5, 0.0, 3.0), "Rosado": (0.0, 1.5, 0.0, 3.0)},
                "SO2 Mol": {"Tinto": (0.50, 1.50, 0.30, 2.00), "Blanco": (0.50, 1.50, 0.30, 2.00), "Rosado": (0.50, 1.50, 0.30, 2.00)},
            }
            r = ranges.get(name, {}).get(wt)
            if not r:
                return f"{value}", "", "#f5f5f5"
            lo, hi, crit_lo, crit_hi = r
            if lo <= value <= hi:
                return f"{value}", "Normal", "#e8f5e9"
            elif value < crit_lo or value > crit_hi:
                if value < crit_lo:
                    return f"{value}", "Muy bajo", "#ffebee"
                return f"{value}", "Critico", "#ffebee"
            elif value < lo:
                return f"{value}", "Bajo", "#fff3e0"
            else:
                return f"{value}", "Alto", "#fff3e0"

        def badge_html(label, value, evaluation, bg_color):
            if value == "-":
                eval_badge = ""
            elif evaluation == "Normal":
                eval_badge = '<span style="color:#2e7d32;font-size:0.75em;">&#10003; Normal</span>'
            elif evaluation == "Brillante":
                eval_badge = '<span style="color:#2e7d32;font-size:0.75em;">&#10003; Brillante</span>'
            elif evaluation in ("Alto", "Bajo"):
                eval_badge = f'<span style="color:#e65100;font-size:0.75em;">&#9888; {evaluation}</span>'
            elif evaluation in ("Critico", "Muy bajo"):
                eval_badge = f'<span style="color:#c62828;font-size:0.75em;">&#10007; {evaluation}</span>'
            else:
                eval_badge = f'<span style="color:#666;font-size:0.75em;">{evaluation}</span>' if evaluation else ""

            return f"""
            <div style="background:{bg_color};border-radius:6px;padding:8px;text-align:center;min-height:65px;">
                <div style="color:#888;font-size:0.7em;text-transform:uppercase;">{label}</div>
                <div style="font-size:1.3em;font-weight:bold;margin:2px 0;">{value}</div>
                {eval_badge}
            </div>"""

        wt = t["wine_type"] or "Tinto"

        ph_val, ph_eval, ph_bg = eval_param("pH", t["ph"], wt)
        at_val, at_eval, at_bg = eval_param("A.T.", t["total_acidity"], wt)
        av_val, av_eval, av_bg = eval_param("A.V.", t["volatile_acidity"], wt)
        so2l_val, so2l_eval, so2l_bg = eval_param("SO2 L", t["free_so2"], wt)
        so2t_val, so2t_eval, so2t_bg = eval_param("SO2 T", t["total_so2"], wt)
        mr_val, mr_eval, mr_bg = eval_param("MR", t["residual_sugar"], wt)
        ntu_val, ntu_eval, ntu_bg = eval_param("NTU", t["ntu"], wt)
        if t["ntu"] is not None and t["ntu"] <= 1.0 and ntu_eval == "Normal":
            ntu_eval = "Brillante"
        so2m_val, so2m_eval, so2m_bg = eval_param("SO2 Mol", t["so2_molecular"], wt)
        alc_val = f"{t['alcohol_degree']}" if t["alcohol_degree"] else "-"
        color_val = f"{t['color']}" if t["color"] else "-"
        co2_val = f"{t['co2']}" if t["co2"] else "-"

        st.markdown(f"""
        <div style="background:#fff;border-radius:10px;padding:20px;border:1px solid #e0e0e0;">
            <h4 style="margin:0 0 4px 0;">Analisis de Laboratorio</h4>
            <div style="color:#888;font-size:0.8em;margin-bottom:12px;">
                Tipo: {wt} &bull; Estado: {t['wine_state'] or '-'} &bull;
                Ultimo control: {t['last_analysis_date'] or '-'}
            </div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
                {badge_html("Grado", alc_val, "", "#f5f5f5")}
                {badge_html("pH", ph_val, ph_eval, ph_bg)}
                {badge_html("A.T.", at_val, at_eval, at_bg)}
                {badge_html("A.V.", av_val, av_eval, av_bg)}
                {badge_html("SO2 L", so2l_val, so2l_eval, so2l_bg)}
                {badge_html("SO2 T", so2t_val, so2t_eval, so2t_bg)}
                {badge_html("MR", mr_val, mr_eval, mr_bg)}
                {badge_html("CO2", co2_val, "", "#f5f5f5")}
                {badge_html("NTU", ntu_val, ntu_eval, ntu_bg)}
                {badge_html("Color", color_val, "", "#f5f5f5")}
                {badge_html("FML", t['fml'] or '-', "", "#f5f5f5")}
                {badge_html("SO2 Mol", so2m_val, so2m_eval, so2m_bg)}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("")

        # --- OTs RECIENTES DE ESTA CUBA ---
        try:
            ots = queries.get_work_orders_by_tank(sel_id, limit=10)
        except Exception:
            ots = []

        if ots:
            st.markdown("**Ordenes de Trabajo recientes**")
            ot_rows = []
            for ot in ots:
                proc = ot.get("winemaking_processes") or {}
                wine_ot = ot.get("wines") or {}
                ot_rows.append({
                    "OT": ot.get("ot_number", "?"),
                    "Fecha": ot.get("date", "-"),
                    "Tipo": ot.get("ot_type", "-"),
                    "Operacion": proc.get("name", "-") if isinstance(proc, dict) else "-",
                    "Vino": wine_ot.get("code", "-") if isinstance(wine_ot, dict) else "-",
                    "Litros": ot.get("liters") or "-",
                    "Estado": ot.get("status", "-"),
                })
            st.dataframe(pd.DataFrame(ot_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Sin OTs registradas para esta cuba")

        # --- GRAFICOS ---
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            pct = t["pct"]
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pct,
                number={"suffix": "%"},
                title={"text": "Nivel"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": tc["fill"]},
                    "steps": [
                        {"range": [0, 30], "color": "#ffebee"},
                        {"range": [30, 70], "color": "#fff8e1"},
                        {"range": [70, 100], "color": "#e8f5e9"},
                    ],
                },
            ))
            fig.update_layout(height=220, margin=dict(t=40, b=10, l=30, r=30))
            st.plotly_chart(fig, use_container_width=True)

        with col_g2:
            lab_params = []
            lab_vals = []
            if t["ph"]: lab_params.append("pH"); lab_vals.append(t["ph"])
            if t["total_acidity"]: lab_params.append("A.T."); lab_vals.append(t["total_acidity"])
            if t["volatile_acidity"]: lab_params.append("A.V."); lab_vals.append(t["volatile_acidity"])
            if t["free_so2"]: lab_params.append("SO2 L"); lab_vals.append(t["free_so2"] / 10)
            if t["total_so2"]: lab_params.append("SO2 T"); lab_vals.append(t["total_so2"] / 10)
            if t["residual_sugar"]: lab_params.append("MR"); lab_vals.append(t["residual_sugar"])
            if t["so2_molecular"]: lab_params.append("SO2 Mol"); lab_vals.append(t["so2_molecular"])

            if lab_params:
                fig = go.Figure(go.Scatterpolar(
                    r=lab_vals, theta=lab_params, fill="toself",
                    line_color=tc["fill"],
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True)),
                    height=220, margin=dict(t=40, b=10, l=40, r=40),
                    title="Perfil Analitico",
                )
                st.plotly_chart(fig, use_container_width=True)

# === TAB RESUMEN GENERAL ===
st.markdown("---")
with st.expander("Graficos Generales"):
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        cepa_data = {}
        for t in tank_data:
            if t["liters"] > 0 and t["grape_code"]:
                cepa_data[t["grape_code"]] = cepa_data.get(t["grape_code"], 0) + t["liters"]
        if cepa_data:
            df_cepa = pd.DataFrame([{"Cepa": k, "Litros": v} for k, v in cepa_data.items()])
            df_cepa = df_cepa.sort_values("Litros", ascending=True)
            fig = px.bar(df_cepa, x="Litros", y="Cepa", orientation="h",
                         color="Litros", color_continuous_scale="Reds")
            fig.update_layout(height=400, showlegend=False, margin=dict(t=10, b=10),
                              title="Litros por Cepa")
            st.plotly_chart(fig, use_container_width=True)

    with col_g2:
        type_data = {}
        tc_chart = {"Tinto": "#DC143C", "Blanco": "#FFD700", "Rosado": "#FF69B4"}
        for t in tank_data:
            if t["liters"] > 0 and t["wine_type"]:
                type_data[t["wine_type"]] = type_data.get(t["wine_type"], 0) + t["liters"]
        if type_data:
            df_type = pd.DataFrame([{"Tipo": k, "Litros": v} for k, v in type_data.items()])
            fig = px.pie(df_type, names="Tipo", values="Litros",
                         color="Tipo", color_discrete_map=tc_chart)
            fig.update_layout(height=400, margin=dict(t=10, b=10), title="Litros por Tipo")
            st.plotly_chart(fig, use_container_width=True)

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        if states:
            df_st = pd.DataFrame([{"Estado": k, "Cubas": v} for k, v in states.items()])
            fig = px.pie(df_st, names="Estado", values="Cubas",
                         color="Estado", color_discrete_map=STATE_COLORS)
            fig.update_layout(height=350, margin=dict(t=10, b=10), title="Estado del Vino")
            st.plotly_chart(fig, use_container_width=True)

    with col_g4:
        pl_data = {}
        for t in tank_data:
            if t["liters"] > 0 and t["product_line"]:
                pl_data[t["product_line"]] = pl_data.get(t["product_line"], 0) + t["liters"]
        if pl_data:
            df_pl = pd.DataFrame([{"Linea": k, "Litros": v} for k, v in pl_data.items()])
            df_pl = df_pl.sort_values("Litros", ascending=True)
            fig = px.bar(df_pl, x="Litros", y="Linea", orientation="h")
            fig.update_layout(height=350, margin=dict(t=10, b=10), title="Litros por Linea")
            st.plotly_chart(fig, use_container_width=True)
