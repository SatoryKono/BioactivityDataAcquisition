# pyright: reportArgumentType=false
"""Integration: EvidenceLocationResolver + file store + composition factory."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.evidence_location import (
    EvidenceLocationResolver,
)
from bioetl.application.services.run_reports.evidence_location_paths import (
    default_evidence_root_alias_registry,
)
from bioetl.composition.factories.evidence_read_context_factory import (
    FileEvidenceReadContextFactory,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationKind,
    EvidenceLocationLookupCode,
    build_run_evidence_location,
)
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)

pytestmark = pytest.mark.integration

_SOURCE_A = "a" * 64
_RUN_A = "ac0b4e22-6a6e-5b7e-818e-106aeaf41390"
_WF = "3dc8ffe4-305b-5d4b-a945-fe8e78f03828"


def test_resolver_opens_registered_file_backed_location(tmp_path: Path) -> None:
    data_root = (tmp_path / "data").resolve()
    data_root.mkdir()
    isolated = data_root / "workflow-a" / "chembl_assay"
    isolated.mkdir(parents=True)
    report_root = tmp_path / "run-reports"
    report_root.mkdir()
    store = FileEvidenceLocationStore(report_root=report_root)
    store.register(
        build_run_evidence_location(
            kind=EvidenceLocationKind.PIPELINE,
            owner="chembl_assay",
            run_id=_RUN_A,
            workflow_run_id=_WF,
            runtime_source_id=_SOURCE_A,
            root_alias=DEFAULT_EVIDENCE_ROOT_ALIAS,
            relative_data_root="workflow-a/chembl_assay",
        )
    )
    resolver = EvidenceLocationResolver(
        locations=store,
        aliases=default_evidence_root_alias_registry(dashboard_data_root=data_root),
        opener=FileEvidenceReadContextFactory(),
    )
    resolved = resolver.resolve(kind="pipeline", owner="chembl_assay", run_id=_RUN_A)
    assert resolved.code is EvidenceLocationLookupCode.FOUND
    assert resolved.data_root == isolated.resolve()
    assert resolved.context is not None
    missing = resolver.load_manifest(resolved, run_id=UUID(_RUN_A))
    assert missing.code is EvidenceLocationLookupCode.MANIFEST_MISSING
