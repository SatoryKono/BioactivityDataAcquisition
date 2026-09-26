"""Nominal import-surface coverage for control-plane port package (#7904)."""

from __future__ import annotations

import importlib

import pytest

from bioetl.domain.ports import control_plane
from bioetl.domain.ports.control_plane import (
    ArtifactByteComparisonPort,
    ContractEvidenceRecorderPort,
    EffectiveConfigArtifactStorePort,
    LineageStorePort,
    RawManifestInspection,
    RawRunManifestInspectionPort,
    RunLedgerPort,
    RunManifestPort,
    WorkflowExecutionStatePort,
    WorkflowLedgerPort,
    WorkflowManifestPort,
)

EXPECTED_EXPORTS = frozenset(
    {
        "ArtifactByteComparisonPort",
        "ContractEvidenceRecorderPort",
        "EffectiveConfigArtifactStorePort",
        "LineageStorePort",
        "RawManifestInspection",
        "RawRunManifestInspectionPort",
        "RunLedgerPort",
        "RunManifestPort",
        "WorkflowExecutionStatePort",
        "WorkflowLedgerPort",
        "WorkflowManifestPort",
    }
)


@pytest.mark.unit
def test_control_plane_package_all_matches_expected_public_surface() -> None:
    """Package __all__ is the governed public control-plane port surface."""
    assert frozenset(control_plane.__all__) == EXPECTED_EXPORTS


@pytest.mark.unit
@pytest.mark.parametrize("export_name", sorted(EXPECTED_EXPORTS))
def test_control_plane_export_is_importable_type(export_name: str) -> None:
    """Each public export is importable from the package as its class object."""
    symbol = getattr(control_plane, export_name)
    assert symbol is not None
    assert isinstance(symbol, type)
    assert symbol.__name__ == export_name


@pytest.mark.unit
def test_control_plane_named_imports_resolve_to_package_exports() -> None:
    """Named imports from the package match attribute exports."""
    assert control_plane.RunManifestPort is RunManifestPort
    assert control_plane.RunLedgerPort is RunLedgerPort
    assert control_plane.WorkflowManifestPort is WorkflowManifestPort
    assert control_plane.WorkflowLedgerPort is WorkflowLedgerPort
    assert control_plane.WorkflowExecutionStatePort is WorkflowExecutionStatePort
    assert control_plane.LineageStorePort is LineageStorePort
    assert control_plane.RawManifestInspection is RawManifestInspection
    assert control_plane.RawRunManifestInspectionPort is RawRunManifestInspectionPort
    assert (
        control_plane.EffectiveConfigArtifactStorePort
        is EffectiveConfigArtifactStorePort
    )
    assert control_plane.ArtifactByteComparisonPort is ArtifactByteComparisonPort
    assert control_plane.ContractEvidenceRecorderPort is ContractEvidenceRecorderPort


@pytest.mark.unit
def test_control_plane_module_docstring_references_adr_044() -> None:
    """Package docs record the ADR and migration/rollback contract (#7904)."""
    module = importlib.import_module("bioetl.domain.ports.control_plane")
    doc = module.__doc__ or ""
    assert "ADR-044" in doc
    assert "Migration" in doc
    assert "Rollback" in doc
