from __future__ import annotations

from typing import List, Tuple


def ask_correlation_type() -> str:
    print("Select correlation type:")
    print("1) gauges vs model")
    print("2) gauges vs stations")
    print("3) model vs stations")
    choice = input("Enter choice [1-3]: ").strip()
    mapping = {"1": "gauges_vs_model", "2": "gauges_vs_stations", "3": "model_vs_stations"}
    return mapping.get(choice, "gauges_vs_model")


def ask_instruments(default: List[str]) -> List[str]:
    print(f"Available instruments: {' '.join(default)}")
    raw = input("Enter instrument ranking (space-separated) or press Enter for default: ").strip()
    if not raw:
        return default
    return [x.upper() for x in raw.split()]


def ask_date_range() -> Tuple[str | None, str | None]:
    start = input("Enter start date (YYYYMMDD) or press Enter: ").strip()
    end = input("Enter end date (YYYYMMDD) or press Enter: ").strip()
    return (start or None, end or None)


def ask_timestep() -> str:
    print("Select timestep:")
    print("1) daily")
    print("2) monthly")
    choice = input("Enter choice [1-2]: ").strip()
    return "monthly" if choice == "2" else "daily"


def ask_pairs() -> List[tuple[str, str]]:
    raw = input("Enter pairs like [44 15] [117 10] or press Enter to skip: ").strip()
    if not raw:
        return []
    pairs = []
    tokens = raw.replace("[", "").replace("]", "").split()
    for i in range(0, len(tokens), 2):
        if i + 1 < len(tokens):
            pairs.append((tokens[i], tokens[i + 1]))
    return pairs
