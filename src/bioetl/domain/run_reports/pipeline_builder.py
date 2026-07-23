"""Build pipeline_run_report_v1 from accounting + run metrics."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.models import (
    BalanceStatus,
    LayerCounts,
    PipelineRunReport,
    StageFunnelRow,
    TrackingCoverage,
)
from bioetl.domain.run_reports.reason_catalog import default_reason_catalog


def _status_from_layers(layers: LayerCounts) -> tuple[BalanceStatus, BalanceStatus, int, int]:
    silver_delta = layers.bronze_records - layers.silver_accounted
    gold_delta = layers.silver_valid - layers.gold_accounted

    def _status(delta: int, baseline: int) -> BalanceStatus:
        if baseline == 0 and delta == 0:
            return BalanceStatus.OK
        if delta == 0:
            return BalanceStatus.OK
        if abs(delta) <= max(1, baseline // 100):
            return BalanceStatus.DEGRADED
        return BalanceStatus.FAILING

    return (
        _status(silver_delta, layers.bronze_records),
        _status(gold_delta, layers.silver_valid),
        silver_delta,
        gold_delta,
    )


def build_pipeline_run_report(
    *,
    identity: Mapping[str, Any],  # Any: report/json payload shape is dynamic
    metrics: Mapping[str, int],
    accounting: StageAccountingAccumulator | None = None,
    artifacts: tuple[dict[str, Any], ...] = (),  # Any: report/json payload shape is dynamic
    reason_catalog_version: str | None = None,
) -> PipelineRunReport:
    """Project a deterministic pipeline run report.

    When ``accounting`` is None, report is built from coarse metrics only
    (tracking_coverage=partial, reason maps empty unless metrics encode totals).
    """
    acc = accounting or StageAccountingAccumulator()
    metrics_map = {str(key): int(value) for key, value in metrics.items()}
    acc.apply_layer_totals(
        bronze=metrics_map.get("records_bronze", 0),
        silver_valid=metrics_map.get("records_silver", 0),
        gold_written=metrics_map.get("records_gold", 0),
        records_fetched=metrics_map.get("records_fetched", 0),
    )
    layers = acc.snapshot_layers_from_metrics(metrics_map)
    funnel = acc.snapshot_funnel(layers)
    return PipelineRunReport(
        identity=dict(identity),
        funnel=funnel,
        layers=layers,
        reasons_top_n=_resolve_top_reasons(acc, layers),
        reconciliation=_build_reconciliation(layers),
        tracking_coverage=_resolve_tracking(acc, funnel, accounting),
        reason_catalog_version=_resolve_catalog_version(
            acc,
            accounting,
            reason_catalog_version,
        ),
        artifacts=artifacts,
    )


def _resolve_tracking(
    accumulator: StageAccountingAccumulator,
    funnel: tuple[StageFunnelRow, ...],
    accounting: StageAccountingAccumulator | None,
) -> TrackingCoverage:
    if accounting is None:
        return TrackingCoverage.PARTIAL
    return accumulator.overall_tracking_coverage(funnel)


def _build_reconciliation(layers: LayerCounts) -> dict[str, Any]:  # Any: report/json payload shape is dynamic
    silver_status, gold_status, silver_delta, gold_delta = _status_from_layers(layers)
    return {
        "silver_vs_bronze_status": silver_status.value,
        "gold_vs_silver_status": gold_status.value,
        "silver_accounted": layers.silver_accounted,
        "gold_accounted": layers.gold_accounted,
        "silver_delta": silver_delta,
        "gold_delta": gold_delta,
    }


def _resolve_catalog_version(
    accumulator: StageAccountingAccumulator,
    accounting: StageAccountingAccumulator | None,
    override: str | None,
) -> str:
    if override is not None:
        return override
    if accounting is not None:
        return accumulator.reason_catalog_version
    return default_reason_catalog().version


def _resolve_top_reasons(
    accumulator: StageAccountingAccumulator,
    layers: LayerCounts,
) -> tuple[dict[str, Any], ...]:  # Any: report/json payload shape is dynamic
    recorded = accumulator.top_reasons()
    if recorded:
        return recorded
    candidates = (
        (
            layers.silver_filtered_out,
            "FILTERED_OUT_SILVER",
            "filtered_out",
            "structural",
        ),
        (
            layers.silver_quarantined,
            "SCHEMA_VALIDATION_FAILURE",
            "quarantined",
            "dq",
        ),
        (
            layers.gold_excluded_by_contract,
            "gold_contract_schema_failure",
            "excluded_by_contract",
            "contract",
        ),
    )
    return tuple(
        {
            "reason_code": code,
            "outcome": outcome,
            "reason_family": family,
            "count": count,
        }
        for count, code, outcome, family in candidates
        if count > 0
    )
