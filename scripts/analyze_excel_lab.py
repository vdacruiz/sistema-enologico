"""
Analiza las columnas de Estado, Lab y Tratamiento del Excel 07 MAY
"""
import pandas as pd
import os, tempfile, shutil

EXCEL = r"C:\Users\cruiz\OneDrive\Pynthon\Scripts\Sistema Enologico\R03-ENO-02 - Inventario de vinos 2026.xlsx"
tmp = os.path.join(tempfile.gettempdir(), "lab_analysis_temp.xlsx")
shutil.copy2(EXCEL, tmp)
df = pd.read_excel(tmp, sheet_name="07 MAY", header=0)
df.columns = [str(c).strip() for c in df.columns]

print("=== TODAS LAS COLUMNAS ===")
for i, c in enumerate(df.columns):
    print("  {:2d}. {}".format(i, repr(c)))

valid = df[df["Cubas"].notna()].copy()
valid["cuba"] = valid["Cubas"].astype(str).str.strip()

# Estado
print("\n=== ESTADO (valores unicos) ===")
if "Estado" in valid.columns:
    estados = valid["Estado"].dropna().astype(str).str.strip().unique()
    for e in sorted(estados):
        count = len(valid[valid["Estado"].astype(str).str.strip() == e])
        print("  {}: {} cubas".format(e, count))

# Envasado
print("\n=== ENVASADO (valores unicos) ===")
if "Envasado" in valid.columns:
    envs = valid["Envasado"].dropna().astype(str).str.strip().unique()
    for e in sorted(envs):
        print("  {}".format(e))

# Lab columns - mostrar datos de las primeras cubas que tienen valores
lab_cols_candidates = []
for c in df.columns:
    if c in ("pH", "A.T.", "A.V.", "SO2 L", "SO2 T", "MR", "CO2", "NTU", "Color", "I.C", "O2", "EP", "ET", "FML"):
        lab_cols_candidates.append(c)
    elif "SO2" in c or "pH" in c:
        lab_cols_candidates.append(c)

# Check columns with special chars
for c in df.columns:
    if any(x in c for x in ["A.", "SO2", "NTU", "Color", "FML", "CO2"]):
        if c not in lab_cols_candidates:
            lab_cols_candidates.append(c)

print("\n=== COLUMNAS DE LAB ENCONTRADAS ===")
for c in lab_cols_candidates:
    non_null = valid[c].dropna()
    numeric = pd.to_numeric(non_null, errors="coerce").dropna()
    print("  {}: {} valores, {} numericos".format(repr(c), len(non_null), len(numeric)))
    if len(numeric) > 0:
        print("    min={:.2f} max={:.2f} mean={:.2f}".format(numeric.min(), numeric.max(), numeric.mean()))

# Muestra de una cuba con datos completos
print("\n=== MUESTRA: Cuba 3 (primeras filas con datos lab) ===")
cols_to_show = ["cuba", "Estado"]
cols_to_show += [c for c in lab_cols_candidates if c in valid.columns]

# Find a row with lab data
for _, row in valid.head(20).iterrows():
    has_lab = False
    for c in lab_cols_candidates:
        val = row.get(c)
        if pd.notna(val) and str(val).strip() not in ("nan", ""):
            has_lab = True
            break
    if has_lab:
        print("  Cuba: {}".format(row.get("cuba", "?")))
        print("  Estado: {}".format(row.get("Estado", "?")))
        for c in lab_cols_candidates:
            print("    {}: {}".format(c, row.get(c, "-")))
        print()

# Anno column
anno_col = None
for c in df.columns:
    clow = c.lower().replace("\xf1", "n")
    if "ano" in clow or "year" in clow or c == "A\xf1o":
        anno_col = c
        break
if not anno_col:
    for c in df.columns:
        if len(c) <= 4 and c not in lab_cols_candidates:
            vals = valid[c].dropna().astype(str).str.strip().unique()
            year_like = [v for v in vals if v.isdigit() and 2019 <= int(v) <= 2030]
            if len(year_like) > 3:
                anno_col = c
                break

if anno_col:
    print("=== COLUMNA AÑO: {} ===".format(repr(anno_col)))
    years = valid[anno_col].dropna().astype(str).str.strip().unique()
    for y in sorted(years):
        print("  {}".format(y))
