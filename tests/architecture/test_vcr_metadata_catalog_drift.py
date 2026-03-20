"""Guard the tracked VCR metadata catalog artifact against generator drift."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_catalog_module():
    script = Path("scripts/qa/report_vcr_metadata_catalog.py")
    spec = importlib.util.spec_from_file_location(
        "vcr_metadata_catalog_gen", str(script)
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_vcr_metadata_catalog_drift_check_passes_current_repo() -> None:
    mod = _load_catalog_module()
    expected = mod.render_catalog_json(Path("tests/fixtures/vcr"))
    artifact_path = Path("reports/quality/vcr-metadata-catalog.json")
    actual = artifact_path.read_text(encoding="utf-8")

    assert actual == expected, (
        "VCR metadata catalog artifact drifted from generator output."
    )
