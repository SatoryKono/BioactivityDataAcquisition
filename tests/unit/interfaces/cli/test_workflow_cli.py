# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for declarative workflow CLI commands."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from bioetl.application.services.workflow.workflow_runner_service import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.application.services.workflow.workflow_transform_service import (
    WorkflowTransformExecutionResult,
)
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    ObservabilityBackendEnsureResult,
)
from bioetl.interfaces.cli.main import cli


pytestmark = pytest.mark.unit


def _limit_safe_multi_pipeline_workflow() -> WorkflowConfig:
    """Workflow that stays valid when CLI --limit is applied to every extract.

    Production chembl_core keeps delete_orphans downstream of assay/target
    extracts; stamping --limit onto those steps is rejected by
    reject_delete_orphans_after_limited_extracts (#8989).
    """
    return WorkflowConfig(
        name="chembl_core",
        defaults=WorkflowRunOptionsConfig(run_type="backfill"),
        steps=(
            WorkflowStepConfig(
                step_id="chembl_activity_ingest",
                pipeline_name="chembl_activity",
            ),
            WorkflowStepConfig(
                step_id="chembl_assay_ingest",
                pipeline_name="chembl_assay",
            ),
            WorkflowStepConfig(
                step_id="chembl_target_ingest",
                pipeline_name="chembl_target",
            ),
            TransformStepConfig(
                step_id="summarize_core_extracts",
                transform_name="summarize_upstream_outputs",
                depends_on=(
                    "chembl_activity_ingest",
                    "chembl_assay_ingest",
                    "chembl_target_ingest",
                ),
            ),
        ),
    )


# Mirrors _WORKFLOW_PUBLICATION_METRIC_NAMES (no high-cardinality grouping).
_EXPECTED_WORKFLOW_PUBLICATION_METRIC_NAMES = (
    "bioetl_workflow_expected",
    "bioetl_workflow_pipeline_expected",
    "bioetl_workflow_runs",
    "bioetl_workflow_runs_total",
    "bioetl_workflow_runs_created",
    "bioetl_workflow_current_status",
    "bioetl_workflow_step_events",
    "bioetl_workflow_step_events_total",
    "bioetl_workflow_step_events_created",
    "bioetl_workflow_step_duration_seconds",
    "bioetl_workflow_step_duration_seconds_bucket",
    "bioetl_workflow_step_duration_seconds_count",
    "bioetl_workflow_step_duration_seconds_sum",
    "bioetl_workflow_step_duration_seconds_created",
)


@dataclass
class _FakeWorkflowRunnerService:
    received_config: object | None = None
    received_kwargs: dict[str, object] | None = None
    recorded_expected_pipeline_metrics_config: object | None = None

    def record_expected_pipeline_metrics(self, config: object) -> None:
        self.recorded_expected_pipeline_metrics_config = config

    async def run_workflow(
        self,
        config: object,
        **kwargs: object,
    ) -> WorkflowRunExecutionResult:
        self.received_config = config
        self.received_kwargs = kwargs
        return WorkflowRunExecutionResult(
            workflow_name="chembl_core",
            status="success",
            steps=(
                WorkflowStepExecutionResult(
                    step_id="chembl_activity_ingest",
                    step_kind="pipeline",
                    status="success",
                ),
                WorkflowStepExecutionResult(
                    step_id="chembl_assay_ingest",
                    step_kind="pipeline",
                    status="success",
                ),
                WorkflowStepExecutionResult(
                    step_id="chembl_target_ingest",
                    step_kind="pipeline",
                    status="success",
                ),
                WorkflowStepExecutionResult(
                    step_id="summarize_core_extracts",
                    step_kind="transform",
                    status="success",
                ),
            ),
            workflow_run_id="00000000-0000-0000-0000-000000000111",
            manifest_id="manifest-111",
            execution_fingerprint="fingerprint-111",
        )


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def test_workflow_cli_uses_dedicated_composition_seam_module() -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    source = inspect.getsource(workflow_cmd)

    assert "bioetl.composition.control_plane_runtime" not in source
    assert "_workflow_composition_seams" in source


