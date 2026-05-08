import streamlit as st
import pandas as pd
from datetime import date, datetime, timezone
from lib import queries
from lib.database import get_supabase_client
from lib.auth import require_permission, has_permission, get_current_user

require_permission("laboratorio", "ver")

st.title("Laboratorio")
st.markdown("Analisis de laboratorio, seguimiento por vino y aprobacion de envasado")


@st.cache_data(ttl=300)
def load_ref():
    return {
        "tanks": queries.get_tanks(),
        "tank_contents": queries.get_tank_contents(),
        "grape_varieties": queries.get_grape_varieties(),
        "wines_in_tanks": queries.get_wines_in_tanks(),
    }


try:
    ref = load_ref()
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")
    st.stop()

content_map = {c["tank_id"]: c for c in ref["tank_contents"]}

tab_nuevo, tab_historial_vino, tab_ficha, tab_envasado, tab_parametros = st.tabs([
    "Nuevo Analisis", "Historial por Vino", "Ficha Tecnica", "Aprobacion Envasado", "Parametros de Referencia"
])


def evaluate_value(value, param):
    if value is None:
        return "Sin dato", "#6c757d"
    critical = param.get("critical_value")
    alert = param.get("alert_value")
    min_n = param.get("min_normal")
    max_n = param.get("max_normal")
    direction = param.get("alert_direction", "above")
    if critical is not None and direction == "above" and value >= float(critical):
        return "CRITICO", "#dc3545"
    if critical is not None and direction == "below" and value <= float(critical):
        return "CRITICO", "#dc3545"
    if alert is not None and direction == "above" and value >= float(alert):
        return "Alerta", "#fd7e14"
    if alert is not None and direction == "below" and value <= float(alert):
        return "Alerta", "#fd7e14"
    if min_n is not None and value < float(min_n):
        return "Bajo", "#ffc107"
    if max_n is not None and value > float(max_n):
        return "Alto", "#ffc107"
    return "Normal", "#28a745"


