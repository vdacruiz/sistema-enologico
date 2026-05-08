"""
Convierte los datos de lab denormalizados en tank_contents
a registros reales de lab_analyses + lab_analysis_results.
Ejecutar DESPUES de la migracion 015.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.database import get_supabase_client

sb = get_supabase_client()

# Cargar parametros de lab (necesitamos el ID por code)
params_db = sb.table("lab_parameters").select("id, code, wine_type, min_normal, max_normal, alert_value, critical_value, alert_direction").execute().data
param_map = {p["code"]: p for p in params_db}

# Mapeo: columna de tank_contents → sufijo del code de parametro
COLUMN_TO_PARAM = {
    "alcohol_degree": "GRADO",
    "ph": "PH",
    "total_acidity": "AT",
    "volatile_acidity": "AV",
    "free_so2": "SO2L",
    "total_so2": "SO2T",
    "residual_sugar": "AR",
    "ntu": "NTU",
    "co2": "CO2",
    "color": "COLOR",
    "so2_molecular": "SO2M",
}

# Cargar tank_contents con datos de lab
contents = sb.table("tank_contents").select(
    "tank_id, wine_id, grape_variety_id, wine_type, "
    "alcohol_degree, ph, total_acidity, volatile_acidity, free_so2, total_so2, "
    "residual_sugar, so2_molecular, ntu, color, co2, last_analysis_date"
).execute().data


def evaluate_value(value, param):
    if value is None:
        return "Sin dato"
    critical = param.get("critical_value")
    alert = param.get("alert_value")
    min_n = param.get("min_normal")
    max_n = param.get("max_normal")
    direction = param.get("alert_direction", "above")

    if critical is not None and direction == "above" and value >= float(critical):
        return "CRITICO"
    if critical is not None and direction == "below" and value <= float(critical):
        return "CRITICO"
    if alert is not None and direction == "above" and value >= float(alert):
        return "Alerta"
    if alert is not None and direction == "below" and value <= float(alert):
        return "Alerta"
    if min_n is not None and value < float(min_n):
        return "Bajo"
    if max_n is not None and value > float(max_n):
        return "Alto"
    return "Normal"


created = 0
skipped = 0
errors = 0

for tc in contents:
    has_lab = any(tc.get(col) is not None for col in COLUMN_TO_PARAM)
    if not has_lab:
        skipped += 1
        continue

    wine_type = tc.get("wine_type") or "Tinto"
    prefix = wine_type.upper()
    if prefix == "ROSADO":
        prefix = "ROSADO"
    elif prefix == "BLANCO":
        prefix = "BLANCO"
    else:
        prefix = "TINTO"

    analysis_date = tc.get("last_analysis_date") or "2026-05-07"

    analysis_data = {
        "date": str(analysis_date),
        "tank_id": tc["tank_id"],
        "wine_type": wine_type,
        "stage": "Guarda",
        "analyst": "Carga Excel",
        "notes": "Datos iniciales importados desde Excel 07 MAY 2026",
        "status": "Confirmado",
    }
    if tc.get("wine_id"):
        analysis_data["wine_id"] = tc["wine_id"]
    if tc.get("grape_variety_id"):
        analysis_data["grape_variety_id"] = tc["grape_variety_id"]

    try:
        result = sb.table("lab_analyses").insert(analysis_data).execute().data
        analysis_id = result[0]["id"]

        results_data = []
        for col, suffix in COLUMN_TO_PARAM.items():
            val = tc.get(col)
            if val is not None:
                code = f"{prefix}_{suffix}"
                param = param_map.get(code)
                if param:
                    evaluation = evaluate_value(float(val), param)
                    results_data.append({
                        "analysis_id": analysis_id,
                        "parameter_id": param["id"],
                        "value": float(val),
                        "evaluation": evaluation,
                    })

        if results_data:
            sb.table("lab_analysis_results").insert(results_data).execute()

        created += 1
    except Exception as e:
        errors += 1
        print("Error tank_id {}: {}".format(tc["tank_id"], e))

print("Analisis creados: {} | Sin datos: {} | Errores: {}".format(created, skipped, errors))

# Verificar
total = sb.table("lab_analyses").select("id", count="exact").execute()
print("Total analisis en BD: {}".format(total.count))
