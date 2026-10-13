from pathlib import Path

import pytest

from aforix.ingest.m9 import run


def test_m9_ingest_fails_explicitly_until_implemented():
    with pytest.raises(NotImplementedError, match="M9/ADCP ingestion is not implemented"):
        run(Path("configs/examples/main.yaml"))
