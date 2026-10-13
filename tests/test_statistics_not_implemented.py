from pathlib import Path

import pytest

from aforix.analysis.statistics import run


def test_statistical_analysis_fails_explicitly_until_implemented():
    with pytest.raises(NotImplementedError, match="Statistical analysis is not implemented"):
        run(Path("configs/examples/main.yaml"))
