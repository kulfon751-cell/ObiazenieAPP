from fastapi import FastAPI, HTTPException, Query, Body, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import shutil
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import os
from datetime import date, datetime, timedelta
import calendar
import pathlib
# initialize logging early
try:
    from .logging_config import setup_logging
    setup_logging()
except Exception:
    # fail silently in environments where logging can't be configured
    pass

# Files expected at repository root by default.
# Allow overriding via environment variables so the app can read files from a network share
# Examples:
#  - set DATA_FILE_PATH="Z:\\folder\\DostepnoscWTygodniach.xlsx"
#  - set PROD_FILE_PATH="\\\\server\\share\\Raport_dane.xlsx"
def _resolve_path_from_env(varname: str, default_path: pathlib.Path) -> pathlib.Path:
    v = os.environ.get(varname)
    if not v:
        return default_path
    try:
        p = pathlib.Path(v)
        if not p.is_absolute():
            # interpret relative paths relative to repo root
            p = (pathlib.Path(__file__).resolve().parent.parent / p).resolve()
        return p
    except Exception:
        return default_path

# Default files: prefer network share on NAS1 (can still be overridden via env vars)
DEFAULT_DATA = pathlib.Path(r"\\nas1\PRODUKCJA\DostepnoscWTygodniach.xlsx")
DEFAULT_PROD = pathlib.Path(r"\\nas1\PRODUKCJA\Raport_dane.xlsx")

DATA_FILE = _resolve_path_from_env('DATA_FILE_PATH', DEFAULT_DATA)
PROD_FILE = _resolve_path_from_env('PROD_FILE_PATH', DEFAULT_PROD)

# Directory where users can upload local copies if they don't have UNC access
ROOT = pathlib.Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / 'uploaded'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Filenames for uploaded overrides
UPLOADED_PROD_NAME = 'Raport_dane.xlsx'
UPLOADED_DATA_NAME = 'DostepnoscWTygodniach.xlsx'

app = FastAPI(title="Dostępność urządzeń")

 

class DevicePartLoad(BaseModel):
    part_number: str
    week: int
    year: int
    praca_tpz: float
    order_id: Optional[str] = None

@app.get('/device_parts/{device_id}', response_model=List[DevicePartLoad])
async def device_parts(device_id: str, month: List[str] = Query(...)):
    """Zwraca obciążenie maszyny po numerze części w wybranych miesiącach."""
    import traceback
    try:
        prod_df = pd.read_excel(PROD_FILE, sheet_name='RaportProdukcja')
        lc = {c.lower(): c for c in prod_df.columns}
        # heuristics to find columns
        group_col = next((lc[k] for k in lc if 'grupa' in k and 'zasob' in k), None) or next((lc[k] for k in lc if 'grupa' in k), None)
        part_col = (next((lc[k] for k in lc if ('numer' in k and ('czesc' in k or 'czes' in k or 'czesci' in k)) or ('nr' in k and 'cz' in k)), None)
                    or next((lc[k] for k in lc if 'numer' in k), None)
                    or next((lc[k] for k in lc if 'part' in k), None))
        week_col = next((lc[k] for k in lc if 'tyd' in k), None) or next((lc[k] for k in lc if 'week' in k), None)
        year_col = next((lc[k] for k in lc if 'rok' in k or 'year' in k or 'rokmies' in k or 'rokmiesiac' in k), None)
        praca_col = next((lc[k] for k in lc if 'praca' in k), None)
        # try to find an "ID zlecenia" / order id column (optional)
        order_col = (next((lc[k] for k in lc if 'id' in k and ('zlec' in k or 'zlecen' in k)), None)
                     or next((lc[k] for k in lc if ('zlec' in k or 'zlecen' in k)), None))

        if not all([group_col, part_col, week_col, year_col, praca_col]):
            raise HTTPException(status_code=500, detail='Brak wymaganych kolumn w RaportProdukcja')

        # parse months
        month_ranges = []
        for m in month:
            try:
                month_dt = datetime.strptime(m, '%Y-%m')
            except ValueError:
                continue
            y = month_dt.year
            mn = month_dt.month
            first = date(y, mn, 1)
            last = date(y, mn, calendar.monthrange(y, mn)[1])
            month_ranges.append((y, mn, first, last))

        # filter by device/group and months
        device_series = prod_df[group_col].astype(str)
        clean_device_id = device_id.lower().strip()
        # exact match (case-insensitive)
        device_mask = device_series.str.lower().str.strip() == clean_device_id
        filtered = prod_df[device_mask].copy()
        # fallback: group contains the device id (e.g. '10250_Frezarki')
        if filtered.empty:
            try:
                filtered = prod_df[device_series.str.lower().str.contains(clean_device_id, na=False)].copy()
            except Exception:
                filtered = prod_df[device_series.str.contains(clean_device_id, na=False)].copy()
        # fallback: digits-only match (e.g. group names like '10250_Frezarki')
        if filtered.empty:
            import re
            digits = ''.join(re.findall(r"\d+", clean_device_id))
            if digits:
                filtered = prod_df[device_series.str.contains(digits, na=False)].copy()
        results = []
        def _parse_year(val):
            try:
                if pd.isna(val):
                    return None
            except Exception:
                pass
            # direct int
            try:
                return int(val)
            except Exception:
                pass
            # string like '2025-09' or '2025-09-01'
            try:
                s = str(val)
                m = s.strip().split('-')
                if len(m) >= 1 and m[0].isdigit() and len(m[0]) == 4:
                    return int(m[0])
                # fallback: find first 4-digit group
                import re
                mm = re.search(r"(\d{4})", s)
                if mm:
                    return int(mm.group(1))
            except Exception:
                pass
            return None

        for _, row in filtered.iterrows():
            try:
                w = int(row[week_col])
            except Exception:
                continue
            y = _parse_year(row[year_col])
            if y is None:
                continue
            try:
                praca = float(row[praca_col])
            except Exception:
                praca = 0.0
            part = str(row[part_col])
            # check week range overlap
            try:
                week_start, week_end = get_week_date_range(y, w)
            except Exception:
                continue
            for (my, mm, mstart, mend) in month_ranges:
                if week_end < mstart or week_start > mend:
                    continue
                # extract order id if available
                ord_id = None
                try:
                    if order_col is not None:
                        v = row[order_col]
                        if pd.isna(v):
                            ord_id = None
                        else:
                            ord_id = str(v)
                except Exception:
                    ord_id = None
                results.append(DevicePartLoad(part_number=part, week=w, year=y, praca_tpz=praca, order_id=ord_id))
                break
        return results
    except HTTPException:
        raise
    except Exception:
        tb = traceback.format_exc()
        try:
            log_path = pathlib.Path(__file__).resolve().parent.parent / 'device_parts_error.log'
            with open(log_path, 'a', encoding='utf-8') as fh:
                fh.write(f"=== {datetime.now().isoformat()} ===\n")
                fh.write(tb + '\n')
        except Exception:
            pass
        raise HTTPException(status_code=500, detail='Błąd wewnętrzny. Sprawdź device_parts_error.log')


