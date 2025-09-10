import sys, pathlib
BASE = pathlib.Path(__file__).resolve().parent
PARENT = BASE.parent
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))
from app.main import load_data, load_production_data, get_week_date_range, working_days_in_month, business_days_between as working_days_between
from datetime import date
import calendar, json

device = '10243'
month = '2025-09'

def main():
    try:
        df = load_data()
    except Exception as e:
        print('ERROR_LOADING', e)
        return
    ddf = df[df['device'].astype(str).str.lower() == device.lower()]
    print('Device rows count:', len(ddf))
    if ddf.empty:
        print('NO_DATA_FOR_DEVICE')
        print('Available devices sample:', df['device'].astype(str).unique()[:30])
        return
    year, month_num = map(int, month.split('-'))
    first_month_day = date(year, month_num, 1)
    last_month_day = date(year, month_num, calendar.monthrange(year, month_num)[1])
    rec = []
    for _, r in ddf.iterrows():
        w = int(r['week']); y = int(r['year'])
        try:
            ws, we = get_week_date_range(y, w)
        except Exception:
            continue
        if we < first_month_day or ws > last_month_day:
            continue
        rec.append({
            'week': w,
            'year': y,
            'week_start': str(ws),
            'week_end': str(we),
            'hours': float(r['hours']),
            'device_group': str(r.get('device') or r.get('Grupa zasobów') or '')
        })
    total = sum(x['hours'] for x in rec)
    result = {
        'device': device,
        'month': month,
        'working_days': working_days_in_month(year, month_num),
        'weekly': rec,
        'monthly_hours_sum': total
    }
    print('RESULT_JSON_START')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print('RESULT_JSON_END')

    # Load production data and compute loads per week (match exact then contains)
    try:
        pdf = load_production_data()
    except Exception as e:
        print('ERROR_LOADING_PRODUCTION', e)
        pdf = None

    monthly_load_sum = 0.0
    monthly_load_prorated = 0.0
    if pdf is not None:
        # ensure group column is string
        pdf['group'] = pdf['group'].astype(str)
        for r in rec:
            grp = (r.get('device_group') or '').strip()
            g_lower = grp.lower()
            y = r['year']; w = r['week']
            prod_row = pdf[(pdf['group'].str.lower() == g_lower) & (pdf['year'] == y) & (pdf['week'] == w)]
            if prod_row.empty and g_lower:
                prod_row = pdf[(pdf['group'].str.lower().str.contains(g_lower, na=False)) & (pdf['year'] == y) & (pdf['week'] == w)]
            load_hours = float(prod_row['praca_tpz'].sum()) if not prod_row.empty else 0.0
            # prorate same way as availability
            from datetime import datetime
            ws_d = datetime.fromisoformat(r['week_start']).date()
            we_d = datetime.fromisoformat(r['week_end']).date()
            wd_week = working_days_between(ws_d, we_d)
            overlap_start = ws_d if ws_d > first_month_day else first_month_day
            overlap_end = we_d if we_d < last_month_day else last_month_day
            overlap = 0
            if overlap_start <= overlap_end:
                overlap = working_days_between(overlap_start, overlap_end)
            prorated_load = load_hours * (overlap / wd_week) if wd_week>0 else 0.0
            r['load_hours'] = load_hours
            r['prorated_load_hours'] = prorated_load
            monthly_load_sum += load_hours
            monthly_load_prorated += prorated_load

    # print combined result similar to API
    combined = {
        'device': device,
        'month': month,
        'working_days': working_days_in_month(year, month_num),
        'weekly': rec,
        'monthly_hours_sum': total,
        'monthly_load_sum': monthly_load_sum,
        'monthly_load_prorated_sum': monthly_load_prorated
    }
    print('\nCOMBINED_RESULT_START')
    print(json.dumps(combined, ensure_ascii=False, indent=2))
    print('COMBINED_RESULT_END')

    # Teraz wersja prorated
    rec_pr = []
    total_pr = 0.0
    for x in rec:
        ws = x['week_start']; we = x['week_end']
        # zamień na date
        from datetime import datetime
        ws_d = datetime.fromisoformat(ws).date()
        we_d = datetime.fromisoformat(we).date()
        wd_week = working_days_between(ws_d, we_d)
        overlap_start = ws_d if ws_d > first_month_day else first_month_day
        overlap_end = we_d if we_d < last_month_day else last_month_day
        overlap = 0
        if overlap_start <= overlap_end:
            overlap = working_days_between(overlap_start, overlap_end)
        pr_hours = x['hours'] * (overlap / wd_week) if wd_week>0 else 0.0
        rec_pr.append({**x, 'prorated_hours': pr_hours, 'overlap_days': overlap, 'week_working_days': wd_week})
        total_pr += pr_hours

    print('PRORATED_RESULT_START')
    print(json.dumps({'weekly_prorated': rec_pr, 'monthly_prorated_sum': total_pr}, ensure_ascii=False, indent=2))
    print('PRORATED_RESULT_END')

if __name__ == '__main__':
    main()
