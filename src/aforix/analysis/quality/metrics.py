from __future__ import annotations

import re

import pandas as pd


def compute_cg_from_weights(weights_pct: pd.Series, tq_pct: pd.Series) -> float:
    weights_pct = pd.to_numeric(weights_pct, errors="coerce").abs()
    tq_pct = pd.to_numeric(tq_pct, errors="coerce")

    mask = weights_pct.notna() & tq_pct.notna()
    if not mask.any():
        raise ValueError("No valid data for CG computation")

    w_pct = weights_pct[mask]
    tq = tq_pct[mask]

    denominator = w_pct.sum()
    if denominator == 0:
        raise ValueError("Sum of weights is zero")

    numerator = ((w_pct / 100.0) * tq).sum()
    return float(100.0 * numerator / denominator)


def find_tq_column(df: pd.DataFrame) -> str:
    candidates = ("tq [%]", "tq(%)", "tq")
    allowed = {_normalize(c) for c in candidates}

    for col in df.columns:
        if _normalize(str(col)) in allowed:
            return str(col)

    raise ValueError("tq column not found (tq != atq != hq)")


def _normalize(v: str) -> str:
    v = v.strip().lower()
    v = v.replace("%", " percent ")
    v = re.sub(r"[\[\]\(\)]", " ", v)
    v = re.sub(r"\s+", " ", v)
    return v.strip()
