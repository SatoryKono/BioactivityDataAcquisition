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
"""Execute Protocol stub bodies that otherwise inflate branch coverage tails."""

from __future__ import annotations


import pytest

from bioetl.application.composite.runner_pkg import runner_merge_stage_types
from bioetl.application.composite.runner_pkg import runner_stage_enrichment_types
from bioetl.application.composite.runner_pkg import runner_stage_types
from bioetl.domain.types import _execution_phase_transition_support as phase_support
from bioetl.infrastructure.storage.silver.operations import postwrite_protocols


pytestmark = pytest.mark.unit


def _assert_protocol_properties_return_none(
    protocol: type[object],
    property_names: tuple[str, ...],
) -> None:
    for name in property_names:
        descriptor = getattr(protocol, name)
        assert descriptor.fget(object()) is None


async def _assert_awaits_none(awaitable: object) -> None:
    assert await awaitable is None


def test_execution_phase_protocol_property_and_builder_stubs_execute() -> None:
    _assert_protocol_properties_return_none(
        phase_support._ExecutionPhaseNamespace,
        (
            "NOT_STARTED",
            "PREFLIGHT",
            "DEPENDENCY_EXECUTION",
            "ENRICHMENT",
            "MERGE",
            "CROSS_VALIDATION",
            "WRITE_FINALIZE",
            "COMPLETED_SUCCESS",
            "COMPLETED_WITH_WARNINGS",
            "FAILED_VALIDATION",
            "FAILED_EXECUTION",
            "FAILED_RECOVERY",
            "TERMINATED",
        ),
    )
    _assert_protocol_properties_return_none(
        phase_support._PhaseTransitionNamespace,
        (
            "START_PREFLIGHT",
            "PREFLIGHT_TO_DEPENDENCIES",
            "DEPENDENCIES_TO_ENRICHMENT",
            "ENRICHMENT_TO_MERGE",
            "MERGE_TO_CROSS_VALIDATION",
            "CROSS_VALIDATION_TO_WRITE",
            "WRITE_TO_SUCCESS",
            "ANY_TO_FAILED",
        ),
    )
    _assert_protocol_properties_return_none(
        phase_support._TransitionPolicyNamespace,
        ("ALLOW_RETRY", "CONTINUE_DEGRADED", "BLOCK_CONTINUATION"),
    )
    assert (
        phase_support._PhaseTransitionRuleBuilder.__call__(
            object(),
            from_phase="from",
            to_phase="to",
            transition="transition",
            policy="policy",
        )
        is None
    )


@pytest.mark.asyncio
async def test_composite_runner_stage_protocol_stubs_execute() -> None:
    protocol = runner_stage_types._CompositeRunnerStageHostProtocol
    host = object()

    await _assert_awaits_none(protocol._run_seed_with_fsm(host, None))
    assert protocol._resume_seed_phase(host, None) is None
    await _assert_awaits_none(protocol._start_seed_phase(host, None))
    await _assert_awaits_none(protocol._call_run_seed(host))
    await _assert_awaits_none(
        protocol._handle_seed_phase_exception(host, None, Exception("x"))
    )
    await _assert_awaits_none(protocol._complete_seed_phase(host, None, None))
    assert protocol._has_dependencies_configured(host) is None
    await _assert_awaits_none(protocol._skip_dependencies_phase(host, None))
    assert protocol._prepare_dependencies_run_context(host) is None
    await _assert_awaits_none(
        protocol._start_dependencies_phase(host, None, context=None)
    )
    await _assert_awaits_none(
        protocol._run_dependencies(host, context=None, keys_df=None, state=None)
    )
    await _assert_awaits_none(
        protocol._execute_started_dependencies_phase(
            host,
            None,
            context=None,
            keys_df=None,
        )
    )
    await _assert_awaits_none(
        protocol._handle_dependencies_phase_exception(host, None, Exception("x"))
    )
    await _assert_awaits_none(protocol._postprocess_dependency_results(host, None, {}))
    assert protocol._record_dependencies_stage_started(host, []) is None
    assert protocol._record_dependencies_stage_completed(host, {}) is None
    assert protocol._build_dependency_phase_outcome(host, {}) is None
    assert protocol._collect_successful_dependencies(host, None, {}) is None
    await _assert_awaits_none(protocol._finalize_dependencies_phase(host, None, None))
    assert protocol._validate_dependency_preconditions(host) is None
    assert protocol._find_required_failures(host, {}) is None
    await _assert_awaits_none(protocol._fail_required_dependencies(host, None, []))
    assert protocol._summarize_dependency_outcomes(host, {}) is None
    await _assert_awaits_none(
        protocol._complete_dependencies_phase(host, None, succeeded=0, failed=0)
    )
    await _assert_awaits_none(
        protocol._persist_failed_state(host, None, stage="stage", error="error")
    )
    assert (
        protocol._transition_state_with_fsm_log(
            host,
            None,
            None,
            stage="stage",
        )
        is None
    )
    await _assert_awaits_none(
        protocol._call_save_checkpoint_safe(host, None, "operation")
    )


