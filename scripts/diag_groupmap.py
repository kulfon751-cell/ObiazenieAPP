import importlib, traceback, pathlib, sys, os

# Ensure the repository root is on sys.path so 'app' can be imported
repo_root = pathlib.Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

try:
    m = importlib.import_module('app.main')
except Exception:
    traceback.print_exc()
    sys.exit(2)
print('PROD_FILE ->', getattr(m, 'PROD_FILE', None))
print('DATA_FILE ->', getattr(m, 'DATA_FILE', None))
print('PROD_FILE exists:', pathlib.Path(getattr(m, 'PROD_FILE')).exists())
print('DATA_FILE exists:', pathlib.Path(getattr(m, 'DATA_FILE')).exists())
# list sheets in PROD_FILE
try:
    import pandas as pd
    pf = str(getattr(m, 'PROD_FILE'))
    print('\nReading sheets from PROD_FILE...')
    sheets = pd.ExcelFile(pf).sheet_names
    print('Sheets:', sheets)
except Exception as e:
    print('Failed to read PROD_FILE sheets:', e)
# attempt to load group map
try:
    gm = m.load_group_map(force=True)
    print('\nGroup map entries:', len(gm))
    sample = list(gm.items())[:20]
    for k,v in sample:
        print(k, '->', v)
except Exception as e:
    print('Failed to load group map:', e)

# show some production rows sample
try:
    pdf = m.load_production_data(force=True)
    print('\nProduction aggregated rows:', len(pdf))
    print(pdf.head(10).to_string())
except Exception as e:
    print('Failed to load production data:', e)
