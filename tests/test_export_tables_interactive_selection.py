from __future__ import annotations

import builtins

from aforix.export.tables.interactive import _choose_many


def test_interactive_station_selection_prefers_exact_station_id_over_numeric_index(monkeypatch):
    options = ["7001", "7071", "70101", "701150"]

    monkeypatch.setattr(builtins, "input", lambda _prompt: "7071")

    selected = _choose_many(
        "Available points/stations",
        options,
        empty_label="all",
        allow_codes=True,
    )

    assert selected == ["7071"]


def test_interactive_station_selection_still_supports_explicit_index(monkeypatch):
    options = ["7001", "7071", "70101", "701150"]

    monkeypatch.setattr(builtins, "input", lambda _prompt: "idx:1")

    selected = _choose_many(
        "Available points/stations",
        options,
        empty_label="all",
        allow_codes=True,
    )

    assert selected == ["7071"]
