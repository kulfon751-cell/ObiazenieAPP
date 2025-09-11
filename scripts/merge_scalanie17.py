"""Merge 'Grupa Zasobów' with 'NazwaUrz.' from Scalanie17.xlsx.
Produces scalanie_group_name.csv at repo root with columns: group, names
names: semicolon-separated unique NazwaUrz. values or empty if none.
"""
import pandas as pd
import pathlib
import sys
import os

ROOT = pathlib.Path(__file__).resolve().parent.parent
# allow overriding via env var SCALANIE_FILE_PATH, otherwise use NAS share
_env_val = os.environ.get('SCALANIE_FILE_PATH')
if _env_val:
    INPUT = pathlib.Path(_env_val)
else:
    INPUT = pathlib.Path(r"\\nas1\PRODUKCJA\Scalanie17.xlsx")
OUTPUT = ROOT / 'scalanie_group_name.csv'

def write_empty():
    empty = pd.DataFrame(columns=['group', 'names'])
    empty.to_csv(OUTPUT, index=False, encoding='utf-8-sig')
    print(f'Zapisano pusty plik: {OUTPUT}')

# jeśli brak pliku -> zapisz pusty CSV i zakończ bez błędu
if not INPUT.exists():
    print(f"Ostrzeżenie: plik nie istnieje: {INPUT}")
    write_empty()
    sys.exit(0)

# read first sheet
try:
    df = pd.read_excel(INPUT)
except Exception as e:
    print('Błąd odczytu pliku:', e)
    write_empty()
    sys.exit(0)

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
    write_empty()
    sys.exit(0)

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
# ensure column name 'names' as documented
out = out.rename(columns={'name': 'names'})

# normalize empty strings
out['names'] = out['names'].replace({'': ''})

out.to_csv(OUTPUT, index=False, encoding='utf-8-sig')
print(f'Zapisano: {OUTPUT}')
