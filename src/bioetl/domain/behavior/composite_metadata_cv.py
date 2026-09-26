"""Cross-validation/DQ summarization helpers for composite metadata."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, TypedDict

from bioetl.domain.types import JsonDict


class MergedRecordExplanationLike(Protocol):
    """Structural view required by explainability summary helpers."""

    @property
    def source_providers(self) -> tuple[str, ...]:
        """Return providers contributing to the merged record."""
        ...

    @property
    def field_explanations(self) -> tuple[object, ...]:
        """Return field-level merge explanations."""
        ...

    @property
    def merge_strategy(self) -> str:
        """Return the merge strategy identifier."""
        ...

    @property
    def conflict_count(self) -> int:
        """Return the number of detected merge conflicts."""
        ...

    @property
    def enrichment_count(self) -> int:
        """Return the number of applied enrichments."""
        ...


class CompositeCvDQSummary(TypedDict):
    """Structured summary for composite cross-validation DQ markers."""

    has_signal: bool
    warning_records: int
    error_records: int
    quarantine_records: int
    validation_passed: bool
    rule_provenance: list[dict[str, str | None]]


def empty_explainability_summary() -> JsonDict:
    """Return the stable summary shape for an empty explanation set."""
    return {
        "record_count": 0,
        "field_count": 0,
        "avg_fields_per_record": 0.0,
        "source_provider_distribution": {},
        "merge_strategy_distribution": {},
        "conflict_summary": {
            "total_conflicts": 0,
            "conflict_rate": 0.0,
            "records_with_conflicts": 0,
        },
        "enrichment_summary": {
            "total_enrichments": 0,
            "enrichment_rate": 0.0,
            "records_with_enrichments": 0,
        },
    }


def safe_ratio(numerator: int, denominator: int) -> float:
    """Divide counts while preserving zero for empty populations."""
    return numerator / denominator if denominator > 0 else 0.0


def _explainability_distributions(
    explanations: Sequence[MergedRecordExplanationLike],
) -> tuple[JsonDict, JsonDict]:
    source_distribution: dict[str, int] = {}
    strategy_distribution: dict[str, int] = {}
    for explanation in explanations:
        for provider in explanation.source_providers:
            source_distribution[provider] = source_distribution.get(provider, 0) + 1
        strategy = explanation.merge_strategy
        strategy_distribution[strategy] = strategy_distribution.get(strategy, 0) + 1
    return source_distribution, strategy_distribution


def _explainability_totals(
    explanations: Sequence[MergedRecordExplanationLike],
) -> dict[str, int]:
    return {
        "total_records": len(explanations),
        "total_fields": sum(len(exp.field_explanations) for exp in explanations),
        "total_conflicts": sum(exp.conflict_count for exp in explanations),
        "total_enrichments": sum(exp.enrichment_count for exp in explanations),
    }


def build_explainability_summary(
    explanations: Sequence[MergedRecordExplanationLike],
) -> JsonDict:
    """Summarize explainability coverage, conflicts, and enrichments."""
    totals = _explainability_totals(explanations)
    source_distribution, strategy_distribution = _explainability_distributions(
        explanations
    )
    records_with_conflicts = sum(1 for exp in explanations if exp.conflict_count > 0)
    records_with_enrichments = sum(
        1 for exp in explanations if exp.enrichment_count > 0
    )
    return {
        "record_count": totals["total_records"],
        "field_count": totals["total_fields"],
        "avg_fields_per_record": safe_ratio(
            totals["total_fields"], totals["total_records"]
        ),
        "source_provider_distribution": source_distribution,
        "merge_strategy_distribution": strategy_distribution,
        "conflict_summary": {
            "total_conflicts": totals["total_conflicts"],
            "conflict_rate": safe_ratio(
                totals["total_conflicts"], totals["total_fields"]
            ),
            "records_with_conflicts": records_with_conflicts,
        },
        "enrichment_summary": {
            "total_enrichments": totals["total_enrichments"],
            "enrichment_rate": safe_ratio(
                records_with_enrichments, totals["total_records"]
            ),
            "records_with_enrichments": records_with_enrichments,
        },
    }


def _is_truthy_marker(value: object) -> bool:
    """Interpret composite CV marker payloads from records."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    if isinstance(value, int):
        return value != 0
    return False


