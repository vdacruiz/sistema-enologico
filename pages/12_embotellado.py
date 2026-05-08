import streamlit as st
import pandas as pd
from datetime import date, datetime, timezone
from lib import queries
from lib.database import get_supabase_client
from lib.auth import require_permission

require_permission("stock_cubas", "ver")

st.title("Embotellado y Trazabilidad por Lote")

tab_crear, tab_consulta, tab_historial = st.tabs(["Crear Lote", "Consulta por Lote", "Historial"])


# =============================================================
# TAB 1: Crear Lote de Embotellado
# =============================================================
with tab_crear:
    st.subheader("Crear Lote de Embotellado")

    try:
        tanks = queries.get_tanks()
        contents = queries.get_tank_contents()
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        st.stop()

    content_map = {c["tank_id"]: c for c in contents}
    tank_map = {t["id"]: t for t in tanks}

    aptas = []
    for t in tanks:
        tc = content_map.get(t["id"])
        if tc and tc.get("apto_envasado") and tc.get("status") == "Ocupado" and float(tc.get("current_liters", 0)) > 0:
            grape = (tc.get("grape_varieties") or {})
            grape_code = grape.get("code", "") if isinstance(grape, dict) else ""
            wine_code = ""
            if tc.get("wine_id"):
                wines_ref = tc.get("wines")
                if wines_ref and isinstance(wines_ref, dict):
                    wine_code = wines_ref.get("code", "")
            label = f"{t['code']} - {grape_code} {wine_code} ({tc.get('current_liters', 0)} L)"
            aptas.append({"tank": t, "content": tc, "label": label})

    if not aptas:
        st.info("No hay cubas aptas para envasado. Marque cubas como 'Apto Envasado' en Stock de Cubas.")
    else:
        tank_sel = st.selectbox(
            "Cuba a embotellar",
            options=range(len(aptas)),
            format_func=lambda i: aptas[i]["label"],
            index=None,
            placeholder="Seleccione cuba...",
            key="emb_tank",
        )

        if tank_sel is not None:
            sel = aptas[tank_sel]
            tc = sel["content"]
            tank = sel["tank"]
            max_liters = float(tc.get("current_liters", 0))

            wine_id = tc.get("wine_id")
            if not wine_id:
                st.error("Esta cuba no tiene vino asignado. No se puede crear lote de trazabilidad.")
            else:
                wine_info = queries.get_wine_by_id(wine_id)
                if wine_info:
                    cepa = (wine_info.get("grape_varieties") or {})
                    linea = (wine_info.get("product_lines") or {})
                    st.markdown(
                        f'<div style="background:#f9fafb;border-radius:10px;padding:14px 18px;'
                        f'border-left:4px solid #722F37;margin-bottom:12px;">'
                        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">'
                        f'<div><small style="color:#888;">VINO</small><br><strong>{wine_info.get("code", "-")}</strong></div>'
                        f'<div><small style="color:#888;">CEPA</small><br><strong>{cepa.get("code", "-")}</strong></div>'
                        f'<div><small style="color:#888;">LINEA</small><br><strong>{linea.get("name", "-")}</strong></div>'
                        f'<div><small style="color:#888;">TIPO</small><br><strong>{wine_info.get("wine_type", "-")}</strong></div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

                lab_html = ""
                lab_fields = [
                    ("Alcohol", "alcohol_degree", "°"), ("pH", "ph", ""),
                    ("Acidez Total", "total_acidity", "g/L"), ("Acidez Volatil", "volatile_acidity", "g/L"),
                    ("SO2 Libre", "free_so2", "mg/L"), ("SO2 Total", "total_so2", "mg/L"),
                    ("Azucar Residual", "residual_sugar", "g/L"), ("NTU", "ntu", ""),
                ]
                vals = []
                for label, field, unit in lab_fields:
                    v = tc.get(field)
                    if v is not None:
                        vals.append(f"<span style='margin-right:16px;'><strong>{label}:</strong> {v} {unit}</span>")
                if vals:
                    lab_html = (
                        '<div style="background:#eff6ff;border-radius:8px;padding:10px 14px;'
                        'margin-bottom:12px;font-size:0.88rem;">'
                        '<strong style="color:#1e40af;">Ultimo analisis:</strong><br>'
                        + "".join(vals) + '</div>'
                    )
                    st.markdown(lab_html, unsafe_allow_html=True)

                today_str = date.today().strftime("%Y%m%d")
                suggested_lot = f"L{tank['code']}-{today_str}"

                col1, col2 = st.columns(2)
                with col1:
                    lot_number = st.text_input("Numero de Lote", value=suggested_lot, key="emb_lot")
                    bottling_date = st.date_input("Fecha de Embotellado", value=date.today(), key="emb_date")
                with col2:
                    liters = st.number_input("Litros a embotellar", min_value=0.0, max_value=max_liters,
                                             value=max_liters, step=100.0, key="emb_liters")
                    bottles = st.number_input("Cantidad de botellas", min_value=0, value=0, step=1, key="emb_bottles")

                col3, col4 = st.columns(2)
                with col3:
                    bottle_format = st.selectbox("Formato", ["750ml", "375ml", "1500ml", "187ml", "3000ml"], key="emb_format")
                with col4:
                    vintage = st.number_input("Cosecha", min_value=2000, max_value=2030,
                                              value=tc.get("vintage_year") or 2025, key="emb_vintage")

                notes = st.text_area("Observaciones", key="emb_notes", placeholder="Notas del embotellado...")

                st.markdown("---")
                if st.button("Crear Lote de Embotellado", type="primary", use_container_width=True, key="emb_save"):
                    if not lot_number.strip():
                        st.error("Debe ingresar un numero de lote")
                    elif liters <= 0:
                        st.error("Los litros deben ser mayor a 0")
                    else:
                        try:
                            lot_data = {
                                "lot_number": lot_number.strip(),
                                "wine_id": wine_id,
                                "tank_id": tank["id"],
                                "bottling_date": str(bottling_date),
                                "liters": liters,
                                "bottles_count": bottles if bottles > 0 else None,
                                "bottle_format": bottle_format,
                                "grape_variety_id": tc.get("grape_variety_id"),
                                "product_line_id": tc.get("product_line_id"),
                                "wine_type": tc.get("wine_type"),
                                "vintage_year": vintage,
                                "alcohol_degree": tc.get("alcohol_degree"),
                                "ph": tc.get("ph"),
                                "total_acidity": tc.get("total_acidity"),
                                "volatile_acidity": tc.get("volatile_acidity"),
                                "free_so2": tc.get("free_so2"),
                                "total_so2": tc.get("total_so2"),
                                "residual_sugar": tc.get("residual_sugar"),
                                "ntu": tc.get("ntu"),
                                "notes": notes if notes else None,
                            }
                            queries.create_bottling_lot(lot_data)

                            client = get_supabase_client()
                            new_liters = max(max_liters - liters, 0)
                            tc_update = {
                                "current_liters": new_liters,
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                                "last_operation": f"Embotellado {liters:.0f} L - Lote {lot_number}",
                            }
                            if new_liters == 0:
                                tc_update["status"] = "Vacio"
                                tc_update["wine_id"] = None
                                tc_update["grape_variety_id"] = None
                                tc_update["product_line_id"] = None
                                tc_update["wine_type"] = None
                                tc_update["wine_state"] = None
                                tc_update["apto_envasado"] = False
                                tc_update["apto_envasado_at"] = None
                                tc_update["apto_envasado_by"] = None
                                tc_update["vintage_year"] = None
                                tc_update["fml"] = None
                                tc_update["last_analysis_date"] = None
                                tc_update["alcohol_degree"] = None
                                tc_update["ph"] = None
                                tc_update["total_acidity"] = None
                                tc_update["volatile_acidity"] = None
                                tc_update["free_so2"] = None
                                tc_update["total_so2"] = None
                                tc_update["residual_sugar"] = None
                                tc_update["so2_molecular"] = None
                                tc_update["ntu"] = None
                                tc_update["color"] = None
                                tc_update["co2"] = None
                                tc_update["test_color_4"] = False
                                tc_update["test_color_4_date"] = None
                                tc_update["test_tartarica_neg4"] = False
                                tc_update["test_tartarica_neg4_date"] = None
                                tc_update["fecha_ac"] = None
                                tc_update["control_mensual_date"] = None
                                tc_update["blend_notes"] = None
                            client.table("tank_contents").update(tc_update).eq("id", tc["id"]).execute()

                            client.table("tank_movements").insert({
                                "date": str(bottling_date),
                                "source_tank_id": tank["id"],
                                "dest_tank_id": None,
                                "wine_id": wine_id,
                                "liters": liters,
                                "operation": "Embotellado",
                                "notes": f"Lote: {lot_number}",
                            }).execute()

                            st.success(f"Lote {lot_number} creado exitosamente - {liters:.0f} L embotellados")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            err = str(e)
                            if "duplicate" in err.lower() or "unique" in err.lower():
                                st.error(f"El numero de lote '{lot_number}' ya existe. Use otro numero.")
                            else:
                                st.error(f"Error: {e}")


# =============================================================
# TAB 2: Consulta por Lote (Trazabilidad Completa)
# =============================================================
with tab_consulta:
    st.subheader("Trazabilidad por Numero de Lote")
    st.markdown("Busque un lote de embotellado para ver toda la historia del vino: operaciones, movimientos, analisis y mezclas.")

    lot_search = st.text_input("Numero de Lote", key="lot_search", placeholder="Ej: L104-20260508")

    if lot_search:
        lot = queries.get_bottling_lot_by_number(lot_search.strip())

        if not lot:
            st.warning(f"No se encontro el lote '{lot_search}'")
        else:
            wine_ref = lot.get("wines") or {}
            grape_ref = lot.get("grape_varieties") or {}
            linea_ref = lot.get("product_lines") or {}
            tank_ref = lot.get("tanks") or {}

            # --- Info del lote ---
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#f9fafb,#eff6ff);border-radius:12px;'
                f'padding:20px;border-left:5px solid #722F37;margin-bottom:16px;">'
                f'<h3 style="margin:0 0 12px 0;color:#722F37;">Lote: {lot.get("lot_number", "-")}</h3>'
                f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;font-size:0.9rem;">'
                f'<div><small style="color:#888;">FECHA</small><br><strong>{lot.get("bottling_date", "-")}</strong></div>'
                f'<div><small style="color:#888;">CUBA</small><br><strong>{tank_ref.get("code", "-") if isinstance(tank_ref, dict) else "-"}</strong></div>'
                f'<div><small style="color:#888;">LITROS</small><br><strong>{lot.get("liters", "-")}</strong></div>'
                f'<div><small style="color:#888;">BOTELLAS</small><br><strong>{lot.get("bottles_count", "-") or "-"} x {lot.get("bottle_format", "-") or "-"}</strong></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            # --- Info del vino ---
            wine_notes = wine_ref.get("notes", "") or ""
            blend_html = ""
            if "Mezcla" in wine_notes:
                blend_html = f'<div style="margin-top:8px;padding:8px;background:#fef3c7;border-radius:6px;font-size:0.85rem;"><strong>Origen mezcla:</strong> {wine_notes}</div>'

            st.markdown(
                f'<div style="background:#f9fafb;border-radius:10px;padding:14px 18px;margin-bottom:12px;">'
                f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;font-size:0.88rem;">'
                f'<div><small style="color:#888;">VINO</small><br><strong>{wine_ref.get("code", "-") if isinstance(wine_ref, dict) else "-"}</strong></div>'
                f'<div><small style="color:#888;">CEPA</small><br><strong>{grape_ref.get("code", "-") if isinstance(grape_ref, dict) else "-"} - {grape_ref.get("name", "") if isinstance(grape_ref, dict) else ""}</strong></div>'
                f'<div><small style="color:#888;">LINEA</small><br><strong>{linea_ref.get("name", "-") if isinstance(linea_ref, dict) else "-"}</strong></div>'
                f'<div><small style="color:#888;">TIPO</small><br><strong>{lot.get("wine_type", "-")}</strong></div>'
                f'<div><small style="color:#888;">COSECHA</small><br><strong>{lot.get("vintage_year", "-")}</strong></div>'
                f'</div>{blend_html}</div>',
                unsafe_allow_html=True,
            )

            # --- Analisis al momento del embotellado ---
            lab_items = []
            lab_snapshot = [
                ("Alcohol", "alcohol_degree", "°"), ("pH", "ph", ""),
                ("Acidez Total", "total_acidity", "g/L"), ("Acidez Volatil", "volatile_acidity", "g/L"),
                ("SO2 Libre", "free_so2", "mg/L"), ("SO2 Total", "total_so2", "mg/L"),
                ("Azucar Residual", "residual_sugar", "g/L"), ("NTU", "ntu", ""),
            ]
            for label, field, unit in lab_snapshot:
                v = lot.get(field)
                if v is not None:
                    lab_items.append(f"<span style='margin-right:16px;'><strong>{label}:</strong> {v} {unit}</span>")
            if lab_items:
                st.markdown(
                    '<div style="background:#ecfdf5;border-radius:8px;padding:12px 14px;margin-bottom:12px;">'
                    '<strong style="color:#065f46;">Analisis al momento del embotellado:</strong><br>'
                    + "".join(lab_items) + '</div>',
                    unsafe_allow_html=True,
                )

            wine_id = lot.get("wine_id")
            if wine_id:
                # --- OTs del vino ---
                try:
                    wine_ots = queries.get_work_orders_by_wine(wine_id)
                except Exception:
                    wine_ots = []

                if wine_ots:
                    st.markdown(f"**Historial de Operaciones** ({len(wine_ots)} OTs)")
                    ot_rows = []
                    for ot in wine_ots:
                        proc = ot.get("winemaking_processes") or {}
                        worker = ot.get("workers") or {}
                        ot_rows.append({
                            "OT": ot.get("ot_number", "-"),
                            "Fecha": ot.get("date", "-"),
                            "Tipo": ot.get("ot_type", "-"),
                            "Operacion": proc.get("name", "-") if isinstance(proc, dict) else "-",
                            "Estado": ot.get("status", "-"),
                            "Litros": ot.get("liters", "-") or "-",
                            "Operario": worker.get("full_name", "-") if isinstance(worker, dict) else "-",
                        })
                    st.dataframe(pd.DataFrame(ot_rows), use_container_width=True, hide_index=True)

                # --- Movimientos del vino ---
                try:
                    movements = queries.get_tank_movements_by_wine(wine_id)
                except Exception:
                    movements = []

                if movements:
                    try:
                        all_tanks = queries.get_tanks()
                        t_map = {t["id"]: t["code"] for t in all_tanks}
                    except Exception:
                        t_map = {}

                    st.markdown(f"**Movimientos entre Cubas** ({len(movements)})")
                    mv_rows = []
                    for m in movements:
                        mv_rows.append({
                            "Fecha": m.get("date", "-"),
                            "Origen": t_map.get(m.get("source_tank_id"), "-"),
                            "Destino": t_map.get(m.get("dest_tank_id"), "-"),
                            "Litros": m.get("liters", "-"),
                            "Operacion": m.get("operation", "-"),
                        })
                    st.dataframe(pd.DataFrame(mv_rows), use_container_width=True, hide_index=True)

                # --- Analisis historicos ---
                try:
                    wine_analyses = queries.get_lab_analyses(wine_id=wine_id, limit=50)
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
                            "Analista": a.get("analyst", "-") or "-",
                        })
                    st.dataframe(pd.DataFrame(an_rows), use_container_width=True, hide_index=True)

                # --- Otros lotes del mismo vino ---
                try:
                    other_lots = queries.get_bottling_lots_by_wine(wine_id)
                    other_lots = [l for l in other_lots if l.get("lot_number") != lot.get("lot_number")]
                except Exception:
                    other_lots = []

                if other_lots:
                    st.markdown(f"**Otros lotes del mismo vino** ({len(other_lots)})")
                    ol_rows = []
                    for bl in other_lots:
                        bl_tank = bl.get("tanks") or {}
                        ol_rows.append({
                            "Lote": bl.get("lot_number", "-"),
                            "Fecha": bl.get("bottling_date", "-"),
                            "Cuba": bl_tank.get("code", "-") if isinstance(bl_tank, dict) else "-",
                            "Litros": bl.get("liters", "-"),
                            "Botellas": bl.get("bottles_count", "-") or "-",
                        })
                    st.dataframe(pd.DataFrame(ol_rows), use_container_width=True, hide_index=True)


