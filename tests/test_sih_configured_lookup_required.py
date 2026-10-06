from __future__ import annotations

import pandas as pd
import pytest

from aforix.export.sih.mappings import (
    resolve_instrumentos_rangos_lookup_id,
    resolve_tipo_aforo_lookup_id,
)


def _config() -> dict:
    return {
        "sih": {
            "lookup_tables": {
                "tipos_aforos": {
                    "file": "tipos_aforos",
                    "key_column": "descripcion",
                    "value_column": "id",
                },
                "instrumentos_rangos": {
                    "file": "instrumentos_rangos",
                    "key_column": "descripcion",
                    "value_column": "id",
                },
            }
        }
    }


def test_configured_tipo_aforo_lookup_must_resolve():
    lookup_tables = {
        "tipos_aforos": pd.DataFrame(
            {"id": ["57"], "descripcion": ["VADEO"]}
        ),
        "instrumentos_rangos": pd.DataFrame(
            {"id": ["10"], "descripcion": ["Acustico"]}
        ),
    }

    with pytest.raises(ValueError, match="tipo_aforo"):
        resolve_tipo_aforo_lookup_id(
            {"tipo_aforo_lookup": "Concepto inexistente"},
            _config(),
            lookup_tables,
        )


def test_configured_instrumentos_rangos_lookup_must_resolve():
    lookup_tables = {
        "tipos_aforos": pd.DataFrame(
            {"id": ["57"], "descripcion": ["VADEO"]}
        ),
        "instrumentos_rangos": pd.DataFrame(
            {"id": ["10"], "descripcion": ["Acustico"]}
        ),
    }

    with pytest.raises(ValueError, match="instrumentos_rangos"):
        resolve_instrumentos_rangos_lookup_id(
            {"instrumentos_rangos_lookup": "Velocimetro puntual"},
            _config(),
            lookup_tables,
        )
