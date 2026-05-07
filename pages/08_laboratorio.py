import streamlit as st
import pandas as pd
from datetime import date
from lib import queries

st.title("Laboratorio")
st.markdown("Analisis de laboratorio y seguimiento de parametros enologicos")

@st.cache_data(ttl=300)
def load_ref():
    return {
        "tanks": queries.get_tanks(),
        "tank_contents": queries.get_tank_contents(),
        "grape_varieties": queries.get_grape_varieties(),
    }

try:
    ref = load_ref()
except Exception as e:
    st.error(f"Error conectando a la base de datos: {e}")
    st.stop()

tab_nuevo, tab_historial, tab_parametros = st.tabs(["Nuevo Analisis", "Historial / Evolucion", "Parametros de Referencia"])


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
# TAB: Nuevo Analisis
# =============================================================
with tab_nuevo:
    st.subheader("Registrar Analisis")

    content_map = {}
    for c in ref["tank_contents"]:
        content_map[c["tank_id"]] = c

    col1, col2, col3 = st.columns(3)
    with col1:
        analysis_date = st.date_input("Fecha", value=date.today(), key="lab_date")
    with col2:
        tank_options = {}
        for t in ref["tanks"]:
            content = content_map.get(t["id"])
            if content and content.get("status") == "Ocupado":
                grape = content.get("grape_varieties")
                grape_txt = grape.get("code", "") if grape else ""
                tank_options[t["id"]] = f"{t['code']} - {grape_txt} ({content.get('current_liters', 0)} L)"
            else:
                tank_options[t["id"]] = f"{t['code']} (Vacia)"

        tank_id = st.selectbox(
            "Cuba", options=list(tank_options.keys()),
            format_func=lambda x: tank_options[x],
            index=None, placeholder="Seleccione cuba...", key="lab_tank"
        )
    with col3:
        stage = st.selectbox("Etapa", [
            "Fermentacion", "Malolactica", "Guarda", "Pre-embotellado", "Estabilizado", "Otro"
        ], key="lab_stage")

    # Determinar tipo de vino de la cuba seleccionada
    wine_type_detected = "Tinto"
    grape_id_detected = None
    wine_id_detected = None
    if tank_id and tank_id in content_map:
        content = content_map[tank_id]
        wt = content.get("wine_type")
        if wt:
            wine_type_detected = wt
        grape_id_detected = content.get("grape_variety_id")
        wine_id_detected = content.get("wine_id")

    wine_type_for_params = wine_type_detected
    if wine_type_for_params == "Rosado":
        wine_type_for_params_lookup = "Rosado"
    elif wine_type_for_params == "Blanco":
        wine_type_for_params_lookup = "Blanco"
    else:
        wine_type_for_params_lookup = "Tinto"

    st.info(f"Tipo de vino detectado: **{wine_type_detected}** - Se usaran los rangos de **{wine_type_for_params_lookup}**")

    # Cargar parametros
    try:
        parameters = queries.get_lab_parameters(wine_type_for_params_lookup)
    except Exception as e:
        st.error(f"Error cargando parametros: {e}")
        parameters = []

    if parameters:
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
                    st.caption("Parametros deshabilitados en etapa de fermentacion: Turbidez, CO2, SO2 Total (MR)")
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
                    p["name"],
                    min_value=0.0,
                    step=0.01,
                    value=0.0,
                    key=f"lab_param_{p['id']}",
                    label_visibility="collapsed",
                    disabled=disabled,
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
            if not tank_id:
                st.error("Debe seleccionar una cuba")
            elif not any(v > 0 for v in values.values()):
                st.error("Debe ingresar al menos un valor")
            else:
                try:
                    analysis_data = {
                        "date": str(analysis_date),
                        "tank_id": tank_id,
                        "wine_type": wine_type_detected,
                        "stage": stage,
                    }
                    if wine_id_detected:
                        analysis_data["wine_id"] = wine_id_detected
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

                    st.success(f"Analisis guardado exitosamente (ID: {analysis_id})")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
    else:
        st.warning("No hay parametros configurados. Ejecute la migracion 006 en Supabase.")