@pytest.fixture(autouse=True)
def _mock_workflow_observability_backend(monkeypatch: Any) -> None:
    import bioetl.interfaces.cli.commands._workflow_command_runtime as workflow_runtime

    monkeypatch.setattr(
        workflow_runtime,
        "ensure_observability_backend_started",
        lambda **_: ObservabilityBackendEnsureResult(
            status="started",
            health_url="http://127.0.0.1:8000/health",
        ),
        raising=True,
    )


@pytest.fixture(autouse=True)
def _mock_workflow_metrics_publication(monkeypatch: Any) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    monkeypatch.setattr(
        workflow_cmd,
        "ensure_metrics_server_started",
        lambda: True,
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "publish_metrics_safely",
        lambda **_: True,
        raising=True,
    )


def test_workflow_help_lists_run_and_status(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["workflow", "--help"])

    assert result.exit_code == 0
    assert "run" in result.output
    assert "status" in result.output


def test_workflow_status_is_bounded_and_step_oriented(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    class _NoHistoryInspectionService:
        def inspect_latest(self, _name: str) -> None:
            return None

    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_inspection_service",
        lambda: _NoHistoryInspectionService(),
        raising=True,
    )

    result = cli_runner.invoke(cli, ["workflow", "status", "chembl_core"])

    assert result.exit_code == 0
    assert "Workflow Status / chembl_core" in result.output
    assert "history: unavailable" in result.output
    assert "chembl_activity_ingest [pipeline]" in result.output
    assert "summarize_core_extracts [transform]" in result.output


def test_workflow_status_renders_chembl_baseline_topology_without_history(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    class _NoHistoryInspectionService:
        def inspect_latest(self, _name: str) -> None:
            return None

    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_inspection_service",
        lambda: _NoHistoryInspectionService(),
        raising=True,
    )

    result = cli_runner.invoke(cli, ["workflow", "status", "chembl_baseline"])

    assert result.exit_code == 0
    assert "Workflow Status / chembl_baseline" in result.output
    assert "run_chembl_assay [pipeline]" in result.output
    assert "reconcile_assay_target_orphans [transform]" in result.output
    assert (
        "reconcile_assay_target_orphans [transform] transform=reconcile_foreign_keys "
        "depends_on=run_chembl_assay, run_chembl_target"
    ) in result.output
    assert (
        "reconcile_target_assay_orphans [transform] transform=reconcile_foreign_keys "
        "depends_on=reconcile_assay_publication_orphans"
    ) in result.output
    assert (
        "reconcile_publication_assay_orphans [transform] "
        "transform=reconcile_foreign_keys "
        "depends_on=reconcile_target_assay_orphans"
    ) in result.output