# =============================================================
# TAB 3: Historial de Embotellado
# =============================================================
with tab_historial:
    st.subheader("Historial de Lotes de Embotellado")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        search = st.text_input("Buscar (lote, vino, cepa)", key="hist_search")
    with col_f2:
        from_d = st.date_input("Desde", value=None, key="hist_from")
    with col_f3:
        to_d = st.date_input("Hasta", value=None, key="hist_to")

    try:
        lots = queries.search_bottling_lots(
            search_term=search if search else None,
            from_date=str(from_d) if from_d else None,
            to_date=str(to_d) if to_d else None,
        )
    except Exception as e:
        st.error(f"Error: {e}")
        lots = []

    if lots:
        rows = []
        for bl in lots:
            wine = bl.get("wines") or {}
            grape = bl.get("grape_varieties") or {}
            linea = bl.get("product_lines") or {}
            tank = bl.get("tanks") or {}
            rows.append({
                "Lote": bl.get("lot_number", "-"),
                "Fecha": bl.get("bottling_date", "-"),
                "Vino": wine.get("code", "-") if isinstance(wine, dict) else "-",
                "Cepa": grape.get("code", "-") if isinstance(grape, dict) else "-",
                "Linea": linea.get("name", "-") if isinstance(linea, dict) else "-",
                "Cuba": tank.get("code", "-") if isinstance(tank, dict) else "-",
                "Litros": bl.get("liters", "-"),
                "Botellas": bl.get("bottles_count", "-") or "-",
                "Formato": bl.get("bottle_format", "-") or "-",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(f"{len(lots)} lotes encontrados")
    else:
        st.info("No hay lotes de embotellado registrados")
