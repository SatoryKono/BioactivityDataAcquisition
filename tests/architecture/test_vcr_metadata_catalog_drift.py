"""Guard the tracked VCR metadata catalog artifact against generator drift."""

from __future__ import annotations

import sys

import pytest

import importlib.util
import json
from pathlib import Path
from typing import Any, Protocol, cast


pytestmark = [pytest.mark.architecture, pytest.mark.slow]


def _normalize_catalog_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload))

    def _normalize_path(value: Any) -> Any:
        if isinstance(value, str):
            return value.replace("\\", "/").strip()
        return value

    cassettes = normalized.get("cassettes")
    if isinstance(cassettes, list):
        normalized_rows: list[dict[str, Any]] = []
        for row in cassettes:
            if not isinstance(row, dict):
                continue
            normalized_row = dict(row)
            normalized_row["cassette_rel_path"] = _normalize_path(
                normalized_row.get("cassette_rel_path")
            )
            normalized_row["metadata_rel_path"] = _normalize_path(
                normalized_row.get("metadata_rel_path")
            )
            owners = row.get("reachability_owner_paths")
            if isinstance(owners, list):
                normalized_row["reachability_owner_paths"] = sorted(
                    {
                        _normalize_path(owner)
                        for owner in owners
                        if isinstance(owner, str)
                    }
                )
            else:
                normalized_row["reachability_owner_paths"] = []
            normalized_rows.append(normalized_row)

        normalized["cassettes"] = sorted(
            normalized_rows,
            key=lambda row: (
                row.get("provider", ""),
                row.get("cassette_rel_path", ""),
                row.get("scenario_stem", ""),
            ),
        )
        normalized["_cassettes_by_path"] = {
            row["cassette_rel_path"]: row
            for row in normalized["cassettes"]
            if row.get("cassette_rel_path")
        }

    providers = normalized.get("providers")
    if isinstance(providers, dict):
        normalized["providers"] = dict(
            sorted(providers.items(), key=lambda item: item[0])
        )

    pruning = normalized.get("pruning")
    if isinstance(pruning, dict):
        duplicate_scenario_stems = pruning.get("duplicate_scenario_stems")
        if isinstance(duplicate_scenario_stems, dict):
            normalized["pruning"]["duplicate_scenario_stems"] = dict(
                sorted(duplicate_scenario_stems.items(), key=lambda item: item[0])
            )
        for key in (
            "orphan_metadata_sidecar_count",
            "metadata_review_required_cassettes",
            "unowned_cassettes",
        ):
            value = normalized["pruning"].get(key)
            if isinstance(value, list):
                normalized["pruning"][key] = sorted(value)
    return normalized


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
    if sys.platform.startswith("win"):
        pytest.skip("Skipped on Windows due to filesystem performance")
    mod = _load_catalog_module()
    expected = mod.render_catalog_json(Path("tests/fixtures/vcr"))
    artifact_path = Path("reports/quality/vcr-metadata-catalog.json")
    actual = artifact_path.read_text(encoding="utf-8")

    actual_payload = _normalize_catalog_payload(json.loads(actual))
    expected_payload = _normalize_catalog_payload(json.loads(expected))
    expected_keys = {
        "schema_version",
        "catalog_kind",
        "vcr_root",
        "totals",
        "pruning",
        "providers",
        "cassettes",
    }
    assert actual_payload.keys() >= expected_keys
    assert expected_payload.keys() >= expected_keys

    for key in ("schema_version", "catalog_kind", "vcr_root"):
        assert actual_payload[key] == expected_payload[key]

    assert actual_payload["totals"] == expected_payload["totals"]
    assert actual_payload["providers"] == expected_payload["providers"]
    assert actual_payload["pruning"] == expected_payload["pruning"]

    actual_rows = cast(
        dict[str, dict[str, Any]], actual_payload.get("_cassettes_by_path", {})
    )
    expected_rows = cast(
        dict[str, dict[str, Any]], expected_payload.get("_cassettes_by_path", {})
    )

    assert actual_rows == expected_rows, (
        "VCR metadata catalog artifact drifted from generator output."
    )


def test_vcr_metadata_catalog_tracks_cassettes_not_sidecars() -> None:
    if sys.platform.startswith("win"):
        pytest.skip("Skipped on Windows due to filesystem performance")
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
    assert totals["unowned_cassette_count"] == 0
    assert totals["metadata_review_required_cassette_count"] == 0
    assert pruning["unowned_cassettes"] == []
    assert pruning["metadata_review_required_cassettes"] == []
    assert not any(
        cassette["reachability_status"] == "metadata_reviewed" for cassette in cassettes
    ), "legacy metadata-reviewed backlog must be burned down to explicit owner paths"
    assert not any(
        cassette["cassette_rel_path"].endswith(("_meta.yaml", "_meta.yml"))
        for cassette in cassettes
    )
    assert all(cassette["scenario_stem"] for cassette in cassettes)
    assert all(cassette["reachability_owner_paths"] for cassette in cassettes)
    assert {cassette["reachability_status"] for cassette in cassettes} <= {
        "direct_reference",
        "generated_reference",
        "metadata_review_required",
    }
