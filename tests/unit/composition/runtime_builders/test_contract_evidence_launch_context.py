"""Real processing contexts must not silently suppress launch evidence."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import json
import pytest

from bioetl.application.core.runner import PipelineRunner
from bioetl.application.services.control_plane.ledger.service import RunLedgerService
from bioetl.composition.runtime_builders.ledger_collaborator import (
    attach_control_plane_collaborators,
)
from bioetl.domain.context import PipelineContext, PipelineRunContext
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane.file_run_ledger_store import FileRunLedgerStore
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


@pytest.mark.parametrize("resume", [False, True])
def test_post_lock_finalization_uses_launch_context(tmp_path, resume):
    run_id = RunID(UUID(int=1))
    manifest_id = str(UUID(int=2))
    launch = PipelineRunContext(
        pipeline_name="chembl_assay",
        run_id=run_id,
        run_type=RunType.BACKFILL,
        manifest_id=manifest_id,
        contract_ref="chembl.assay",
        contract_schema_hash="a" * 64,
        resume=resume,
    )
    runner = object.__new__(PipelineRunner)
    runner._context = PipelineContext(
        run_id=run_id,
        run_type=RunType.BACKFILL,
        logger=NoOpLogger(),
        started_at=datetime(2026, 9, 14, tzinfo=UTC),
    )
    runner._services = None
    runner._contract_evidence_context = None
    runner._contract_evidence_recorder = None
    runner._lock_runtime_service = SimpleNamespace(
        get_context=lambda: SimpleNamespace(owner_id="measured-lock-owner")
    )
    ledger = RunLedgerService(
        ledger_port=FileRunLedgerStore(base_path=tmp_path / "run_ledger"),
        manifest_id=manifest_id,
        run_id=run_id,
    )
    attach_control_plane_collaborators(runner, ledger, launch_context=launch)
    runner._finalize_contract_evidence()
    payload = json.loads(
        (
            tmp_path / "run_manifest" / f"{manifest_id}.contract-evidence.json"
        ).read_text()
    )
    assert payload["manifest_id"] == manifest_id
    assert payload["contract_comparison_status"] == "compatible"
    assert payload["resume_contract"] == (
        "resume_requested" if resume else "resume_not_requested"
    )
    assert payload["lock_owner_id"] == "measured-lock-owner"
