from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import pandas as pd

from aforix.analysis.section_profiles.config import load_section_profiles_config
from aforix.analysis.section_profiles.inputs import load_points_by_instrument
from aforix.analysis.section_profiles.filters import (
    filter_instruments,
    filter_points,
    filter_date_range,
    ensure_columns,
)
from aforix.analysis.section_profiles.naming import (
    make_run_dir,
    make_output_name,
    make_sheet_name,
    unique_sheet_name,
)
from aforix.analysis.section_profiles.excel import write_excel


def run_section_profiles(config_path: Path, override_config: Dict[str, Any] | None = None) -> Path:
    cfg = override_config or load_section_profiles_config(config_path)

    normalized_root = Path(cfg.get('input_dirs', {}).get('normalized_root', 'database/normalized'))
    output_root = Path(cfg.get('output', {}).get('run_output_root', 'runs/analysis_section_profiles'))

    instruments_cfg = cfg.get('instruments', {})
    selection = cfg.get('selection', {}) or {}

    x_axis = cfg.get('defaults', {}).get('x_axis', 'distance_m')
    y_axis = cfg.get('defaults', {}).get('y_axis', 'depth_m')
    chart_type = cfg.get('defaults', {}).get('chart_type', 'scatter')

    df = load_points_by_instrument(normalized_root, instruments_cfg)
    if df.empty:
        return make_run_dir(output_root)

    inst_sel = selection.get('instruments')
    inst_set = set(inst_sel) if isinstance(inst_sel, list) else None
    df = filter_instruments(df, inst_set)

    pts_sel = selection.get('points')
    pts_set = set(pts_sel) if isinstance(pts_sel, list) else None
    df = filter_points(df, pts_set)

    df = filter_date_range(df, selection.get('start_date'), selection.get('end_date'))

    available_cols = set(df.columns)
    if x_axis not in available_cols:
        raise ValueError(f"Column '{x_axis}' is not available. Available columns: {sorted(available_cols)}")
    if y_axis not in available_cols:
        raise ValueError(f"Column '{y_axis}' is not available. Available columns: {sorted(available_cols)}")

    df = ensure_columns(df, x_axis, y_axis)

    if df.empty:
        return make_run_dir(output_root)

    group_cols = ['station_id', 'measurement_date', 'measurement_time', 'instrument', 'instrument_code']
    available = [c for c in group_cols if c in df.columns]

    sheets = []
    used_sheet_names: set[str] = set()
    for _, g in df.groupby(available, dropna=False):
        g2 = g.copy()

        row0 = g2.iloc[0].to_dict()
        base_sheet_name = make_sheet_name(
            row0,
            cfg.get('excel', {}).get('sheet_name_template', '{station_id}_{measurement_date}_{instrument_code}')
        )
        sheet_name = unique_sheet_name(base_sheet_name, used_sheet_names)

        summary = {
            'x_axis': x_axis,
            'y_axis': y_axis,
            'station_id': row0.get('station_id'),
            'measurement_date': row0.get('measurement_date'),
            'measurement_time': row0.get('measurement_time'),
            'instrument': row0.get('instrument'),
            'instrument_code': row0.get('instrument_code'),
            'chart_type': chart_type,
            'source_file': row0.get('normalized_source_table'),
            'n_rows': len(g2),
        }

        sheets.append({'sheet_name': sheet_name, 'data': g2, 'summary': summary})

    out_dir = make_run_dir(output_root)

    out_name = make_output_name(
        cfg.get('excel', {}).get('output_name_template', 'section_profile_{y_axis}_by_{x_axis}_{instrument_tag}_{points_tag}_{date_range}.xlsx'),
        x_axis=x_axis,
        y_axis=y_axis,
        instruments=selection.get('instruments'),
        points=selection.get('points'),
        start_date=selection.get('start_date'),
        end_date=selection.get('end_date'),
    )

    output_path = out_dir / out_name

    write_excel(
        output_path,
        sheets,
        x_axis=x_axis,
        y_axis=y_axis,
        chart_type=chart_type,
        excel_cfg=cfg.get('excel', {}),
    )

    return out_dir
