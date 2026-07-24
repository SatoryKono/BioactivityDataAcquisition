"""Value objects for pipeline and workflow run reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


def _copy_present_attributes(
    payload: dict[str, Any],  # Any: dynamic report serialization payload
    source: object,
    names: tuple[str, ...],
) -> None:
    """Copy non-null attributes into a dynamic report payload."""
    for name in names:
        value = getattr(source, name)
        if value is not None:
            payload[name] = value


def _copy_present_mappings(
    payload: dict[str, Any],  # Any: dynamic report serialization payload
    source: object,
    names: tuple[str, ...],
) -> None:
    """Copy non-null mapping attributes into a dynamic report payload."""
    for name in names:
        value = getattr(source, name)
        if value is not None:
            payload[name] = dict(value)


def _copy_reason_items(
    payload: dict[str, Any],  # Any: dynamic report serialization payload
    name: str,
    items: tuple[dict[str, Any], ...],  # Any: dynamic reason payload
) -> None:
    """Copy a non-empty tuple of dynamic reason mappings."""
    if items:
        payload[name] = [dict(item) for item in items]


class BalanceStatus(StrEnum):
    """Stage or layer balance status."""

    OK = "OK"
    DEGRADED = "DEGRADED"
    FAILING = "FAILING"
    UNKNOWN = "UNKNOWN"


class TrackingCoverage(StrEnum):
    """How completely removals are instrumented."""

    FULL = "full"
    PARTIAL = "partial"
    NOT_TRACKED = "not_tracked"


class RemovalOutcome(StrEnum):
    """Canonical removal outcome buckets (Processed Records aligned)."""

    FILTERED_OUT = "filtered_out"
    QUARANTINED = "quarantined"
    SKIPPED = "skipped"
    DEDUPLICATED = "deduplicated"
    EXCLUDED_BY_CONTRACT = "excluded_by_contract"
    OTHER = "other"


class StageId(StrEnum):
    """Canonical pipeline stage identifiers for funnel reporting."""

    EXTRACT = "extract"
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    EXPORT = "export"


@dataclass(frozen=True, slots=True)
class ReasonRemoval:
    """One reason-coded removal aggregate."""

    outcome: str
    reason_code: str
    count: int
    reason_family: str | None = None
    sample_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:  # Any: report/json payload shape is dynamic
        payload: dict[str, Any] = {  # Any: report/json payload shape is dynamic
            "outcome": self.outcome,
            "reason_code": self.reason_code,
            "count": self.count,
        }
        if self.reason_family is not None:
            payload["reason_family"] = self.reason_family
        if self.sample_refs:
            payload["sample_refs"] = list(self.sample_refs)
        return payload


@dataclass(frozen=True, slots=True)
class StageFunnelRow:
    """One funnel stage row with conservation metadata."""

    stage_id: str
    records_in: int
    records_out: int
    removed_total: int
    removals: tuple[ReasonRemoval, ...]
    balance_status: BalanceStatus
    tracking: TrackingCoverage
    unaccounted: int = 0

    def to_dict(self) -> dict[str, Any]:  # Any: report/json payload shape is dynamic
        return {
            "stage_id": self.stage_id,
            "records_in": self.records_in,
            "records_out": self.records_out,
            "removed_total": self.removed_total,
            "removals": [item.to_dict() for item in self.removals],
            "balance_status": self.balance_status.value,
            "tracking": self.tracking.value,
            "unaccounted": self.unaccounted,
        }


@dataclass(frozen=True, slots=True)
class LayerCounts:
    """Layer rollup compatible with Processed Records buckets."""

    bronze_records: int = 0
    silver_valid: int = 0
    silver_filtered_out: int = 0
    silver_quarantined: int = 0
    silver_skipped: int = 0
    silver_deduplicated: int = 0
    gold_written: int = 0
    gold_excluded_by_contract: int = 0
    gold_quarantined: int = 0
    gold_skipped: int = 0
    gold_deduplicated: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)

    @property
    def silver_accounted(self) -> int:
        return (
            self.silver_valid
            + self.silver_filtered_out
            + self.silver_quarantined
            + self.silver_skipped
            + self.silver_deduplicated
        )

    @property
    def gold_accounted(self) -> int:
        return (
            self.gold_written
            + self.gold_excluded_by_contract
            + self.gold_quarantined
            + self.gold_skipped
            + self.gold_deduplicated
        )


@dataclass(frozen=True, slots=True)
class PipelineRunReport:
    """Canonical pipeline_run_report_v1 payload."""

    identity: dict[str, Any]  # Any: report/json payload shape is dynamic
    funnel: tuple[StageFunnelRow, ...]
    layers: LayerCounts
    reasons_top_n: tuple[
        dict[str, Any], ...
    ]  # Any: report/json payload shape is dynamic
    reconciliation: dict[str, Any]  # Any: report/json payload shape is dynamic
    tracking_coverage: TrackingCoverage
    reason_catalog_version: str
    artifacts: tuple[
        dict[str, Any], ...
    ] = ()  # Any: report/json payload shape is dynamic
    failure: dict[str, Any] | None = None  # Any: optional failure block
    io: dict[str, Any] | None = None  # Any: optional IO summary
    quarantine: dict[str, Any] | None = None  # Any: optional quarantine rollup
    dq_summary: dict[str, Any] | None = None  # Any: optional DQ aggregate
    contract_summary: dict[str, Any] | None = None  # Any: optional contract aggregate
    schema_versions: dict[str, Any] | None = None  # Any: optional fingerprints
    stage_timings: dict[str, Any] | None = None  # Any: optional stage durations
    http_summary: dict[str, Any] | None = None  # Any: optional HTTP rollup
    performance: dict[str, Any] | None = None  # Any: optional throughput
    schema_version: str = "pipeline_run_report_v1"

    def to_dict(self) -> dict[str, Any]:  # Any: report/json payload shape is dynamic
        payload: dict[str, Any] = {  # Any: report/json payload shape is dynamic
            "schema_version": self.schema_version,
            "reason_catalog_version": self.reason_catalog_version,
            "identity": dict(self.identity),
            "funnel": [row.to_dict() for row in self.funnel],
            "layers": self.layers.to_dict(),
            "reasons_top_n": [dict(item) for item in self.reasons_top_n],
            "artifacts": [dict(item) for item in self.artifacts],
            "reconciliation": dict(self.reconciliation),
            "tracking_coverage": self.tracking_coverage.value,
        }
        _copy_present_mappings(
            payload,
            self,
            (
                "failure",
                "io",
                "quarantine",
                "dq_summary",
                "contract_summary",
                "schema_versions",
                "stage_timings",
                "http_summary",
                "performance",
            ),
        )
        return payload


@dataclass(frozen=True, slots=True)
class WorkflowExecutionRow:
    """One executed workflow step with extraction counters."""

    step_id: str
    status: str
    records_extracted: int
    kind: str | None = None
    pipeline_name: str | None = None
    records_bronze: int | None = None
    records_silver: int | None = None
    records_gold: int | None = None
    pipeline_run_id: str | None = None
    pipeline_manifest_id: str | None = None
    pipeline_report_ref: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    top_reasons: tuple[dict[str, Any], ...] = ()  # Any: optional child reasons
    skip_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:  # Any: report/json payload shape is dynamic
        payload: dict[str, Any] = {  # Any: report/json payload shape is dynamic
            "step_id": self.step_id,
            "status": self.status,
            "records_extracted": self.records_extracted,
        }
        _copy_present_attributes(
            payload,
            self,
            (
                "kind",
                "pipeline_name",
                "records_bronze",
                "records_silver",
                "records_gold",
                "pipeline_run_id",
                "pipeline_manifest_id",
                "pipeline_report_ref",
                "error_type",
                "error_message",
                "skip_reason",
            ),
        )
        _copy_reason_items(payload, "top_reasons", self.top_reasons)
        return payload


@dataclass(frozen=True, slots=True)
class WorkflowRunReport:
    """Canonical workflow_run_report_v1 payload."""

    identity: dict[str, Any]  # Any: report/json payload shape is dynamic
    plan_steps: tuple[dict[str, Any], ...]  # Any: report/json payload shape is dynamic
    execution: tuple[WorkflowExecutionRow, ...]
    totals: dict[str, Any]  # Any: report/json payload shape is dynamic
    index: dict[str, Any] = field(
        default_factory=dict
    )  # Any: report/json payload shape is dynamic
    reasons_rollup: tuple[dict[str, Any], ...] = ()  # Any: aggregated child reasons
    schema_version: str = "workflow_run_report_v1"

    def to_dict(self) -> dict[str, Any]:  # Any: report/json payload shape is dynamic
        payload: dict[str, Any] = {  # Any: report/json payload shape is dynamic
            "schema_version": self.schema_version,
            "identity": dict(self.identity),
            "plan": {"steps": [dict(step) for step in self.plan_steps]},
            "execution": [row.to_dict() for row in self.execution],
            "totals": dict(self.totals),
            "index": dict(self.index),
        }
        _copy_reason_items(payload, "reasons_rollup", self.reasons_rollup)
        return payload
