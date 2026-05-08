import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from lib import queries
from lib.auth import has_permission

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
        "wine_id": c.get("wine_id") if c else None,
        "grape_code": grape_code,
        "grape_name": grape_name,
        "product_line": pl_name,
        "wine_type": wine_type or "",
        "wine_state": wine_state or "",
        "vintage_year": c.get("vintage_year") if c else None,
        "fml": c.get("fml") if c else None,
        "apto_envasado": c.get("apto_envasado", False) if c else False,
        "apto_envasado_at": c.get("apto_envasado_at") if c else None,
        "apto_envasado_by": c.get("apto_envasado_by") if c else None,
        "content_id": c.get("id") if c else None,
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

# === SELECTOR DE CUBA (arriba, acceso rapido) ===
st.markdown(f"**{len(filtered)}** cubas" + (f" (de {total})" if len(filtered) != total else ""))

detail_opts = {}
if filtered:
    for t in filtered:
        label = f"Cuba {t['code']}"
        if t["wine_code"]:
            label += f" - {t['wine_code']}"
        if t["wine_state"]:
            label += f" [{t['wine_state']}]"
        detail_opts[t["id"]] = label

sel_id = st.selectbox("Seleccione cuba:",
                      options=list(detail_opts.keys()),
                      format_func=lambda x: detail_opts[x],
                      index=None, placeholder="Seleccione una cuba para ver detalle...",
                      key="tc_sel") if detail_opts else None


# === BADGE DINAMICO (evaluacion viene de la BD) ===
def badge_html(label, value, evaluation):
    eval_styles = {
        "Normal": ("#e8f5e9", "#2e7d32", "&#10003; Normal"),
        "Alto": ("#fff3e0", "#e65100", "&#9888; Alto"),
        "Bajo": ("#fff3e0", "#e65100", "&#9888; Bajo"),
        "Alerta": ("#f8d7da", "#c62828", "&#9888; Alerta"),
        "CRITICO": ("#ffebee", "#c62828", "&#10007; CRITICO"),
    }
    bg, color, text = eval_styles.get(evaluation, ("#f5f5f5", "#666", ""))
    eval_badge = f'<span style="color:{color};font-size:0.75em;">{text}</span>' if evaluation and evaluation != "Sin dato" else ""

    return f"""
    <div style="background:{bg};border-radius:6px;padding:8px;text-align:center;min-height:65px;">
        <div style="color:#888;font-size:0.7em;text-transform:uppercase;">{label}</div>
        <div style="font-size:1.3em;font-weight:bold;margin:2px 0;">{value}</div>
        {eval_badge}
    </div>"""


