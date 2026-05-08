"""
Carga Estado del vino y datos de laboratorio del Excel 07 MAY a tank_contents.
Ejecutar DESPUES de la migracion 014.
"""
import pandas as pd
import os, sys, tempfile, shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.database import get_supabase_client

EXCEL = r"C:\Users\cruiz\OneDrive\Pynthon\Scripts\Sistema Enologico\R03-ENO-02 - Inventario de vinos 2026.xlsx"
EXCLUDE_TANKS = {"Borra En Pasta 2026", "Ticket", "Total Borra En Pasta", "nan", "", "None"}

VALID_STATES = {"Sulfitado", "Estabilizado", "VENDIMIA", "Trasegada", "Sin especificar"}

sb = get_supabase_client()

# Cargar tank map
tanks_db = sb.table("tanks").select("id, code").eq("is_active", True).execute().data
tank_map = {t["code"]: t["id"] for t in tanks_db}

# Leer Excel
tmp = os.path.join(tempfile.gettempdir(), "tank_lab_temp.xlsx")
shutil.copy2(EXCEL, tmp)
df = pd.read_excel(tmp, sheet_name="07 MAY", header=0)
df.columns = [str(c).strip() for c in df.columns]

anno_col = [c for c in df.columns if "o" in c and len(c) <= 4 and c not in ("Tipo", "Frio")][0]
alcohol_col = [c for c in df.columns if c.startswith("A") and len(c) == 2 and c != "A."][0] if any(c for c in df.columns if c.startswith("A") and len(c) == 2) else None

valid = df[df["Cubas"].notna()].copy()
valid["cuba"] = valid["Cubas"].astype(str).str.strip()

updated = 0
errors = 0

for _, row in valid.iterrows():
    cuba = row["cuba"]
    if cuba in EXCLUDE_TANKS:
        continue
    if len(cuba) >= 5 and cuba.isdigit():
        continue

    tank_id = tank_map.get(cuba)
    if not tank_id:
        continue

    update_data = {}

    # Estado del vino
    estado = str(row.get("Estado", "")).strip()
    if estado and estado not in ("nan", "None", "Cubas"):
        if estado in VALID_STATES:
            update_data["wine_state"] = estado
        elif "FML" in estado or "SECA" in estado:
            update_data["wine_state"] = estado
        elif estado == "FLOTACION":
            update_data["wine_state"] = "Flotacion"
        elif not estado[0].isdigit():
            update_data["wine_state"] = estado

    # Año
    anno = str(row.get(anno_col, "")).strip()
    if anno and anno not in ("nan", "None", "Difere") and not anno.startswith("2026-0"):
        try:
            update_data["vintage_year"] = int(float(anno))
        except (ValueError, TypeError):
            pass

    # Lab data
    def safe_float(val):
        try:
            v = float(val)
            if pd.notna(v):
                return v
        except (ValueError, TypeError):
            pass
        return None

    ph = safe_float(row.get("pH"))
    if ph and 2.5 <= ph <= 5.0:
        update_data["ph"] = ph

    at = safe_float(row.get("A.T."))
    if at and 0 < at <= 15:
        update_data["total_acidity"] = at

    av = safe_float(row.get("A.V."))
    if av and 0 < av <= 5:
        update_data["volatile_acidity"] = av

    so2l = safe_float(row.get("SO2 L"))
    if so2l and 0 < so2l <= 200:
        update_data["free_so2"] = so2l

    so2t = safe_float(row.get("SO2 T"))
    if so2t and 0 < so2t <= 500:
        update_data["total_so2"] = so2t

    mr = safe_float(row.get("MR"))
    if mr and 0 <= mr <= 100:
        update_data["residual_sugar"] = mr

    so2m = safe_float(row.get("SO2 MOLECULAR"))
    if so2m and 0 <= so2m <= 5:
        update_data["so2_molecular"] = round(so2m, 4)

    ntu = safe_float(row.get("NTU"))
    if ntu and 0 <= ntu <= 100:
        update_data["ntu"] = ntu

    co2_val = safe_float(row.get("CO2"))
    if co2_val and 0 < co2_val <= 5000:
        update_data["co2"] = co2_val

    color_val = safe_float(row.get("Color"))
    if color_val and 0 < color_val <= 100:
        update_data["color"] = color_val

    if alcohol_col:
        alc = safe_float(row.get(alcohol_col))
        if alc and 8 <= alc <= 20:
            update_data["alcohol_degree"] = alc

    fml = str(row.get("FML", "")).strip()
    if fml and fml not in ("nan", "None"):
        update_data["fml"] = fml

    # Fecha ultimo analisis
    ctrl = row.get("CONTROL MENSUAL SO2L/AV/CO")
    if pd.notna(ctrl):
        try:
            fecha = pd.Timestamp(ctrl)
            if fecha.year >= 2024:
                update_data["last_analysis_date"] = str(fecha.date())
        except Exception:
            pass

    if update_data:
        try:
            sb.table("tank_contents").update(update_data).eq("tank_id", tank_id).execute()
            updated += 1
        except Exception as e:
            errors += 1
            print("Error cuba {}: {}".format(cuba, e))

print("Actualizados: {} | Errores: {}".format(updated, errors))

# Verificar
with_state = sb.table("tank_contents").select("id", count="exact").neq("wine_state", "null").not_.is_("wine_state", "null").execute()
with_ph = sb.table("tank_contents").select("id", count="exact").not_.is_("ph", "null").execute()
print("Con estado: {} | Con pH: {}".format(with_state.count, with_ph.count))
