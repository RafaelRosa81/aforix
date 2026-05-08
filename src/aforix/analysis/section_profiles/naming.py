from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

MAX_SHEET_NAME_LEN = 31


def make_run_dir(output_root: Path) -> Path:
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = output_root / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def safe_sheet_name(name: str) -> str:
    safe = str(name)
    for old, new in {
        '/': '-',
        '\\': '-',
        '*': '-',
        '?': '-',
        '[': '(',
        ']': ')',
        ':': '-',
    }.items():
        safe = safe.replace(old, new)
    safe = safe.strip() or 'Sheet'
    return safe[:MAX_SHEET_NAME_LEN]


def unique_sheet_name(name: str, used: set[str]) -> str:
    base = safe_sheet_name(name)
    if base not in used:
        used.add(base)
        return base
    counter = 2
    while True:
        suffix = f'_{counter}'
        candidate = safe_sheet_name(base[: MAX_SHEET_NAME_LEN - len(suffix)] + suffix)
        if candidate not in used:
            used.add(candidate)
            return candidate
        counter += 1


def make_sheet_name(row: dict, template: str) -> str:
    values = {
        'station_id': row.get('station_id', 'unknown'),
        'measurement_date': compact_date(row.get('measurement_date', 'unknown')),
        'measurement_time': safe_token(row.get('measurement_time', '')),
        'instrument': row.get('instrument', 'unknown'),
        'instrument_code': row.get('instrument_code', row.get('instrument', '')),
    }
    return safe_sheet_name(template.format(**values))


def make_output_name(
    template: str,
    *,
    x_axis: str,
    y_axis: str,
    instruments: Iterable[str] | str | None,
    points: Iterable[str] | str | None,
    start_date: str | None,
    end_date: str | None,
) -> str:
    values = {
        'x_axis': safe_token(x_axis),
        'y_axis': safe_token(y_axis),
        'instrument_tag': selection_tag(instruments, all_value='all'),
        'points_tag': selection_tag(points, all_value='all'),
        'date_range': date_range_tag(start_date, end_date),
    }
    name = template.format(**values)
    if not name.lower().endswith('.xlsx'):
        name += '.xlsx'
    return name


def selection_tag(values: Iterable[str] | str | None, *, all_value: str = 'all') -> str:
    if values is None:
        return all_value
    if isinstance(values, str):
        if values.strip().lower() == 'all':
            return all_value
        parts = [v.strip() for v in values.split(',') if v.strip()]
    else:
        parts = [str(v).strip() for v in values if str(v).strip()]
    if not parts:
        return all_value
    return '-'.join(safe_token(p) for p in parts)


def date_range_tag(start_date: str | None, end_date: str | None) -> str:
    start = compact_date(start_date) if start_date else 'start'
    end = compact_date(end_date) if end_date else 'end'
    if start == 'start' and end == 'end':
        return 'all_dates'
    return f'{start}_{end}'


def compact_date(value) -> str:
    text = str(value).strip()
    if not text or text.lower() in {'none', 'nan', 'nat'}:
        return 'unknown'
    return re.sub(r'[^0-9]', '', text)[:8] or safe_token(text)


def safe_token(value) -> str:
    text = str(value).strip()
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'[^A-Za-z0-9_.-]+', '-', text)
    return text.strip('._-') or 'unknown'
