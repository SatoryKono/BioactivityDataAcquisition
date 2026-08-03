# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for dataset snapshot export sidecar manifests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from bioetl.application.services.export_manifests import (
    build_export_checksum_manifest,
    build_export_sidecar_payloads,
)
from bioetl.domain.ports import ExportFileFingerprint


pytestmark = pytest.mark.unit


class _FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 5, 1, 2, 3, 4, 987654, tzinfo=UTC)


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
        row_count=2,
        columns=("activity_id", "molecule_id"),
        data_fingerprint=_fingerprint(),
        timestamp_opts=("2026-04-28T00:00:00Z", False, None),
        run_ids=("run-1",),
        code_revision="abc123",
    )
    second = build_export_sidecar_payloads(
        table_name="chembl.activity",
        layer="silver",
        export_format="csv",
        row_count=2,
        columns=("activity_id", "molecule_id"),
        data_fingerprint=_fingerprint(),
        timestamp_opts=("2026-04-28T00:00:00Z", False, None),
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
        row_count=3,
        columns=("publication_id", "title"),
        data_fingerprint=_fingerprint("exports/gold_composite_publication.csv"),
        timestamp_opts=("2026-04-28T00:00:00Z", False, None),
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


def test_build_export_sidecar_payloads_records_governed_export_metadata() -> None:
    sidecars = build_export_sidecar_payloads(
        table_name="chembl.activity",
        layer="silver",
        export_format="csv",
        row_count=2,
        columns=("activity_id", "molecule_id"),
        data_fingerprint=_fingerprint(),
        timestamp_opts=("2026-04-28T00:00:00Z", False, None),
        access=(
            "operator@example.test",
            "viewer",
            "filters-sha256",
            "2026-05-01T00:00:00Z",
            "default",
            "export-audit:abc123",
        ),
        redacted_columns=("raw_payload",),
    )

    governance = sidecars.provenance_manifest["export_governance"]

    assert governance == {
        "audit_ref": "export-audit:abc123",
        "requester": "operator@example.test",
        "role": "viewer",
        "filters_hash": "filters-sha256",
        "expires_at": "2026-05-01T00:00:00Z",
        "redaction_profile": "default",
        "redacted_columns": ["raw_payload"],
    }


def test_build_export_sidecar_payloads_unknown_provider_strict_mode_fails() -> None:
    with pytest.raises(ValueError, match="Missing provider attribution"):
        build_export_sidecar_payloads(
            table_name="unknown.entity",
            layer="silver",
            export_format="csv",
            row_count=1,
            columns=("id",),
            data_fingerprint=_fingerprint("exports/silver_unknown_entity.csv"),
            timestamp_opts=("2026-04-28T00:00:00Z", False, None),
            strict=True,
        )


def test_build_export_sidecar_payloads_requires_generated_at_by_default() -> None:
    with pytest.raises(ValueError, match="generated_at must be provided"):
        build_export_sidecar_payloads(
            table_name="chembl.activity",
            layer="silver",
            export_format="csv",
            row_count=2,
            columns=("activity_id",),
            data_fingerprint=_fingerprint(),
        )


def test_build_export_sidecar_payloads_allows_operator_timestamp_opt_in() -> None:
    sidecars = build_export_sidecar_payloads(
        table_name="chembl.activity",
        layer="silver",
        export_format="csv",
        row_count=2,
        columns=("activity_id",),
        data_fingerprint=_fingerprint(),
        timestamp_opts=(None, True, None),
    )

    assert isinstance(sidecars.provenance_manifest["generated_at"], str)
    assert sidecars.provenance_manifest["generated_at"]


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


def test_build_export_checksum_manifest_requires_generated_at_by_default() -> None:
    with pytest.raises(ValueError, match="generated_at must be provided"):
        build_export_checksum_manifest(
            dataset_bundle_id="bundle-1",
            generated_at=None,
            fingerprints=(_fingerprint("exports/data.csv"),),
        )


def test_operator_timestamp_opt_in_can_use_clock_port() -> None:
    sidecars = build_export_sidecar_payloads(
        table_name="chembl.activity",
        layer="silver",
        export_format="csv",
        row_count=2,
        columns=("activity_id",),
        data_fingerprint=_fingerprint(),
        timestamp_opts=(None, True, _FixedClock()),
    )

    assert sidecars.provenance_manifest["generated_at"] == "2026-05-01T02:03:04Z"
    assert sidecars.licensing_manifest["generated_at"] == "2026-05-01T02:03:04Z"


def test_checksum_manifest_operator_timestamp_opt_in_can_use_clock_port() -> None:
    payload = build_export_checksum_manifest(
        dataset_bundle_id="bundle-1",
        generated_at=None,
        fingerprints=(_fingerprint("exports/data.csv"),),
        allow_nondeterministic_generated_at=True,
        clock=_FixedClock(),
    )

    assert payload["generated_at"] == "2026-05-01T02:03:04Z"