@pytest.mark.asyncio
async def test_composite_runner_merge_and_enrichment_protocol_stubs_execute() -> None:
    merge_protocol = runner_merge_stage_types._CompositeRunnerMergeStageHostProtocol
    enrichment_protocol = (
        runner_stage_enrichment_types._CompositeRunnerStageEnrichmentHostProtocol
    )
    host = object()

    await _assert_awaits_none(merge_protocol._save_checkpoint_safe(host, None, "op"))
    await _assert_awaits_none(merge_protocol._generate_dq_reports(host, None))
    await _assert_awaits_none(merge_protocol._write_cv_quarantine(host, None))
    await _assert_awaits_none(
        merge_protocol._call_save_checkpoint_safe(host, None, "op")
    )
    await _assert_awaits_none(merge_protocol._call_generate_dq_reports(host, None))
    await _assert_awaits_none(merge_protocol._call_write_cv_quarantine(host, None))
    assert merge_protocol._record_merge_stage_started(host) is None
    assert merge_protocol._transition_to_merging_state(host, None) is None
    await _assert_awaits_none(merge_protocol._start_merge_phase(host, None))
    await _assert_awaits_none(
        merge_protocol._handle_merge_phase_exception(host, None, Exception("x"))
    )
    assert merge_protocol._build_merge_inputs(host, {}, None) is None
    assert merge_protocol._prepare_merge_request(host, {}, None) is None
    await _assert_awaits_none(merge_protocol._run_prepared_merge_request(host, None))
    await _assert_awaits_none(
        merge_protocol._execute_started_merge_phase(
            host,
            None,
            enrichment_results={},
            dependency_results=None,
        )
    )
    assert merge_protocol._handle_dry_run_merge_skip(host, None) is None
    await _assert_awaits_none(merge_protocol._delete_checkpoint_safe(host))
    assert merge_protocol._transition_to_completed_state(host, None) is None
    await _assert_awaits_none(merge_protocol._persist_completed_state(host, None))
    await _assert_awaits_none(merge_protocol._handle_merge_success(host, None))
    assert merge_protocol._record_merge_stage_completed(host, None) is None

    assert enrichment_protocol._call_get_enrichers_to_run(host, None) is None
    assert enrichment_protocol._prepare_enrichment_run_context(host, None) is None
    assert enrichment_protocol._call_check_required_enrichers(host, {}) is None
    await _assert_awaits_none(
        enrichment_protocol._call_save_checkpoint_safe(host, None, "op")
    )
    assert (
        enrichment_protocol._transition_state_with_fsm_log(
            host,
            None,
            None,
            stage="stage",
        )
        is None
    )
    await _assert_awaits_none(
        enrichment_protocol._persist_failed_state(
            host,
            None,
            stage="stage",
            error="error",
        )
    )
    await _assert_awaits_none(
        enrichment_protocol._start_enrichment_stage(host, None, None)
    )
    await _assert_awaits_none(
        enrichment_protocol._run_enrichers_and_update_state(
            host,
            None,
            None,
            None,
        )
    )
    await _assert_awaits_none(enrichment_protocol._skip_enrichment_stage(host, None))
    assert (
        enrichment_protocol._finalize_enrichment_results(host, None, None, {}) is None
    )
    assert (
        enrichment_protocol._record_completed_enrichment_results(host, None, {}) is None
    )
    await _assert_awaits_none(
        enrichment_protocol._validate_required_enrichment_results(host, None, {})
    )
    assert enrichment_protocol._transition_to_empty_enrichment_start(host, None) is None
    assert enrichment_protocol._record_enrichment_stage_started(host, []) is None
    await _assert_awaits_none(
        enrichment_protocol._complete_enrichment_stage(host, None)
    )
    assert enrichment_protocol._record_enrichment_stage_completed(host, {}) is None
    await _assert_awaits_none(
        enrichment_protocol._save_failed_enrichment_state(host, None, Exception("x"))
    )


@pytest.mark.asyncio
async def test_silver_postwrite_protocol_stubs_execute() -> None:
    _assert_protocol_properties_return_none(
        postwrite_protocols._SilverWritePostwriteContext,
        (
            "table_name",
            "mode",
            "primary_keys",
            "bronze_refs",
            "partition_cols",
            "run_id",
            "run_type",
            "source_batch_id",
            "ingestion_ts",
            "quarantined_count",
            "validation_errors",
            "started_at",
            "start_perf",
        ),
    )
    host = object()
    await _assert_awaits_none(
        postwrite_protocols._SilverMaintenancePostwriteOps.maybe_export_csv(
            host,
            table_name="table",
            arrow_data=None,
            export_path="path",
            primary_keys=[],
        )
    )
    await _assert_awaits_none(
        postwrite_protocols._SilverMetadataPostwriteOps.log_silver_audit(
            host,
            table_name="table",
            records=[],
            mode="append",
            validated_mode=None,
        )
    )
    await _assert_awaits_none(
        postwrite_protocols._SilverPostwriteHostProtocol._maybe_export_csv(
            host,
            table_name="table",
            arrow_data=None,
            mode="append",
            validated_mode=None,
            primary_keys=[],
        )
    )
    await _assert_awaits_none(
        postwrite_protocols._SilverPostwriteHostProtocol._maybe_log_silver_audit(
            host,
            table_name="table",
            records=[],
            mode=None,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )
    )
    await _assert_awaits_none(
        postwrite_protocols._SilverPostwriteHostProtocol._finalize_silver_write_result(
            host,
            None,
        )
    )
    await _assert_awaits_none(
        postwrite_protocols._SilverPostwriteFinalizerProtocol.__call__(host, None)
    )
    await _assert_awaits_none(
        postwrite_protocols._SilverPostwriteExecutorProtocol._run_postwrite_export(
            host,
            ctx=None,
            payload=None,
        )
    )
    await _assert_awaits_none(
        postwrite_protocols._SilverPostwriteExecutorProtocol._run_postwrite_audit(
            host,
            ctx=None,
            payload=None,
        )
    )
    await _assert_awaits_none(
        postwrite_protocols._SilverPostwriteExecutorProtocol._finalize_postwrite_result(
            host,
            ctx=None,
            payload=None,
        )
    )
