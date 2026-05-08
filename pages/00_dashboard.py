import streamlit as st
import pandas as pd
from datetime import date, timedelta
from lib import queries
from lib.auth import require_permission

require_permission("dashboard", "ver")

st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
    <h1 style="margin:0;padding:0;">Centro de Control</h1>
</div>
<p style="color:#6b7280;font-size:0.9rem;margin-top:0;">
    Vista general del estado operativo de la bodega
</p>
""", unsafe_allow_html=True)

@st.cache_data(ttl=120)
def load_dashboard_data():
    return {
        "tanks": queries.get_tanks(),
        "tank_contents": queries.get_tank_contents(),
        "stock_total": queries.get_stock_total(),
        "low_stock": queries.get_low_stock_alerts(),
        "expiry_alerts": queries.get_expiry_alerts(),
        "recent_ots": queries.get_work_orders_with_status(str(date.today() - timedelta(days=7))),
        "receptions": queries.get_wine_receptions(limit=100),
        "supplies": queries.get_supplies(),
    }

try:
    data = load_dashboard_data()
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

# ============================================================
# METRICAS PRINCIPALES (KPIs)
# ============================================================

tanks = data["tanks"]
contents = data["tank_contents"]
total_tanks = len(tanks)
occupied = [c for c in contents if c.get("status") == "Ocupado"]
total_liters = sum(c.get("current_liters", 0) or 0 for c in contents)
tank_cap_map = {t["id"]: t.get("capacity_liters", 0) or 0 for t in tanks}
tanks_with_cap = [t for t in tanks if (t.get("capacity_liters", 0) or 0) > 0]
total_capacity = sum(t["capacity_liters"] for t in tanks_with_cap)
liters_in_cap_tanks = sum(
    c.get("current_liters", 0) or 0 for c in contents
    if tank_cap_map.get(c.get("tank_id"), 0) > 0
)
pct_use = (liters_in_cap_tanks / total_capacity * 100) if total_capacity > 0 else 0

today_ots = data["recent_ots"]
ots_pending = len([o for o in today_ots if o.get("status") == "Pendiente"])
ots_process = len([o for o in today_ots if o.get("status") == "En Proceso"])
ots_done_today = len([o for o in today_ots
                      if o.get("status") == "Completada"
                      and str(o.get("completed_at", ""))[:10] == str(date.today())])

low_stock_count = len(data["low_stock"])
expiry_count = len(data["expiry_alerts"])

def kpi_card(label, value, sub, accent_color, icon=""):
    return f"""
    <div class="vda-card" style="border-top:3px solid {accent_color};text-align:center;">
        <div class="vda-kpi">
            <div style="font-size:1.3rem;margin-bottom:6px;">{icon}</div>
            <div class="vda-kpi-label">{label}</div>
            <div class="vda-kpi-value" style="color:{accent_color};">{value}</div>
            <div class="vda-kpi-sub">{sub}</div>
        </div>
    </div>"""

col1, col2, col3, col4, col5 = st.columns(5)

col1.markdown(kpi_card("Litros en Cubas", f"{total_liters:,.0f}",
    f"{pct_use:.1f}% capacidad", "#722F37", "&#127863;"), unsafe_allow_html=True)

col2.markdown(kpi_card("Cubas Ocupadas", f"{len(occupied)} / {total_tanks}",
    f"{total_tanks - len(occupied)} disponibles", "#059669", "&#127983;"), unsafe_allow_html=True)

col3.markdown(kpi_card("OTs Semana", f"{ots_pending + ots_process + ots_done_today}",
    f"{ots_pending} pend. | {ots_process} proceso | {ots_done_today} hoy", "#2563eb", "&#128203;"), unsafe_allow_html=True)

low_color = "#dc2626" if low_stock_count > 0 else "#059669"
col4.markdown(kpi_card("Bajo Stock", f"{low_stock_count}",
    f"de {len(data['supplies'])} insumos", low_color, "&#128230;"), unsafe_allow_html=True)

exp_color = "#d97706" if expiry_count > 0 else "#059669"
col5.markdown(kpi_card("Por Vencer", f"{expiry_count}",
    "proximos 90 dias", exp_color, "&#9888;"), unsafe_allow_html=True)

st.markdown("<div class='vda-divider'></div>", unsafe_allow_html=True)

# ============================================================
# ALERTAS ACTIVAS
# ============================================================

alerts_low = data["low_stock"]
alerts_expiry = data["expiry_alerts"]

if alerts_low or alerts_expiry:
    st.markdown('<div class="vda-section-title">Alertas Activas</div>', unsafe_allow_html=True)

    col_a1, col_a2 = st.columns(2)

    with col_a1:
        if alerts_low:
            st.markdown(f"""
            <div class="vda-card" style="border-top:3px solid #dc2626;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                    <span style="font-weight:600;color:#1e1e2f;">Insumos bajo stock minimo</span>
                    <span class="vda-badge vda-badge-danger">{len(alerts_low)}</span>
                </div>
            """, unsafe_allow_html=True)
            for a in alerts_low[:8]:
                name = a.get("supply_name", a.get("name", "?"))
                stock = a.get("total_stock", a.get("current_stock", 0)) or 0
                min_s = a.get("min_stock", 0) or 0
                pct = (float(stock) / float(min_s) * 100) if min_s > 0 else 0
                color = "#dc2626" if pct < 30 else "#d97706" if pct < 60 else "#ca8a04"
                bg = "#fef2f2" if pct < 30 else "#fffbeb" if pct < 60 else "#fefce8"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'padding:8px 12px;margin:4px 0;border-radius:8px;background:{bg};'
                    f'border-left:3px solid {color};">'
                    f'<span style="font-size:0.88rem;">{name}</span>'
                    f'<span style="font-weight:700;color:{color};font-size:0.85rem;">{float(stock):.1f} / {float(min_s):.0f}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            rest_html = f'<div style="text-align:center;color:#9ca3af;font-size:0.8rem;margin-top:8px;">... y {len(alerts_low) - 8} mas</div>' if len(alerts_low) > 8 else ""
            st.markdown(f'{rest_html}</div>', unsafe_allow_html=True)
        else:
            st.success("Sin alertas de stock")

    with col_a2:
        if alerts_expiry:
            st.markdown(f"""
            <div class="vda-card" style="border-top:3px solid #d97706;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                    <span style="font-weight:600;color:#1e1e2f;">Lotes por vencer / vencidos</span>
                    <span class="vda-badge vda-badge-warning">{len(alerts_expiry)}</span>
                </div>
            """, unsafe_allow_html=True)
            for a in alerts_expiry[:8]:
                name = a.get("supply_name", a.get("name", "?"))
                lot = a.get("lot_number", "?")
                exp = a.get("expiry_date", "?")
                status = a.get("expiry_status", "")
                color = "#dc2626" if status == "VENCIDO" else "#d97706"
                bg = "#fef2f2" if status == "VENCIDO" else "#fffbeb"
                label_bg = "#dc2626" if status == "VENCIDO" else "#d97706"
                label = "VENCIDO" if status == "VENCIDO" else "POR VENCER"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'padding:8px 12px;margin:4px 0;border-radius:8px;background:{bg};'
                    f'border-left:3px solid {color};">'
                    f'<span style="font-size:0.88rem;">{name} <span style="color:#9ca3af;">Lote: {lot}</span></span>'
                    f'<span class="vda-badge" style="background:{label_bg};color:white;">{label} {exp}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            rest_html = f'<div style="text-align:center;color:#9ca3af;font-size:0.8rem;margin-top:8px;">... y {len(alerts_expiry) - 8} mas</div>' if len(alerts_expiry) > 8 else ""
            st.markdown(f'{rest_html}</div>', unsafe_allow_html=True)
        else:
            st.success("Sin alertas de vencimiento")

st.markdown("<div class='vda-divider'></div>", unsafe_allow_html=True)

# ============================================================
# OTs DE LA SEMANA + RECEPCIONES DE VINO
# ============================================================

col_ot, col_wine = st.columns(2)

with col_ot:
    st.markdown("""
    <div class="vda-card">
        <div class="vda-section-title">Ordenes de Trabajo &mdash; Ultimos 7 dias</div>
    """, unsafe_allow_html=True)
    if today_ots:
        status_counts = {}
        for ot in today_ots:
            s = ot.get("status", "?")
            status_counts[s] = status_counts.get(s, 0) + 1

        status_colors = {
            "Pendiente": "#d97706",
            "En Proceso": "#2563eb",
            "Completada": "#059669",
            "Anulada": "#6b7280",
        }
        status_bg = {
            "Pendiente": "#fef3c7",
            "En Proceso": "#dbeafe",
            "Completada": "#d1fae5",
            "Anulada": "#f3f4f6",
        }

        for status, count in status_counts.items():
            color = status_colors.get(status, "#999")
            bg = status_bg.get(status, "#f3f4f6")
            pct_bar = min(count / max(len(today_ots), 1) * 100, 100)
            st.markdown(
                f'<div style="margin:8px 0;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
                f'<span style="font-weight:600;font-size:0.88rem;color:#1e1e2f;">{status}</span>'
                f'<span class="vda-badge" style="background:{bg};color:{color};">{count}</span></div>'
                f'<div style="background:#f3f4f6;border-radius:6px;height:6px;">'
                f'<div style="background:{color};border-radius:6px;height:6px;width:{pct_bar}%;'
                f'transition:width 0.5s ease;"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        ot_rows = []
        for ot in today_ots[:10]:
            cepa = ot.get("grape_varieties", {})
            process = ot.get("winemaking_processes", {})
            worker = ot.get("workers", {})
            ot_rows.append({
                "OT": ot.get("ot_number", "?"),
                "Fecha": ot.get("date", "-"),
                "Cepa": cepa.get("code", "-") if cepa else "-",
                "Operacion": process.get("name", "-") if process else "-",
                "Operario": worker.get("full_name", "-") if worker else "-",
                "Estado": ot.get("status", "-"),
            })

        df_ot = pd.DataFrame(ot_rows)

        def color_status(val):
            colors = {
                "Pendiente": "background-color: #fef3c7; color: #92400e",
                "En Proceso": "background-color: #dbeafe; color: #1e40af",
                "Completada": "background-color: #d1fae5; color: #065f46",
                "Anulada": "background-color: #f3f4f6; color: #4b5563",
            }
            return colors.get(val, "")

        st.dataframe(
            df_ot.style.map(color_status, subset=["Estado"]),
            use_container_width=True, hide_index=True, height=300,
        )
    else:
        st.markdown("</div>", unsafe_allow_html=True)
        st.info("Sin OTs en los ultimos 7 dias")

with col_wine:
    st.markdown("""
    <div class="vda-card">
        <div class="vda-section-title">Recepciones de Vino &mdash; Mes Actual</div>
    """, unsafe_allow_html=True)
    receptions = data["receptions"]

    current_month = date.today().strftime("%Y-%m")
    month_recs = [r for r in receptions if str(r.get("date", ""))[:7] == current_month]

    if month_recs:
        compras = [r for r in month_recs if r.get("reception_type") == "Compra Vino"]
        vendimia = [r for r in month_recs if r.get("reception_type") == "Vendimia"]
        liters_compra = sum(r.get("liters", 0) or 0 for r in compras)
        liters_vendimia = sum(r.get("liters", 0) or 0 for r in vendimia)
        total_rec = liters_compra + liters_vendimia

        st.markdown(f"""
        <div style="display:flex;gap:12px;margin-bottom:16px;">
            <div style="flex:1;background:#f0fdf4;border-radius:8px;padding:12px;text-align:center;">
                <div style="font-size:0.7rem;text-transform:uppercase;color:#6b7280;letter-spacing:0.05em;">Total</div>
                <div style="font-size:1.3rem;font-weight:700;color:#059669;">{total_rec:,.0f} L</div>
            </div>
            <div style="flex:1;background:#eff6ff;border-radius:8px;padding:12px;text-align:center;">
                <div style="font-size:0.7rem;text-transform:uppercase;color:#6b7280;letter-spacing:0.05em;">Compras</div>
                <div style="font-size:1.3rem;font-weight:700;color:#2563eb;">{liters_compra:,.0f} L</div>
            </div>
            <div style="flex:1;background:#fdf4ff;border-radius:8px;padding:12px;text-align:center;">
                <div style="font-size:0.7rem;text-transform:uppercase;color:#6b7280;letter-spacing:0.05em;">Vendimia</div>
                <div style="font-size:1.3rem;font-weight:700;color:#7c3aed;">{liters_vendimia:,.0f} L</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        cepa_liters = {}
        for r in month_recs:
            cepa = r.get("grape_varieties", {})
            cepa_code = cepa.get("code", "?") if cepa else "?"
            cepa_liters[cepa_code] = cepa_liters.get(cepa_code, 0) + (r.get("liters", 0) or 0)

        if cepa_liters:
            st.markdown("**Litros por Cepa:**")
            df_cepa = pd.DataFrame([
                {"Cepa": k, "Litros": v} for k, v in
                sorted(cepa_liters.items(), key=lambda x: x[1], reverse=True)
            ])
            st.bar_chart(df_cepa.set_index("Cepa"))

        rec_rows = []
        for r in month_recs[:10]:
            cepa = r.get("grape_varieties", {})
            rec_rows.append({
                "Fecha": r.get("date", "-"),
                "Tipo": r.get("reception_type", "-"),
                "Cepa": cepa.get("code", "-") if cepa else "-",
                "Litros": r.get("liters", 0),
                "Grado": r.get("alcohol_degree") or "-",
            })
        if rec_rows:
            st.dataframe(pd.DataFrame(rec_rows), use_container_width=True, hide_index=True, height=200)
    else:
        st.markdown("</div>", unsafe_allow_html=True)
        st.info("Sin recepciones este mes")