class WeeklyAvailability(BaseModel):
    week_number: int
    iso_year: int
    hours: float
    start_date: date
    end_date: date
    prorated_hours: Optional[float] = None
    load_hours: Optional[float] = None
    prorated_load_hours: Optional[float] = None


class AvailabilityResponse(BaseModel):
    device_id: str
    month: str
    working_days_in_month: int
    weekly: List[WeeklyAvailability]
    # legacy/primary sum (kept for compatibility) - equals prorated or full depending on `prorated` flag
    monthly_hours_sum: float
    prorated: bool = False
    # explicit both-sum fields
    monthly_hours_full_sum: float
    monthly_hours_prorated_sum: float
    monthly_load_full_sum: float = 0.0
    monthly_load_prorated_sum: float = 0.0


class DeviceAggregate(BaseModel):
    device_id: str
    display_name: Optional[str] = None
    department: Optional[str] = None
    monthly_hours_full_sum: float
    monthly_hours_prorated_sum: float
    monthly_load_full_sum: float
    monthly_load_prorated_sum: float
    shortage_full: float
    shortage_prorated: float


# module-level caches (no annotations)
_cache_df = None
_cache_mtime = None
_prod_cache_df = None
_prod_cache_mtime = None
_group_map_cache = None
_group_map_mtime = None


def load_data(force: bool = False) -> pd.DataFrame:
    """Load availability data from DostepnoscWTygodniach.xlsx and normalize columns."""
    global _cache_df, _cache_mtime
    # prefer uploaded file if present
    uploaded = UPLOAD_DIR / UPLOADED_DATA_NAME
    source = uploaded if uploaded.exists() else DATA_FILE
    if not source.exists():
        raise FileNotFoundError(f"Brak pliku: {source}")
    mtime = source.stat().st_mtime
    if force or _cache_df is None or _cache_mtime != mtime:
        df = pd.read_excel(source)
        lc = {c.lower(): c for c in df.columns}
        device_col = next((lc[k] for k in lc if k in ['device', 'urzadzenie', 'grupa zasobów', 'grupa_zasobow', 'grupa zasobow', 'resource', 'maszyna']), None)
        if device_col is None:
            for original in df.columns:
                if original.lower().replace('ó', 'o').replace('_', ' ') == 'grupa zasobow':
                    device_col = original
                    break
        week_col = next((lc[k] for k in lc if k in ['week', 'tydzien', 'nr_tyg', 'nr tyg', 'tydzien realizacji', 'tydzien_realizacji']), None)
        year_col = next((lc[k] for k in lc if k in ['year', 'rok']), None)
        hours_col = next((lc[k] for k in lc if k in ['hours', 'godziny', 'dostepnosc', 'dostepnosctygodniowa', 'available_hours', 'dostepnosc tygodniowa', 'dostepnosc_tygodniowa']), None)
        if not all([device_col, week_col, year_col, hours_col]):
            raise ValueError("Nie rozpoznano wymaganych kolumn (device/week/year/hours)")
        df = df.rename(columns={device_col: 'device', week_col: 'week', year_col: 'year', hours_col: 'hours'})
        df['week'] = pd.to_numeric(df['week'], errors='coerce').astype('Int64').fillna(0).astype(int)
        df['year'] = pd.to_numeric(df['year'], errors='coerce').astype('Int64').fillna(datetime.now().year).astype(int)
        df['hours'] = pd.to_numeric(df['hours'], errors='coerce').fillna(0.0).astype(float)
        _cache_df = df
        _cache_mtime = mtime
    return _cache_df


def load_production_data(force: bool = False) -> pd.DataFrame:
    """Load and aggregate production data from sheet 'RaportProdukcja' into group/year/week sums."""
    global _prod_cache_df, _prod_cache_mtime
    # prefer uploaded production file if present
    uploaded = UPLOAD_DIR / UPLOADED_PROD_NAME
    source = uploaded if uploaded.exists() else PROD_FILE
    if not source.exists():
        raise FileNotFoundError(f"Brak pliku produkcji: {source}")
    mtime = source.stat().st_mtime
    if force or _prod_cache_df is None or _prod_cache_mtime != mtime:
        pdf = pd.read_excel(source, sheet_name='RaportProdukcja')
        lc = {c.lower(): c for c in pdf.columns}
        group_col = next((lc[k] for k in lc if 'grupa' in k and 'zasob' in k), None)
        if group_col is None:
            group_col = next((c for c in pdf.columns if 'grupa' in str(c).lower() and 'zasob' in str(c).lower()), None)
        week_col = next((lc[k] for k in lc if 'tyd' in k and 'realiz' in k), None)
        if week_col is None:
            week_col = next((c for c in pdf.columns if 'tydzie' in str(c).lower() or 'tydzien' in str(c).lower()), None)
        praca_col = next((lc[k] for k in lc if 'praca' in k and ('tpz' in k or '+' in k) or 'praca+tpz' in k), None)
        if praca_col is None:
            praca_col = next((c for c in pdf.columns if 'praca' in str(c).lower()), None)
        rokmies_col = next((lc[k] for k in lc if 'rokmies' in k), None)
        year_col = next((lc[k] for k in lc if k in ['year', 'rok']), None)
        if group_col is None or week_col is None or praca_col is None:
            raise ValueError('Nie rozpoznano kolumn produkcji (grupa/tydzien/praca)')
        # try to infer year
        if year_col is None:
            if rokmies_col is not None:
                pdf['year'] = pdf[rokmies_col].astype(str).str.slice(0, 4).astype(int)
            else:
                tr = next((c for c in pdf.columns if 'termin' in str(c).lower()), None)
                if tr is not None:
                    pdf['year'] = pd.to_datetime(pdf[tr], errors='coerce').dt.year.fillna(datetime.now().year).astype(int)
                else:
                    pdf['year'] = datetime.now().year
        else:
            pdf['year'] = pd.to_numeric(pdf[year_col], errors='coerce').fillna(datetime.now().year).astype(int)

        pdf = pdf.rename(columns={group_col: 'group', week_col: 'week', praca_col: 'praca_tpz'})
        pdf['group'] = pdf['group'].astype(str)
        pdf['week'] = pd.to_numeric(pdf['week'], errors='coerce').fillna(0).astype(int)
        pdf['praca_tpz'] = pd.to_numeric(pdf['praca_tpz'], errors='coerce').fillna(0.0)
        agg = pdf.groupby(['group', 'year', 'week'], as_index=False)['praca_tpz'].sum()
        _prod_cache_df = agg
        _prod_cache_mtime = mtime
    return _prod_cache_df


