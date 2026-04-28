"""Tests for dataset snapshot export sidecar manifests."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.application.services.export_manifests import (
    build_export_checksum_manifest,
    build_export_sidecar_payloads,
)
from bioetl.domain.ports import ExportFileFingerprint


def _fingerprint(
    path: str = "exports/silver_chembl_activity.csv",
) -> ExportFileFingerprint:
    return ExportFileFingerprint(
        path=Path(path),
        size_bytes=11,
        sha256="a" * 64,
    )


def test_build_export_sidecar_payloads_is_deterministic_for_stable_inputs() -> None:
    first = build_export_sidecar_payloads(
        table_name="chembl.activity",
        layer="silver",
        export_format="csv",
        output_path=Path("exports/silver_chembl_activity.csv"),
        row_count=2,
        columns=("activity_id", "molecule_id"),
        data_fingerprint=_fingerprint(),
        generated_at="2026-04-28T00:00:00Z",
        run_ids=("run-1",),
        code_revision="abc123",
    )
    second = build_export_sidecar_payloads(
        table_name="chembl.activity",
        layer="silver",
        export_format="csv",
        output_path=Path("exports/silver_chembl_activity.csv"),
        row_count=2,
        columns=("activity_id", "molecule_id"),
        data_fingerprint=_fingerprint(),
        generated_at="2026-04-28T00:00:00Z",
        run_ids=("run-1",),
        code_revision="abc123",
    )

    assert first == second
    assert first.provenance_manifest["dataset_bundle_id"] == first.dataset_bundle_id
    assert first.licensing_manifest["dataset_bundle_id"] == first.dataset_bundle_id
    assert first.provenance_manifest["run_ids"] == ["run-1"]
    assert first.licensing_manifest["code_license"] == {
        "license_name": "MIT",
        "license_url": "https://opensource.org/license/mit",
        "scope": "BioETL source code only",
    }


def test_build_export_sidecar_payloads_includes_composite_provider_licenses() -> None:
    sidecars = build_export_sidecar_payloads(
        table_name="composite.publication",
        layer="gold",
        export_format="csv",
        output_path=Path("exports/gold_composite_publication.csv"),
        row_count=3,
        columns=("publication_id", "title"),
        data_fingerprint=_fingerprint("exports/gold_composite_publication.csv"),
        generated_at="2026-04-28T00:00:00Z",
    )

    providers = [
        entry["provider"]
        for entry in sidecars.licensing_manifest["data_licenses"]
        if isinstance(entry, dict)
    ]

    assert providers == ["chembl", "openalex", "pubmed", "semanticscholar"]
    assert "must not be treated as MIT-licensed data" in str(
        sidecars.licensing_manifest["mixed_license_behavior"]
    )


def test_build_export_sidecar_payloads_unknown_provider_strict_mode_fails() -> None:
    with pytest.raises(ValueError, match="Missing provider attribution"):
        build_export_sidecar_payloads(
            table_name="unknown.entity",
            layer="silver",
            export_format="csv",
            output_path=Path("exports/silver_unknown_entity.csv"),
            row_count=1,
            columns=("id",),
            data_fingerprint=_fingerprint("exports/silver_unknown_entity.csv"),
            generated_at="2026-04-28T00:00:00Z",
            strict=True,
        )


def test_build_export_checksum_manifest_lists_data_and_sidecar_files() -> None:
    payload = build_export_checksum_manifest(
        dataset_bundle_id="bundle-1",
        generated_at="2026-04-28T00:00:00Z",
        fingerprints=(
            _fingerprint("exports/data.csv"),
            _fingerprint("exports/data.provenance-manifest.json"),
        ),
    )

    assert payload["manifest_type"] == "bioetl.dataset_snapshot.checksums"
    assert payload["algorithm"] == "sha256"
    assert payload["files"] == [
        {
            "path": "exports/data.csv",
            "size_bytes": 11,
            "sha256": "a" * 64,
        },
        {
            "path": "exports/data.provenance-manifest.json",
            "size_bytes": 11,
            "sha256": "a" * 64,
        },
    ]
