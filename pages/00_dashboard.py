import streamlit as st
import pandas as pd
from datetime import date, timedelta
from lib import queries
from lib.auth import require_permission

require_permission("dashboard", "ver")

st.title("Centro de Control")

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

col1, col2, col3, col4, col5 = st.columns(5)

col1.markdown(f"""
<div style="background:white;border-radius:8px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,0.12);
            border-left:4px solid #722F37;text-align:center;">
    <div style="color:#666;font-size:0.8em;text-transform:uppercase;letter-spacing:0.5px;">Litros en Cubas</div>
    <div style="color:#1a1a2e;font-size:1.8em;font-weight:700;">{total_liters:,.0f}</div>
    <div style="color:#999;font-size:0.75em;">{pct_use:.1f}% capacidad</div>
</div>
""", unsafe_allow_html=True)

col2.markdown(f"""
<div style="background:white;border-radius:8px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,0.12);
            border-left:4px solid #28a745;text-align:center;">
    <div style="color:#666;font-size:0.8em;text-transform:uppercase;letter-spacing:0.5px;">Cubas Ocupadas</div>
    <div style="color:#1a1a2e;font-size:1.8em;font-weight:700;">{len(occupied)} / {total_tanks}</div>
    <div style="color:#999;font-size:0.75em;">{total_tanks - len(occupied)} disponibles</div>
</div>
""", unsafe_allow_html=True)

col3.markdown(f"""
<div style="background:white;border-radius:8px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,0.12);
            border-left:4px solid #007bff;text-align:center;">
    <div style="color:#666;font-size:0.8em;text-transform:uppercase;letter-spacing:0.5px;">OTs Semana</div>
    <div style="color:#1a1a2e;font-size:1.8em;font-weight:700;">{ots_pending + ots_process + ots_done_today}</div>
    <div style="color:#999;font-size:0.75em;">{ots_pending} pend. | {ots_process} proceso | {ots_done_today} hoy</div>
</div>
""", unsafe_allow_html=True)

col4.markdown(f"""
<div style="background:white;border-radius:8px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,0.12);
            border-left:4px solid {'#dc3545' if low_stock_count > 0 else '#28a745'};text-align:center;">
    <div style="color:#666;font-size:0.8em;text-transform:uppercase;letter-spacing:0.5px;">Insumos Bajo Stock</div>
    <div style="color:{'#dc3545' if low_stock_count > 0 else '#1a1a2e'};font-size:1.8em;font-weight:700;">{low_stock_count}</div>
    <div style="color:#999;font-size:0.75em;">de {len(data['supplies'])} insumos</div>
</div>
""", unsafe_allow_html=True)

