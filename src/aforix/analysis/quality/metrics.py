from __future__ import annotations

import pandas as pd


def compute_cg_nivus(points_df: pd.DataFrame, sections_df: pd.DataFrame) -> float:
    tq_col = _find_column(points_df, ["tq", "percent_q"])
    factor_col = _find_column(sections_df, ["factor", "percent_q"])

    tq_vals = points_df[tq_col].astype(float).tolist()
    f_vals = sections_df[factor_col].astype(float).tolist()

    n_points = len(tq_vals)
    n_sections = len(f_vals)

    if n_sections != n_points + 2:
        raise ValueError("Invalid Nivus structure: sections != points + 2")

    w_dec = [abs(f / 100.0) for f in f_vals]
    w_pct = [abs(f) for f in f_vals]

    W = [0.0] * n_points
    W[0] = w_dec[0] + w_dec[1]
    if n_points > 1:
        W[-1] = w_dec[-2] + w_dec[-1]

    for i in range(1, n_points - 1):
        W[i] = w_dec[i + 1]

    D = sum(w_pct)
    S = sum(W[i] * tq_vals[i] for i in range(n_points))

    return (100.0 * S) / D


def _find_column(df: pd.DataFrame, candidates: list[str]) -> str:
    for c in df.columns:
        name = c.lower()
        for cand in candidates:
            if cand in name:
                return c
    raise ValueError("Column not found")
