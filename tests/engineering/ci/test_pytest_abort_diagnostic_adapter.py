import sys
from pathlib import Path

import pytest
from scripts.engineering.ci.pytest_abort_diagnostic_adapter import (
    PytestAbortDiagnosticAdapter,
)


@pytest.mark.unit
def test_normal_exit(tmp_path: Path):
    adapter = PytestAbortDiagnosticAdapter(timeout=5)
    cmd = [sys.executable, "-c", "import sys; sys.exit(0)"]
    manifest = adapter.run(cmd, None, tmp_path)
    assert manifest.status == "NORMAL_EXIT"
    assert manifest.exit_code == 0
    assert manifest.signal is None

@pytest.mark.unit
def test_nonzero_exit(tmp_path: Path):
    adapter = PytestAbortDiagnosticAdapter(timeout=5)
    cmd = [sys.executable, "-c", "import sys; sys.exit(42)"]
    manifest = adapter.run(cmd, None, tmp_path)
    assert manifest.status == "NONZERO_EXIT"
    assert manifest.exit_code == 42
    assert manifest.signal is None

@pytest.mark.unit
def test_memory_error(tmp_path: Path):
    adapter = PytestAbortDiagnosticAdapter(timeout=5)
    # Trigger MemoryError by exhausting memory, this might just exit with 1 or similar
    cmd = [sys.executable, "-c", "raise MemoryError('out of memory')"]
    manifest = adapter.run(cmd, None, tmp_path)
    assert manifest.status == "NONZERO_EXIT"
    assert manifest.exit_code == 1
    assert manifest.signal is None

@pytest.mark.unit
def test_timeout(tmp_path: Path):
    adapter = PytestAbortDiagnosticAdapter(timeout=1, dump_margin=1)
    cmd = [sys.executable, "-c", "import time; time.sleep(10)"]
    manifest = adapter.run(cmd, None, tmp_path)
    assert manifest.status == "WATCHDOG_TIMEOUT"
    assert manifest.exit_code is not None
    # signal might be SIGABRT or SIGKILL depending on OS

@pytest.mark.unit
def test_abort_signal(tmp_path: Path):
    adapter = PytestAbortDiagnosticAdapter(timeout=5)
    cmd = [sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGABRT)"]
    manifest = adapter.run(cmd, None, tmp_path)
    assert manifest.status == "SIGNAL_ABORT"
    assert manifest.exit_code is not None
    assert manifest.exit_code < 0
    assert manifest.signal is not None

@pytest.mark.unit
def test_missing_evidence(tmp_path: Path):
    adapter = PytestAbortDiagnosticAdapter(timeout=5)
    evidence_path = tmp_path / "expected.xml"
    cmd = [sys.executable, "-c", "import sys; sys.exit(0)"]
    manifest = adapter.run(cmd, evidence_path, tmp_path)
    assert manifest.status == "NORMAL_EXIT"
    assert manifest.missing_evidence is True
