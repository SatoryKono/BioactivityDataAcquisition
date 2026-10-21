from __future__ import annotations

import pytest
from pathlib import Path

@pytest.mark.unit
def test_run_pytest_sh_strips_no_benchmark() -> None:
    script = (Path(__file__).resolve().parents[6] / "scripts/engineering/dev/run_pytest.sh").read_text(encoding="utf-8")
    assert 'PYTEST_ARGS+=("-p" "benchmark")' in script

@pytest.mark.unit
def test_run_pytest_ps1_strips_no_benchmark() -> None:
    script = (Path(__file__).resolve().parents[6] / "scripts/engineering/dev/run_pytest.ps1").read_text(encoding="utf-8")
    assert '$script:PytestArgs += @("-p", "benchmark")' in script
