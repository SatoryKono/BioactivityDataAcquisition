"""The runtime import harness must reject even swallowed forbidden imports."""

from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture


def test_runtime_and_engineering_preserve_fixed_input_output(tmp_path: Path) -> None:
    from bioetl.composition.observability_runtime import collect_metric_inventory
    from scripts.engineering.qa import (
        report_observability_metric_inventory as engineering,
    )

    source = tmp_path / "src/bioetl/application/probe.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        'metrics.increment_counter("bioetl_qm07_fixed_total")\n', encoding="utf-8"
    )
    # The registry belongs to the distribution, even when the scanned input root
    # is an external fixture containing no metric-definition modules.
    expected = engineering.collect_metric_inventory(tmp_path)
    actual = collect_metric_inventory(tmp_path)
    assert actual == expected
    assert len(actual) == 51
    assert len(actual["registered_metrics"]) > 1
    assert "bioetl_qm07_fixed_total" in actual["runtime_without_registry"]
    source.write_text(
        'metrics.increment_counter("bioetl_qm07_new_total")\n', encoding="utf-8"
    )
    changed = engineering.collect_metric_inventory(tmp_path)
    assert "bioetl_qm07_new_total" in changed["runtime_without_registry"]
    assert "bioetl_qm07_fixed_total" not in changed["runtime_without_registry"]


def test_guard_detects_swallowed_forbidden_attempt(tmp_path: Path) -> None:
    import subprocess
    import sys

    harness = Path(__file__).with_name("runtime_smoke.py")
    code = (
        "import runpy; "
        f"Guard = runpy.run_path({str(harness)!r})['ScriptsImportGuard']; "
        "guard = Guard(); "
        "guard.__enter__(); "
        "exec('try:\\n __import__(\"scripts.engineering.qa\")\\nexcept ImportError:\\n pass'); "
        "guard.__exit__(None, None, None)"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    assert "Forbidden runtime import attempts: ['scripts']" in result.stderr


def test_source_runtime_smoke_isolated(tmp_path: Path) -> None:
    import json
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[3]
    harness = root / "tests/architecture/qm_07/runtime_smoke.py"
    code = (
        "import sys, runpy; "
        f"sys.path.insert(0, {str(root / 'src')!r}); "
        f"sys.argv = [{str(harness)!r}, {str(tmp_path)!r}]; "
        f"runpy.run_path({str(harness)!r}, run_name='__main__')"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["attempts"] == []
    assert Path(payload["bioetl_origin"]).resolve().is_relative_to(root / "src")
