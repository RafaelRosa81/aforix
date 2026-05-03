from __future__ import annotations

import pandas as pd


def compute_cg_from_weights(weights_pct: pd.Series, tq_pct: pd.Series) -> float:
    weights_pct = pd.to_numeric(weights_pct, errors="coerce").abs()
    tq_pct = pd.to_numeric(tq_pct, errors="coerce")

    mask = weights_pct.notna() & tq_pct.notna()
    if not mask.any():
        raise ValueError("No valid data for CG computation")

    w_pct = weights_pct[mask]
    tq = tq_pct[mask]

    w_dec = w_pct / 100.0

    D = w_pct.sum()
    if D == 0:
        raise ValueError("Sum of weights is zero")

    S = (w_dec * tq).sum()

    return float(100.0 * S / D)


def find_column(df: pd.DataFrame, candidates: tuple[str, ...]) -> str:
    cols_lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        cand_l = cand.lower()
        for col_l, col in cols_lower.items():
            if cand_l in col_l:
                return col
    raise ValueError(f"Column not found among candidates={candidates}")
