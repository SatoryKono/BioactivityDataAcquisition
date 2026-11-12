"""TC-04 snapshot immutability and offline completeness."""

from __future__ import annotations

import pytest

from iuphar_target_class.policy import policy_document
from iuphar_target_class.snapshot import (
    VERSION_DIFFER,
    VERSION_MATCHED,
    VERSION_UNAVAILABLE,
    SnapshotProvider,
    TargetView,
    absence_status,
    assess_completeness,
    freeze_record,
)

pytestmark = pytest.mark.unit


def _target(target_id: str, accession: str) -> TargetView:
    payload = {"id": target_id, "uniprot": accession, "type": "gpcr"}
    return TargetView(
        target_id=target_id,
        uniprot_ids=(accession,),
        gene_symbol="OPRM1",
        species="human",
        family_ids=("900",),
        taxon="human",
        type_name="gpcr",
        record=freeze_record("target", target_id, payload),
    )


def test_snapshot_immutability() -> None:
    provider = SnapshotProvider((_target("1", "P35372"),), ())
    first = provider.get_target("1")
    second = provider.get_target("1")
    assert first.payload_sha256 == second.payload_sha256
    assert first.records[0].payload == second.records[0].payload
    mutated = bytearray(first.records[0].payload)
    mutated[0] = 0
    assert provider.get_target("1").records[0].payload == first.records[0].payload
    assert (
        provider.indexes.version
        == SnapshotProvider(
            (_target("1", "P35372"),),
            (),
        ).indexes.version
    )


def test_totals_mismatch_marks_snapshot_incomplete() -> None:
    result = assess_completeness(
        coverage_approved=True,
        required_types_loaded=True,
        pagination_complete=True,
        transport_or_schema_errors=False,
        totals_match=False,
        provider_versions=VERSION_MATCHED,
        version_limitation_recorded=False,
    )
    assert result.complete is False
    assert result.publishable is False
    assert absence_status(result) == "source_unavailable"


def test_unavailable_versions_are_version_unverified() -> None:
    blocked = assess_completeness(
        coverage_approved=True,
        required_types_loaded=True,
        pagination_complete=True,
        transport_or_schema_errors=False,
        totals_match=True,
        provider_versions=VERSION_UNAVAILABLE,
        version_limitation_recorded=False,
    )
    assert blocked.version_unverified is True
    assert absence_status(blocked) == "source_unavailable"
    limited = assess_completeness(
        coverage_approved=True,
        required_types_loaded=True,
        pagination_complete=True,
        transport_or_schema_errors=False,
        totals_match=True,
        provider_versions=VERSION_UNAVAILABLE,
        version_limitation_recorded=True,
    )
    assert limited.version_unverified is True
    assert limited.allows_not_found is True
    assert limited.publishable is False
    assert absence_status(limited) == "not_found"


def test_unapproved_coverage_is_not_a_release() -> None:
    parameters = policy_document()["parameters"]
    assert isinstance(parameters, dict)
    assert parameters["snapshot_coverage"] is None
    assert parameters["snapshot_species"] is None
    result = assess_completeness(
        coverage_approved=False,
        required_types_loaded=True,
        pagination_complete=True,
        transport_or_schema_errors=False,
        totals_match=True,
        provider_versions=VERSION_MATCHED,
        version_limitation_recorded=False,
    )
    assert result.publishable is False
    assert "не утверждены" in result.reason
    assert absence_status(result) == "source_unavailable"


def test_differing_versions_are_incomplete() -> None:
    result = assess_completeness(
        coverage_approved=True,
        required_types_loaded=True,
        pagination_complete=True,
        transport_or_schema_errors=False,
        totals_match=True,
        provider_versions=VERSION_DIFFER,
        version_limitation_recorded=False,
    )
    assert result.complete is False
    assert absence_status(result) == "source_unavailable"


@pytest.mark.parametrize(
    ("version", "unverified"),
    [(VERSION_MATCHED, False), (VERSION_DIFFER, False), (VERSION_UNAVAILABLE, True)],
)
def test_unapproved_coverage_preserves_independent_version_limitation(
    version: str, unverified: bool
) -> None:
    result = assess_completeness(
        coverage_approved=False,
        required_types_loaded=True,
        pagination_complete=True,
        transport_or_schema_errors=False,
        totals_match=True,
        provider_versions=version,
        version_limitation_recorded=True,
    )
    assert result.version_unverified is unverified
    assert result.complete is False
    assert result.publishable is False
    assert result.allows_not_found is False
    assert "не утверждены" in result.reason
    assert absence_status(result) == "source_unavailable"


def test_missing_family_is_a_diagnostic_not_silence() -> None:
    provider = SnapshotProvider((), ())
    hit = provider.get_families(("900",))
    assert hit.records == ()
    assert hit.diagnostics == ("missing family 900",)
