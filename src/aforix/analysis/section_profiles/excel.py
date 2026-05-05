from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import pandas as pd
from openpyxl import load_workbook
from openpyxl.chart import ScatterChart, BarChart, Reference, Series


def write_excel(
    output_path: Path,
    sheets: list[dict],
    *,
    x_axis: str,
    y_axis: str,
    chart_type: str,
    excel_cfg: Dict[str, Any] | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sh in sheets:
            name = sh['sheet_name']
            df = sh['data']
            summary = sh['summary']

            sum_df = pd.DataFrame(list(summary.items()), columns=['item', 'value'])
            sum_df.to_excel(writer, sheet_name=name, index=False, startrow=0)

            start_row = len(sum_df) + 2
            df.to_excel(writer, sheet_name=name, index=False, startrow=start_row)

    wb = load_workbook(output_path)

    for sh in sheets:
        ws = wb[sh['sheet_name']]
        df = sh['data']

        if df.empty:
            continue

        # FIX: ensure only one chart per sheet
        ws._charts = []

        start_row = len(sh['summary']) + 3
        end_row = start_row + len(df) - 1

        headers = list(df.columns)
        if x_axis not in headers or y_axis not in headers:
            continue

        x_col = headers.index(x_axis) + 1
        y_col = headers.index(y_axis) + 1

        x_ref = Reference(ws, min_col=x_col, min_row=start_row + 1, max_row=end_row + 1)
        y_ref = Reference(ws, min_col=y_col, min_row=start_row + 1, max_row=end_row + 1)

        if chart_type == 'bar':
            chart = BarChart()
            chart.add_data(y_ref, titles_from_data=False)
            chart.set_categories(x_ref)
        else:
            chart = ScatterChart()
            series = Series(y_ref, x_ref, title=y_axis)
            chart.series.append(series)

        chart.title = f"{y_axis} vs {x_axis}"
        chart.x_axis.title = x_axis
        chart.y_axis.title = y_axis

        anchor = (excel_cfg or {}).get('chart_anchor', 'H2')
        ws.add_chart(chart, anchor)

    wb.save(output_path)
    return output_path
