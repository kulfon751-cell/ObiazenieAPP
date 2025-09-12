from pathlib import Path

import pandas as pd

from scripts import merge_scalanie17 as m


def create_excel(path: Path, df: pd.DataFrame):
    df.to_excel(path, index=False, engine="openpyxl")


def test_basic_merge(tmp_path: Path):
    src = tmp_path / "Scalanie17.xlsx"
    df = pd.DataFrame({
        "Grupa Zasobów": ["100", "100", "200"],
        "NazwaUrz.": ["A", "B", "C"],
    })
    create_excel(src, df)
    out_csv = tmp_path / "out.csv"
    result = m.main(input_path=str(src), output_path=str(out_csv))
    assert set(result.columns) == {"group", "names"}
    g100 = result[result.group == "100"].names.iloc[0]
    assert set(g100.split(";")) == {"A", "B"}
    g200 = result[result.group == "200"].names.iloc[0]
    assert g200 == "C"


def test_missing_file_creates_empty(tmp_path: Path):
    missing = tmp_path / "nosuch.xlsx"
    out_csv = tmp_path / "out.csv"
    res = m.main(str(missing), str(out_csv))
    assert res.empty
    assert out_csv.exists()


def test_empty_sheets_produces_empty(tmp_path: Path):
    src = tmp_path / "Scalanie17.xlsx"
    # create an excel with one empty sheet
    with pd.ExcelWriter(src, engine="openpyxl") as w:
        pd.DataFrame().to_excel(w, sheet_name="Sheet1", index=False)
    out = tmp_path / "out.csv"
    res = m.main(str(src), str(out))
    assert res.empty


def test_non_string_values_and_misnamed_columns(tmp_path: Path):
    src = tmp_path / "Scalanie17.xlsx"
    # column names slightly different and values non-string
    df = pd.DataFrame({
        "GRUPA ZASOBOW": [100, 100, 200],
        "NAZWA_URZ": [None, 2, 3],
    })
    create_excel(src, df)
    out = tmp_path / "out.csv"
    res = m.main(str(src), str(out))
    # should have groups and names concatenated (numbers coerced to strings)
    assert "100" in res['group'].values
    row = res[res['group'] == '100']
    assert not row.empty