def load_group_map(force: bool = False) -> dict:
    """Load mapping of group -> department from sheet 'GrupaZasobow' in Raport_dane.xlsx."""
    global _group_map_cache, _group_map_mtime
    if not PROD_FILE.exists():
        return {}
    mtime = PROD_FILE.stat().st_mtime
    if force or _group_map_cache is None or _group_map_mtime != mtime:
        try:
            gm = pd.read_excel(PROD_FILE, sheet_name='GrupaZasobow')
        except Exception:
            # try alternative sheet name with diacritics
            try:
                gm = pd.read_excel(PROD_FILE, sheet_name='GrupaZasobów')
            except Exception:
                _group_map_cache = {}
                _group_map_mtime = mtime
                return _group_map_cache

        lc = {c.lower(): c for c in gm.columns}
        # find group column
        group_col = next((lc[k] for k in lc if 'grupa' in k and 'zasob' in k), None)
        if group_col is None:
            group_col = next((c for c in gm.columns if 'grupa' in str(c).lower()), None)
        # find department column
        dept_col = next((lc[k] for k in lc if 'dzia' in k or 'dział' in k or 'department' in k), None)
        if dept_col is None:
            dept_col = next((c for c in gm.columns if 'dział' in str(c).lower() or 'dzial' in str(c).lower()), None)

        if group_col is None or dept_col is None:
            _group_map_cache = {}
            _group_map_mtime = mtime
            return _group_map_cache

        gm = gm.rename(columns={group_col: 'group', dept_col: 'department'})
        gm['group'] = gm['group'].astype(str)
        gm['department'] = gm['department'].astype(str)
        mapping = {str(r['group']).strip().lower(): str(r['department']).strip() for _, r in gm.iterrows()}
        _group_map_cache = mapping
        _group_map_mtime = mtime
    return _group_map_cache


def get_week_date_range(year: int, week: int):
    """Return ISO week start (Mon) and end (Sun) dates."""
    first_week_day = datetime.fromisocalendar(year, week, 1).date()
    last_week_day = datetime.fromisocalendar(year, week, 7).date()
    return first_week_day, last_week_day


def business_days_between(start: date, end: date) -> int:
    days = 0
    d = start
    while d <= end:
        if d.weekday() < 5:
            days += 1
        d += timedelta(days=1)
    return days


def working_days_in_month(year: int, month: int) -> int:
    first = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)
    return business_days_between(first, last)


@app.get('/availability/{device_id}', response_model=AvailabilityResponse)
async def availability(device_id: str, month: List[str] = Query(...), prorate: bool = False):
    """Compute availability for a device across one or more months (business days only).
    Accepts multiple `month=YYYY-MM` query params and returns weekly records for any week overlapping the selected months.
    """
    # parse months into ranges
    month_ranges = []
    for m in month:
        try:
            month_dt = datetime.strptime(m, '%Y-%m')
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Parametr month musi mieć format YYYY-MM: {m}")
        y = month_dt.year
        mn = month_dt.month
        first_month_day = date(y, mn, 1)
        last_month_day = date(y, mn, calendar.monthrange(y, mn)[1])
        month_ranges.append((first_month_day, last_month_day))

    # match device by text equality (case-insensitive)
    df = load_data()
    device_df = df[df['device'].astype(str).str.lower() == device_id.lower()].copy()
    if device_df.empty:
        raise HTTPException(status_code=404, detail="Nie znaleziono urządzenia")

    try:
        prod_df = load_production_data()
    except Exception:
        prod_df = pd.DataFrame(columns=['group', 'year', 'week', 'praca_tpz'])

    weekly_records = []
    for _, row in device_df.iterrows():
        w = int(row['week'])
        y = int(row['year'])
        try:
            week_start, week_end = get_week_date_range(y, w)
        except Exception:
            # bad week number
            continue
        # check overlap with any selected month ranges
        overlaps_any = False
        total_overlap_days = 0
        for (first_month_day, last_month_day) in month_ranges:
            if week_end < first_month_day or week_start > last_month_day:
                continue
            overlaps_any = True
            overlap_start = week_start if week_start > first_month_day else first_month_day
            overlap_end = week_end if week_end < last_month_day else last_month_day
            if overlap_start <= overlap_end:
                total_overlap_days += business_days_between(overlap_start, overlap_end)
        if not overlaps_any:
            continue
        hours = float(row['hours'])
        working_days_week = business_days_between(week_start, week_end)
        # prorated across total overlapping days
        prorated_hours = hours * (total_overlap_days / working_days_week) if working_days_week > 0 else 0.0

        # find production load by matching group name (Grupa zasobów)
        grp = str(row.get('device') or row.get('Grupa zasobów') or row.get('grupa zasobów') or '').strip()
        g_lower = grp.lower()
        # exact match first
        prod_row = prod_df[(prod_df['group'].astype(str).str.lower() == g_lower) & (prod_df['year'] == y) & (prod_df['week'] == w)]
        # fallback: group contains the device/group substring
        if prod_row.empty:
            prod_row = prod_df[(prod_df['group'].astype(str).str.lower().str.contains(g_lower, na=False)) & (prod_df['year'] == y) & (prod_df['week'] == w)]
        load_hours = float(prod_row['praca_tpz'].sum()) if not prod_row.empty else 0.0
        prorated_load = load_hours * (total_overlap_days / working_days_week) if working_days_week > 0 else 0.0

        weekly_records.append({
            'week_number': w,
            'iso_year': y,
            'hours': hours,
            'start_date': week_start,
            'end_date': week_end,
            'prorated_hours': prorated_hours,
            'load_hours': load_hours,
            'prorated_load_hours': prorated_load,
        })

    if not weekly_records:
        raise HTTPException(status_code=404, detail="Brak danych tygodniowych w wybranych miesiącach")

    # compute both full and prorated monthly sums
    monthly_hours_full = sum(r['hours'] for r in weekly_records)
    monthly_hours_pr = sum((r.get('prorated_hours') or 0.0) for r in weekly_records)
    monthly_load_full = sum((r.get('load_hours') or 0.0) for r in weekly_records)
    monthly_load_pr = sum((r.get('prorated_load_hours') or 0.0) for r in weekly_records)

    # preserve existing primary field behavior for backward compatibility
    monthly_hours = monthly_hours_pr if prorate else monthly_hours_full
    monthly_load = monthly_load_pr if prorate else monthly_load_full

    # compute total working days across selected months
    total_working_days = 0
    for (mstart, mend) in month_ranges:
        total_working_days += business_days_between(mstart, mend)

    resp = AvailabilityResponse(
        device_id=device_id,
        month=','.join(month),
        working_days_in_month=total_working_days,
        weekly=[WeeklyAvailability(**r) for r in weekly_records],
        monthly_hours_sum=monthly_hours,
        prorated=bool(prorate),
        monthly_hours_full_sum=monthly_hours_full,
        monthly_hours_prorated_sum=monthly_hours_pr,
        monthly_load_full_sum=monthly_load_full,
        monthly_load_prorated_sum=monthly_load_pr,
    )
    return resp