# =============================================================
# TAB: Historial / Evolucion
# =============================================================
with tab_historial:
    st.subheader("Historial de Analisis")

    col_hf1, col_hf2 = st.columns(2)
    with col_hf1:
        hist_tank_options = {t["id"]: t["code"] for t in ref["tanks"]}
        hist_tank = st.selectbox(
            "Filtrar por Cuba:", options=[None] + list(hist_tank_options.keys()),
            format_func=lambda x: "Todas" if x is None else hist_tank_options[x],
            key="hist_tank"
        )

    try:
        analyses = queries.get_lab_analyses(tank_id=hist_tank, limit=100)
    except Exception:
        analyses = []

    if analyses:
        rows = []
        for a in analyses:
            tank = a.get("tanks")
            tank_txt = tank.get("code", "-") if tank else "-"
            grape = a.get("grape_varieties")
            grape_txt = grape.get("code", "-") if grape else "-"

            rows.append({
                "ID": a["id"],
                "Fecha": a.get("date", "-"),
                "Cuba": tank_txt,
                "Cepa": grape_txt,
                "Tipo": a.get("wine_type", "-"),
                "Etapa": a.get("stage", "-"),
                "Analista": a.get("analyst") or "-",
            })

        df_hist = pd.DataFrame(rows)
        st.dataframe(df_hist, use_container_width=True, hide_index=True, height=300)

        # Detalle de un analisis seleccionado
        st.markdown("---")
        analysis_options = {a["id"]: f"{a.get('date', '-')} - Cuba {(a.get('tanks') or {}).get('code', '?')}" for a in analyses}
        selected_analysis = st.selectbox(
            "Ver detalle de analisis:",
            options=list(analysis_options.keys()),
            format_func=lambda x: analysis_options[x],
            index=None,
            placeholder="Seleccione un analisis...",
            key="hist_detail"
        )

        if selected_analysis:
            try:
                results = queries.get_lab_analysis_results(selected_analysis)
                if results:
                    detail_rows = []
                    for r in results:
                        param = r.get("lab_parameters", {})
                        eval_text = r.get("evaluation", "-")
                        detail_rows.append({
                            "Parametro": param.get("name", "-") if param else "-",
                            "Valor": r.get("value", "-"),
                            "Unidad": param.get("unit", "") if param else "",
                            "Rango Normal": f"{float(param.get('min_normal', 0)):.1f} - {float(param.get('max_normal', 0)):.1f}" if param else "-",
                            "Evaluacion": eval_text,
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
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.info("Sin resultados para este analisis")
            except Exception as e:
                st.warning(f"Error cargando detalle: {e}")

        # Grafico de evolucion
        if hist_tank:
            st.markdown("---")
            st.subheader("Evolucion de Parametros")

            try:
                history = queries.get_lab_history_for_tank(hist_tank)
                if history:
                    param_names = list(set(
                        r.get("lab_parameters", {}).get("name", "?") for r in history if r.get("lab_parameters")
                    ))
                    param_names.sort()

                    selected_params = st.multiselect(
                        "Parametros a graficar:",
                        options=param_names,
                        default=param_names[:3] if len(param_names) >= 3 else param_names,
                        key="hist_chart_params"
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
                                })

                        if chart_data:
                            df_chart = pd.DataFrame(chart_data)
                            for param_name in selected_params:
                                df_p = df_chart[df_chart["Parametro"] == param_name].sort_values("Fecha")
                                if not df_p.empty:
                                    st.markdown(f"**{param_name}**")
                                    st.line_chart(df_p.set_index("Fecha")["Valor"])
                else:
                    st.info("Sin datos historicos para esta cuba")
            except Exception as e:
                st.warning(f"Error cargando evolucion: {e}")
    else:
        st.info("No hay analisis registrados" + (" para esta cuba" if hist_tank else ""))


# =============================================================
# TAB: Parametros de Referencia
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