# =============================================================
# TAB 1: Nuevo Analisis (seleccion por vino, no por cuba)
# =============================================================
with tab_nuevo:
    st.subheader("Registrar Analisis")

    wine_options = {}
    wine_tank_map = {}
    for wt in ref["wines_in_tanks"]:
        wine = wt.get("wines") or {}
        tank = wt.get("tanks") or {}
        grape = wt.get("grape_varieties") or {}
        if not wine.get("id"):
            continue
        w_code = wine.get("code", "?")
        t_code = tank.get("code", "?")
        g_code = grape.get("code", "")
        liters = wt.get("current_liters", 0)
        label = f"{w_code} | Cuba {t_code} | {g_code} | {liters} L"
        key = (wine["id"], wt["tank_id"])
        wine_options[key] = label
        wine_tank_map[key] = wt

    col1, col2 = st.columns(2)
    with col1:
        analysis_date = st.date_input("Fecha", value=date.today(), key="lab_date")
    with col2:
        stage = st.selectbox("Etapa", [
            "Fermentacion", "Malolactica", "Guarda", "Pre-embotellado", "Estabilizado", "Otro"
        ], key="lab_stage")

    selected_key = st.selectbox(
        "Vino (Cuba)",
        options=list(wine_options.keys()),
        format_func=lambda x: wine_options[x],
        index=None,
        placeholder="Seleccione vino...",
        key="lab_wine_tank",
    )

    wine_id_detected = None
    tank_id = None
    grape_id_detected = None
    wine_type_detected = "Tinto"

    if selected_key:
        wt_data = wine_tank_map[selected_key]
        wine_id_detected = selected_key[0]
        tank_id = selected_key[1]
        grape_id_detected = wt_data.get("grape_variety_id")
        wt = wt_data.get("wine_type")
        if wt:
            wine_type_detected = wt

        wine_ref = wt_data.get("wines") or {}
        grape_ref = wt_data.get("grape_varieties") or {}
        tank_ref = wt_data.get("tanks") or {}
        st.markdown(
            f'<div style="background:#f9fafb;border-radius:10px;padding:12px 16px;'
            f'border-left:4px solid #722F37;margin:8px 0;">'
            f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;font-size:0.88rem;">'
            f'<div><small style="color:#888;">VINO</small><br><strong>{wine_ref.get("code", "-")}</strong></div>'
            f'<div><small style="color:#888;">CUBA</small><br><strong>{tank_ref.get("code", "-")}</strong></div>'
            f'<div><small style="color:#888;">CEPA</small><br><strong>{grape_ref.get("code", "-")}</strong></div>'
            f'<div><small style="color:#888;">TIPO</small><br><strong>{wine_type_detected}</strong></div>'
            f'<div><small style="color:#888;">ESTADO</small><br><strong>{wt_data.get("wine_state", "-") or "-"}</strong></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    wine_type_for_params_lookup = "Tinto"
    if wine_type_detected == "Rosado":
        wine_type_for_params_lookup = "Rosado"
    elif wine_type_detected == "Blanco":
        wine_type_for_params_lookup = "Blanco"

    try:
        parameters = queries.get_lab_parameters(wine_type_for_params_lookup)
    except Exception as e:
        st.error(f"Error cargando parametros: {e}")
        parameters = []

    if parameters and selected_key:
        st.markdown("---")
        st.subheader("Parametros")

        skip_in_fermentation = {"NTU", "CO2", "SO2T"}
        skip_note_shown = False

        values = {}
        for p in parameters:
            param_short = p["code"].split("_", 1)[1] if "_" in p["code"] else p["code"]
            disabled = False
            if stage == "Fermentacion" and param_short in skip_in_fermentation:
                disabled = True
                if not skip_note_shown:
                    st.caption("Parametros deshabilitados en fermentacion: Turbidez, CO2, SO2 Total")
                    skip_note_shown = True

            col_name, col_range, col_input, col_eval = st.columns([2.5, 2, 2, 1.5])
            with col_name:
                unit_txt = f" ({p['unit']})" if p['unit'] else ""
                st.markdown(f"**{p['name']}**{unit_txt}")
            with col_range:
                min_n = p.get("min_normal")
                max_n = p.get("max_normal")
                range_txt = ""
                if min_n is not None and max_n is not None:
                    range_txt = f"{float(min_n):.1f} - {float(max_n):.1f}"
                elif max_n is not None:
                    range_txt = f"< {float(max_n):.1f}"
                alert_txt = ""
                if p.get("alert_value"):
                    alert_txt = f" | Alerta: >{float(p['alert_value']):.1f}"
                st.markdown(f"Rango: {range_txt}{alert_txt}")
            with col_input:
                val = st.number_input(
                    p["name"], min_value=0.0, step=0.01, value=0.0,
                    key=f"lab_param_{p['id']}", label_visibility="collapsed", disabled=disabled,
                )
                if not disabled:
                    values[p["id"]] = val
            with col_eval:
                if not disabled and val > 0:
                    eval_text, eval_color = evaluate_value(val, p)
                    st.markdown(
                        f'<span style="background:{eval_color};color:white;padding:4px 10px;'
                        f'border-radius:4px;font-weight:bold;font-size:0.85em;">{eval_text}</span>',
                        unsafe_allow_html=True,
                    )
                elif disabled:
                    st.markdown("*N/A*")

        analyst = st.text_input("Analista", key="lab_analyst", placeholder="Nombre del analista...")
        notes = st.text_area("Observaciones", key="lab_notes", placeholder="Notas del analisis...")

        st.markdown("---")
        if st.button("Guardar Analisis", type="primary", use_container_width=True):
            if not selected_key:
                st.error("Debe seleccionar un vino")
            elif not any(v > 0 for v in values.values()):
                st.error("Debe ingresar al menos un valor")
            else:
                try:
                    analysis_data = {
                        "date": str(analysis_date),
                        "tank_id": tank_id,
                        "wine_id": wine_id_detected,
                        "wine_type": wine_type_detected,
                        "stage": stage,
                    }
                    if grape_id_detected:
                        analysis_data["grape_variety_id"] = grape_id_detected
                    if analyst:
                        analysis_data["analyst"] = analyst
                    if notes:
                        analysis_data["notes"] = notes

                    result = queries.create_lab_analysis(analysis_data)
                    analysis_id = result[0]["id"]

                    results_data = []
                    for param_id, val in values.items():
                        if val > 0:
                            param = next(p for p in parameters if p["id"] == param_id)
                            eval_text, _ = evaluate_value(val, param)
                            results_data.append({
                                "analysis_id": analysis_id,
                                "parameter_id": param_id,
                                "value": val,
                                "evaluation": eval_text,
                            })
                    queries.create_lab_analysis_results(results_data)

                    param_field_map = {
                        "ALCOHOL": "alcohol_degree", "PH": "ph",
                        "AT": "total_acidity", "AV": "volatile_acidity",
                        "SO2L": "free_so2", "SO2T": "total_so2",
                        "AR": "residual_sugar", "SO2M": "so2_molecular",
                        "NTU": "ntu", "COLOR": "color", "CO2": "co2",
                    }
                    tc_update = {"last_analysis_date": str(analysis_date)}
                    for param_id, val in values.items():
                        if val > 0:
                            param = next(p for p in parameters if p["id"] == param_id)
                            short = param["code"].split("_", 1)[1] if "_" in param["code"] else param["code"]
                            if short in param_field_map:
                                tc_update[param_field_map[short]] = val
                    tc_row = content_map.get(tank_id)
                    if tc_row:
                        get_supabase_client().table("tank_contents").update(tc_update).eq("id", tc_row["id"]).execute()

                    st.success(f"Analisis guardado exitosamente (ID: {analysis_id})")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
    elif not selected_key:
        st.info("Seleccione un vino para registrar analisis")


# =============================================================
# TAB 2: Historial por Vino
# =============================================================
with tab_historial_vino:
    st.subheader("Historial de Analisis por Vino")

    hist_wine_options = {}
    for wt in ref["wines_in_tanks"]:
        wine = wt.get("wines") or {}
        grape = wt.get("grape_varieties") or {}
        tank = wt.get("tanks") or {}
        if not wine.get("id"):
            continue
        wid = wine["id"]
        if wid not in hist_wine_options:
            hist_wine_options[wid] = f"{wine.get('code', '?')} | {grape.get('code', '')} | Cuba {tank.get('code', '?')}"

    hist_wine_id = st.selectbox(
        "Seleccionar Vino:",
        options=list(hist_wine_options.keys()),
        format_func=lambda x: hist_wine_options[x],
        index=None,
        placeholder="Seleccione vino...",
        key="hist_wine",
    )

    if hist_wine_id:
        try:
            analyses = queries.get_lab_analyses(wine_id=hist_wine_id, limit=100)
        except Exception:
            analyses = []

        if analyses:
            st.markdown(f"**{len(analyses)} analisis registrados para este vino**")
            rows = []
            for a in analyses:
                tank = a.get("tanks")
                tank_txt = tank.get("code", "-") if tank else "-"
                rows.append({
                    "ID": a["id"],
                    "Fecha": a.get("date", "-"),
                    "Cuba": tank_txt,
                    "Tipo": a.get("wine_type", "-"),
                    "Etapa": a.get("stage", "-"),
                    "Analista": a.get("analyst") or "-",
                    "Estado": a.get("status", "-"),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=250)

            st.markdown("---")
            analysis_options = {}
            for a in analyses:
                tank = a.get("tanks") or {}
                analysis_options[a["id"]] = f"{a.get('date', '-')} - Cuba {tank.get('code', '?')} - {a.get('stage', '')}"

            selected_analysis = st.selectbox(
                "Ver detalle de analisis:",
                options=list(analysis_options.keys()),
                format_func=lambda x: analysis_options[x],
                index=None,
                placeholder="Seleccione un analisis...",
                key="hist_detail",
            )

            if selected_analysis:
                try:
                    results = queries.get_lab_analysis_results(selected_analysis)
                    if results:
                        detail_rows = []
                        for r in results:
                            param = r.get("lab_parameters", {})
                            detail_rows.append({
                                "Parametro": param.get("name", "-") if param else "-",
                                "Valor": r.get("value", "-"),
                                "Unidad": param.get("unit", "") if param else "",
                                "Rango Normal": f"{float(param.get('min_normal', 0)):.1f} - {float(param.get('max_normal', 0)):.1f}" if param and param.get("min_normal") is not None else "-",
                                "Evaluacion": r.get("evaluation", "-"),
                            })
                        df_detail = pd.DataFrame(detail_rows)

                        def color_eval(val):
                            colors = {
                                "Normal": "background-color: #d4edda; color: #155724",
                                "Alto": "background-color: #fff3cd; color: #856404",
                                "Bajo": "background-color: #fff3cd; color: #856404",
                                "Alerta": "background-color: #f8d7da; color: #721c24",
                                "CRITICO": "background-color: #dc3545; color: white",
                            }
                            return colors.get(val, "")

                        st.dataframe(
                            df_detail.style.map(color_eval, subset=["Evaluacion"]),
                            use_container_width=True, hide_index=True,
                        )
                except Exception as e:
                    st.warning(f"Error cargando detalle: {e}")

            # Grafico de evolucion por vino
            st.markdown("---")
            st.subheader("Evolucion de Parametros")
            try:
                history = queries.get_lab_history_for_wine(hist_wine_id)
                if history:
                    param_names = sorted(set(
                        r.get("lab_parameters", {}).get("name", "?")
                        for r in history if r.get("lab_parameters")
                    ))
                    selected_params = st.multiselect(
                        "Parametros a graficar:",
                        options=param_names,
                        default=param_names[:3] if len(param_names) >= 3 else param_names,
                        key="hist_chart_params",
                    )
                    if selected_params:
                        chart_data = []
                        for r in history:
                            param = r.get("lab_parameters", {})
                            if param and param.get("name") in selected_params:
                                chart_data.append({
                                    "Fecha": r["date"],
                                    "Parametro": param["name"],
                                    "Valor": float(r.get("value", 0)),
                                    "Cuba": r.get("tank_code", "-"),
                                })
                        if chart_data:
                            df_chart = pd.DataFrame(chart_data)
                            for param_name in selected_params:
                                df_p = df_chart[df_chart["Parametro"] == param_name].sort_values("Fecha")
                                if not df_p.empty:
                                    st.markdown(f"**{param_name}**")
                                    st.line_chart(df_p.set_index("Fecha")["Valor"])
                else:
                    st.info("Sin datos historicos para este vino")
            except Exception as e:
                st.warning(f"Error cargando evolucion: {e}")
        else:
            st.info("Sin analisis registrados para este vino")
    else:
        st.info("Seleccione un vino para ver su historial de analisis")


# =============================================================
# TAB 3: Ficha Tecnica del Vino (auto-generada desde OTs + Lab)
# =============================================================
with tab_ficha:
    st.subheader("Ficha Tecnica del Vino")
    st.markdown("Resumen automatico de tratamientos, procesos y analisis aplicados al vino — generado desde las OTs completadas.")

    ficha_wine_options = {}
    ficha_wine_data = {}
    for wt in ref["wines_in_tanks"]:
        wine = wt.get("wines") or {}
        grape = wt.get("grape_varieties") or {}
        tank = wt.get("tanks") or {}
        if not wine.get("id"):
            continue
        wid = wine["id"]
        if wid not in ficha_wine_options:
            ficha_wine_options[wid] = f"{wine.get('code', '?')} | {grape.get('code', '')} | Cuba {tank.get('code', '?')}"
            ficha_wine_data[wid] = wt

    ficha_wine_id = st.selectbox(
        "Seleccionar Vino:",
        options=list(ficha_wine_options.keys()),
        format_func=lambda x: ficha_wine_options[x],
        index=None,
        placeholder="Seleccione vino...",
        key="ficha_wine",
    )

    if ficha_wine_id:
        wt_data = ficha_wine_data[ficha_wine_id]
        wine_ref = wt_data.get("wines") or {}
        grape_ref = wt_data.get("grape_varieties") or {}
        tank_ref = wt_data.get("tanks") or {}

        st.markdown(
            f'<div style="background:#f9fafb;border-radius:10px;padding:14px 18px;'
            f'border-left:4px solid #722F37;margin-bottom:16px;">'
            f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:10px;font-size:0.88rem;">'
            f'<div><small style="color:#888;">VINO</small><br><strong>{wine_ref.get("code", "-")}</strong></div>'
            f'<div><small style="color:#888;">CUBA</small><br><strong>{tank_ref.get("code", "-")}</strong></div>'
            f'<div><small style="color:#888;">CEPA</small><br><strong>{grape_ref.get("code", "-")}</strong></div>'
            f'<div><small style="color:#888;">TIPO</small><br><strong>{wt_data.get("wine_type", "-")}</strong></div>'
            f'<div><small style="color:#888;">ESTADO</small><br><strong>{wt_data.get("wine_state", "-") or "-"}</strong></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # --- Obtener todas las OTs completadas del vino ---
        try:
            wine_ots = queries.get_work_orders_by_wine(ficha_wine_id, limit=200)
            completed_ots = [ot for ot in wine_ots if ot.get("status") == "Completada"]
        except Exception:
            completed_ots = []

        # --- Mapear procesos aplicados desde OTs ---
        processes_applied = {}
        for ot in completed_ots:
            proc = ot.get("winemaking_processes") or {}
            proc_name = proc.get("name", "") if isinstance(proc, dict) else ""
            if proc_name and proc_name not in processes_applied:
                processes_applied[proc_name] = {
                    "date": ot.get("date", "-"),
                    "ot": ot.get("ot_number", "?"),
                    "worker": (ot.get("workers") or {}).get("full_name", "-") if isinstance(ot.get("workers"), dict) else "-",
                }

        # --- Mapear insumos aplicados desde work_order_lines ---
        supplies_applied = {}
        for ot in completed_ots:
            if ot.get("ot_type") != "Insumos":
                continue
            try:
                lines = queries.get_work_order_lines(ot["id"])
                for ln in lines:
                    qty = float(ln.get("quantity", 0) or 0)
                    if qty <= 0:
                        continue
                    sup = ln.get("supplies") or {}
                    sup_name = sup.get("name", "?") if isinstance(sup, dict) else "?"
                    sup_unit = sup.get("unit", "") if isinstance(sup, dict) else ""
                    lot = ln.get("supply_lots") or {}
                    lot_num = lot.get("lot_number", "-") if isinstance(lot, dict) else "-"
                    if sup_name not in supplies_applied:
                        supplies_applied[sup_name] = []
                    supplies_applied[sup_name].append({
                        "qty": qty, "unit": sup_unit, "lot": lot_num,
                        "date": ot.get("date", "-"), "ot": ot.get("ot_number", "?"),
                    })
            except Exception:
                pass

        # --- Mapear keywords de insumos a categorias del Excel ---
        treatment_categories = {
            "Enzima": ["enzima", "enzimatica"],
            "Gelatina": ["gelatina"],
            "Bentonita": ["bentonita"],
            "CMC / Zenith": ["cmc", "zenith"],
            "BIC": ["bic", "bicarbonato"],
            "Sulfirex": ["sulfirex"],
            "Goma": ["goma arabiga", "goma"],
            "Sorbato": ["sorbato"],
            "Meta": ["metabisulfito", "meta ", "k2s2o5"],
        }

        process_categories = {
            "Frio": ["frio", "estabilizacion frio", "est. tartarica"],
            "F. Tangencial": ["tangencial"],
            "Trasiego": ["trasiego"],
            "Placas": ["placas"],
            "Envasado": ["envasado"],
        }

        def match_category(name, keywords):
            name_lower = name.lower()
            return any(kw in name_lower for kw in keywords)

        # --- SECCION 1: Tratamientos (Insumos) ---
        st.markdown("### Tratamientos Aplicados (Insumos)")

        treat_html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">'
        for cat_name, keywords in treatment_categories.items():
            found = []
            for sup_name, applications in supplies_applied.items():
                if match_category(sup_name, keywords):
                    found.extend(applications)
            if found:
                total_qty = sum(a["qty"] for a in found)
                last_date = max(a["date"] for a in found)
                unit = found[0]["unit"]
                ot_nums = ", ".join(f'#{a["ot"]}' for a in found)
                treat_html += (
                    f'<div style="background:#d1fae5;border-radius:8px;padding:10px 12px;border:1px solid #6ee7b7;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<strong>{cat_name}</strong>'
                    f'<span style="background:#059669;color:white;padding:2px 8px;border-radius:10px;font-size:0.75rem;font-weight:600;">SI</span></div>'
                    f'<div style="font-size:0.8rem;color:#065f46;margin-top:4px;">'
                    f'{total_qty:.2f} {unit} | {last_date} | OT {ot_nums}</div></div>'
                )
            else:
                treat_html += (
                    f'<div style="background:#f3f4f6;border-radius:8px;padding:10px 12px;border:1px solid #e5e7eb;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<strong style="color:#6b7280;">{cat_name}</strong>'
                    f'<span style="background:#d1d5db;color:#6b7280;padding:2px 8px;border-radius:10px;font-size:0.75rem;">NO</span></div></div>'
                )
        treat_html += '</div>'
        st.markdown(treat_html, unsafe_allow_html=True)

        # --- SECCION 2: Procesos Enologicos ---
        st.markdown("### Procesos Enologicos")

        proc_html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">'
        for cat_name, keywords in process_categories.items():
            found = None
            for proc_name, info in processes_applied.items():
                if match_category(proc_name, keywords):
                    found = info
                    break
            if found:
                proc_html += (
                    f'<div style="background:#dbeafe;border-radius:8px;padding:10px 12px;border:1px solid #93c5fd;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<strong>{cat_name}</strong>'
                    f'<span style="background:#2563eb;color:white;padding:2px 8px;border-radius:10px;font-size:0.75rem;font-weight:600;">SI</span></div>'
                    f'<div style="font-size:0.8rem;color:#1e40af;margin-top:4px;">'
                    f'{found["date"]} | OT #{found["ot"]} | {found["worker"]}</div></div>'
                )
            else:
                proc_html += (
                    f'<div style="background:#f3f4f6;border-radius:8px;padding:10px 12px;border:1px solid #e5e7eb;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<strong style="color:#6b7280;">{cat_name}</strong>'
                    f'<span style="background:#d1d5db;color:#6b7280;padding:2px 8px;border-radius:10px;font-size:0.75rem;">NO</span></div></div>'
                )
        proc_html += '</div>'
        st.markdown(proc_html, unsafe_allow_html=True)

        # --- SECCION 3: FML + Tests de estabilidad ---
        st.markdown("### Estabilidad y Tests")

        fml_val = wt_data.get("fml") or "-"
        test_color = wt_data.get("test_color_4", False)
        test_tart = wt_data.get("test_tartarica_neg4", False)
        fecha_ac = wt_data.get("fecha_ac") or "-"
        ctrl_mensual = wt_data.get("control_mensual_date") or "-"
        blend = wt_data.get("blend_notes") or "-"

        stab_html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">'
        stab_items = [
            ("FML", fml_val, fml_val not in ("-", None, "", "No")),
            ("Test 4° Color", str(wt_data.get("test_color_4_date", "-") or "-"), test_color),
            ("Test -4° E. Tartarica", str(wt_data.get("test_tartarica_neg4_date", "-") or "-"), test_tart),
            ("Fecha A.C.", str(fecha_ac), fecha_ac != "-"),
            ("Control Mensual", str(ctrl_mensual), ctrl_mensual != "-"),
            ("Mezcla / Composicion", blend[:40], blend != "-"),
        ]
        for label, detail, is_done in stab_items:
            if is_done:
                stab_html += (
                    f'<div style="background:#fef3c7;border-radius:8px;padding:10px 12px;border:1px solid #fcd34d;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<strong>{label}</strong>'
                    f'<span style="background:#d97706;color:white;padding:2px 8px;border-radius:10px;font-size:0.75rem;font-weight:600;">SI</span></div>'
                    f'<div style="font-size:0.8rem;color:#92400e;margin-top:4px;">{detail}</div></div>'
                )
            else:
                stab_html += (
                    f'<div style="background:#f3f4f6;border-radius:8px;padding:10px 12px;border:1px solid #e5e7eb;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<strong style="color:#6b7280;">{label}</strong>'
                    f'<span style="background:#d1d5db;color:#6b7280;padding:2px 8px;border-radius:10px;font-size:0.75rem;">NO</span></div></div>'
                )
        stab_html += '</div>'
        st.markdown(stab_html, unsafe_allow_html=True)

        # --- Editar tests de estabilidad ---
        if has_permission("laboratorio", "ver"):
            with st.expander("Registrar Tests de Estabilidad"):
                tc_row = content_map.get(wt_data["tank_id"])
                if tc_row:
                    col_t1, col_t2 = st.columns(2)
                    with col_t1:
                        new_test_color = st.checkbox("Test 4° Color aprobado", value=test_color, key="ficha_test_color")
                        new_test_color_date = st.date_input("Fecha Test Color", value=None, key="ficha_test_color_date")
                        new_test_tart = st.checkbox("Test -4° Tartarica aprobado", value=test_tart, key="ficha_test_tart")
                        new_test_tart_date = st.date_input("Fecha Test Tartarica", value=None, key="ficha_test_tart_date")
                    with col_t2:
                        new_fecha_ac = st.date_input("Fecha A.C.", value=None, key="ficha_fecha_ac")
                        new_ctrl_mensual = st.date_input("Control Mensual", value=None, key="ficha_ctrl_mensual")
                        new_blend = st.text_input("Mezcla / Composicion", value=blend if blend != "-" else "", key="ficha_blend")

                    if st.button("Guardar Tests", type="primary", key="ficha_save_tests"):
                        try:
                            update_data = {
                                "test_color_4": new_test_color,
                                "test_tartarica_neg4": new_test_tart,
                            }
                            if new_test_color_date:
                                update_data["test_color_4_date"] = str(new_test_color_date)
                            if new_test_tart_date:
                                update_data["test_tartarica_neg4_date"] = str(new_test_tart_date)
                            if new_fecha_ac:
                                update_data["fecha_ac"] = str(new_fecha_ac)
                            if new_ctrl_mensual:
                                update_data["control_mensual_date"] = str(new_ctrl_mensual)
                            if new_blend:
                                update_data["blend_notes"] = new_blend
                            get_supabase_client().table("tank_contents").update(update_data).eq("id", tc_row["id"]).execute()
                            st.success("Tests actualizados")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        # --- SECCION 4: Parametros de laboratorio actuales ---
        st.markdown("### Parametros de Laboratorio Actuales")
        lab_params_html = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;">'
        lab_display = [
            ("Alcohol", "alcohol_degree", "°"), ("pH", "ph", ""),
            ("Acidez Total", "total_acidity", "g/L"), ("Acidez Volatil", "volatile_acidity", "g/L"),
            ("SO2 Libre", "free_so2", "mg/L"), ("SO2 Total", "total_so2", "mg/L"),
            ("SO2 Molecular", "so2_molecular", "mg/L"), ("Azucar Residual", "residual_sugar", "g/L"),
            ("NTU", "ntu", ""), ("Color", "color", ""), ("CO2", "co2", "mg/L"),
        ]
        for label, field, unit in lab_display:
            v = wt_data.get(field)
            if v is not None:
                lab_params_html += (
                    f'<div style="background:#eff6ff;border-radius:8px;padding:8px 12px;text-align:center;">'
                    f'<div style="font-size:0.72rem;color:#6b7280;text-transform:uppercase;">{label}</div>'
                    f'<div style="font-size:1.1rem;font-weight:700;color:#1e40af;">{v} {unit}</div></div>'
                )
            else:
                lab_params_html += (
                    f'<div style="background:#f9fafb;border-radius:8px;padding:8px 12px;text-align:center;">'
                    f'<div style="font-size:0.72rem;color:#6b7280;text-transform:uppercase;">{label}</div>'
                    f'<div style="font-size:1.1rem;color:#d1d5db;">-</div></div>'
                )
        lab_params_html += '</div>'
        st.markdown(lab_params_html, unsafe_allow_html=True)
        last_a = wt_data.get("last_analysis_date")
        if last_a:
            st.caption(f"Ultimo analisis: {last_a}")

        # --- SECCION 5: Detalle de TODOS los insumos aplicados ---
        if supplies_applied:
            st.markdown("### Detalle de Insumos Aplicados")
            sup_rows = []
            for sup_name, apps in supplies_applied.items():
                for a in apps:
                    sup_rows.append({
                        "Insumo": sup_name,
                        "Cantidad": f"{a['qty']:.2f} {a['unit']}",
                        "Lote": a["lot"],
                        "Fecha": a["date"],
                        "OT": f"#{a['ot']}",
                    })
            st.dataframe(pd.DataFrame(sup_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Seleccione un vino para ver su ficha tecnica")


# =============================================================
# TAB 4: Aprobacion de Envasado
# =============================================================
with tab_envasado:
    st.subheader("Aprobacion para Envasado")
    st.markdown("Revise los parametros del vino y apruebe o revoque la aptitud para embotellado.")

    wines_in_tanks = ref["wines_in_tanks"]

    if not wines_in_tanks:
        st.info("No hay vinos en cubas actualmente")
    else:
        col_env_search, col_env_filter = st.columns([2, 1])
        with col_env_search:
            env_search = st.text_input("Buscar vino (codigo, cepa, cuba):", key="env_search", placeholder="Ej: 25/26-071, CS, 104...")
        with col_env_filter:
            env_filter = st.radio("Filtrar:", ["Todos", "Pendientes", "Aprobados"], horizontal=True, key="env_filter")

        filtered = wines_in_tanks
        if env_filter == "Pendientes":
            filtered = [w for w in filtered if not w.get("apto_envasado")]
        elif env_filter == "Aprobados":
            filtered = [w for w in filtered if w.get("apto_envasado")]

        if env_search:
            s = env_search.lower()
            filtered = [w for w in filtered if
                        s in ((w.get("wines") or {}).get("code", "")).lower() or
                        s in ((w.get("grape_varieties") or {}).get("code", "")).lower() or
                        s in ((w.get("grape_varieties") or {}).get("name", "")).lower() or
                        s in ((w.get("tanks") or {}).get("code", "")).lower()]

        st.caption(f"{len(filtered)} vinos encontrados")

        if not filtered:
            st.info("Sin resultados para este filtro")
        else:
            for wt in filtered:
                wine = wt.get("wines") or {}
                tank = wt.get("tanks") or {}
                grape = wt.get("grape_varieties") or {}
                is_apto = wt.get("apto_envasado", False)

                badge = ('<span style="background:#059669;color:white;padding:3px 10px;border-radius:12px;'
                         'font-size:0.78rem;font-weight:600;">APTO</span>' if is_apto else
                         '<span style="background:#6b7280;color:white;padding:3px 10px;border-radius:12px;'
                         'font-size:0.78rem;">Pendiente</span>')

                lab_vals = []
                lab_fields = [
                    ("Alcohol", "alcohol_degree", "°"), ("pH", "ph", ""),
                    ("AT", "total_acidity", "g/L"), ("AV", "volatile_acidity", "g/L"),
                    ("SO2L", "free_so2", "mg/L"), ("SO2T", "total_so2", "mg/L"),
                    ("AR", "residual_sugar", "g/L"), ("NTU", "ntu", ""),
                ]
                for label, field, unit in lab_fields:
                    v = wt.get(field)
                    if v is not None:
                        lab_vals.append(f"<span style='margin-right:12px;font-size:0.82rem;'>"
                                        f"<strong>{label}:</strong> {v}{unit}</span>")
                lab_html = "".join(lab_vals) if lab_vals else "<span style='color:#6b7280;font-size:0.82rem;'>Sin datos de analisis</span>"

                last_date = wt.get("last_analysis_date") or "-"
                aprobado_html = ""
                if is_apto:
                    aprobado_html = (f'<div style="margin-top:6px;padding:6px 10px;background:#d1fae5;'
                                     f'border-radius:6px;font-size:0.82rem;color:#065f46;">'
                                     f'<strong>Aprobado</strong> por {wt.get("apto_envasado_by", "-")} '
                                     f'el {str(wt.get("apto_envasado_at", "-"))[:10]}</div>')

                card = (f'<div style="background:white;border-radius:10px;padding:14px 18px;margin-bottom:10px;'
                        f'border-left:4px solid {"#059669" if is_apto else "#d97706"};'
                        f'box-shadow:0 1px 2px rgba(0,0,0,0.05);">')
                card += f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                card += (f'<div><strong style="font-size:1rem;">{wine.get("code", "?")}</strong>'
                         f' <span style="color:#6b7280;">| Cuba {tank.get("code", "?")}'
                         f' | {grape.get("code", "")} | {wt.get("current_liters", 0)} L</span></div>')
                card += f'<div>{badge}</div></div>'
                card += f'<div style="margin-top:8px;">{lab_html}</div>'
                card += f'<div style="margin-top:4px;font-size:0.78rem;color:#6b7280;">Ultimo analisis: {last_date}</div>'
                card += aprobado_html + '</div>'
                st.markdown(card, unsafe_allow_html=True)

                tc_row = content_map.get(wt["tank_id"])
                if tc_row and has_permission("laboratorio", "ver"):
                    col_apr, col_rev = st.columns(2)
                    with col_apr:
                        if not is_apto:
                            if st.button("Aprobar para Envasado", key=f"apr_{wt['tank_id']}", type="primary"):
                                try:
                                    user = get_current_user()
                                    get_supabase_client().table("tank_contents").update({
                                        "apto_envasado": True,
                                        "apto_envasado_at": datetime.now(timezone.utc).isoformat(),
                                        "apto_envasado_by": user.get("full_name", "?"),
                                    }).eq("id", tc_row["id"]).execute()
                                    st.success(f"Vino {wine.get('code', '')} aprobado para envasado")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    with col_rev:
                        if is_apto:
                            if st.button("Revocar Aprobacion", key=f"rev_{wt['tank_id']}"):
                                try:
                                    get_supabase_client().table("tank_contents").update({
                                        "apto_envasado": False,
                                        "apto_envasado_at": None,
                                        "apto_envasado_by": None,
                                    }).eq("id", tc_row["id"]).execute()
                                    st.warning(f"Aprobacion revocada para {wine.get('code', '')}")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")

                    st.markdown("")


# =============================================================
# TAB 5: Parametros de Referencia
# =============================================================
with tab_parametros:
    st.subheader("Rangos de Referencia por Tipo de Vino")

    ref_type = st.radio("Tipo de vino:", ["Tinto", "Blanco", "Rosado"], horizontal=True, key="ref_type")

    try:
        params = queries.get_lab_parameters(ref_type)
        if params:
            ref_rows = []
            for p in params:
                min_n = float(p["min_normal"]) if p.get("min_normal") is not None else "-"
                max_n = float(p["max_normal"]) if p.get("max_normal") is not None else "-"
                alert = float(p["alert_value"]) if p.get("alert_value") is not None else "-"
                critical = float(p["critical_value"]) if p.get("critical_value") is not None else "-"
                ref_rows.append({
                    "Parametro": p["name"],
                    "Unidad": p.get("unit", ""),
                    "Min Normal": min_n,
                    "Max Normal": max_n,
                    "Alerta": alert,
                    "Critico": critical,
                    "Direccion": p.get("alert_direction", "-"),
                })
            st.dataframe(pd.DataFrame(ref_rows), use_container_width=True, hide_index=True)
        else:
            st.warning("No hay parametros configurados para este tipo")
    except Exception as e:
        st.warning(f"Error: {e}")

    st.markdown("---")
    st.markdown("""
    **Notas:**
    - Durante **fermentacion**: no evaluar Turbidez (NTU), CO2, SO2 Total
    - Cuando esta **estabilizado**: no recomendar frio/CMC
    - Los rangos Blanco y Rosado comparten los mismos parametros
    """)