def _build_cv_rule_provenance_entry(
    *,
    rule_id: str,
    severity: str,
    decision: str,
    record_count: int,
    contract_version: str | None,
    report_artifact_path: str | None,
) -> dict[str, str | None]:
    """Build one stable provenance entry for composite cross-validation."""
    return {
        "rule_id": rule_id,
        "contract_version": contract_version,
        "config_path": "cross_validation",
        "layer": "composite",
        "field": None,
        "severity": severity,
        "decision": decision,
        "violation_kind": "cross_validation_mismatch",
        "report_artifact_path": report_artifact_path,
        "record_count": str(record_count),
    }


def _count_cv_markers(
    records: Sequence[Mapping[str, object]],
) -> tuple[int, int, int]:
    """Return warning-only, error-marker, and quarantine counts."""
    warning_only_count = 0
    error_marker_count = 0
    quarantine_count = 0
    for record in records:
        warning_only_inc, error_marker_inc, quarantine_inc = _marker_increments(record)
        warning_only_count += warning_only_inc
        error_marker_count += error_marker_inc
        quarantine_count += quarantine_inc
    return warning_only_count, error_marker_count, quarantine_count


def _marker_increments(record: Mapping[str, object]) -> tuple[int, int, int]:
    """Return warning-only, error-marker, and quarantine increments."""
    has_warning = _is_truthy_marker(record.get("_cv_warn"))
    has_error = _is_truthy_marker(record.get("_cv_error"))
    has_quarantine = _is_truthy_marker(record.get("_cv_quarantine"))
    warning_only_inc = int(has_warning and not has_error and not has_quarantine)
    error_marker_inc = int(has_error or has_quarantine)
    quarantine_inc = int(has_quarantine)
    return warning_only_inc, error_marker_inc, quarantine_inc


def _build_cv_rule_provenance(
    *,
    warning_only_count: int,
    error_count: int,
    quarantine_count: int,
    contract_version: str | None,
    report_artifact_path: str | None,
) -> list[dict[str, str | None]]:
    """Build stable provenance rows for warning/nullify/quarantine decisions."""
    provenance: list[dict[str, str | None]] = []
    if warning_only_count > 0:
        provenance.append(
            _build_cv_rule_provenance_entry(
                rule_id="composite.cross_validation.warning",
                severity="warning",
                decision="warn",
                record_count=warning_only_count,
                contract_version=contract_version,
                report_artifact_path=report_artifact_path,
            )
        )
    nullified_count = max(error_count - quarantine_count, 0)
    if nullified_count > 0:
        provenance.append(
            _build_cv_rule_provenance_entry(
                rule_id="composite.cross_validation.nullify",
                severity="error",
                decision="skip",
                record_count=nullified_count,
                contract_version=contract_version,
                report_artifact_path=report_artifact_path,
            )
        )
    if quarantine_count > 0:
        provenance.append(
            _build_cv_rule_provenance_entry(
                rule_id="composite.cross_validation.quarantine",
                severity="error",
                decision="quarantine",
                record_count=quarantine_count,
                contract_version=contract_version,
                report_artifact_path=report_artifact_path,
            )
        )
    return provenance


def summarize_composite_cv_dq(
    records: Sequence[Mapping[str, object]],
    *,
    contract_version: str | None = None,
    report_artifact_path: str | None = None,
) -> CompositeCvDQSummary:
    """Summarize composite cross-validation markers into DQ-oriented semantics."""
    if not records:
        return {
            "has_signal": False,
            "warning_records": 0,
            "error_records": 0,
            "quarantine_records": 0,
            "validation_passed": True,
            "rule_provenance": [],
        }

    warning_only_count, error_marker_count, quarantine_count = _count_cv_markers(
        records
    )
    # error_records includes quarantined rows (overlap with quarantine_records):
    # _marker_increments counts has_error OR has_quarantine as error markers.
    error_count = error_marker_count
    provenance = _build_cv_rule_provenance(
        warning_only_count=warning_only_count,
        error_count=error_count,
        quarantine_count=quarantine_count,
        contract_version=contract_version,
        report_artifact_path=report_artifact_path,
    )

    return {
        "has_signal": bool(warning_only_count or error_count or quarantine_count),
        "warning_records": warning_only_count,
        "error_records": error_count,
        "quarantine_records": quarantine_count,
        "validation_passed": error_count == 0,
        "rule_provenance": provenance,
    }