# === PANEL DETALLE ===
if sel_id:
    t = next(x for x in filtered if x["id"] == sel_id)
    tc = TYPE_COLORS.get(t["wine_type"], TYPE_COLORS[""])
    sc = STATE_COLORS.get(t["wine_state"], "#607D8B")

    # Buscar ultimo analisis: por vino si tiene, sino por cuba
    analysis = None
    analysis_results = []
    try:
        if t["wine_id"]:
            analysis = queries.get_latest_analysis_for_wine(t["wine_id"])
        if not analysis:
            analysis = queries.get_latest_analysis_for_tank(sel_id)
        if analysis:
            analysis_results = queries.get_lab_analysis_results(analysis["id"])
    except Exception:
        pass

    analysis_date = analysis.get("date", "-") if analysis else "-"

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
            <div><small style="color:#888;">ULTIMO ANALISIS</small><br><strong>{analysis_date}</strong></div>
            <div><small style="color:#888;">FML</small><br><strong>{t['fml'] or '-'}</strong></div>
            <div><small style="color:#888;">ENVASADO</small><br>
                {"<span style='background:#059669;color:white;padding:3px 10px;border-radius:4px;font-size:0.85em;font-weight:600;'>APTO</span>" if t['apto_envasado'] else "<span style='background:#6b7280;color:white;padding:3px 10px;border-radius:4px;font-size:0.85em;'>No aprobado</span>"}
            </div>
        </div>
        {"<div style='margin-top:10px;padding:8px 12px;background:#d1fae5;border-radius:6px;border:1px solid #6ee7b7;font-size:0.85rem;color:#065f46;'><strong>Aprobado para envasado</strong> por " + str(t['apto_envasado_by'] or '-') + " el " + str(t['apto_envasado_at'] or '-')[:10] + "</div>" if t['apto_envasado'] else ""}
    </div>
    """, unsafe_allow_html=True)

    # --- APROBAR / REVOCAR ENVASADO ---
    if t["wine_id"] and t["liters"] > 0 and has_permission("laboratorio", "ver"):
        if not t["apto_envasado"]:
            if st.button("Aprobar para Envasado", key="btn_aprobar_env", type="primary"):
                try:
                    from lib.auth import get_current_user as get_user
                    current = get_user()
                    queries.get_supabase_client().table("tank_contents").update({
                        "apto_envasado": True,
                        "apto_envasado_at": datetime.now().isoformat(),
                        "apto_envasado_by": current.get("full_name", "?"),
                    }).eq("id", t["content_id"]).execute()
                    st.success("Vino aprobado para envasado")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            if st.button("Revocar aprobacion de envasado", key="btn_revocar_env"):
                try:
                    queries.get_supabase_client().table("tank_contents").update({
                        "apto_envasado": False,
                        "apto_envasado_at": None,
                        "apto_envasado_by": None,
                    }).eq("id", t["content_id"]).execute()
                    st.warning("Aprobacion revocada")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("")

    # --- ANALISIS DE LABORATORIO (100% dinamico desde lab_analyses) ---
    if analysis_results:
        badges = ""
        for r in analysis_results:
            param = r.get("lab_parameters") or {}
            name = param.get("name", "?")
            unit = param.get("unit", "")
            value = r.get("value")
            evaluation = r.get("evaluation", "")
            display_val = f"{float(value):.2f}" if value is not None else "-"
            if unit:
                name = f"{name} ({unit})"
            badges += badge_html(name, display_val, evaluation)

        stage_txt = analysis.get("stage", "-")
        analyst_txt = analysis.get("analyst", "-")
        st.markdown(f"""
        <div style="background:#fff;border-radius:10px;padding:20px;border:1px solid #e0e0e0;">
            <h4 style="margin:0 0 4px 0;">Analisis de Laboratorio</h4>
            <div style="color:#888;font-size:0.8em;margin-bottom:12px;">
                Fecha: {analysis_date} &bull; Etapa: {stage_txt} &bull;
                Analista: {analyst_txt}
            </div>
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">
                {badges}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Sin analisis de laboratorio registrados para este vino")

    st.markdown("")

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
        if analysis_results:
            radar_names = []
            radar_vals = []
            for r in analysis_results:
                param = r.get("lab_parameters") or {}
                value = r.get("value")
                min_n = param.get("min_normal")
                max_n = param.get("max_normal")
                if value is not None and min_n is not None and max_n is not None:
                    rng = float(max_n) - float(min_n)
                    if rng > 0:
                        normalized = (float(value) - float(min_n)) / rng * 10
                        radar_names.append(param.get("name", "?"))
                        radar_vals.append(round(normalized, 1))

            if len(radar_names) >= 3:
                fig = go.Figure(go.Scatterpolar(
                    r=radar_vals, theta=radar_names, fill="toself",
                    line_color=tc["fill"],
                ))
                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 15])),
                    height=220, margin=dict(t=40, b=10, l=40, r=40),
                    title="Perfil Analitico (normalizado)",
                )
                st.plotly_chart(fig, use_container_width=True)

    # --- OTs RECIENTES DE LA CUBA ---
    try:
        ots = queries.get_work_orders_by_tank(sel_id, limit=10)
    except Exception:
        ots = []

    if ots:
        st.markdown("**Ordenes de Trabajo recientes (esta cuba)**")
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

    # === TRAZABILIDAD DEL VINO ===
    if t["wine_id"]:
        st.markdown("")
        if st.button("Ver Trazabilidad Completa del Vino", type="primary", key="btn_trace"):
            st.session_state["show_trace"] = t["wine_id"]

        if st.session_state.get("show_trace") == t["wine_id"]:
            st.markdown("---")
            st.markdown(f"### Trazabilidad: {t['wine_code']}")

            try:
                wine_info = queries.get_wine_by_id(t["wine_id"])
            except Exception:
                wine_info = None

            if wine_info:
                cepa_w = (wine_info.get("grape_varieties") or {})
                linea_w = (wine_info.get("product_lines") or {})
                notes_w = wine_info.get("notes", "") or ""

                st.markdown(f"""
                <div class="vda-card" style="border-left:4px solid #722F37;">
                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;">
                        <div><small style="color:#888;">CODIGO</small><br><strong>{wine_info.get('code', '-')}</strong></div>
                        <div><small style="color:#888;">CEPA</small><br><strong>{cepa_w.get('code', '-')} - {cepa_w.get('name', '-')}</strong></div>
                        <div><small style="color:#888;">LINEA</small><br><strong>{linea_w.get('name', '-')}</strong></div>
                        <div><small style="color:#888;">TIPO</small><br><strong>{wine_info.get('wine_type', '-')}</strong></div>
                    </div>
                    {"<div style='margin-top:10px;padding:8px 12px;background:#fef3c7;border-radius:6px;font-size:0.88rem;'><strong>Origen:</strong> " + notes_w + "</div>" if "Mezcla" in notes_w else ""}
                </div>
                """, unsafe_allow_html=True)

            # --- Todas las OTs del vino con detalle ---
            try:
                wine_ots = queries.get_work_orders_by_wine(t["wine_id"])
            except Exception:
                wine_ots = []

            if wine_ots:
                st.markdown(f"**Historial Completo de Operaciones** ({len(wine_ots)} OTs)")

                for ot in wine_ots:
                    proc = ot.get("winemaking_processes") or {}
                    worker = ot.get("workers") or {}
                    ot_type = ot.get("ot_type", "Insumos")
                    ot_status = ot.get("status", "-")
                    ot_num = ot.get("ot_number", "?")
                    ot_date = ot.get("date", "-")
                    ot_liters = ot.get("liters") or "-"
                    obs = ot.get("observations") or ""

                    src_tank = ot.get("tanks!work_orders_source_tank_id_fkey") or ot.get("tanks", {})
                    dst_tank = ot.get("tanks!work_orders_dest_tank_id_fkey") or {}
                    src_code = src_tank.get("code", "-") if isinstance(src_tank, dict) else "-"
                    dst_code = dst_tank.get("code", "-") if isinstance(dst_tank, dict) else "-"

                    proc_name = proc.get("name", "-") if isinstance(proc, dict) else "-"
                    worker_name = worker.get("full_name", "-") if isinstance(worker, dict) else "-"

                    status_colors = {
                        "Completada": ("#d1fae5", "#065f46", "#059669"),
                        "Pendiente": ("#fef3c7", "#92400e", "#d97706"),
                        "En Proceso": ("#dbeafe", "#1e40af", "#2563eb"),
                        "Anulada": ("#f3f4f6", "#4b5563", "#6b7280"),
                    }
                    s_bg, s_text, s_border = status_colors.get(ot_status, ("#f3f4f6", "#4b5563", "#6b7280"))
                    type_icon = "&#128230;" if ot_type == "Insumos" else "&#127858;"

                    if ot_type == "Movimiento":
                        cubas_html = f"<strong>Cuba {src_code}</strong> &#10132; <strong>Cuba {dst_code}</strong> | {ot_liters} L"
                    else:
                        cubas_html = f"<strong>Cuba {src_code}</strong>" if src_code != "-" else ""

                    # Cargar lineas de insumos
                    ot_lines_html = ""
                    if ot_type == "Insumos" and ot_status == "Completada":
                        try:
                            ot_lines = queries.get_work_order_lines(ot["id"])
                            if ot_lines:
                                items = []
                                for ln in ot_lines:
                                    sup = (ln.get("supplies") or {})
                                    sup_name = sup.get("name", "?")
                                    sup_unit = sup.get("unit", "")
                                    qty = ln.get("quantity", 0) or 0
                                    lot = (ln.get("supply_lots") or {})
                                    lot_num = lot.get("lot_number", "-") if isinstance(lot, dict) else "-"
                                    if qty > 0:
                                        items.append(
                                            f'<div style="display:flex;justify-content:space-between;padding:4px 0;'
                                            f'border-bottom:1px solid #f3f4f6;">'
                                            f'<span>{sup_name}</span>'
                                            f'<span style="color:#1e40af;font-weight:600;">{qty:.2f} {sup_unit} '
                                            f'<span style="color:#6b7280;font-weight:400;">Lote: {lot_num}</span></span>'
                                            f'</div>'
                                        )
                                if items:
                                    ot_lines_html = (
                                        '<div style="margin-top:8px;padding:10px 12px;background:#f9fafb;'
                                        'border-radius:6px;border:1px solid #e5e7eb;">'
                                        '<div style="font-size:0.75rem;color:#6b7280;text-transform:uppercase;'
                                        'letter-spacing:0.05em;margin-bottom:6px;">Insumos aplicados</div>'
                                        + "".join(items) + '</div>'
                                    )
                        except Exception:
                            pass

                    obs_html = ""
                    if obs:
                        obs_html = f'<div style="margin-top:6px;font-size:0.82rem;color:#6b7280;font-style:italic;">Obs: {obs[:100]}</div>'

                    st.markdown(f"""
                    <div style="background:white;border-radius:10px;padding:14px 18px;margin-bottom:8px;
                                border-left:4px solid {s_border};box-shadow:0 1px 2px rgba(0,0,0,0.05);">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div>
                                <span style="font-weight:700;color:#1e1e2f;">OT #{ot_num}</span>
                                <span style="background:{s_bg};color:{s_text};padding:2px 8px;border-radius:12px;
                                      font-size:0.72rem;font-weight:600;margin-left:6px;">{ot_status}</span>
                                <span style="color:#6b7280;font-size:0.8rem;margin-left:8px;">{type_icon} {ot_type}</span>
                            </div>
                            <span style="color:#6b7280;font-size:0.82rem;">{ot_date}</span>
                        </div>
                        <div style="margin-top:8px;display:flex;gap:16px;font-size:0.88rem;color:#374151;">
                            <span><strong>Operacion:</strong> {proc_name}</span>
                            <span>{cubas_html}</span>
                            <span><strong>Operario:</strong> {worker_name}</span>
                        </div>
                        {ot_lines_html}
                        {obs_html}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Sin operaciones registradas para este vino")

            # --- Analisis de laboratorio del vino ---
            try:
                wine_analyses = queries.get_lab_analyses(wine_id=t["wine_id"], limit=20)
            except Exception:
                wine_analyses = []

            if wine_analyses:
                st.markdown(f"**Historial de Analisis de Laboratorio** ({len(wine_analyses)})")
                an_rows = []
                for a in wine_analyses:
                    tank_a = a.get("tanks") or {}
                    an_rows.append({
                        "Fecha": a.get("date", "-"),
                        "Cuba": tank_a.get("code", "-") if isinstance(tank_a, dict) else "-",
                        "Etapa": a.get("stage", "-"),
                        "Analista": a.get("analyst", "-"),
                        "Estado": a.get("status", "-"),
                    })
                st.dataframe(pd.DataFrame(an_rows), use_container_width=True, hide_index=True)

            # --- Movimientos entre cubas ---
            try:
                movements = queries.get_tank_movements_by_wine(t["wine_id"])
            except Exception:
                movements = []

            if movements:
                st.markdown(f"**Movimientos entre Cubas** ({len(movements)})")
                mv_rows = []
                for m in movements:
                    src = m.get("tanks!tank_movements_source_tank_id_fkey") or {}
                    dst = m.get("tanks!tank_movements_dest_tank_id_fkey") or {}
                    wo = m.get("work_orders") or {}
                    mv_rows.append({
                        "Fecha": m.get("date", "-"),
                        "Origen": src.get("code", "-") if isinstance(src, dict) else "-",
                        "Destino": dst.get("code", "-") if isinstance(dst, dict) else "-",
                        "Litros": m.get("liters", "-"),
                        "Operacion": m.get("operation", "-"),
                        "OT": wo.get("ot_number", "-") if isinstance(wo, dict) else "-",
                    })
                st.dataframe(pd.DataFrame(mv_rows), use_container_width=True, hide_index=True)

            if st.button("Cerrar Trazabilidad", key="btn_close_trace"):
                del st.session_state["show_trace"]
                st.rerun()

# === GRILLA VISUAL DE CUBAS (en expander para no saturar) ===
st.markdown("---")
with st.expander(f"Grilla Visual ({len(filtered)} cubas)", expanded=False):
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

# === GRAFICOS GENERALES ===
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
