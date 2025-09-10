"""Merge 'Grupa Zasobów' with 'NazwaUrz.' from Scalanie17.xlsx.
Produces scalanie_group_name.csv at repo root with columns: group, names
names: semicolon-separated unique NazwaUrz. values or empty if none.
"""
import pandas as pd
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INPUT = ROOT / 'Scalanie17.xlsx'
OUTPUT = ROOT / 'scalanie_group_name.csv'

if not INPUT.exists():
    print(f"Plik nie istnieje: {INPUT}")
    sys.exit(2)

# read first sheet
try:
    df = pd.read_excel(INPUT)
except Exception as e:
    print('Błąd odczytu pliku:', e)
    sys.exit(3)

# normalize columns to lower
cols = {c.lower(): c for c in df.columns}
# find group column
group_col = None
for k, orig in cols.items():
    if 'grupa' in k and 'zasob' in k:
        group_col = orig
        break
if group_col is None:
    # try approximate
    for k, orig in cols.items():
        if 'grupa' in k:
            group_col = orig
            break

# find name column
name_col = None
for k, orig in cols.items():
    if 'nazwa' in k and ('urz' in k or 'urz.' in k or 'urzad' in k or 'urząd' in k):
        name_col = orig
        break
if name_col is None:
    for k, orig in cols.items():
        if 'nazwa' in k or 'urz' in k or 'urzad' in k:
            name_col = orig
            break

if group_col is None:
    print('Nie znaleziono kolumny z Grupą zasobów w pliku.')
    sys.exit(4)

# ensure columns exist in df
grp_series = df[group_col].astype(str).str.strip()
if name_col:
    name_series = df[name_col].astype(str).str.strip()
else:
    name_series = pd.Series([''] * len(df))

out = (
    pd.DataFrame({'group': grp_series, 'name': name_series})
    .groupby('group', dropna=False)['name']
    .apply(lambda s: ';'.join(sorted({v for v in s if v and str(v).strip().lower() not in ['nan','none']})))
    .reset_index()
)
# replace empty strings with empty (already empty)
out['name'] = out['name'].replace({'': ''})

out.to_csv(OUTPUT, index=False, encoding='utf-8-sig')
print(f'Zapisano: {OUTPUT}')
