"""
Carga el contenido actual de cada cuba desde el Excel 07 MAY.
Llena la tabla tank_contents con wine_id, grape_variety_id, litros, estado.
"""
import pandas as pd
import os, sys, tempfile, shutil, re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.database import get_supabase_client

EXCEL = r"C:\Users\cruiz\OneDrive\Pynthon\Scripts\Sistema Enologico\R03-ENO-02 - Inventario de vinos 2026.xlsx"
EXCLUDE_TANKS = {"Borra En Pasta 2026", "Ticket", "Total Borra En Pasta", "nan", "", "None"}
EXCLUDE_CODES = {"BORRAS DULCES", "BORRAS TINTO", "FLOTACION", "TERCERA GOTA", "Fecha", "nan", "", "None"}

CEPA_MAP = {
    "CS/MR": "CS-MR", "CS/MR ": "CS-MR", "CS/SY": "CS-SY", "CS/CR": "CS-CR",
    "SB/CH": "SB-CH", "SB/CH ": "SB-CH", "SY/CS": "SY-CS", "CS ": "CS",
}

sb = get_supabase_client()

# Cargar referencia
tanks_db = sb.table("tanks").select("id, code").eq("is_active", True).execute().data
tank_map = {t["code"]: t["id"] for t in tanks_db}

wines_db = sb.table("wines").select("id, code, grape_variety_id, product_line_id, wine_type").execute().data
wine_map = {w["code"]: w for w in wines_db}

cepas_db = sb.table("grape_varieties").select("id, code").execute().data
cepa_map = {c["code"]: c["id"] for c in cepas_db}

# Limpiar tank_contents existente
existing = sb.table("tank_contents").select("id", count="exact").execute()
if existing.count > 0:
    print("Limpiando {} registros existentes de tank_contents...".format(existing.count))
    all_tc = sb.table("tank_contents").select("id").execute().data
    for tc in all_tc:
        sb.table("tank_contents").delete().eq("id", tc["id"]).execute()
    print("  Limpiado")

# Leer Excel
tmp = os.path.join(tempfile.gettempdir(), "tank_contents_temp.xlsx")
shutil.copy2(EXCEL, tmp)
df = pd.read_excel(tmp, sheet_name="07 MAY", header=0)
df.columns = [str(c).strip() for c in df.columns]

codigo_col = [c for c in df.columns if "digo" in c][0]
clasif_col = [c for c in df.columns if "Clasificaci" in c][0]
litros_col = [c for c in df.columns if "reales" in c][0]
estado_col = "Estado"

valid = df[df["Cubas"].notna()].copy()
valid["cuba"] = valid["Cubas"].astype(str).str.strip()
valid["codigo"] = valid[codigo_col].astype(str).str.strip()
valid["variedad"] = valid["Variedad"].astype(str).str.strip()
valid["tipo"] = valid["Tipo"].astype(str).str.strip()
valid["litros"] = pd.to_numeric(valid[litros_col], errors="coerce").fillna(0)
valid["estado_xl"] = valid[estado_col].astype(str).str.strip() if estado_col in valid.columns else "nan"
valid["envasado"] = valid["Envasado"].astype(str).str.strip() if "Envasado" in valid.columns else "nan"

to_insert = []
skipped = []
errors = []

for _, row in valid.iterrows():
    cuba_code = row["cuba"]
    if cuba_code in EXCLUDE_TANKS:
        continue
    if len(cuba_code) >= 5 and cuba_code.isdigit():
        continue

    tank_id = tank_map.get(cuba_code)
    if not tank_id:
        skipped.append("Cuba {} no encontrada en BD".format(cuba_code))
        continue

    codigo = row["codigo"]
    litros = row["litros"]

    apto = row.get("envasado", "").upper() == "SI"
    estado_vino = row["estado_xl"] if row["estado_xl"] not in ("nan", "None", "") else None

    if codigo in EXCLUDE_CODES or re.match(r"^\d{4}-\d{2}", codigo) or re.match(r"^\d{5,}$", codigo):
        if litros > 0:
            cepa_raw = row["variedad"]
            cepa_db = CEPA_MAP.get(cepa_raw, cepa_raw)
            cepa_id = cepa_map.get(cepa_db)
            tipo = row["tipo"].strip() if row["tipo"] not in ("nan", "None") else None
            to_insert.append({
                "tank_id": tank_id,
                "wine_id": None,
                "grape_variety_id": cepa_id,
                "wine_type": tipo if tipo and tipo != "nan" else None,
                "current_liters": int(litros),
                "status": "Ocupado" if litros > 0 else "Vacio",
                "apto_envasado": apto,
                "wine_state": estado_vino,
            })
        else:
            to_insert.append({
                "tank_id": tank_id,
                "current_liters": 0,
                "status": "Vacio",
            })
        continue

    wine = wine_map.get(codigo)
    if not wine:
        errors.append("Vino '{}' no encontrado en BD para cuba {}".format(codigo, cuba_code))
        cepa_raw = row["variedad"]
        cepa_db = CEPA_MAP.get(cepa_raw, cepa_raw)
        cepa_id = cepa_map.get(cepa_db)
        tipo = row["tipo"].strip() if row["tipo"] not in ("nan", "None") else None
        to_insert.append({
            "tank_id": tank_id,
            "wine_id": None,
            "grape_variety_id": cepa_id,
            "wine_type": tipo if tipo and tipo != "nan" else None,
            "current_liters": int(litros),
            "status": "Ocupado" if litros > 0 else "Vacio",
            "apto_envasado": apto,
            "wine_state": estado_vino,
        })
        continue

    to_insert.append({
        "tank_id": tank_id,
        "wine_id": wine["id"],
        "grape_variety_id": wine["grape_variety_id"],
        "product_line_id": wine["product_line_id"],
        "wine_type": wine["wine_type"],
        "current_liters": int(litros),
        "status": "Ocupado" if litros > 0 else "Vacio",
        "apto_envasado": apto,
        "wine_state": estado_vino,
    })

print("A insertar: {}".format(len(to_insert)))
print("Errores: {}".format(len(errors)))
print("Omitidos: {}".format(len(skipped)))

if errors:
    print("\nERRORES:")
    for e in errors:
        print("  " + e)

# Insertar
inserted = 0
dupes = 0
for tc in to_insert:
    try:
        sb.table("tank_contents").insert(tc).execute()
        inserted += 1
    except Exception as e:
        err_str = str(e)
        if "duplicate" in err_str or "unique" in err_str.lower():
            dupes += 1
        else:
            print("  Error cuba {}: {}".format(tc.get("tank_id"), e))

print("\nInsertados: {} | Duplicados: {}".format(inserted, dupes))

# Verificar
total = sb.table("tank_contents").select("id", count="exact").execute()
ocupados = sb.table("tank_contents").select("id", count="exact").gt("current_liters", 0).execute()
print("Total registros: {} | Cubas con vino: {}".format(total.count, ocupados.count))
