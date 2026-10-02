from __future__ import annotations

import pandas as pd

from aforix.export.sih.mappings import resolve_tipo_aforo_lookup_id


def test_tipo_aforo_lookup_ignores_case_and_surrounding_whitespace():
    instrument_cfg = {
        "tipo_aforo_lookup": "Vadeo",
    }
    sih_config = {
        "sih": {
            "lookup_tables": {
                "tipos_aforos": {
                    "file": "tipos_aforos",
                    "key_column": "descripcion",
                    "value_column": "id",
                }
            }
        }
    }
    lookup_tables = {
        "tipos_aforos": pd.DataFrame(
            {
                "id": ["57"],
                "descripcion": ["  VADEO  "],
            }
        )
    }

    assert (
        resolve_tipo_aforo_lookup_id(
            instrument_cfg,
            sih_config,
            lookup_tables,
        )
        == "57"
    )
