"""Architecture test: no new datetime.now() / datetime.now(UTC) in test code.

This is the test-side counterpart of test_no_datetime_now_in_infrastructure.py.
Tests should use deterministic timestamps via ``tests.helpers.clock.FixedClock``
or ``tests.helpers.clock.StepClock`` (or plain ``datetime(...)`` constants)
instead of calling ``datetime.now()``.

The ALLOWED_PATHS set acts as a ratchet: every file listed here is a known
legacy consumer.  The set should only shrink over time — new test files must
NOT be added.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture.datetime_now_policy_support import (
    assert_allowed_paths_exist,
    collect_datetime_now_calls,
    collect_datetime_policy_violations,
    find_stale_datetime_exemptions,
)

TESTS_DIR = Path("tests")

# Paths relative to ``tests/`` that are allowed to use datetime.now().
# This allowlist should shrink over time as files are migrated to FixedClock /
# StepClock or fixed datetime constants.
ALLOWED_PATHS: set[str] = {
    "benchmarks/test_bronze_write.py",
    "benchmarks/test_delta_write.py",
    "e2e/test_advanced_scenarios_e2e.py",
    "e2e/test_checkpoint_e2e.py",
    "e2e/test_gold_layer_e2e.py",
    "e2e/test_resilience_scenarios_e2e.py",
    "fakes/quarantine_fake.py",
    "integration/infrastructure/storage/test_metadata_integration.py",
    "integration/interfaces/test_cli_run_manifest.py",
    "integration/test_cross_provider_doi_normalization.py",
    "integration/test_dq_monitor_integration.py",
    "integration/test_dq_report_integration.py",
    "integration/test_runner_lifecycle.py",
    "performance/test_batching_performance.py",
    "smoke/test_control_plane_rollout_smoke.py",
    "unit/application/composite/runner_test_support.py",
    "unit/application/composite/test_checkpoint.py",
    "unit/application/composite/test_dependency_result_mapper.py",
    "unit/application/composite/test_fsm_pipeline_scenarios.py",
    "unit/application/composite/test_merger_post_join.py",
    "unit/application/composite/test_runner.py",
    "unit/application/composite/test_runner_checkpoint_resume.py",
    "unit/application/composite/test_runner_fsm.py",
    "unit/application/composite/test_runner_required_flag.py",
    "unit/application/composite/test_runner_robustness.py",
    "unit/application/core/test_batch_writer.py",
    "unit/application/core/test_batch_writer_io_mixin.py",
    "unit/application/core/test_dq_report_integration.py",
    "unit/application/core/test_postrun_metadata_write_service.py",
    "unit/application/core/test_postrun_metadata_writes.py",
    "unit/application/core/test_postrun_service.py",
    "unit/application/core/test_protocols.py",
    "unit/application/core/test_quarantine_manager.py",
    "unit/application/core/test_runner_execution_flow.py",
    "unit/application/pipelines/common/test_base_publication_transformer.py",
    "unit/application/pipelines/crossref/test_crossref_transformer.py",
    "unit/application/pipelines/openalex/test_transformer.py",
    "unit/application/services/dq/test_bronze_analyzer.py",
    "unit/application/services/dq/test_gold_analyzer.py",
    "unit/application/services/dq/test_gold_analyzer_extended.py",
    "unit/application/services/dq/test_logical_validation.py",
    "unit/application/services/dq/test_structural_validation.py",
    "unit/application/services/test_bronze_cleanup_service.py",
    "unit/application/services/test_data_quality_service.py",
    "unit/application/services/test_dq_report_generation_mixin.py",
    "unit/application/services/test_dq_report_service.py",
    "unit/application/services/test_dq_report_service_coverage.py",
    "unit/application/services/test_health_service.py",
    "unit/application/services/test_lineage_inspection_service.py",
    "unit/application/services/test_metadata_coordinator_governance.py",
    "unit/application/services/test_metadata_lineage_node_builders.py",
    "unit/application/services/test_metrics_service.py",
    "unit/application/services/test_quarantine_service.py",
    "unit/application/services/test_run_ledger_service.py",
    "unit/application/services/test_run_manifest_diagnostics.py",
    "unit/composition/factories/pipeline/test_checkpoint_metadata_helpers.py",
    "unit/domain/models/test_metadata_output.py",
    "unit/domain/ports/test_noop_audit.py",
    "unit/domain/ports/test_port_dtos.py",
    "unit/domain/ports/test_protocol_stubs.py",
    "unit/domain/schemas/chembl/test_schemas.py",
    "unit/domain/schemas/common/test_publication_base.py",
    "unit/domain/schemas/openalex/test_publication_schema.py",
    "unit/domain/schemas/test_year_validation.py",
    "unit/domain/services/test_merged_metadata_explainability.py",
    "unit/domain/test_contract_identity.py",
    "unit/domain/test_entities.py",
    "unit/domain/test_pipeline_context.py",
    "unit/domain/value_objects/test_dq_result.py",
    "unit/domain/value_objects/test_run_context.py",
    "unit/infrastructure/adapters/common/test_api_request_collector.py",
    "unit/infrastructure/audit/test_file_audit.py",
    "unit/infrastructure/control_plane/test_control_plane_observability_metrics.py",
    "unit/infrastructure/control_plane/test_file_lineage_store.py",
    "unit/infrastructure/control_plane/test_file_run_manifest_store.py",
    "unit/infrastructure/export/test_dq_report_writer.py",
    "unit/infrastructure/factories/test_factories.py",
    "unit/infrastructure/observability/test_zscore_detector.py",
    "unit/infrastructure/quarantine/test_unified_quarantine_security.py",
    "unit/infrastructure/storage/_lineage_fragment_helpers.py",
    "unit/infrastructure/storage/silver_writer/conftest.py",
    "unit/infrastructure/storage/silver_writer/test_silver_writer_core.py",
    "unit/infrastructure/storage/test_gold_writer_integration.py",
    "unit/infrastructure/storage/test_gold_writer_metadata_operations.py",
    "unit/infrastructure/storage/test_noop_metadata_writer.py",
    "unit/infrastructure/test_observability.py",
    "unit/infrastructure/test_storage.py",
    "unit/infrastructure/time/test_system_clock.py",
    "unit/interfaces/cli/commands/test_lineage_commands.py",
    "unit/interfaces/cli/commands/test_run_manifest_commands.py",
    "unit/interfaces/cli/test_run_all_service_mock.py",
}


def _tests_base() -> Path:
    """Resolve tests base path from either repo root or tests cwd."""
    if TESTS_DIR.exists():
        return TESTS_DIR
    return Path(__file__).parent.parent


def _relative_test_path(py_file: Path) -> str:
    """Return tests-relative POSIX path for stable allowlist matching."""
    return py_file.relative_to(_tests_base()).as_posix()


def _datetime_now_calls(py_file: Path) -> list[str]:
    """Collect datetime.now()/utcnow() calls for a Python file."""
    return collect_datetime_now_calls(
        py_file,
        relative_path=_relative_test_path(py_file),
        tolerate_syntax_error=True,
    )


class TestNoDatetimeNowInTests:
    """Tests ensuring test code uses deterministic timestamps."""

    @pytest.fixture
    def test_python_files(self) -> list[Path]:
        """Get all Python files under tests/, excluding architecture tests."""
        base = _tests_base()
        arch = base / "architecture"
        return [
            py_file
            for py_file in sorted(base.rglob("*.py"))
            if not py_file.is_relative_to(arch)
        ]

    def test_no_datetime_now_in_tests(self, test_python_files: list[Path]) -> None:
        """Test code MUST NOT introduce new datetime.now() / datetime.now(UTC) calls.

        Use ``tests.helpers.clock.FixedClock`` or ``tests.helpers.clock.StepClock``
        for deterministic timestamps, or plain ``datetime(2025, 1, 1, ...)`` constants.
        """
        violations = collect_datetime_policy_violations(
            py_files=test_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_test_path,
            tolerate_syntax_error=True,
        )

        assert not violations, (
            "datetime.now()/utcnow() found in test code:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nUse tests.helpers.clock.FixedClock / StepClock or fixed "
            "datetime constants instead. See tests/helpers/clock.py."
        )

    def test_allowed_paths_still_exist(self, test_python_files: list[Path]) -> None:
        """Verify allowlisted paths still exist — remove stale entries."""
        assert_allowed_paths_exist(
            py_files=test_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_test_path,
        )

    def test_allowed_paths_still_require_exception(
        self, test_python_files: list[Path]
    ) -> None:
        """Force removal of allowlist entries once datetime usage is refactored away."""
        stale_exemptions = find_stale_datetime_exemptions(
            py_files=test_python_files,
            allowed_paths=ALLOWED_PATHS,
            relative_path_fn=_relative_test_path,
            tolerate_syntax_error=True,
        )

        assert not stale_exemptions, (
            "Remove stale datetime exceptions that no longer need allowlisting: "
            f"{stale_exemptions}"
        )
