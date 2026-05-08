"""
Sincroniza cubas: agrega faltantes del Excel, desactiva las que no estan en el Excel.
"""
import pandas as pd
import os, sys, tempfile, shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.database import get_supabase_client

EXCEL = r"C:\Users\cruiz\OneDrive\Pynthon\Scripts\Sistema Enologico\R03-ENO-02 - Inventario de vinos 2026.xlsx"
EXCLUDE_TANKS = {"Borra En Pasta 2026", "Ticket", "Total Borra En Pasta", "nan", "", "None"}
NUMERIC_JUNK_MIN_LEN = 5

sb = get_supabase_client()

# Leer Excel
tmp = os.path.join(tempfile.gettempdir(), "tanks_exec_temp.xlsx")
shutil.copy2(EXCEL, tmp)
df = pd.read_excel(tmp, sheet_name="07 MAY", header=0)
df.columns = [str(c).strip() for c in df.columns]
valid = df[df["Cubas"].notna()].copy()
valid["cuba"] = valid["Cubas"].astype(str).str.strip()

excel_tanks = set()
for c in valid["cuba"].unique():
    c = str(c).strip()
    if c and c not in EXCLUDE_TANKS:
        if len(c) >= NUMERIC_JUNK_MIN_LEN and c.isdigit():
            continue
        excel_tanks.add(c)

print("Cubas validas del Excel: {}".format(len(excel_tanks)))

# Leer BD
db_tanks = sb.table("tanks").select("id, code, is_active").execute().data
db_codes = {t["code"]: t for t in db_tanks}

# 1. AGREGAR FALTANTES
to_add = excel_tanks - set(db_codes.keys())
if to_add:
    print("\nAgregando {} cubas nuevas:".format(len(to_add)))
    for code in sorted(to_add):
        try:
            sb.table("tanks").insert({"code": code, "is_active": True}).execute()
            print("  + {}".format(code))
        except Exception as e:
            print("  ERROR {}: {}".format(code, e))
else:
    print("\nNo hay cubas nuevas que agregar")

# 2. DESACTIVAR las que no estan en Excel
to_deactivate = []
for t in db_tanks:
    if t["is_active"] and t["code"] not in excel_tanks:
        to_deactivate.append(t)

if to_deactivate:
    print("\nDesactivando {} cubas:".format(len(to_deactivate)))
    deactivated = 0
    for t in to_deactivate:
        try:
            sb.table("tanks").update({"is_active": False}).eq("id", t["id"]).execute()
            deactivated += 1
        except Exception as e:
            print("  ERROR {}: {}".format(t["code"], e))
    print("  Desactivadas: {}".format(deactivated))
else:
    print("\nNo hay cubas que desactivar")

# 3. Verificar
active = sb.table("tanks").select("id", count="exact").eq("is_active", True).execute()
print("\nCubas activas en BD: {}".format(active.count))
