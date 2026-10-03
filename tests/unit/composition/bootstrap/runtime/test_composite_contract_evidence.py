"""Composite sidecars use the selected manifest and actual lock owner."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.application.composite.runner_pkg.runner import CompositePipelineRunner
from bioetl.composition.bootstrap.runtime._composite_control_plane_support import (
    create_composite_contract_finalizer,
)

MODULE = "bioetl.composition.bootstrap.runtime._composite_control_plane_support"


@pytest.mark.parametrize("resume", [False, True])
def test_contract_sidecar_binds_runtime_identity(tmp_path, resume):
    manifest = SimpleNamespace(
        run_id="parent-run",
        pipeline_name="composite_assay",
        code_provenance=SimpleNamespace(
            contract_ref="composite.assay", contract_schema_hash="a" * 64
        ),
    )
    with (
        patch(
            f"{MODULE}.get_settings", return_value=SimpleNamespace(data_dir=tmp_path)
        ),
        patch(f"{MODULE}.FileRunManifestStore.get", return_value=manifest),
    ):
        finalize = create_composite_contract_finalizer(
            pipeline_name="composite_assay", manifest_id="parent-manifest"
        )
        finalize("parent-run", resume)
        payload = json.loads(
            (
                tmp_path
                / "output/control/run_manifest/parent-manifest.contract-evidence.json"
            ).read_text()
        )
        assert payload["manifest_id"] == "parent-manifest"
        assert payload["lock_owner_id"] == "parent-run"
        assert payload["contract_comparison_status"] == "compatible"
        assert payload["resume_contract"] == (
            "resume_requested" if resume else "resume_not_requested"
        )
        with pytest.raises(RuntimeError, match="identity mismatch"):
            finalize("foreign-run", resume)


@pytest.mark.asyncio
async def test_contract_finalization_precedes_locked_phase_execution():
    runner = object.__new__(CompositePipelineRunner)
    runner._run_id_str = "parent-run"
    runner._runtime = SimpleNamespace(resume=False)
    events = []
    runner._contract_evidence_finalizer = lambda *args: events.append("contract")

    async def prepare():
        events.append("prepare")
        return "state"

    runner._prepare_run_state = prepare
    runner._execute_locked_run_phases = AsyncMock(return_value=("state", "context"))
    runner._complete_successful_run = AsyncMock(return_value="result")
    assert await runner._run_with_lock() == "result"
    assert events == ["contract", "prepare"]
    runner._contract_evidence_finalizer = MagicMock(
        side_effect=RuntimeError("cannot persist")
    )
    runner._execute_locked_run_phases.reset_mock()
    with pytest.raises(RuntimeError, match="cannot persist"):
        await runner._run_with_lock()
    runner._execute_locked_run_phases.assert_not_called()
