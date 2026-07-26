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


def _optional_mapping(
    value: Mapping[str, Any] | None,  # Any: dynamic optional report block
) -> dict[str, Any] | None:  # Any: copied dynamic report block
    """Copy an optional dynamic mapping without leaking caller mutation."""
    return dict(value) if value else None


def _status_from_layers(
    layers: LayerCounts,
) -> tuple[BalanceStatus, BalanceStatus, int, int]:
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
    artifacts: tuple[
        dict[str, Any], ...  # Any: dynamic artifact payload
    ] = (),  # Any: report/json payload shape is dynamic
    reason_catalog_version: str | None = None,
    failure: Mapping[str, Any] | None = None,  # Any: optional failure block
    io: Mapping[str, Any] | None = None,  # Any: optional IO summary
    quarantine: Mapping[str, Any] | None = None,  # Any: optional quarantine
    dq_summary: Mapping[str, Any] | None = None,  # Any: optional DQ
    contract_summary: Mapping[str, Any] | None = None,  # Any: optional contract
    schema_versions: Mapping[str, Any] | None = None,  # Any: optional fingerprints
    stage_timings: Mapping[str, Any] | None = None,  # Any: optional timings
    http_summary: Mapping[str, Any] | None = None,  # Any: optional HTTP
    performance: Mapping[str, Any] | None = None,  # Any: optional throughput
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
    reasons = _resolve_top_reasons(acc, layers)
    resolved_contract = _resolve_contract_summary(contract_summary, reasons, layers)
    resolved_performance = _resolve_performance(
        performance=performance,
        identity=identity,
        metrics_map=metrics_map,
        stage_timings=stage_timings,
    )
    return PipelineRunReport(
        identity=dict(identity),
        funnel=funnel,
        layers=layers,
        reasons_top_n=reasons,
        reconciliation=_build_reconciliation(layers),
        tracking_coverage=_resolve_tracking(acc, funnel, accounting),
        reason_catalog_version=_resolve_catalog_version(
            acc,
            accounting,
            reason_catalog_version,
        ),
        artifacts=artifacts,
        failure=_optional_mapping(failure),
        io=_optional_mapping(io),
        quarantine=_optional_mapping(quarantine),
        dq_summary=_optional_mapping(dq_summary),
        contract_summary=resolved_contract,
        schema_versions=_optional_mapping(schema_versions),
        stage_timings=_optional_mapping(stage_timings),
        http_summary=_optional_mapping(http_summary),
        performance=resolved_performance,
    )


def _resolve_contract_summary(
    contract_summary: Mapping[str, Any] | None,  # Any: optional contract
    reasons: tuple[dict[str, Any], ...],  # Any: reasons payload
    layers: LayerCounts,
) -> dict[str, Any] | None:  # Any: optional contract
    if contract_summary is not None:
        return dict(contract_summary)
    excluded = layers.gold_excluded_by_contract
    contract_reasons = [dict(item) for item in reasons if _is_contract_reason(item)]
    if not _has_contract_activity(excluded, contract_reasons):
        return None
    return {
        "gold_excluded_by_contract": excluded,
        "reasons": contract_reasons,
    }


def _is_contract_reason(
    item: Mapping[str, Any],  # Any: dynamic reason payload
) -> bool:
    return (
        item.get("reason_family") == "contract"
        or item.get("outcome") == "excluded_by_contract"
    )


def _has_contract_activity(
    excluded: int,
    contract_reasons: list[dict[str, Any]],  # Any: dynamic reason payload
) -> bool:
    return excluded > 0 or bool(contract_reasons)


def _resolve_performance(
    *,
    performance: Mapping[str, Any] | None,  # Any: optional performance payload
    identity: Mapping[str, Any],  # Any: dynamic report identity payload
    metrics_map: Mapping[str, int],
    stage_timings: Mapping[str, Any] | None,  # Any: optional timing payload
) -> dict[str, Any] | None:  # Any: dynamic performance payload
    if performance:
        return dict(performance)
    return _derive_performance(
        identity=identity,
        metrics_map=metrics_map,
        stage_timings=stage_timings,
    )


def _derive_performance(
    *,
    identity: Mapping[str, Any],  # Any: identity payload
    metrics_map: Mapping[str, int],
    stage_timings: Mapping[str, Any] | None,  # Any: optional timings
) -> dict[str, Any] | None:  # Any: optional performance
    duration = identity.get("duration_seconds")
    if not isinstance(duration, (int, float)) or duration <= 0:
        return None
    fetched = int(metrics_map.get("records_fetched", 0) or 0)
    payload: dict[str, Any] = {  # Any: optional performance
        "duration_seconds": float(duration),
        "records_per_second": _records_per_second(fetched, float(duration)),
    }
    if stage_timings:
        payload["stage_timings_present"] = True
    return payload


def _records_per_second(fetched: int, duration: float) -> float | None:
    if fetched == 0:
        return None
    return round(fetched / duration, 4)


def _resolve_tracking(
    accumulator: StageAccountingAccumulator,
    funnel: tuple[StageFunnelRow, ...],
    accounting: StageAccountingAccumulator | None,
) -> TrackingCoverage:
    if accounting is None:
        return TrackingCoverage.PARTIAL
    return accumulator.overall_tracking_coverage(funnel)


def _build_reconciliation(
    layers: LayerCounts,
) -> dict[str, Any]:  # Any: report/json payload shape is dynamic
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
