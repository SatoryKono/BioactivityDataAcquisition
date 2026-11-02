# pyright: reportArgumentType=false
"""Path and alias helpers for evidence locations (RF-002 / #12680)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.application.services.run_reports.evidence_location_paths import (
    EVIDENCE_LOCATIONS_DIRNAME,
    default_evidence_root_alias_registry,
    resolve_evidence_location_path,
    resolve_evidence_locations_root,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
)

pytestmark = pytest.mark.unit


def test_evidence_locations_catalog_layout(tmp_path: Path) -> None:
    report_root = tmp_path / "reports" / "run-reports"
    catalog = resolve_evidence_locations_root(report_root=report_root)
    assert catalog == report_root / EVIDENCE_LOCATIONS_DIRNAME
    path = resolve_evidence_location_path(
        kind=EvidenceLocationKind.PIPELINE,
        owner="chembl_assay",
        run_id="ac0b4e22-6a6e-5b7e-818e-106aeaf41390",
        report_root=report_root,
    )
    assert path == (
        catalog
        / "pipeline"
        / "chembl_assay"
        / "ac0b4e22-6a6e-5b7e-818e-106aeaf41390.json"
    )


def test_alias_registry_resolves_standard_and_isolated_roots(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    data_root.mkdir()
    aliases = default_evidence_root_alias_registry(
        dashboard_data_root=data_root.resolve()
    )
    standard = aliases.resolve_data_root(
        root_alias=DEFAULT_EVIDENCE_ROOT_ALIAS,
        relative_data_root=".",
    )
    assert standard == data_root.resolve()
    isolated = aliases.resolve_data_root(
        root_alias=DEFAULT_EVIDENCE_ROOT_ALIAS,
        relative_data_root="workflow-limit100-20261102T144403Z/chembl_assay",
    )
    assert isolated == (
        data_root.resolve() / "workflow-limit100-20261102T144403Z" / "chembl_assay"
    )


def test_alias_registry_rejects_unknown_and_relative_bases(tmp_path: Path) -> None:
    with pytest.raises(EvidenceLocationInvalidError, match="absolute"):
        default_evidence_root_alias_registry(dashboard_data_root=Path("data"))
    aliases = default_evidence_root_alias_registry(
        dashboard_data_root=(tmp_path / "data").resolve()
    )
    with pytest.raises(EvidenceLocationInvalidError, match="unknown"):
        aliases.absolute_base("other_alias")