st.markdown("<div class='vda-divider'></div>", unsafe_allow_html=True)

# ============================================================
# MAPA DE CUBAS
# ============================================================

st.markdown('<div class="vda-section-title">Estado de Cubas</div>', unsafe_allow_html=True)

content_map = {c["tank_id"]: c for c in contents}

occupied_tanks = [t for t in tanks if content_map.get(t["id"], {}).get("status") == "Ocupado"]
tank_list = sorted(occupied_tanks, key=lambda t: t.get("code", ""))

if not tank_list:
    st.info("No hay cubas ocupadas actualmente")
else:
    cols_per_row = 8
    for i in range(0, len(tank_list), cols_per_row):
        chunk = tank_list[i:i + cols_per_row]
        cols = st.columns(cols_per_row)
        for j, t in enumerate(chunk):
            content = content_map.get(t["id"])
            liters = content.get("current_liters", 0) if content else 0
            capacity = t.get("capacity_liters", 0) or 1
            pct = min(liters / capacity * 100, 100)

            grape_txt = ""
            if content and content.get("grape_varieties"):
                grape_txt = content["grape_varieties"].get("code", "")

            fill_color = "#059669" if pct >= 80 else "#d97706" if pct >= 40 else "#dc2626"

            with cols[j]:
                st.markdown(
                    f'<div style="background:white;border:1px solid #e5e7eb;border-radius:10px;'
                    f'padding:10px 8px;text-align:center;min-height:90px;'
                    f'box-shadow:0 1px 2px rgba(0,0,0,0.04);">'
                    f'<div style="font-weight:700;font-size:0.85rem;color:#1e1e2f;">{t["code"]}</div>'
                    f'<div style="font-size:0.7rem;color:#722F37;font-weight:500;">{grape_txt}</div>'
                    f'<div style="font-size:0.8rem;font-weight:600;color:#374151;margin:3px 0;">{liters:,.0f} L</div>'
                    f'<div style="background:#f3f4f6;border-radius:4px;height:5px;margin-top:4px;">'
                    f'<div style="background:{fill_color};border-radius:4px;height:5px;width:{pct}%;"></div>'
                    f'</div>'
                    f'<div style="font-size:0.65rem;color:#9ca3af;margin-top:2px;">{pct:.0f}%</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

st.markdown("<div class='vda-divider'></div>", unsafe_allow_html=True)

# ============================================================
# RESUMEN STOCK INSUMOS
# ============================================================

st.markdown('<div class="vda-section-title">Stock de Insumos &mdash; Resumen</div>', unsafe_allow_html=True)

stock = data["stock_total"]
if stock:
    stock_rows = []
    for s in stock[:20]:
        name = s.get("supply_name", s.get("name", "?"))
        total = float(s.get("total_stock", 0) or 0)
        min_s = float(s.get("min_stock", 0) or 0)
        unit = s.get("unit", "")

        if min_s > 0:
            pct = total / min_s * 100
            if pct < 30:
                level = "CRITICO"
            elif pct < 60:
                level = "BAJO"
            elif pct < 100:
                level = "ALERTA"
            else:
                level = "OK"
        else:
            level = "OK" if total > 0 else "SIN STOCK"

        stock_rows.append({
            "Insumo": name,
            "Stock": f"{total:.1f} {unit}",
            "Minimo": f"{min_s:.0f}" if min_s > 0 else "-",
            "Estado": level,
        })

    df_stock = pd.DataFrame(stock_rows)

    def color_level(val):
        colors = {
            "OK": "background-color: #d1fae5; color: #065f46",
            "ALERTA": "background-color: #fef3c7; color: #92400e",
            "BAJO": "background-color: #fee2e2; color: #991b1b",
            "CRITICO": "background-color: #dc2626; color: white; font-weight: 700",
            "SIN STOCK": "background-color: #6b7280; color: white",
        }
        return colors.get(val, "")

    st.dataframe(
        df_stock.style.map(color_level, subset=["Estado"]),
        use_container_width=True, hide_index=True, height=400,
    )
else:
    st.info("Sin datos de stock")
