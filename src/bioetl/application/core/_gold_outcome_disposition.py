"""Map attributed DQ outcomes onto Gold write and quarantine routing.

Sync validation fills a quarantine accumulator. ``write_gold`` sends those
requests through ``write_quarantine_requests``. Disposition ``FAIL``,
``SKIP``, and any unattributable blocking violation stay fail-closed.
Schema violations quarantine a row only when that rule id has an explicit
``QUARANTINE`` override. Without an explicit outcome policy the caller keeps
``.validate()``.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.behavior.dq_contract_rule_source import (
    has_explicit_outcome_policy,
    override_disposition,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.types import BatchID, JsonDict
from bioetl.domain.types.dq_contracts import DQDisposition, DQViolationKind
from bioetl.domain.types.dq_record_attribution import (
    AttributedDQViolation,
    DQOutcomeChannel,
)

__all__ = [
    "GoldQuarantineEntry",
    "GoldQuarantineRuleRecord",
    "GoldWriteOutcome",
    "bind_gold_quarantine_batch_if_supported",
    "consume_gold_outcome_quarantine_count",
    "plan_gold_outcome_write",
    "supports_outcome_channel",
]


@dataclass(frozen=True, slots=True)
class GoldQuarantineRuleRecord:
    """Rule metadata stored on one per-record quarantine request."""

    rule_id: str
    contract_ref: str | None
    config_path: str | None
    disposition: str


@dataclass(frozen=True, slots=True)
class GoldQuarantineEntry:
    """One normalized record routed to quarantine with its rule metadata."""

    source_index: int
    record_key: str | None
    record: JsonDict
    rules: tuple[GoldQuarantineRuleRecord, ...]


@dataclass(frozen=True, slots=True)
class GoldWriteOutcome:
    """Sync decision for one Gold validation batch."""

    fail_closed: bool
    records_to_write: tuple[JsonDict, ...]
    quarantine_items: tuple[GoldQuarantineEntry, ...]
    fail_closed_reasons: tuple[str, ...]


def supports_outcome_channel(validator: object) -> bool:
    """Whether the validator class implements the outcome channel.

    Instance-only attributes (including mocks) do not opt in.
    """
    method = getattr(type(validator), "validate_with_outcomes", None)
    return callable(method)


def plan_gold_outcome_write(
    records: list[JsonDict],
    channel: DQOutcomeChannel,
    config: DQConfig | None,
) -> GoldWriteOutcome:
    """Split a batch into Gold rows and per-record quarantine items."""
    if not has_explicit_outcome_policy(config):
        return _fail_closed(
            records,
            ("outcome policy is not explicit",) if not channel.is_valid else (),
            fail_closed=not channel.is_valid,
        )
    reasons = _fail_closed_reasons(channel.violations, config)
    if reasons or (not channel.is_valid and not _routable(channel.violations, config)):
        if not reasons:
            reasons = ("outcome channel rejected the batch without a quarantine route",)
        return _fail_closed(records, reasons, fail_closed=True)
    items = _quarantine_items(records, channel.violations, config)
    dropped = {item.source_index for item in items}
    kept = tuple(record for index, record in enumerate(records) if index not in dropped)
    return GoldWriteOutcome(
        fail_closed=False,
        records_to_write=kept,
        quarantine_items=items,
        fail_closed_reasons=(),
    )


def bind_gold_quarantine_batch_if_supported(
    writer: object,
    batch_id: BatchID,
) -> None:
    """Attach the current batch id when the writer owns Gold quarantine routing."""
    method = getattr(type(writer), "bind_gold_quarantine_batch", None)
    if callable(method):
        method(writer, batch_id)


def consume_gold_outcome_quarantine_count(writer: object) -> int:
    """Read and clear the quarantine count recorded by the last Gold write."""
    state = getattr(writer, "__dict__", None)
    if not isinstance(state, dict):
        return 0
    if "_last_gold_outcome_quarantine_count" not in state:
        return 0
    raw = state["_last_gold_outcome_quarantine_count"]
    state["_last_gold_outcome_quarantine_count"] = 0
    if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
        return raw
    return 0


def _fail_closed(
    records: list[JsonDict],
    reasons: tuple[str, ...],
    *,
    fail_closed: bool,
) -> GoldWriteOutcome:
    return GoldWriteOutcome(
        fail_closed=fail_closed,
        records_to_write=tuple(records),
        quarantine_items=(),
        fail_closed_reasons=reasons,
    )


def _routable(
    violations: tuple[AttributedDQViolation, ...],
    config: DQConfig | None,
) -> bool:
    return any(_route_allowed(violation, config) for violation in violations)


def _fail_closed_reasons(
    violations: tuple[AttributedDQViolation, ...],
    config: DQConfig | None,
) -> tuple[str, ...]:
    reasons: list[str] = []
    for violation in violations:
        outcome = violation.outcome
        is_schema = outcome.violation_kind == DQViolationKind.SCHEMA_VIOLATION
        if not is_schema and outcome.disposition in (
            DQDisposition.PASS,
            DQDisposition.WARN,
        ):
            continue
        if _route_allowed(violation, config):
            continue
        reasons.append(_reason(violation))
    return tuple(reasons)


def _route_allowed(
    violation: AttributedDQViolation,
    config: DQConfig | None,
) -> bool:
    outcome = violation.outcome
    if outcome.disposition != DQDisposition.QUARANTINE or not violation.attributable:
        return False
    if outcome.violation_kind != DQViolationKind.SCHEMA_VIOLATION:
        return True
    return override_disposition(config, outcome.rule_id) == DQDisposition.QUARANTINE


def _quarantine_items(
    records: list[JsonDict],
    violations: tuple[AttributedDQViolation, ...],
    config: DQConfig | None,
) -> tuple[GoldQuarantineEntry, ...]:
    grouped: dict[int, list[AttributedDQViolation]] = {}
    for violation in violations:
        if not _route_allowed(violation, config) or violation.record is None:
            continue
        grouped.setdefault(violation.record.source_index, []).append(violation)
    items: list[GoldQuarantineEntry] = []
    for source_index in sorted(grouped):
        group = sorted(grouped[source_index], key=_violation_rule_key)
        record = records[source_index]
        identity = group[0].record
        items.append(
            GoldQuarantineEntry(
                source_index=source_index,
                record_key=None if identity is None else identity.record_key,
                record=dict(record),
                rules=tuple(_rule_metadata(violation) for violation in group),
            )
        )
    return tuple(items)


def _violation_rule_key(violation: AttributedDQViolation) -> tuple[str, str, str]:
    outcome = violation.outcome
    return (
        outcome.rule_id,
        outcome.violation_kind.value,
        outcome.config_path or "",
    )


def _rule_metadata(violation: AttributedDQViolation) -> GoldQuarantineRuleRecord:
    outcome = violation.outcome
    policy = outcome.policy_ref
    return GoldQuarantineRuleRecord(
        rule_id=outcome.rule_id,
        contract_ref=None if policy is None else policy.contract_ref,
        config_path=outcome.config_path,
        disposition=outcome.disposition.value,
    )


def _reason(violation: AttributedDQViolation) -> str:
    record = violation.record
    location = "schema" if record is None else str(record.source_index)
    return (
        f"{violation.outcome.rule_id}: "
        f"disposition={violation.outcome.disposition.value} record={location}"
    )
