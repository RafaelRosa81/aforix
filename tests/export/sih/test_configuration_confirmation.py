from __future__ import annotations

import pandas as pd
import pytest

from aforix.export.sih.confirmation import confirm_instrument_configurations


@pytest.fixture
def config():
    return {
        "sih": {
            "instruments": {
                "flowtracker": {
                    "enabled": True,
                    "id_tipo_actuacion": 4,
                    "tipo_aforo_lookup": "VADEO",
                    "instrumentos_rangos_lookup": "Acustico",
                    "instrument_lookup_fields": {
                        "marca": None, "nro_serie": None,
                        "modelo": "instrument", "codigo": None,
                    },
                },
                "molinete": {
                    "enabled": True,
                    "id_tipo_actuacion": 4,
                    "tipo_aforo_lookup": "VADEO",
                    "instrumentos_rangos_lookup": "Velocimetro",
                    "instrument_lookup_fields": {
                        "marca": None, "nro_serie": "helice",
                        "modelo": "molinete", "codigo": None,
                    },
                },
            },
            "ive": {"borders": {"left": "zero", "right": "zero"}},
        }
    }


@pytest.fixture
def selection():
    return pd.DataFrame({"instrument": ["flowtracker", "molinete", "flowtracker"]})


def test_confirms_each_instrument_once(config, selection, capsys):
    prompts = []
    def ask(prompt):
        prompts.append(prompt)
        return "s"

    assert confirm_instrument_configurations(config, selection, ask=ask)
    assert len(prompts) == 2
    out = capsys.readouterr().out
    assert "Aforos seleccionados: 2" in out
    assert "Aforos seleccionados: 1" in out
    assert "Número de serie: helice" in out
    assert "Margen izquierdo: Profundidad cero" in out
    assert "Margen derecho: Profundidad cero" in out


def test_rejection_aborts(config, selection):
    assert not confirm_instrument_configurations(config, selection, ask=lambda _: "n")


def test_empty_response_aborts(config, selection):
    assert not confirm_instrument_configurations(config, selection, ask=lambda _: "")


def test_eof_aborts(config, selection):
    def eof(_):
        raise EOFError()
    assert not confirm_instrument_configurations(config, selection, ask=eof)


def test_yes_skips_prompts(config, selection):
    def forbidden(_):
        raise AssertionError("should not prompt")
    assert confirm_instrument_configurations(config, selection, assume_yes=True, ask=forbidden)


def test_unknown_instrument_rejected_even_with_yes(config):
    selection = pd.DataFrame({"instrument": ["unknown"]})
    with pytest.raises(ValueError, match="desconocido"):
        confirm_instrument_configurations(config, selection, assume_yes=True)
