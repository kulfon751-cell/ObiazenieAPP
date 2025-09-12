import sys
import pathlib
import pandas as pd

# Upewnij się, że katalog główny repo jest na sys.path
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import merge_scalanie17 as m  # teraz powinno działać

def create_excel(path: pathlib.Path, df: pd.DataFrame):
    df.to_excel(path, index=False, engine="openpyxl")

def test_basic_merge(tmp_path):
    src = tmp_path / "Scalanie17.xlsx"
    df = pd.DataFrame({
        "Grupa Zasobów": ["100", "100", "200"],
        "NazwaUrz.": ["A", "B", "C"]
    })
    create_excel(src, df)
    out_csv = tmp_path / "out.csv"
    result = m.main(input_path=str(src), output_path=str(out_csv))
    assert set(result.columns) == {"group", "names"}
    g100 = result[result.group == "100"].names.iloc[0]
    assert g100 in {"A;B", "B;A"}
    g200 = result[result.group == "200"].names.iloc[0]
    assert g200 == "C"

def test_missing_file(tmp_path):
    missing = tmp_path / "brak.xlsx"
    out_csv = tmp_path / "empty.csv"
    result = m.main(input_path=str(missing), output_path=str(out_csv))
    assert result.empty
    assert out_csv.exists()