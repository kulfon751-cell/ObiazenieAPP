import pandas as pd
from pathlib import Path
import re

PROD = Path(__file__).resolve().parent / 'Raport_dane.xlsx'
print('PROD file:', PROD)
try:
    df = pd.read_excel(PROD, sheet_name='RaportProdukcja')
except Exception as e:
    print('Failed to read RaportProdukcja:', e)
    raise SystemExit(1)

print('\nColumns:')
for c in df.columns:
    print('-', repr(c))

lc = {str(c).lower(): c for c in df.columns}
print('\nNormalized keys:')
print(list(lc.keys()))

# find candidate group columns
group_candidates = [c for c in df.columns if 'grup' in str(c).lower() or 'group' in str(c).lower() or 'zasob' in str(c).lower()]
print('\nGroup candidate columns:')
print(group_candidates)

# search for '10250' anywhere
needle = '10250'
mask_any = df.apply(lambda row: row.astype(str).str.contains(needle, na=False).any(), axis=1)
print('\nRows with any cell containing', needle, ':', int(mask_any.sum()))

if mask_any.sum() > 0:
    sample = df[mask_any].head(20)
    print('\nSample rows (up to 20) with any cell containing', needle, ':')
    print(sample.to_csv(index=False, sep='|'))
else:
    # also try digits search (in case of spaces or formatting)
    print('\nNo direct string matches for', needle, "— trying digit-only search")
    def digits_only(s):
        return ''.join(re.findall(r"\d+", str(s)))
    mask_digits = df.apply(lambda row: row.astype(str).apply(digits_only).str.contains(needle).any(), axis=1)
    print('Rows matching digits-only:', int(mask_digits.sum()))
    if mask_digits.sum() > 0:
        print(df[mask_digits].head(20).to_csv(index=False, sep='|'))

# show unique values from group candidate columns (first 50 each)
for col in group_candidates:
    vals = df[col].astype(str).unique()[:50]
    print(f"\nUnique values in {col} (up to 50):")
    for v in vals:
        print('-', v)

print('\nDone')
