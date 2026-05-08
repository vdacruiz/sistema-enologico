"""
Carga masiva de tratamientos historicos desde Excel 07 MAY.
Lee OTs de tratamientos (Enzima, Bentonita, Meta, etc.) y actualiza tank_contents.
"""
import os, sys, tempfile, shutil
import openpyxl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.database import get_supabase_client

EXCEL = r"C:\Users\cruiz\OneDrive\Pynthon\Scripts\Sistema Enologico\R03-ENO-02 - Inventario de vinos 2026.xlsx"
SHEET = "07 MAY"

TREATMENT_COLS = {
    11: "enzima",
    12: "gelatina",
    13: "bentonita",
    14: "frio",
    15: "meta",
    16: "cmc",
    17: "bic",
    18: "tangencial",
    19: "trasiego",
    20: "placas",
    21: "sulfirex",
    22: "goma",
    23: "sorbato",
}
SORBATO_DOSIS_COL = 24

sb = get_supabase_client()

tanks_db = sb.table("tanks").select("id, code").eq("is_active", True).execute().data
tank_map = {str(t["code"]): t["id"] for t in tanks_db}

tc_db = sb.table("tank_contents").select("id, tank_id").execute().data
tc_map = {tc["tank_id"]: tc["id"] for tc in tc_db}

tmp = os.path.join(tempfile.gettempdir(), "treatments_temp.xlsx")
shutil.copy2(EXCEL, tmp)
wb = openpyxl.load_workbook(tmp, data_only=True)
ws = wb[SHEET]

def parse_ots(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    parts = []
    for chunk in s.replace("-", ",").replace(";", ",").replace(" ", ",").split(","):
        chunk = chunk.strip()
        if chunk.isdigit():
            parts.append(chunk)
        elif chunk:
            parts.append(chunk)
    return ",".join(parts) if parts else None

def has_ot_numbers(value):
    if value is None:
        return False
    s = str(value).strip()
    if not s:
        return False
    for chunk in s.replace("-", ",").replace(";", ",").replace(" ", ",").split(","):
        if chunk.strip().isdigit():
            return True
    return bool(s)

updated = 0
skipped = 0
not_found = 0

for row in ws.iter_rows(min_row=2, max_row=1638, values_only=False):
    tank_num = row[0].value
    if tank_num is None:
        continue

    tank_code = str(tank_num)
    tank_id = tank_map.get(tank_code)
    if not tank_id:
        continue

    tc_id = tc_map.get(tank_id)
    if not tc_id:
        not_found += 1
        continue

    update_data = {}
    has_any = False

    for col_idx, field in TREATMENT_COLS.items():
        cell_val = row[col_idx - 1].value
        if cell_val is not None:
            has_any = True
            update_data[f"has_{field}"] = True
            ots = parse_ots(cell_val)
            if ots:
                update_data[f"{field}_ots"] = ots

    sorbato_dosis = row[SORBATO_DOSIS_COL - 1].value
    if sorbato_dosis is not None:
        update_data["sorbato_dosis"] = str(sorbato_dosis)

    if has_any:
        try:
            sb.table("tank_contents").update(update_data).eq("id", tc_id).execute()
            updated += 1
            if updated % 50 == 0:
                print(f"  ... {updated} cubas actualizadas")
        except Exception as e:
            print(f"  ERROR cuba {tank_code}: {e}")
            skipped += 1
    else:
        skipped += 1

print(f"\nResultado:")
print(f"  Cubas actualizadas: {updated}")
print(f"  Sin tratamientos: {skipped}")
print(f"  Sin registro en tank_contents: {not_found}")
print("Listo!")
