from __future__ import annotations

import re


class PairValidationError(ValueError):
    pass


def parse_pairs(raw: str | None) -> list[tuple[str, str]]:
    if raw is None or not str(raw).strip():
        return []

    text = str(raw).strip()
    blocks = re.findall(r"\[([^\]]+)\]", text)

    if not blocks:
        raise PairValidationError("Invalid pairs format. Expected bracketed pairs like '[1 44] [8 117]'.")

    remainder = re.sub(r"\[[^\]]+\]", "", text).strip()
    if remainder:
        raise PairValidationError("Invalid text outside pair blocks. Expected format like '[1 44] [8 117]'.")

    pairs: list[tuple[str, str]] = []
    for block in blocks:
        parts = block.replace(",", " ").split()
        if len(parts) != 2:
            raise PairValidationError("Each pair must contain exactly two values, for example '[1 44]'.")
        pairs.append((parts[0].strip(), parts[1].strip()))

    return pairs


def validate_pair_selection(correlation_type: str, pairs: str | None, all_pairs: bool) -> None:
    has_pairs = bool(pairs and str(pairs).strip())

    if all_pairs and has_pairs:
        raise PairValidationError("Use either all_pairs=true or pairs, not both.")

    if correlation_type == "model_vs_stations" and not all_pairs and not has_pairs:
        raise PairValidationError("model_vs_stations requires pairs unless all_pairs=true.")

    if has_pairs:
        parse_pairs(pairs)