@app.get('/', response_class=HTMLResponse)
async def simple_ui():
    # show banner when uploaded override files exist
    banner_html = ''
    try:
        ups = []
        if (UPLOAD_DIR / UPLOADED_PROD_NAME).exists():
            ups.append(f'Raport: {UPLOADED_PROD_NAME}')
        if (UPLOAD_DIR / UPLOADED_DATA_NAME).exists():
            ups.append(f'Dostępność: {UPLOADED_DATA_NAME}')
        if ups:
            banner_html = f"""
            <div id='uploadBanner' style='background:#07303a;color:#bde4ff;padding:10px;border-radius:6px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center'>
                <div><strong>Używane pliki z katalogu uploaded/:</strong> {'; '.join(ups)}</div>
                <div><button id='clearUploadsBtn' style='background:#ef4444;color:white;border:0;padding:6px 8px;border-radius:4px;cursor:pointer'>Wyczyść nadpisania</button></div>
            </div>
            """
    except Exception:
        banner_html = ''

    html = """
<!doctype html>
<!doctype html>
<html>
    <head>
        <meta charset="utf-8" />
        <title>Dostępność - dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root{--bg:#0f1720;--panel:#111827;--muted:#9CA3AF;--text:#E5E7EB;--accent:#60A5FA;--good:#34D399;--bad:#EF4444}
            body{background:var(--bg);color:var(--text);font-family:Segoe UI, Arial;margin:1rem}
            .layout{display:grid;grid-template-rows:auto 1fr;gap:1rem}
            header{font-size:1.6rem;font-weight:700;margin-bottom:.25rem;text-align:center;padding:10px 14px;border-radius:8px;background:linear-gradient(90deg, rgba(52,211,153,0.06), rgba(239,68,68,0.04));color:var(--text);max-width:900px;margin:0 auto}
            .content{display:grid;grid-template-columns:260px 1fr;gap:1rem}
            .panel{background:var(--panel);padding:12px;border-radius:6px}
            .slicers label{display:block;margin:.4rem 0;color:var(--muted)}
            input[type=text], select{width:100%;padding:6px;border-radius:4px;border:1px solid #203040;background:#081018;color:var(--text)}
            table{width:100%;border-collapse:collapse;color:var(--text);font-size:0.9rem}
            th,td{padding:6px;border-bottom:1px solid rgba(255,255,255,0.03);text-align:left}
            th{color:var(--muted);font-weight:600}
            tr:hover{background:rgba(255,255,255,0.02);cursor:pointer}
            .kpis{display:flex;gap:8px;margin-top:8px}
            .kpi{flex:1;padding:8px;background:#07121a;border-radius:6px;text-align:center}
            .kpi .v{font-size:1.2rem;font-weight:700}
            #chart{height:320px}
            /* month dropdown open state */
            #monthList{display:none}
            #monthList.open{display:block}
            /* chevron indicator */
            .chev{display:inline-block;width:16px;text-align:center;transition:transform .18s ease;color:var(--muted);margin-right:6px}
            .chev.open{transform:rotate(90deg);color:var(--accent)}
            /* spinner */
            .spinner{display:inline-block;width:18px;height:18px;border:2px solid rgba(255,255,255,0.08);border-top-color:var(--accent);border-radius:50%;animation:spin .9s linear infinite;vertical-align:middle;margin-left:6px}
            @keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
            .parts-row td{background:transparent}
            .parts-table{border-collapse:collapse;width:100%}
            .parts-table th,.parts-table td{padding:6px;border-bottom:1px solid rgba(255,255,255,0.03);text-align:left}
            /* responsive tweaks for narrow screens */
            @media (max-width:700px){
                .content{grid-template-columns:1fr}
                #monthList{position:static;max-height:180px;overflow:auto}
                /* hide columns 'Nazwa' and 'Dział' to save space */
                #devicesTable th:nth-child(3), #devicesTable td:nth-child(3),
                #devicesTable th:nth-child(2), #devicesTable td:nth-child(2){display:none}
                #devicesTable th,#devicesTable td{font-size:0.85rem}
                .kpi{font-size:0.9rem}
                .chev{width:12px}
            }
        </style>
    </head>
    <body>
        <div class="layout">
            __BANNER__
            <header>Obciążenie urządzęń - dashboard</header>
            <div class="content">
                <div class="panel slicers">
                    <div class="slicer-label">Miesiąc (wybierz kilka)
                        <div id="monthDropdown" style="position:relative">
                            <button id="monthToggle" type="button" aria-expanded="false" style="width:100%;text-align:left;padding:6px;border-radius:4px;border:1px solid #203040;background:#081018;color:var(--text)">Wybierz miesiące</button>
                            <div id="monthList" style="position:absolute;left:0;right:0;z-index:50;max-height:220px;overflow:auto;background:#07121a;border:1px solid #203040;padding:8px;margin-top:6px;border-radius:6px">
                                <!-- month checkboxes inserted here -->
                            </div>
                            <div id="monthStatus" style="color:var(--muted);font-size:0.85rem;margin-top:6px">(status)</div>
                        </div>
                    </div>
                    <button id="clearMonths" style="margin-top:6px;padding:6px 8px;background:#0b1220;border-radius:6px;border:1px solid #203040;color:var(--muted)">Wyczyść</button>
                    <label>Dział
                        <select id="department"><option value="__all__">Wszystkie</option></select>
                    </label>
                    <!-- Top N removed; show all devices -->
                    <!-- prorated values hidden in UI by request -->
                    <button id="refresh" style="margin-top:8px;padding:8px 10px;background:var(--accent);border-radius:6px;border:0;color:#04233a">Odśwież</button>
                    <a href="/upload" style="display:block;margin-top:8px;padding:6px 8px;background:#061126;border-radius:6px;color:var(--accent);text-decoration:none;text-align:center">Załaduj pliki (jeśli brak dostępu do \u005C\u005Cnas1)</a>
                    <div class="kpis" style="margin-top:10px">
                        <div class="kpi"><div class="t">Suma dostępności (full)</div><div id="sum_full" class="v">-</div></div>
                        <div class="kpi"><div class="t">Suma obciążenia (full)</div><div id="load_full" class="v">-</div></div>
                    </div>
                </div>
                <div>
                    <div class="panel" style="margin-bottom:8px">
                        <strong>Urządzenia</strong>
                        <div style="height:300px;overflow:auto;margin-top:8px">
                            <table id="devicesTable">
                                <thead><tr><th>Nr</th><th>Nazwa</th><th>Dział</th><th>Dostępność/h</th><th>Obciążenie/h</th><th>Niedobór/h</th></tr></thead>
                                <tbody></tbody>
                            </table>
                        </div>
                    </div>
                    <div class="panel">
                        <canvas id="chart"></canvas>
                    </div>
                    <div class="panel" style="margin-top:8px">
                        <div style="text-align:center;margin-bottom:8px;">
                            <div style="display:inline-block;width:100%;max-width:520px;padding:8px 12px;border-radius:8px;background:linear-gradient(90deg, rgba(96,165,250,0.06), rgba(37,99,235,0.04));font-weight:700;color:var(--text)">Obciążenie wg Indeksu</div>
                        </div>
                        <div style="height:260px;overflow:auto;margin-top:8px">
                            <canvas id="partsChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <script>
            console.log('[ui] script start');
            function setMonthStatus(msg){ try{ const s=document.getElementById('monthStatus'); if(s) s.textContent = msg; }catch(e){} }
            setMonthStatus('init');
            let myChart;
            let partsChart;
            try{
                const chartEl = document.getElementById('chart');
                if(chartEl && chartEl.getContext){
                    const chartCtx = chartEl.getContext('2d');
                    myChart = new Chart(chartCtx, {type:'bar',data:{labels:[],datasets:[
                        {label:'Dostępność (h)',backgroundColor:'#34D399',borderColor:'#16A34A',borderWidth:1,data:[]},
                        {label:'Obciążenie (h)',backgroundColor:'#EF4444',borderColor:'#B91C1C',borderWidth:1,data:[]} 
                    ]},options:{plugins:{legend:{labels:{color:'#E5E7EB'}}},scales:{x:{ticks:{color:'#E5E7EB'}},y:{ticks:{color:'#E5E7EB'}}},maintainAspectRatio:false}});
                }else{
                    throw new Error('Canvas not available');
                }
            }catch(e){
                console.warn('[ui] Chart init failed, continuing without chart', e);
                setMonthStatus('chart init failed');
                // fallback minimal chart-like object so code calling myChart.update() doesn't crash
                myChart = { data: { labels: [], datasets: [ { data: [] }, { data: [] } ] }, update: function(){} };
            }

            // init parts chart (shows sum of praca_tpz per part)
            try{
                const partsEl = document.getElementById('partsChart');
                if(partsEl && partsEl.getContext){
                    const pCtx = partsEl.getContext('2d');
                    partsChart = new Chart(pCtx, {type:'bar',data:{labels:[],datasets:[{label:'Czas części (h)',backgroundColor:'#60A5FA',borderColor:'#2563EB',borderWidth:1,data:[]}]},options:{plugins:{legend:{labels:{color:'#E5E7EB'}}},scales:{x:{ticks:{color:'#E5E7EB'}},y:{ticks:{color:'#E5E7EB'}}},maintainAspectRatio:false}});
                }else{
                    throw new Error('Parts canvas not available');
                }
            }catch(e){
                console.warn('[ui] partsChart init failed, continuing without partsChart', e);
                partsChart = { data: { labels: [], datasets: [ { data: [] } ] }, update: function(){} };
            }

            async function loadDevices(){
                const months = Array.from(document.querySelectorAll('.month-checkbox:checked')).map(i=>i.value).filter(Boolean);
                const tbody = document.querySelector('#devicesTable tbody');
                // if no months selected, clear table and return
                if(months.length===0){ tbody.innerHTML=''; return; }
                // show spinner row while loading devices
                tbody.innerHTML='';
                const spinnerRow = document.createElement('tr');
                spinnerRow.className = 'devices-spinner';
                const spinnerTd = document.createElement('td');
                spinnerTd.colSpan = 6;
                spinnerTd.style.padding = '12px';
                const sp = document.createElement('span'); sp.className = 'spinner'; spinnerTd.appendChild(sp);
                spinnerRow.appendChild(spinnerTd);
                tbody.appendChild(spinnerRow);

                const url = `/devices?` + months.map(m=>'month='+encodeURIComponent(m)).join('&');
                let r;
                try{
                    r = await fetch(url);
                }catch(err){
                    spinnerRow.remove();
                    alert('Błąd ładowania urządzeń: ' + (err && err.message ? err.message : ''));
                    return;
                }
                if(!r.ok){ spinnerRow.remove(); alert('Błąd ładowania urządzeń'); return }
                const data = await r.json();
                // remove spinner now that data arrived
                spinnerRow.remove();
                let sumAvail=0,sumLoad=0;
                // show all devices
                // UI always shows full (non-prorated) values
                const showPr = false;
                // sort by shortage_prorated ascending (most negative first)
                data.sort((a,b)=> a.shortage_prorated - b.shortage_prorated);
                // populate department select (preserve previously selected value)
                const deptSel = document.getElementById('department');
                const prevDept = deptSel.value;
                const depts = new Set(["__all__"]);
                data.forEach(x=>{ if(x.department) depts.add(x.department); });
                deptSel.innerHTML=''; [...depts].forEach(d=>{ const o=document.createElement('option'); o.value=d; o.textContent = (d==='__all__' ? 'Wszystkie' : d); if(prevDept && d===prevDept) o.selected = true; deptSel.appendChild(o); });

                const selectedDept = deptSel.value || '__all__';

                const displayed = data.filter(d => selectedDept==='__all__' || d.department===selectedDept);
                // compute min/max shortage for color scaling
                const shortageVals = displayed.map(x => Number(x.shortage_full) || 0);
                const minShort = shortageVals.length ? Math.min(...shortageVals) : 0;
                const maxShort = shortageVals.length ? Math.max(...shortageVals) : 0;
                function shortageColor(v){
                    if(minShort === maxShort) return {css:'', bright:255};
                    const t = ((v - minShort) / (maxShort - minShort));
                    const r = Math.round(239 + (52 - 239) * t); // red->green interpolation
                    const g = Math.round(68 + (211 - 68) * t);
                    const b = Math.round(68 + (153 - 68) * t);
                    const bright = (r*0.299 + g*0.587 + b*0.114);
                    return { css: `rgb(${r},${g},${b})`, bright };
                }

                displayed.forEach(d=>{
                    const tr = document.createElement('tr');
                    // include a chevron indicator in the first column
                    tr.innerHTML = `<td><span class="chev">▶</span> ${d.device_id}</td><td>${d.display_name||''}</td><td>${d.department||''}</td><td>${d.monthly_hours_full_sum.toFixed(1)}</td><td>${d.monthly_load_full_sum.toFixed(1)}</td><td>${d.shortage_full.toFixed(1)}</td>`;
                    tr.onclick = async ()=>{
                        // toggle existing expanded row for this device
                        const next = tr.nextElementSibling;
                        const chev = tr.querySelector('.chev');
                        if(next && next.classList.contains('parts-row')){
                            next.remove();
                            if(chev) chev.classList.remove('open');
                            return;
                        }
                        document.getElementById('deviceInput')?.remove();
                        const inp=document.createElement('input'); inp.id='deviceInput'; inp.type='hidden'; inp.value=d.device_id; document.body.appendChild(inp);
                        const monthsSel = Array.from(document.querySelectorAll('.month-checkbox:checked')).map(i=>i.value);
                        if(monthsSel.length===0) return;
                        loadDeviceDetails(d.device_id, monthsSel, showPr);

                        // Usuń inne rozwinięte tabele
                        document.querySelectorAll('.parts-row').forEach(e=>e.remove());
                        // insert spinner row immediately
                        const spinnerRow = document.createElement('tr');
                        spinnerRow.className = 'parts-row';
                        const spinnerTd = document.createElement('td');
                        spinnerTd.colSpan = 6;
                        spinnerTd.style.padding = '8px 12px';
                        const sp = document.createElement('span'); sp.className = 'spinner'; spinnerTd.appendChild(sp);
                        spinnerRow.appendChild(spinnerTd);
                        tr.parentNode.insertBefore(spinnerRow, tr.nextSibling);
                        if(chev) chev.classList.add('open');

                        const partsUrl = `/device_parts/${encodeURIComponent(d.device_id)}?` + monthsSel.map(m=>'month='+encodeURIComponent(m)).join('&');
                        try{
                            const partsResp = await fetch(partsUrl);
                            if(!partsResp.ok){ throw new Error('Błąd ładowania części'); }
                            const parts = await partsResp.json();
                            // remove spinner row
                            spinnerRow.remove();
                            // ensure chronological order: sort by year then week (ascending)
                            try{ parts.sort((a,b)=> (a.year - b.year) || (a.week - b.week)); }catch(e){ console.warn('[ui] parts sort failed', e); }
                            if(!parts || parts.length === 0){
                                // show no-data message
                                const msgRow = document.createElement('tr');
                                msgRow.className = 'parts-row';
                                const mtd = document.createElement('td'); mtd.colSpan = 6; mtd.style.padding='8px 12px'; mtd.textContent = 'Brak części dla wybranego okresu';
                                msgRow.appendChild(mtd);
                                tr.parentNode.insertBefore(msgRow, tr.nextSibling);
                                return;
                            }

                            // build inner table markup
                            const partsTable = document.createElement('table');
                            partsTable.className = 'parts-table';
                            partsTable.style.margin = '8px 0';
                            partsTable.style.background = '#07121a';
                            partsTable.style.borderRadius = '6px';
                            partsTable.style.width = '100%';
                            partsTable.innerHTML = `<thead><tr><th>Numer części</th><th>ID zlecenia</th><th>Tydzień</th><th>Rok</th><th>Obciążenie</th></tr></thead><tbody></tbody>`;
                            parts.forEach(p => {
                                const row = document.createElement('tr');
                                row.innerHTML = `<td>${p.part_number}</td><td>${p.order_id||''}</td><td>${p.week}</td><td>${p.year}</td><td>${(p.praca_tpz||0).toFixed(1)}</td>`;
                                partsTable.querySelector('tbody').appendChild(row);
                            });

                            // update partsChart: aggregate total praca_tpz per part_number
                            try{
                                const agg = {};
                                parts.forEach(p => { const key = p.part_number || '(unknown)'; agg[key] = (agg[key] || 0) + (Number(p.praca_tpz) || 0); });
                                // sort entries by aggregated value descending (largest -> smallest)
                                const entries = Object.entries(agg).sort((a,b)=> (b[1] || 0) - (a[1] || 0));
                                const labels = entries.map(e => e[0]);
                                const values = entries.map(e => e[1]);
                                partsChart.data.labels = labels;
                                partsChart.data.datasets[0].data = values;
                                partsChart.update();
                            }catch(e){ console.warn('[ui] update partsChart failed', e); }

                            // insert a new table row below the clicked row with colspan to span the devices table
                            const partsRow = document.createElement('tr');
                            partsRow.className = 'parts-row';
                            const td = document.createElement('td');
                            td.colSpan = 6;
                            td.style.padding = '8px 12px';
                            td.appendChild(partsTable);
                            partsRow.appendChild(td);
                            tr.parentNode.insertBefore(partsRow, tr.nextSibling);
                        }catch(err){
                            spinnerRow.remove();
                            if(chev) chev.classList.remove('open');
                            alert(err.message || 'Błąd ładowania części');
                        }
                    };
                    tbody.appendChild(tr);
                    // color the shortage cell
                    try{
                        const td = tr.querySelector('td:last-child');
                        const val = Number(d.shortage_full) || 0;
                        const c = shortageColor(val);
                        if(td){ td.style.background = c.css; td.style.color = (c.bright < 140 ? 'white' : 'black'); }
                    }catch(e){ }
                    sumAvail += d.monthly_hours_full_sum; sumLoad += d.monthly_load_full_sum;
                });
                document.getElementById('sum_full').textContent = sumAvail.toFixed(1);
                document.getElementById('load_full').textContent = sumLoad.toFixed(1);
            }

            async function loadDeviceDetails(device, months, showPr){
                const url = `/availability/${encodeURIComponent(device)}?` + months.map(m=>'month='+encodeURIComponent(m)).join('&');
                const r = await fetch(url);
                if(!r.ok){ alert('Błąd ładowania szczegółów'); return }
                const data = await r.json();
                // sort weeks by year/week
                const weeks = (data.weekly || []).slice().sort((a,b)=> (a.iso_year - b.iso_year) || (a.week_number - b.week_number));
                const labels = weeks.map(w=> w.iso_year + '-' + String(w.week_number).padStart(2,'0'));
                const avail = weeks.map(w=> (w.hours||0));
                const load = weeks.map(w=> (w.load_hours||0));
                myChart.data.labels = labels; myChart.data.datasets[0].data = avail; myChart.data.datasets[1].data = load; myChart.update();
            }

            // populate month checkbox list with +/-12 months around current month (defensive)
            (function(){
                try{
                    console.log('[ui] init month list');
                    setMonthStatus('initializing month list');
                    const list = document.getElementById('monthList');
                    const toggle = document.getElementById('monthToggle');
                    if(!list){ console.error('[ui] monthList element not found'); return; }
                    const now = new Date();
                    const defaultVal = now.getFullYear() + '-' + String(now.getMonth()+1).padStart(2,'0');
                    const start = new Date(now.getFullYear(), now.getMonth()-12, 1);
                    for(let i=0;i<25;i++){
                        const d = new Date(start.getFullYear(), start.getMonth()+i, 1);
                        const val = d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0');
                        if (val.startsWith('2024-')) continue; // pomiń wszystkie miesiące z 2024
                        const id = 'm_' + i;
                        const wrapper = document.createElement('div');
                        wrapper.style.display = 'inline-flex';
                        wrapper.style.alignItems = 'center';
                        wrapper.style.marginRight = '12px';
                        wrapper.style.marginBottom = '6px';
                        const chk = document.createElement('input'); chk.type='checkbox'; chk.className='month-checkbox'; chk.id = id; chk.value = val;
                        const lbl = document.createElement('label'); lbl.htmlFor = id; lbl.style.marginLeft='8px'; lbl.style.color='var(--text)'; lbl.textContent = val;
                        chk.onchange = ()=>{ updateMonthToggleText(); loadDevices(); };
                        wrapper.appendChild(chk); wrapper.appendChild(lbl);
                        list.appendChild(wrapper);
                    }
                    function updateMonthToggleText(){
                        const sel = Array.from(document.querySelectorAll('.month-checkbox:checked')).map(i=>i.value);
                        toggle.textContent = sel.length ? sel.join(', ') : 'Wybierz miesiące';
                    }
                    // toggle dropdown (use class toggle + ARIA)
                    try{ toggle.addEventListener('click', (e)=>{ e.stopPropagation(); const l = document.getElementById('monthList'); l.classList.toggle('open'); toggle.setAttribute('aria-expanded', l.classList.contains('open')); }); }catch(e){ console.warn('[ui] addEventListener failed for monthToggle', e); }
                    // close when clicking outside the dropdown
                    document.addEventListener('click', (e)=>{ const dd = document.getElementById('monthDropdown'); if(!dd.contains(e.target)) { const l = document.getElementById('monthList'); l.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); } });
                    // initialize button text
                    updateMonthToggleText();
                    // clear button
                    document.getElementById('clearMonths').onclick = (e)=>{ e.stopPropagation(); document.querySelectorAll('.month-checkbox').forEach(c=>c.checked=false); updateMonthToggleText(); loadDevices(); };
                    // if nothing was inserted, show a helpful message
                    if(list.children.length === 0){
                        const m = document.createElement('div'); m.style.color='var(--muted)'; m.textContent = 'Brak dostępnych miesięcy'; list.appendChild(m);
                        setMonthStatus('no months inserted');
                    }else{
                        setMonthStatus('months loaded');
                    }
                }catch(err){
                    console.error('[ui] error initializing month list', err);
                    setMonthStatus('error initializing months: ' + (err && err.message ? err.message : ''));
                    try{ const list = document.getElementById('monthList'); if(list){ list.innerHTML = '<div style="color:var(--muted)">Błąd inicjalizacji listy miesięcy: ' + (err && err.message ? err.message : '') + '</div>'; } }catch(e){}
                }
            })();
            document.getElementById('refresh').onclick = loadDevices;
            document.getElementById('department').onchange = loadDevices;
            // attach clear uploads button (if present)
            try{
                const btn = document.getElementById('clearUploadsBtn');
                if(btn){ btn.addEventListener('click', async function(){
                    if(!confirm('Wyczyścić pliki uploaded/?')) return;
                    try{
                        const resp = await fetch('/upload/clear', { method: 'POST' });
                        if(resp.ok){ location.reload(); return; }
                        const j = await resp.json();
                        alert('Błąd: ' + (j && j.errors ? j.errors.join('; ') : JSON.stringify(j)));
                    }catch(e){ alert('Błąd: ' + (e && e.message ? e.message : e)); }
                }); }
            }catch(e){ console.warn('attach clearUploadsBtn failed', e); }
            // initial load
            loadDevices();
        </script>
    </body>
</html>
"""
    # inject banner_html safely (avoid f-string parsing of CSS braces)
    html = html.replace('__BANNER__', banner_html)
    return HTMLResponse(content=html)



