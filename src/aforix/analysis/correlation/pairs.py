from __future__ import annotations

import re


PAIR_FORMAT_EXAMPLE = "[44 1] [117 8]"


class PairValidationError(ValueError):
    pass


def pair_format_hint(correlation_type: str | None = None) -> str:
    if correlation_type == "gauges_vs_stations":
        return (
            "Expected bracketed pairs like '[station_id gauge_point]'. "
            f"Example: '{PAIR_FORMAT_EXAMPLE}'."
        )

    if correlation_type == "model_vs_stations":
        return (
            "Expected bracketed pairs like '[station_id model_id]'. "
            "Example: '[44 model_point_1] [117 model_point_8]'."
        )

    return f"Expected bracketed pairs like '{PAIR_FORMAT_EXAMPLE}'."


def parse_pairs(
    raw: str | None,
    *,
    correlation_type: str | None = None,
) -> list[tuple[str, str]]:
    if raw is None or not str(raw).strip():
        return []

    text = str(raw).strip()
    blocks = re.findall(r"\[([^\]]+)\]", text)
    hint = pair_format_hint(correlation_type)

    if not blocks:
        raise PairValidationError(f"Invalid pairs format. {hint}")

    remainder = re.sub(r"\[[^\]]+\]", "", text).strip()
    if remainder:
        raise PairValidationError(f"Invalid text outside pair blocks. {hint}")

    pairs: list[tuple[str, str]] = []
    for block in blocks:
        parts = block.replace(",", " ").split()
        if len(parts) != 2:
            raise PairValidationError(
                "Each pair must contain exactly two values. "
                f"Invalid block: '[{block}]'. {hint}"
            )
        pairs.append((parts[0].strip(), parts[1].strip()))

    return pairs


def validate_pair_selection(correlation_type: str, pairs: str | None, all_pairs: bool) -> None:
    has_pairs = bool(pairs and str(pairs).strip())

    if all_pairs and has_pairs:
        raise PairValidationError("Use either all_pairs=true or pairs, not both.")

    if correlation_type == "model_vs_stations" and not all_pairs and not has_pairs:
        raise PairValidationError(
            "model_vs_stations requires pairs unless all_pairs=true. "
            f"{pair_format_hint(correlation_type)}"
        )

    if has_pairs:
        parse_pairs(pairs, correlation_type=correlation_type)
