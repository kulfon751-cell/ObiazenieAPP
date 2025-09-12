"""Merge 'Grupa Zasobów' with 'NazwaUrz.' from Scalanie17.xlsx.
Generuje scalanie_group_name.csv (kolumny: group,names) z unikalnymi nazwami (semicolon).
Przy braku pliku lub kolumn tworzy pusty CSV.
Można wywołać jako moduł (main()) w testach.
Env override: SCALANIE_FILE_PATH.
"""
from __future__ import annotations
import pandas as pd
import pathlib
import os
from typing import Optional
import logging

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_INPUT = pathlib.Path(r"\\nas1\PRODUKCJA\Scalanie17.xlsx")
DEFAULT_OUTPUT = ROOT / "scalanie_group_name.csv"

EXCLUDE_STR = {"nan", "none"}

def detect_input(path_override: Optional[str] = None) -> pathlib.Path:
    env_val = os.environ.get("SCALANIE_FILE_PATH")
    if path_override:
        return pathlib.Path(path_override)
    if env_val:
        return pathlib.Path(env_val)
    return DEFAULT_INPUT

def write_empty_csv(output: pathlib.Path) -> None:
    pd.DataFrame(columns=["group", "names"]).to_csv(output, index=False, encoding="utf-8-sig")
    logging.getLogger(__name__).info("Zapisano pusty plik: %s", output)

def read_source_excel(path: pathlib.Path) -> Optional[pd.DataFrame]:
    """Read Excel file defensively. If there are multiple sheets, concat them vertically.
    Returns None on failure.
    """
    # try cache first
    try:
        from app.cache import load_df, save_df
        cached = load_df(path)
        if cached is not None:
            logging.getLogger(__name__).info("Loaded cached DataFrame for %s", path)
            return cached
    except Exception:
        # cache optional — ignore on failure
        pass

    try:
        # read all sheets -> dict of DataFrames
        data = pd.read_excel(path, engine="openpyxl", sheet_name=None)
    except Exception as e:
        logging.getLogger(__name__).exception("Błąd odczytu pliku: %s", e)
        return None
    if isinstance(data, dict):
        # concat sheets that have at least one column
        dfs = [df for df in data.values() if isinstance(df, pd.DataFrame) and df.shape[1] > 0]
        if not dfs:
            return pd.DataFrame()
        try:
            res = pd.concat(dfs, ignore_index=True, sort=False)
            try:
                from app.cache import save_df
                save_df(path, res)
            except Exception:
                pass
            return res
        except Exception as e:
            logging.getLogger(__name__).exception("Błąd łączenia arkuszy: %s", e)
            return None
    if isinstance(data, pd.DataFrame):
        return data
    return None

def find_columns(df: pd.DataFrame) -> tuple[Optional[str], Optional[str]]:
    # normalize column names to strings
    cols = [str(c) for c in df.columns]
    low_map = {c.lower(): orig for c, orig in zip(cols, df.columns)}
    group_col = None
    for k, orig in low_map.items():
        if "grupa" in k and "zasob" in k:
            group_col = orig
            break
    if not group_col:
        for k, orig in low_map.items():
            if "grupa" in k:
                group_col = orig
                break
    name_col = None
    for k, orig in low_map.items():
        if "nazwa" in k and ("urz" in k or "urz." in k or "urzad" in k or "urząd" in k):
            name_col = orig
            break
    if not name_col:
        for k, orig in low_map.items():
            if any(x in k for x in ["nazwa", "urz", "urzad"]):
                name_col = orig
                break
    return group_col, name_col

def build_output(df: pd.DataFrame, group_col: str, name_col: Optional[str]) -> pd.DataFrame:
    # coerce to string and strip; handle missing columns gracefully
    grp = df.get(group_col, pd.Series([None] * len(df))).astype(object).fillna("").astype(str).str.strip()
    if name_col and name_col in df.columns:
        names = df.get(name_col, pd.Series([""] * len(df))).astype(object).fillna("").astype(str).str.strip()
    else:
        names = pd.Series([""] * len(df))
    out = (
        pd.DataFrame({"group": grp, "name": names})
        .groupby("group", dropna=False)["name"]
        .apply(lambda s: ";".join(sorted({v for v in s if v and v.strip().lower() not in EXCLUDE_STR})))
        .reset_index()
        .rename(columns={"name": "names"})
    )
    out["names"] = out["names"].replace({"": ""})
    return out

def main(input_path: Optional[str] = None, output_path: Optional[str] = None) -> pd.DataFrame:
    INPUT = detect_input(input_path)
    OUTPUT = pathlib.Path(output_path) if output_path else DEFAULT_OUTPUT
    if not INPUT.exists():
        logging.getLogger(__name__).warning("Scalanie file not found: %s", INPUT)
        write_empty_csv(OUTPUT)
        return pd.DataFrame(columns=["group", "names"])

    df = read_source_excel(INPUT)
    if df is None:
        write_empty_csv(OUTPUT)
        return pd.DataFrame(columns=["group", "names"])

    # if empty DataFrame after reading sheets
    if isinstance(df, pd.DataFrame) and df.shape[0] == 0:
        logging.getLogger(__name__).warning("Plik zawiera puste arkusze lub brak danych.")
        write_empty_csv(OUTPUT)
        return pd.DataFrame(columns=["group", "names"])

    group_col, name_col = find_columns(df)
    if not group_col:
        logging.getLogger(__name__).warning("Nie znaleziono kolumny z Grupą zasobów.")
        write_empty_csv(OUTPUT)
        return pd.DataFrame(columns=["group", "names"])

    out = build_output(df, group_col, name_col)
    try:
        out.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
        logging.getLogger(__name__).info("Zapisano: %s", OUTPUT)
    except Exception as e:
        logging.getLogger(__name__).exception("Błąd zapisu pliku CSV: %s", e)
        # attempt to write an empty CSV as fallback
        write_empty_csv(OUTPUT)
    return out

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print("Usage: merge_scalanie17.py <Scalanie17.xlsx> <out.csv>")
