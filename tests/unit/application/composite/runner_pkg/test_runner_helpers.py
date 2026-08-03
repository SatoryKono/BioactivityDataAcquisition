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
"""Unit tests for runner_helpers — pure helper functions for CompositePipelineRunner."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.runner_pkg.runner_helpers import (
    add_not_run_results,
    calculate_had_warnings,
    get_mergeable_dependencies,
    get_mergeable_enrichers,
    log_enrichment_summary,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)


# ---------------------------------------------------------------------------
# Fakes / factories
# ---------------------------------------------------------------------------


def _make_logger() -> MagicMock:
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


def _make_enricher_cfg(
    pipeline: str,
    *,
    required: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(pipeline=pipeline, required=required)


def _make_dependency_cfg(
    pipeline: str,
    *,
    silver_table: str | None = "silver/test",
) -> SimpleNamespace:
    return SimpleNamespace(pipeline=pipeline, silver_table=silver_table)


def _success_enrichment(name: str, records: int = 10) -> EnrichmentResult:
    return EnrichmentResult(
        enricher_name=name,
        status=EnrichmentStatus.SUCCESS,
        records_input=records,
        records_enriched=records,
    )


def _failed_enrichment(name: str) -> EnrichmentResult:
    return EnrichmentResult(
        enricher_name=name,
        status=EnrichmentStatus.FAILED,
        error_message="test failure",
    )


def _timeout_enrichment(name: str) -> EnrichmentResult:
    return EnrichmentResult(
        enricher_name=name,
        status=EnrichmentStatus.TIMEOUT,
        error_message="timed out",
    )


def _skipped_enrichment(name: str) -> EnrichmentResult:
    return EnrichmentResult(enricher_name=name, status=EnrichmentStatus.SKIPPED)


def _not_run_enrichment(name: str) -> EnrichmentResult:
    return EnrichmentResult.not_run(enricher_name=name)


def _success_dep(name: str) -> DependencyResult:
    return DependencyResult(pipeline_name=name, status=DependencyStatus.SUCCESS)


def _failed_dep(name: str) -> DependencyResult:
    return DependencyResult(pipeline_name=name, status=DependencyStatus.FAILED)


def _skipped_dep(name: str) -> DependencyResult:
    return DependencyResult(pipeline_name=name, status=DependencyStatus.SKIPPED)


# ---------------------------------------------------------------------------
# log_enrichment_summary
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_log_enrichment_summary_when_empty_then_no_log_call() -> None:
    logger = _make_logger()
    log_enrichment_summary({}, "my_composite", logger)
    logger.info.assert_not_called()


@pytest.mark.unit
def test_log_enrichment_summary_when_success_then_logs_info() -> None:
    logger = _make_logger()
    results = {"enricher_a": _success_enrichment("enricher_a", records=5)}

    log_enrichment_summary(results, "my_composite", logger)

    logger.info.assert_called_once()
    call_kwargs = logger.info.call_args.kwargs
    assert call_kwargs["total_enrichers"] == 1
    assert call_kwargs["success"] == 1
    assert call_kwargs["failed"] == 0
    assert call_kwargs["total_records_enriched"] == 5


@pytest.mark.unit
def test_log_enrichment_summary_when_mixed_statuses_then_correct_counts() -> None:
    logger = _make_logger()
    results = {
        "enricher_a": _success_enrichment("enricher_a", records=10),
        "enricher_b": _failed_enrichment("enricher_b"),
        "enricher_c": _timeout_enrichment("enricher_c"),
        "enricher_d": _not_run_enrichment("enricher_d"),
    }

    log_enrichment_summary(results, "composite", logger)

    call_kwargs = logger.info.call_args.kwargs
    assert call_kwargs["total_enrichers"] == 4
    assert call_kwargs["success"] == 1
    assert call_kwargs["failed"] == 1
    assert call_kwargs["timeout"] == 1
    assert call_kwargs["not_run"] == 1
    assert "enricher_b" in call_kwargs["failed_enrichers"]
    assert "enricher_d" in call_kwargs["not_run_enrichers"]


@pytest.mark.unit
def test_log_enrichment_summary_when_no_failures_then_failed_enrichers_is_none() -> (
    None
):
    logger = _make_logger()
    results = {"enricher_a": _success_enrichment("enricher_a")}

    log_enrichment_summary(results, "composite", logger)

    call_kwargs = logger.info.call_args.kwargs
    assert call_kwargs["failed_enrichers"] is None


# ---------------------------------------------------------------------------
# calculate_had_warnings
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_calculate_had_warnings_when_no_failures_then_returns_false() -> None:
    logger = _make_logger()
    results = {"req": _success_enrichment("req"), "opt": _success_enrichment("opt")}

    result = calculate_had_warnings(results, frozenset({"req"}), "composite", logger)

    assert result is False
    logger.warning.assert_not_called()


@pytest.mark.unit
def test_calculate_had_warnings_when_optional_failed_then_returns_true() -> None:
    logger = _make_logger()
    results = {"opt": _failed_enrichment("opt")}

    result = calculate_had_warnings(results, frozenset(), "composite", logger)

    assert result is True
    logger.warning.assert_called_once()


@pytest.mark.unit
def test_calculate_had_warnings_when_optional_timeout_then_returns_true() -> None:
    logger = _make_logger()
    results = {"opt": _timeout_enrichment("opt")}

    result = calculate_had_warnings(results, frozenset(), "composite", logger)

    assert result is True


@pytest.mark.unit
def test_calculate_had_warnings_when_required_failed_then_returns_false() -> None:
    """Required enricher failure is not counted as a warning (it should have raised)."""
    logger = _make_logger()
    results = {"req": _failed_enrichment("req")}

    result = calculate_had_warnings(results, frozenset({"req"}), "composite", logger)

    assert result is False
    logger.warning.assert_not_called()


@pytest.mark.unit
def test_calculate_had_warnings_when_empty_results_then_returns_false() -> None:
    logger = _make_logger()

    result = calculate_had_warnings({}, frozenset(), "composite", logger)

    assert result is False


# ---------------------------------------------------------------------------
# add_not_run_results
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_add_not_run_results_when_required_only_false_then_returns_unchanged() -> None:
    logger = _make_logger()
    existing: dict[str, EnrichmentResult] = {}
    all_enrichers = [_make_enricher_cfg("opt_a", required=False)]

    result = add_not_run_results(
        existing,
        enrichers_to_run=[],
        all_enrichers=all_enrichers,
        completed_enrichers=frozenset(),
        required_only=False,
        composite_name="composite",
        logger=logger,
    )

    assert result == {}


@pytest.mark.unit
def test_add_not_run_results_when_optional_skipped_then_adds_not_run_entry() -> None:
    logger = _make_logger()
    existing: dict[str, EnrichmentResult] = {}
    all_enrichers = [
        _make_enricher_cfg("req_a", required=True),
        _make_enricher_cfg("opt_b", required=False),
    ]

    result = add_not_run_results(
        existing,
        enrichers_to_run=[_make_enricher_cfg("req_a", required=True)],
        all_enrichers=all_enrichers,
        completed_enrichers=frozenset(),
        required_only=True,
        composite_name="composite",
        logger=logger,
    )

    assert "opt_b" in result
    assert result["opt_b"].status == EnrichmentStatus.NOT_RUN


@pytest.mark.unit
def test_add_not_run_results_when_optional_already_completed_then_not_added() -> None:
    logger = _make_logger()
    existing: dict[str, EnrichmentResult] = {}
    all_enrichers = [_make_enricher_cfg("opt_a", required=False)]

    result = add_not_run_results(
        existing,
        enrichers_to_run=[],
        all_enrichers=all_enrichers,
        completed_enrichers=frozenset({"opt_a"}),
        required_only=True,
        composite_name="composite",
        logger=logger,
    )

    assert "opt_a" not in result


@pytest.mark.unit
def test_add_not_run_results_when_optional_already_in_results_then_not_overwritten() -> (
    None
):
    logger = _make_logger()
    original_result = _skipped_enrichment("opt_a")
    existing = {"opt_a": original_result}
    all_enrichers = [_make_enricher_cfg("opt_a", required=False)]

    result = add_not_run_results(
        existing,
        enrichers_to_run=[],
        all_enrichers=all_enrichers,
        completed_enrichers=frozenset(),
        required_only=True,
        composite_name="composite",
        logger=logger,
    )

    assert result["opt_a"] is original_result


# ---------------------------------------------------------------------------
# get_mergeable_enrichers
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_mergeable_enrichers_when_success_then_included() -> None:
    logger = _make_logger()
    cfg = _make_enricher_cfg("enricher_a")
    results = {"enricher_a": _success_enrichment("enricher_a")}

    mergeable = get_mergeable_enrichers(results, [cfg], logger)

    assert cfg in mergeable


@pytest.mark.unit
@pytest.mark.parametrize(
    "status",
    [EnrichmentStatus.NOT_RUN, EnrichmentStatus.SKIPPED],
)
def test_get_mergeable_enrichers_when_non_mergeable_status_then_excluded(
    status: EnrichmentStatus,
) -> None:
    logger = _make_logger()
    cfg = _make_enricher_cfg("enricher_a")
    results = {
        "enricher_a": EnrichmentResult(enricher_name="enricher_a", status=status)
    }

    mergeable = get_mergeable_enrichers(results, [cfg], logger)

    assert cfg not in mergeable
    logger.debug.assert_called_once()


@pytest.mark.unit
def test_get_mergeable_enrichers_when_no_result_then_excluded() -> None:
    logger = _make_logger()
    cfg = _make_enricher_cfg("enricher_a")

    mergeable = get_mergeable_enrichers({}, [cfg], logger)

    assert len(mergeable) == 0


@pytest.mark.unit
def test_get_mergeable_enrichers_when_failed_then_included() -> None:
    """FAILED enrichers still have partial data worth attempting to merge."""
    logger = _make_logger()
    cfg = _make_enricher_cfg("enricher_a")
    results = {"enricher_a": _failed_enrichment("enricher_a")}

    mergeable = get_mergeable_enrichers(results, [cfg], logger)

    assert cfg in mergeable


# ---------------------------------------------------------------------------
# get_mergeable_dependencies
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_mergeable_dependencies_when_success_and_silver_table_then_included() -> (
    None
):
    logger = _make_logger()
    cfg = _make_dependency_cfg("dep_a", silver_table="silver/dep_a")
    results = {"dep_a": _success_dep("dep_a")}

    mergeable = get_mergeable_dependencies(results, [cfg], logger)

    assert cfg in mergeable


@pytest.mark.unit
def test_get_mergeable_dependencies_when_skipped_then_included() -> None:
    """SKIPPED (resumed) dependency already has data in Silver — must be merged."""
    logger = _make_logger()
    cfg = _make_dependency_cfg("dep_a", silver_table="silver/dep_a")
    results = {"dep_a": _skipped_dep("dep_a")}

    mergeable = get_mergeable_dependencies(results, [cfg], logger)

    assert cfg in mergeable


@pytest.mark.unit
def test_get_mergeable_dependencies_when_no_result_then_excluded() -> None:
    logger = _make_logger()
    cfg = _make_dependency_cfg("dep_a")

    mergeable = get_mergeable_dependencies({}, [cfg], logger)

    assert len(mergeable) == 0
    logger.debug.assert_called_once()


@pytest.mark.unit
def test_get_mergeable_dependencies_when_no_silver_table_then_excluded() -> None:
    logger = _make_logger()
    cfg = _make_dependency_cfg("dep_a", silver_table=None)
    results = {"dep_a": _success_dep("dep_a")}

    mergeable = get_mergeable_dependencies(results, [cfg], logger)

    assert len(mergeable) == 0


@pytest.mark.unit
def test_get_mergeable_dependencies_when_failed_then_excluded() -> None:
    logger = _make_logger()
    cfg = _make_dependency_cfg("dep_a", silver_table="silver/dep_a")
    results = {"dep_a": _failed_dep("dep_a")}

    mergeable = get_mergeable_dependencies(results, [cfg], logger)

    assert cfg not in mergeable


@pytest.mark.unit
def test_get_mergeable_dependencies_when_mixed_then_only_eligible_included() -> None:
    logger = _make_logger()
    cfg_success = _make_dependency_cfg("dep_a", silver_table="silver/dep_a")
    cfg_failed = _make_dependency_cfg("dep_b", silver_table="silver/dep_b")
    cfg_skipped = _make_dependency_cfg("dep_c", silver_table="silver/dep_c")
    results = {
        "dep_a": _success_dep("dep_a"),
        "dep_b": _failed_dep("dep_b"),
        "dep_c": _skipped_dep("dep_c"),
    }

    mergeable = get_mergeable_dependencies(
        results,
        [cfg_success, cfg_failed, cfg_skipped],
        logger,
    )

    assert cfg_success in mergeable
    assert cfg_skipped in mergeable
    assert cfg_failed not in mergeable