col5.markdown(f"""
<div style="background:white;border-radius:8px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,0.12);
            border-left:4px solid {'#fd7e14' if expiry_count > 0 else '#28a745'};text-align:center;">
    <div style="color:#666;font-size:0.8em;text-transform:uppercase;letter-spacing:0.5px;">Lotes por Vencer</div>
    <div style="color:{'#fd7e14' if expiry_count > 0 else '#1a1a2e'};font-size:1.8em;font-weight:700;">{expiry_count}</div>
    <div style="color:#999;font-size:0.75em;">proximos 90 dias</div>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# ALERTAS ACTIVAS
# ============================================================

alerts_low = data["low_stock"]
alerts_expiry = data["expiry_alerts"]

if alerts_low or alerts_expiry:
    st.markdown("### Alertas Activas")

    col_a1, col_a2 = st.columns(2)

    with col_a1:
        if alerts_low:
            st.markdown(f"**Insumos bajo stock minimo** ({len(alerts_low)})")
            for a in alerts_low[:8]:
                name = a.get("supply_name", a.get("name", "?"))
                stock = a.get("total_stock", a.get("current_stock", 0)) or 0
                min_s = a.get("min_stock", 0) or 0
                pct = (float(stock) / float(min_s) * 100) if min_s > 0 else 0
                color = "#dc3545" if pct < 30 else "#fd7e14" if pct < 60 else "#ffc107"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'padding:6px 12px;margin:3px 0;border-radius:4px;background:#fff;'
                    f'border-left:3px solid {color};">'
                    f'<span>{name}</span>'
                    f'<span style="font-weight:bold;color:{color};">{float(stock):.1f} / {float(min_s):.0f}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if len(alerts_low) > 8:
                st.caption(f"... y {len(alerts_low) - 8} mas")
        else:
            st.success("Sin alertas de stock")

    with col_a2:
        if alerts_expiry:
            st.markdown(f"**Lotes por vencer / vencidos** ({len(alerts_expiry)})")
            for a in alerts_expiry[:8]:
                name = a.get("supply_name", a.get("name", "?"))
                lot = a.get("lot_number", "?")
                exp = a.get("expiry_date", "?")
                status = a.get("expiry_status", "")
                color = "#dc3545" if status == "VENCIDO" else "#fd7e14"
                label = "VENCIDO" if status == "VENCIDO" else "POR VENCER"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;'
                    f'padding:6px 12px;margin:3px 0;border-radius:4px;background:#fff;'
                    f'border-left:3px solid {color};">'
                    f'<span>{name} (Lote: {lot})</span>'
                    f'<span style="background:{color};color:white;padding:2px 8px;border-radius:3px;'
                    f'font-size:0.75em;font-weight:bold;">{label} {exp}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if len(alerts_expiry) > 8:
                st.caption(f"... y {len(alerts_expiry) - 8} mas")
        else:
            st.success("Sin alertas de vencimiento")

st.markdown("---")

# ============================================================
# OTs DE LA SEMANA + RECEPCIONES DE VINO
# ============================================================

col_ot, col_wine = st.columns(2)

with col_ot:
    st.markdown("### Ordenes de Trabajo - Ultimos 7 dias")
    if today_ots:
        status_counts = {}
        for ot in today_ots:
            s = ot.get("status", "?")
            status_counts[s] = status_counts.get(s, 0) + 1

        status_colors = {
            "Pendiente": "#ffc107",
            "En Proceso": "#007bff",
            "Completada": "#28a745",
            "Anulada": "#6c757d",
        }

        for status, count in status_counts.items():
            color = status_colors.get(status, "#999")
            pct_bar = min(count / max(len(today_ots), 1) * 100, 100)
            st.markdown(
                f'<div style="margin:6px 0;">'
                f'<div style="display:flex;justify-content:space-between;margin-bottom:2px;">'
                f'<span style="font-weight:600;">{status}</span><span>{count}</span></div>'
                f'<div style="background:#eee;border-radius:4px;height:8px;">'
                f'<div style="background:{color};border-radius:4px;height:8px;width:{pct_bar}%;"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Ultimas OTs
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
                "Pendiente": "background-color: #fff3cd",
                "En Proceso": "background-color: #cce5ff",
                "Completada": "background-color: #d4edda",
                "Anulada": "background-color: #e2e3e5",
            }
            return colors.get(val, "")

        st.dataframe(
            df_ot.style.map(color_status, subset=["Estado"]),
            use_container_width=True, hide_index=True, height=300,
        )
    else:
        st.info("Sin OTs en los ultimos 7 dias")

with col_wine:
    st.markdown("### Recepciones de Vino - Mes Actual")
    receptions = data["receptions"]

    current_month = date.today().strftime("%Y-%m")
    month_recs = [r for r in receptions if str(r.get("date", ""))[:7] == current_month]

    if month_recs:
        compras = [r for r in month_recs if r.get("reception_type") == "Compra Vino"]
        vendimia = [r for r in month_recs if r.get("reception_type") == "Vendimia"]
        liters_compra = sum(r.get("liters", 0) or 0 for r in compras)
        liters_vendimia = sum(r.get("liters", 0) or 0 for r in vendimia)
        total_rec = liters_compra + liters_vendimia

        col_w1, col_w2, col_w3 = st.columns(3)
        col_w1.metric("Total", f"{total_rec:,.0f} L")
        col_w2.metric("Compras", f"{liters_compra:,.0f} L")
        col_w3.metric("Vendimia", f"{liters_vendimia:,.0f} L")

        # Por cepa
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

        # Tabla reciente
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
        st.info("Sin recepciones este mes")

st.markdown("---")

# ============================================================
# MAPA DE CUBAS
# ============================================================

st.markdown("### Estado de Cubas")

content_map = {c["tank_id"]: c for c in contents}

# Agrupar cubas en filas de 6
cols_per_row = 6
tank_list = sorted(tanks, key=lambda t: t.get("code", ""))

for i in range(0, len(tank_list), cols_per_row):
    chunk = tank_list[i:i + cols_per_row]
    cols = st.columns(cols_per_row)
    for j, t in enumerate(chunk):
        content = content_map.get(t["id"])
        status = content.get("status", "Vacio") if content else "Vacio"
        liters = content.get("current_liters", 0) if content else 0
        capacity = t.get("capacity_liters", 0) or 1
        pct = min(liters / capacity * 100, 100)

        grape_txt = ""
        if content and content.get("grape_varieties"):
            grape_txt = content["grape_varieties"].get("code", "")

        bg_colors = {
            "Ocupado": "#d4edda",
            "Vacio": "#f8f9fa",
            "En proceso": "#fff3cd",
            "Limpieza": "#cce5ff",
        }
        bg = bg_colors.get(status, "#f8f9fa")
        border_color = "#28a745" if status == "Ocupado" else "#dee2e6"

        with cols[j]:
            st.markdown(
                f'<div style="background:{bg};border:2px solid {border_color};border-radius:8px;'
                f'padding:10px;text-align:center;min-height:100px;">'
                f'<div style="font-weight:700;font-size:0.95em;">{t["code"]}</div>'
                f'<div style="font-size:0.75em;color:#666;">{grape_txt}</div>'
                f'<div style="font-size:0.85em;font-weight:600;">{liters:,.0f} L</div>'
                f'<div style="background:#ddd;border-radius:3px;height:6px;margin-top:4px;">'
                f'<div style="background:{border_color};border-radius:3px;height:6px;width:{pct}%;"></div>'
                f'</div>'
                f'<div style="font-size:0.7em;color:#999;">{pct:.0f}%</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.markdown("---")

# ============================================================
# RESUMEN STOCK INSUMOS
# ============================================================

st.markdown("### Stock de Insumos - Resumen")

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
            "OK": "background-color: #d4edda; color: #155724",
            "ALERTA": "background-color: #fff3cd; color: #856404",
            "BAJO": "background-color: #f8d7da; color: #721c24",
            "CRITICO": "background-color: #dc3545; color: white",
            "SIN STOCK": "background-color: #6c757d; color: white",
        }
        return colors.get(val, "")

    st.dataframe(
        df_stock.style.map(color_level, subset=["Estado"]),
        use_container_width=True, hide_index=True, height=400,
    )
else:
    st.info("Sin datos de stock")
