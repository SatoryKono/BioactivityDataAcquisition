"""Composite sidecars use the selected manifest and actual lock owner."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.application.composite.runner_pkg.runner import CompositePipelineRunner
from bioetl.composition.bootstrap.runtime.run_status import (
    create_composite_contract_finalizer,
    create_composite_reporter,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)

MODULE = "bioetl.composition.bootstrap.runtime.run_status"


pytestmark = pytest.mark.unit


def test_missing_composite_manifest_cannot_create_contract_evidence(tmp_path):
    with patch(
        f"{MODULE}.get_settings", return_value=SimpleNamespace(data_dir=tmp_path)
    ):
        finalize = create_composite_contract_finalizer(
            pipeline_name="composite_assay", manifest_id="missing-parent"
        )
        with pytest.raises(
            RuntimeError, match="Composite contract manifest is missing"
        ):
            finalize("parent-run", False)
    assert not (
        tmp_path / "output/control/run_manifest/missing-parent.contract-evidence.json"
    ).exists()


@pytest.mark.parametrize("archive_root_configured", [False, True])
def test_composite_reporter_archives_parent_identity_in_selected_roots(
    tmp_path, archive_root_configured
):
    settings = SimpleNamespace(
        data_dir=tmp_path / "data",
        archive_root=tmp_path / "archive" if archive_root_configured else None,
        report_root=tmp_path / "reports",
    )
    archived = []
    with (
        patch(f"{MODULE}.get_settings", return_value=settings),
        patch(
            f"{MODULE}.archive_successful_run",
            side_effect=lambda **kw: archived.append(kw),
        ),
    ):
        reporter = create_composite_reporter(
            pipeline_name="composite_assay",
            manifest_id="parent-manifest",
            logger=MagicMock(),
        )
        parent = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="composite_assay",
            run_id="parent-run",
            run_type="composite",
            manifest_id="parent-manifest",
        )
        reporter.archive(parent)
    assert len(archived) == 1
    assert archived[0]["result"] is parent
    assert archived[0]["options"] is None
    assert archived[0]["data_root"] == settings.data_dir
    assert archived[0]["archive_root"] == settings.archive_root
    assert archived[0]["report_root"] == settings.report_root


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


def test_composite_archive_bootstrap_imports_in_fresh_process():
    """Capture/report assembly must not cycle with archive assessment imports."""
    import os
    from pathlib import Path
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[5]
    environment = dict(os.environ, PYTHONPATH=str(root / "src"))
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import bioetl.composition.control_plane_archive; import bioetl.composition.bootstrap.runtime.runtime_basics",
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
