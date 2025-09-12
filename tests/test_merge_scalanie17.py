import pandas as pd
import pathlib
from scripts import merge_scalanie17 as m

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
    out = m.main(input_path=str(src), output_path=str(out_csv))
    assert set(out.columns) == {"group", "names"}
    row_100 = out[out["group"] == "100"]["names"].iloc[0]
    assert row_100 in {"A;B", "B;A"}
    row_200 = out[out["group"] == "200"]["names"].iloc[0]
    assert row_200 == "C"

def test_missing_file(tmp_path):
    missing = tmp_path / "no_file.xlsx"
    out_csv = tmp_path / "empty.csv"
    out = m.main(input_path=str(missing), output_path=str(out_csv))
    assert out.empty
    assert out_csv.exists()