@app.get('/upload', response_class=HTMLResponse)
async def upload_form():
    html = """
<!doctype html>
<html><head><meta charset='utf-8'><title>Załaduj pliki</title></head><body style='font-family:Segoe UI, Arial;margin:20px;'>
<h2>Załaduj pliki Excel (Raport_dane.xlsx i DostepnoscWTygodniach.xlsx)</h2>
<p>Jeśli aplikacja nie ma dostępu do udziału sieciowego, możesz przesłać lokalne kopie tutaj. Pliki zostaną zapisane i użyte przez aplikacją.</p>
<form action='/upload' method='post' enctype='multipart/form-data'>
  <div><label>Raport produkcji (Raport_dane.xlsx):</label><br><input type='file' name='prodfile' accept='.xlsx,.xls'></div>
  <div style='margin-top:8px;'><label>Dostępność (DostepnoscWTygodniach.xlsx):</label><br><input type='file' name='datafile' accept='.xlsx,.xls'></div>
  <div style='margin-top:12px;'><button type='submit'>Wyślij pliki</button></div>
</form>
<p style='margin-top:10px;'><a href='/'>Powrót do dashboardu</a></p>
</body></html>
"""
    return HTMLResponse(content=html)


@app.post('/upload')
async def handle_upload(prodfile: UploadFile = File(None), datafile: UploadFile = File(None)):
    saved = []
    errors = []
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Nie można utworzyć katalogu upload: {e}"})

    if prodfile is not None:
        target = UPLOAD_DIR / UPLOADED_PROD_NAME
        try:
            with open(target, 'wb') as out_f:
                shutil.copyfileobj(prodfile.file, out_f)
            saved.append(str(target.name))
        except Exception as e:
            errors.append(f'prodfile: {e}')

    if datafile is not None:
        target = UPLOAD_DIR / UPLOADED_DATA_NAME
        try:
            with open(target, 'wb') as out_f:
                shutil.copyfileobj(datafile.file, out_f)
            saved.append(str(target.name))
        except Exception as e:
            errors.append(f'datafile: {e}')

    # If user posted via browser form, redirect back to root
    if errors:
        return JSONResponse(status_code=500, content={"saved": saved, "errors": errors})
    return RedirectResponse(url='/', status_code=303)