def test_workflow_run_dry_run_smoke_uses_canonical_example_without_network(
    cli_runner: CliRunner,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    fake_service = _FakeWorkflowRunnerService()
    cached_bronze_path = tmp_path / "bronze"
    cached_bronze_path.mkdir()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: fake_service,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_core",
            "--dry-run",
            "--only-steps",
            "summarize_core_extracts",
            "--required-persistence-profile",
            "degraded_observable",
            "--use-cached-bronze",
            "--cached-bronze-path",
            str(cached_bronze_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Workflow: chembl_core" in result.output
    assert "Workflow run ID: 00000000-0000-0000-0000-000000000111" in result.output
    assert fake_service.received_config is not None
    config = fake_service.received_config
    step_ids = tuple(step.step_id for step in config.steps)
    assert step_ids == (
        "chembl_activity_ingest",
        "chembl_assay_ingest",
        "chembl_target_ingest",
        "summarize_core_extracts",
    )
    pipeline_steps = [
        step
        for step in config.steps
        if getattr(step, "pipeline_name", None) is not None
    ]
    assert all(
        getattr(step.run_options, "dry_run", None) is True for step in pipeline_steps
    )


def test_workflow_run_accepts_pipeline_style_runtime_overrides(
    cli_runner: CliRunner,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    fake_service = _FakeWorkflowRunnerService()
    input_csv = tmp_path / "ids.csv"
    input_csv.write_text("id\nCHEMBL1\n", encoding="utf-8")
    cached_bronze_path = tmp_path / "bronze"
    cached_bronze_path.mkdir()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: fake_service,
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "load_workflow_config",
        lambda name: _limit_safe_multi_pipeline_workflow(),
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_core",
            "--limit",
            "1000",
            "--start-offset",
            "5",
            "--input-csv",
            str(input_csv),
            "--filter-column",
            "molecule_id",
            "--filter-field",
            "molecule_chembl_id",
            "--vacuum-after-run",
            "--vacuum-retention-days",
            "7",
            "--log-level",
            "DEBUG",
            "--ignore-yaml-filter",
            "--skip-gold",
            "--execution-context",
            "shared",
            "--use-cached-bronze",
            "--cached-bronze-path",
            str(cached_bronze_path),
            "--cached-bronze-date",
            "2026-05-08",
            "--exact-replay",
            "--replay-of-run-id",
            "run-parent-1",
            "--replay-of-manifest-id",
            "manifest-parent-1",
            "--tracing",
            "--debug-export",
            "--debug-export-format",
            "csv",
            "--debug-export-format",
            "xlsx",
            "--debug-export-dir",
            "artifacts/debug_exports",
        ],
    )

    assert result.exit_code == 0, result.output
    assert fake_service.received_config is not None
    config = fake_service.received_config
    pipeline_steps = [
        step
        for step in config.steps
        if getattr(step, "pipeline_name", None) is not None
    ]
    assert pipeline_steps
    assert all(
        getattr(step.run_options, "limit", None) == 1000 for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "start_offset", None) == 5 for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "input_csv", None) == str(input_csv)
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "filter_column", None) == "molecule_id"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "filter_field", None) == "molecule_chembl_id"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "vacuum_after_run", None) is True
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "vacuum_retention_days", None) == 7
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "log_level", None) == "DEBUG"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "ignore_yaml_filter", None) is True
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "skip_gold", None) is True for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "execution_context", None) == "shared"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "use_cached_bronze", None) is True
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "cached_bronze_path", None) == str(cached_bronze_path)
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "cached_bronze_date", None) == "2026-05-08"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "exact_replay", None) is True
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "replay_of_run_id", None) == "run-parent-1"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "replay_of_manifest_id", None) == "manifest-parent-1"
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "enable_tracing", None) is True
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "debug_export_enabled", None) is True
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "debug_export_formats", None) == ("csv", "xlsx")
        for step in pipeline_steps
    )
    assert all(
        getattr(step.run_options, "debug_export_dir", None) == "artifacts/debug_exports"
        for step in pipeline_steps
    )


def test_workflow_run_scopes_delete_orphans_when_limit_follows_extracts(
    cli_runner: CliRunner,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    """CLI limits must scope delete_orphans to this run before execution."""
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    fake_service = _FakeWorkflowRunnerService()
    cached_bronze_path = tmp_path / "bronze"
    cached_bronze_path.mkdir()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: fake_service,
        raising=True,
    )
    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_core",
            "--limit",
            "1000",
            "--required-persistence-profile",
            "degraded_observable",
            "--use-cached-bronze",
            "--cached-bronze-path",
            str(cached_bronze_path),
        ],
    )

    assert result.exit_code == 0, result.output
    received = fake_service.received_config
    assert isinstance(received, WorkflowConfig)
    steps = {step.step_id: step for step in received.steps}
    assert steps["chembl_assay_ingest"].run_options.limit == 1000
    assert steps["chembl_target_ingest"].run_options.limit == 1000
    reconcile = steps["reconcile_assay_target_orphans"]
    assert reconcile.config is not None
    assert reconcile.config["action"] == "delete_orphans"
    assert reconcile.config["source_scope"] == "current_run"


