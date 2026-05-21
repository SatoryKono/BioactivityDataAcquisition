"""Guard the tracked VCR metadata catalog artifact against generator drift."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Protocol, cast


class CatalogModule(Protocol):
    """Typed surface for the catalog generator module."""

    def render_catalog_json(self, vcr_root: Path) -> str: ...


def _load_catalog_module() -> CatalogModule:
    script = Path("scripts/engineering/qa/report_vcr_metadata_catalog.py")
    spec = importlib.util.spec_from_file_location(
        "vcr_metadata_catalog_gen", str(script)
    )
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load module from {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast(CatalogModule, module)


def test_vcr_metadata_catalog_drift_check_passes_current_repo() -> None:
    mod = _load_catalog_module()
    expected = mod.render_catalog_json(Path("tests/fixtures/vcr"))
    artifact_path = Path("reports/quality/vcr-metadata-catalog.json")
    actual = artifact_path.read_text(encoding="utf-8")

    assert actual == expected, (
        "VCR metadata catalog artifact drifted from generator output."
    )


def test_vcr_metadata_catalog_tracks_cassettes_not_sidecars() -> None:
    mod = _load_catalog_module()
    payload = cast(
        dict[str, Any], json.loads(mod.render_catalog_json(Path("tests/fixtures/vcr")))
    )
    vcr_root = Path("tests/fixtures/vcr")
    cassette_files = [
        path
        for path in vcr_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".yaml", ".yml"}
        and not path.name.endswith(("_meta.yaml", "_meta.yml"))
    ]
    metadata_files = list(vcr_root.rglob("*_meta.yaml")) + list(
        vcr_root.rglob("*_meta.yml")
    )

    totals = cast(dict[str, Any], payload["totals"])
    pruning = cast(dict[str, Any], payload["pruning"])
    cassettes = cast(list[dict[str, Any]], payload["cassettes"])

    assert totals["cassette_count"] == len(cassette_files)
    assert totals["metadata_sidecar_count"] == len(metadata_files)
    assert totals["duplicate_scenario_stem_count"] == 0
    assert pruning["duplicate_scenario_stems"] == {}
    assert pruning["orphan_metadata_sidecar_count"] == 0
    assert not any(
        cassette["cassette_rel_path"].endswith(("_meta.yaml", "_meta.yml"))
        for cassette in cassettes
    )
    assert all(cassette["scenario_stem"] for cassette in cassettes)
