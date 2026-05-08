"""
1. Agrega cepa PG y lineas Pater/Reserva Especial si no existen
2. Inserta todos los vinos parseados del Excel
"""
import pandas as pd
import os, sys, tempfile, shutil, re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.database import get_supabase_client

EXCEL = r"C:\Users\cruiz\OneDrive\Pynthon\Scripts\Sistema Enologico\R03-ENO-02 - Inventario de vinos 2026.xlsx"

sb = get_supabase_client()

# === PASO 1: Agregar referencia faltante ===
cepas = {c["code"]: c["id"] for c in sb.table("grape_varieties").select("id, code").execute().data}
lineas = {l["name"]: l["id"] for l in sb.table("product_lines").select("id, name").execute().data}

if "PG" not in cepas:
    r = sb.table("grape_varieties").insert({"code": "PG", "name": "Pinot Grigio", "wine_type": "Blanco"}).execute().data
    cepas["PG"] = r[0]["id"]
    print("Agregado PG id={}".format(r[0]["id"]))

if "Pater" not in lineas:
    r = sb.table("product_lines").insert({"name": "Pater", "sort_order": 10}).execute().data
    lineas["Pater"] = r[0]["id"]
    print("Agregado Pater id={}".format(r[0]["id"]))

if "Reserva Especial" not in lineas:
    r = sb.table("product_lines").insert({"name": "Reserva Especial", "sort_order": 5}).execute().data
    lineas["Reserva Especial"] = r[0]["id"]
    print("Agregado Reserva Especial id={}".format(r[0]["id"]))

# Reload
cepas = {c["code"]: c["id"] for c in sb.table("grape_varieties").select("id, code").execute().data}
lineas = {l["name"]: l["id"] for l in sb.table("product_lines").select("id, name").execute().data}

# === PASO 2: Leer Excel ===
tmp = os.path.join(tempfile.gettempdir(), "vinos_insert_temp.xlsx")
shutil.copy2(EXCEL, tmp)
df = pd.read_excel(tmp, sheet_name="07 MAY", header=0)
df.columns = [str(c).strip() for c in df.columns]
codigo_col = [c for c in df.columns if "digo" in c][0]
clasif_col = [c for c in df.columns if "Clasificaci" in c][0]

valid = df[df["Cubas"].notna()].copy()
valid["codigo"] = valid[codigo_col].astype(str).str.strip()
valid["variedad"] = valid["Variedad"].astype(str).str.strip()
valid["tipo"] = valid["Tipo"].astype(str).str.strip()
valid["clasif"] = valid[clasif_col].astype(str).str.strip()

# === PASO 3: Mapeos ===
EXCLUDE = {"BORRAS DULCES", "BORRAS TINTO", "FLOTACION", "TERCERA GOTA", "Fecha", "nan", "", "None"}
CEPA_MAP = {
    "CS/MR": "CS-MR", "CS/MR ": "CS-MR", "CS/SY": "CS-SY", "CS/CR": "CS-CR",
    "SB/CH": "SB-CH", "SB/CH ": "SB-CH", "SY/CS": "SY-CS", "CS ": "CS",
}
CLASIF_MAP = {
    "Entry Level": "Entry Level", "Varietal": "Varietal", "Varietal ": "Varietal",
    "Reserva": "Reserva", "Reserva Especial": "Reserva Especial", "Reserva Especial ": "Reserva Especial",
    "R2": "Reserva 2", "Gran Reserva": "Gran Reserva", "Gran Reserva ": "Gran Reserva",
    "GR2": "Gran Reserva 2", "Premium": "Premium", "Premium ": "Premium",
    "Pater": "Pater", "Pater ": "Pater", "Heredium": "Heredium", "Heredium ": "Heredium",
    "Icono": "Icono",
}

existing = {w["code"] for w in sb.table("wines").select("code").execute().data}

wines_df = valid[["codigo", "variedad", "tipo", "clasif"]].drop_duplicates(subset=["codigo"])
to_insert = []
errors = []

for _, r in wines_df.iterrows():
    code = r["codigo"]
    if code in EXCLUDE or re.match(r"^\d{4}-\d{2}", code) or re.match(r"^\d{5,}$", code):
        continue
    if code in existing:
        continue

    cepa_raw = r["variedad"]
    cepa_db = CEPA_MAP.get(cepa_raw, cepa_raw)
    if cepa_db not in cepas:
        errors.append("Cepa {} no existe: {}".format(cepa_db, code))
        continue

    clasif_raw = r["clasif"]
    linea_name = CLASIF_MAP.get(clasif_raw)
    linea_id = lineas.get(linea_name) if linea_name else None

    tipo = r["tipo"].strip() if r["tipo"] not in ("nan", "None") else "Tinto"
    vintage = None
    m = re.search(r"(\d{2})/\d{2}-\d+", code)
    if m:
        vintage = int("20" + m.group(1))

    to_insert.append({
        "code": code,
        "grape_variety_id": cepas[cepa_db],
        "product_line_id": linea_id,
        "wine_type": tipo,
        "vintage_year": vintage,
        "is_active": True,
    })

if errors:
    print("Errores ({})".format(len(errors)))
    for e in errors:
        print("  " + e)

# === PASO 4: Insertar ===
print("Insertando {} vinos...".format(len(to_insert)))
inserted = 0
for i in range(0, len(to_insert), 50):
    batch = to_insert[i:i+50]
    try:
        sb.table("wines").insert(batch).execute()
        inserted += len(batch)
        print("  {} / {}".format(inserted, len(to_insert)))
    except Exception as e:
        print("  Error batch: {}".format(e))
        for w in batch:
            try:
                sb.table("wines").insert(w).execute()
                inserted += 1
            except Exception as e2:
                print("    Error {}: {}".format(w["code"], e2))

print("Total insertados: {}".format(inserted))