def test_workflow_run_forwards_baseline_resume_repair_steps(
    cli_runner: CliRunner,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    fake_service = _FakeWorkflowRunnerService()
    cached_bronze_path = tmp_path / "bronze"
    cached_bronze_path.mkdir()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: fake_service,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_baseline",
            "--resume-last",
            "--repair-steps",
            "reconcile_assay_target_orphans",
            "--required-persistence-profile",
            "degraded_observable",
            "--use-cached-bronze",
            "--cached-bronze-path",
            str(cached_bronze_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert fake_service.received_kwargs is not None
    assert fake_service.received_kwargs["resume_last"] is True
    assert fake_service.received_kwargs["repair_steps"] == (
        "reconcile_assay_target_orphans",
    )


def test_workflow_run_forwards_occurrence_pinned_resume_selectors(
    cli_runner: CliRunner,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    fake_service = _FakeWorkflowRunnerService()
    cached_bronze_path = tmp_path / "bronze"
    cached_bronze_path.mkdir()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: fake_service,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_core",
            "--resume-manifest-id",
            "manifest-123",
            "--required-persistence-profile",
            "degraded_observable",
            "--use-cached-bronze",
            "--cached-bronze-path",
            str(cached_bronze_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert fake_service.received_kwargs is not None
    assert fake_service.received_kwargs["resume_last"] is False
    assert fake_service.received_kwargs["resume_manifest_id"] == "manifest-123"
    assert fake_service.received_kwargs["resume_run_id"] is None


def test_workflow_run_rejects_conflicting_resume_selectors(
    cli_runner: CliRunner,
) -> None:
    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_core",
            "--resume-last",
            "--resume-manifest-id",
            "manifest-123",
        ],
    )

    assert result.exit_code != 0
    assert "--resume-last cannot be used together with --resume-manifest-id" in (
        result.output
    )


def test_workflow_run_starts_metrics_server_and_publishes_metrics(
    cli_runner: CliRunner,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    fake_service = _FakeWorkflowRunnerService()
    started_calls: list[bool] = []
    published_calls: list[dict[str, object]] = []
    cached_bronze_path = tmp_path / "bronze"
    cached_bronze_path.mkdir()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: fake_service,
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "ensure_metrics_server_started",
        lambda: started_calls.append(True) or True,
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "publish_metrics_safely",
        lambda **kwargs: published_calls.append(kwargs) or True,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_activity",
            "--limit",
            "5",
            "--required-persistence-profile",
            "degraded_observable",
            "--use-cached-bronze",
            "--cached-bronze-path",
            str(cached_bronze_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert started_calls == [True]
    assert published_calls == [
        {
            "run_label": "bioetl",
            "workflow_name": "chembl_activity",
            "pipeline_names": ("chembl_activity",),
            "metric_names": (
                "bioetl_workflow_expected",
                "bioetl_workflow_pipeline_expected",
            ),
        },
        {
            "run_label": "bioetl",
            "workflow_name": "chembl_activity",
            "pipeline_names": ("chembl_activity",),
            "pipeline_name": "chembl_activity",
            "run_type": "backfill",
            "metric_names": _EXPECTED_WORKFLOW_PUBLICATION_METRIC_NAMES,
        },
        {
            "run_label": "bioetl",
            "workflow_name": "chembl_activity",
            "pipeline_names": ("chembl_activity",),
            "pipeline_name": "chembl_activity",
            "run_type": "backfill",
        },
    ]


def test_workflow_run_reports_blocked_destructive_dry_run_step(
    cli_runner: CliRunner,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    class _PreviewWorkflowExecutionService:
        def record_expected_pipeline_metrics(self, config: object) -> None:
            del config

        async def run_workflow(
            self,
            config: object,
            **_: object,
        ) -> WorkflowRunExecutionResult:
            return WorkflowRunExecutionResult(
                workflow_name=getattr(config, "name", "chembl_baseline"),
                status="success",
                steps=(
                    WorkflowStepExecutionResult(
                        step_id="reconcile_assay_target_orphans",
                        step_kind="transform",
                        status="success",
                        payload=WorkflowTransformExecutionResult(
                            step_id="reconcile_assay_target_orphans",
                            transform_name="reconcile_foreign_keys",
                            status="success",
                            fingerprint="fingerprint-preview",
                            output={
                                "dry_run": True,
                                "would_mutate": True,
                                "mutated": False,
                            },
                        ),
                    ),
                ),
                workflow_run_id="00000000-0000-0000-0000-000000000333",
                manifest_id="manifest-333",
                execution_fingerprint="fingerprint-333",
            )

    cached_bronze_path = tmp_path / "bronze"
    cached_bronze_path.mkdir()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: _PreviewWorkflowExecutionService(),
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_baseline",
            "--dry-run",
            "--required-persistence-profile",
            "degraded_observable",
            "--use-cached-bronze",
            "--cached-bronze-path",
            str(cached_bronze_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "dry-run blocked destructive mutation" in result.output


def test_workflow_run_omits_pipeline_grouping_for_multi_pipeline_workflow(
    cli_runner: CliRunner,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    fake_service = _FakeWorkflowRunnerService()
    published_calls: list[dict[str, object]] = []
    cached_bronze_path = tmp_path / "bronze"
    cached_bronze_path.mkdir()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: fake_service,
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "ensure_metrics_server_started",
        lambda: True,
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "publish_metrics_safely",
        lambda **kwargs: published_calls.append(kwargs) or True,
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "load_workflow_config",
        lambda name: _limit_safe_multi_pipeline_workflow(),
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_core",
            "--limit",
            "5",
            "--required-persistence-profile",
            "degraded_observable",
            "--use-cached-bronze",
            "--cached-bronze-path",
            str(cached_bronze_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert published_calls == [
        {
            "run_label": "bioetl",
            "workflow_name": "chembl_core",
            "pipeline_names": ("chembl_activity", "chembl_assay", "chembl_target"),
            "metric_names": (
                "bioetl_workflow_expected",
                "bioetl_workflow_pipeline_expected",
            ),
        },
        {
            "run_label": "bioetl",
            "workflow_name": "chembl_core",
            "pipeline_names": ("chembl_activity", "chembl_assay", "chembl_target"),
            "pipeline_name": None,
            "run_type": None,
            "metric_names": _EXPECTED_WORKFLOW_PUBLICATION_METRIC_NAMES,
        },
    ]


def test_workflow_run_publishes_metrics_even_when_workflow_fails(
    cli_runner: CliRunner,
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd
    from bioetl.interfaces.cli.exit_codes import ExitCode

    class _FailingWorkflowExecutionService:
        def record_expected_pipeline_metrics(self, config: object) -> None:
            del config

        async def run_workflow(
            self,
            config: object,
            **_: object,
        ) -> WorkflowRunExecutionResult:
            return WorkflowRunExecutionResult(
                workflow_name=getattr(config, "name", "chembl_activity"),
                status="failed",
                steps=(
                    WorkflowStepExecutionResult(
                        step_id="run_chembl_activity",
                        step_kind="pipeline",
                        status="failed",
                        error_type="RuntimeError",
                        error_message="boom",
                    ),
                ),
                workflow_run_id="00000000-0000-0000-0000-000000000222",
                manifest_id="manifest-222",
                execution_fingerprint="fingerprint-222",
            )

    published_calls: list[dict[str, object]] = []
    cached_bronze_path = tmp_path / "bronze"
    cached_bronze_path.mkdir()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: _FailingWorkflowExecutionService(),
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "ensure_metrics_server_started",
        lambda: True,
        raising=True,
    )
    monkeypatch.setattr(
        workflow_cmd,
        "publish_metrics_safely",
        lambda **kwargs: published_calls.append(kwargs) or True,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_activity",
            "--required-persistence-profile",
            "degraded_observable",
            "--use-cached-bronze",
            "--cached-bronze-path",
            str(cached_bronze_path),
        ],
    )

    assert result.exit_code == ExitCode.PIPELINE_ERROR
    assert published_calls == [
        {
            "run_label": "bioetl",
            "workflow_name": "chembl_activity",
            "pipeline_names": ("chembl_activity",),
            "metric_names": (
                "bioetl_workflow_expected",
                "bioetl_workflow_pipeline_expected",
            ),
        },
        {
            "run_label": "bioetl",
            "workflow_name": "chembl_activity",
            "pipeline_names": ("chembl_activity",),
            "pipeline_name": "chembl_activity",
            "run_type": "backfill",
            "metric_names": _EXPECTED_WORKFLOW_PUBLICATION_METRIC_NAMES,
        },
        {
            "run_label": "bioetl",
            "workflow_name": "chembl_activity",
            "pipeline_names": ("chembl_activity",),
            "pipeline_name": "chembl_activity",
            "run_type": "backfill",
        },
    ]


def test_workflow_run_rejects_strict_profile_without_cached_bronze(
    cli_runner: CliRunner,
) -> None:
    from bioetl.interfaces.cli.exit_codes import ExitCode

    result = cli_runner.invoke(
        cli,
        ["workflow", "run", "chembl_activity", "--limit", "5"],
    )

    assert result.exit_code == ExitCode.CONFIG_ERROR
    assert "Workflow configuration error" in result.output
    assert "requires immutable snapshot-backed Bronze inputs" in result.output
    assert "--use-cached-bronze" in result.output
    assert "degraded_observable" not in result.output


def test_workflow_run_accepts_explicit_degraded_diagnostic_without_cached_bronze(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    fake_service = _FakeWorkflowRunnerService()
    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: fake_service,
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        [
            "workflow",
            "run",
            "chembl_publication",
            "--limit",
            "5",
            "--required-persistence-profile",
            "degraded_observable",
        ],
    )

    assert result.exit_code == 0, result.output
    assert fake_service.received_config is not None
    step = fake_service.received_config.steps[0]
    assert step.run_options.required_persistence_profile == "degraded_observable"


def test_workflow_status_json_payload_includes_explicit_limits(
    cli_runner: CliRunner,
    monkeypatch: Any,
) -> None:
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    class _NoHistoryInspectionService:
        def inspect_latest(self, _name: str) -> None:
            return None

    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_inspection_service",
        lambda: _NoHistoryInspectionService(),
        raising=True,
    )

    result = cli_runner.invoke(
        cli,
        ["workflow", "status", "chembl_core", "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"execution_history_available": false' in result.output.lower()
    assert '"history_scope": "bounded-static-config"' in result.output


def test_multi_pipeline_push_failure_preserves_success_and_report(
    cli_runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An unreachable backup gateway cannot discard a successful workflow report."""
    import json
    from importlib import import_module
    from structlog.testing import capture_logs
    from bioetl.composition.bootstrap.assembly.metrics_service import (
        create_metrics_service,
    )
    from bioetl.interfaces.cli.commands.domains.health.metrics_publication_integration import (
        publish_metrics_safely,
    )
    import bioetl.interfaces.cli.commands.workflow as workflow_cmd

    report = tmp_path / "workflow-report.json"

    class ReportingService(_FakeWorkflowRunnerService):
        async def run_workflow(
            self, config: object, **kwargs: object
        ) -> WorkflowRunExecutionResult:
            result = await super().run_workflow(config, **kwargs)
            report.write_text(json.dumps({"status": result.status}), encoding="utf-8")
            return result

    attempts: list[dict[str, object]] = []

    def unavailable_gateway(*args: object, **kwargs: object) -> None:
        attempts.append(kwargs)
        raise ConnectionRefusedError("private gateway exception detail")

    monkeypatch.setattr(
        workflow_cmd,
        "get_workflow_execution_service",
        lambda registry=None: ReportingService(),
    )
    monkeypatch.setattr(workflow_cmd, "ensure_metrics_server_started", lambda: True)
    monkeypatch.setattr(workflow_cmd, "publish_metrics_safely", publish_metrics_safely)
    monkeypatch.setattr(
        workflow_cmd,
        "load_workflow_config",
        lambda name: _limit_safe_multi_pipeline_workflow(),
    )
    monkeypatch.setattr(
        import_module("bioetl.composition.observability_runtime"),
        "bootstrap_metrics_service",
        create_metrics_service,
    )
    monkeypatch.setattr(
        import_module("bioetl.infrastructure.observability.server"),
        "push_to_gateway",
        unavailable_gateway,
    )
    from bioetl.composition.bootstrap.runtime.logger_bootstrap import bootstrap_logger

    bootstrap_logger(pipeline="unknown")
    with capture_logs() as logs:
        result = cli_runner.invoke(
            cli,
            [
                "workflow",
                "run",
                "chembl_core",
                "--required-persistence-profile",
                "degraded_observable",
            ],
        )

    assert result.exit_code == 0, result.output
    assert json.loads(report.read_text(encoding="utf-8")) == {"status": "success"}
    failures = [entry for entry in logs if entry["event"] == "push_failed"]
    assert len(failures) == len(attempts) == 2, (logs, result.output)
    for entry in failures:
        assert entry["workflow_name"] == "chembl_core"
        assert entry["pipeline_names"] == (
            "chembl_activity",
            "chembl_assay",
            "chembl_target",
        )
        assert entry["run_type"] is None
        assert entry["gateway_class"] == "http"
        assert entry["error_type"] == "ConnectionRefusedError"
        assert "private gateway exception detail" not in str(entry)
    assert all(attempt["grouping_key"] == {} for attempt in attempts)