@app.post('/upload/clear')
async def clear_uploads():
    errors = []
    removed = []
    try:
        p1 = UPLOAD_DIR / UPLOADED_PROD_NAME
        if p1.exists():
            try:
                p1.unlink()
                removed.append(str(p1.name))
            except Exception as e:
                errors.append(f'{p1.name}: {e}')
        p2 = UPLOAD_DIR / UPLOADED_DATA_NAME
        if p2.exists():
            try:
                p2.unlink()
                removed.append(str(p2.name))
            except Exception as e:
                errors.append(f'{p2.name}: {e}')
    except Exception as e:
        return JSONResponse(status_code=500, content={"errors": [str(e)]})
    return JSONResponse(status_code=200, content={"removed": removed, "errors": errors})



@app.get('/devices', response_model=List[DeviceAggregate])
async def devices(month: List[str] = Query(...)):
    """Aggregate devices for given month(s): accepts multiple `month=YYYY-MM` query params and sums across them."""
    # parse months into (first_day, last_day) ranges
    month_ranges = []
    for m in month:
        try:
            month_dt = datetime.strptime(m, '%Y-%m')
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Parametr month musi mieć format YYYY-MM: {m}")
        y = month_dt.year
        mn = month_dt.month
        first = date(y, mn, 1)
        last = date(y, mn, calendar.monthrange(y, mn)[1])
        month_ranges.append((first, last))

    df = load_data()
    try:
        prod_df = load_production_data()
    except Exception:
        prod_df = pd.DataFrame(columns=['group', 'year', 'week', 'praca_tpz'])
    group_map = load_group_map()
    # try load scalanie map (group -> NazwaUrz.) produced by scripts/merge_scalanie17.py
    scalanie_file = pathlib.Path(__file__).resolve().parent.parent / 'scalanie_group_name.csv'
    scalanie_map = {}
    if scalanie_file.exists():
        try:
            sm_df = pd.read_csv(scalanie_file, dtype=str)
            if 'group' in sm_df.columns and 'name' in sm_df.columns:
                scalanie_map = {str(r['group']).strip().lower(): (str(r['name']).strip() or '') for _, r in sm_df.iterrows()}
        except Exception:
            scalanie_map = {}

    results = []
    # group by device (preserve display name if present)
    for device, g in df.groupby('device'):
        weekly_records = []
        for _, row in g.iterrows():
            w = int(row['week'])
            y = int(row['year'])
            try:
                week_start, week_end = get_week_date_range(y, w)
            except Exception:
                continue
            # skip weeks that don't overlap any selected month ranges
            overlaps_any = False
            overlap_days_total = 0
            overlap_days_by_range = []
            for (first_month_day, last_month_day) in month_ranges:
                if week_end < first_month_day or week_start > last_month_day:
                    overlap_days_by_range.append(0)
                    continue
                overlaps_any = True
                overlap_start = week_start if week_start > first_month_day else first_month_day
                overlap_end = week_end if week_end < last_month_day else last_month_day
                od = business_days_between(overlap_start, overlap_end) if overlap_start <= overlap_end else 0
                overlap_days_by_range.append(od)
                overlap_days_total += od
            if not overlaps_any:
                continue
            hours = float(row['hours'])
            working_days_week = business_days_between(week_start, week_end)
            # prorate for this week across all selected months proportionally to overlap days
            prorated_hours = 0.0
            prorated_load = 0.0
            # compute full hours for week as-is

            grp = str(row.get('device') or row.get('Grupa zasobów') or row.get('grupa zasobów') or '').strip()
            g_lower = grp.lower()
            prod_row = prod_df[(prod_df['group'].astype(str).str.lower() == g_lower) & (prod_df['year'] == y) & (prod_df['week'] == w)]
            if prod_row.empty:
                prod_row = prod_df[(prod_df['group'].astype(str).str.lower().str.contains(g_lower, na=False)) & (prod_df['year'] == y) & (prod_df['week'] == w)]
            load_hours = float(prod_row['praca_tpz'].sum()) if not prod_row.empty else 0.0
            # If the week overlaps multiple selected months, prorate by total overlapping business days
            total_overlap_days = overlap_days_total
            if working_days_week > 0 and total_overlap_days > 0:
                prorated_hours = hours * (total_overlap_days / working_days_week)
                prorated_load = load_hours * (total_overlap_days / working_days_week)

            weekly_records.append({
                'hours': hours,
                'prorated_hours': prorated_hours,
                'load_hours': load_hours,
                'prorated_load_hours': prorated_load,
            })

        if not weekly_records:
            continue

        full_hours = sum(r['hours'] for r in weekly_records)
        pr_hours = sum(r['prorated_hours'] for r in weekly_records)
        full_load = sum(r['load_hours'] for r in weekly_records)
        pr_load = sum(r['prorated_load_hours'] for r in weekly_records)

        # determine department by exact or contains match against group_map keys
        dept = None
        try_key = str(device).strip().lower()
        if try_key in group_map:
            dept = group_map.get(try_key)
        else:
            # fallback: find any mapping key that contains device substring
            for k,v in group_map.items():
                if try_key and try_key in k:
                    dept = v
                    break

        # determine display name from scalanie map (leave empty if not found)
        dkey = str(device).strip().lower()
        disp_name = scalanie_map.get(dkey, '')
        results.append(DeviceAggregate(
            device_id=str(device),
            display_name=disp_name,
            department=dept,
            monthly_hours_full_sum=full_hours,
            monthly_hours_prorated_sum=pr_hours,
            monthly_load_full_sum=full_load,
            monthly_load_prorated_sum=pr_load,
            shortage_full=full_hours - full_load,
            shortage_prorated=pr_hours - pr_load,
        ))

    # sort by shortage_prorated desc
    results_sorted = sorted(results, key=lambda x: x.shortage_prorated)
    return results_sorted
