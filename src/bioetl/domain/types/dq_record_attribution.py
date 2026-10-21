"""Record attribution for rule-level DQ outcomes.

``DQRuleOutcome`` stays rule-scoped: it has no record id and no row index.
Write-path routing must use this contract. Affected rows are never inferred
from ``affected_fields``.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from bioetl.domain.types.dq_contracts import DQRuleOutcome

__all__ = [
    "CANONICAL_RECORD_KEY_FIELDS",
    "AttributedDQViolation",
    "DQOutcomeChannel",
    "DQRecordIdentity",
    "attributed_violation_sort_key",
    "record_identity",
    "sort_attributed_violations",
]

CANONICAL_RECORD_KEY_FIELDS: tuple[str, ...] = (
    "entity_id",
    "activity_id",
    "assay_id",
    "molecule_id",
    "target_id",
    "record_id",
    "compound_id",
    "id",
)


@dataclass(frozen=True, slots=True)
class DQRecordIdentity:
    """Identity of one normalized record inside a validation batch.

    ``source_index`` is the 0-based position in the post-normalization list
    passed to the validator. ``record_key`` is the first present canonical
    identifier on that record, when one exists.
    """

    source_index: int
    record_key: str | None = None

    def __post_init__(self) -> None:
        if self.source_index < 0:
            raise ValueError("source_index must be >= 0")


@dataclass(frozen=True, slots=True)
class AttributedDQViolation:
    """One rule outcome bound to at most one normalized source record.

    ``record is None`` means the violation has no row identity (schema-level
    or otherwise unattributable). Those violations keep fail-closed behavior.
    Several violations may share one ``DQRecordIdentity``.
    """

    outcome: DQRuleOutcome
    record: DQRecordIdentity | None

    @property
    def attributable(self) -> bool:
        """Whether the violation is bound to one source record."""
        return self.record is not None


@dataclass(frozen=True, slots=True)
class DQOutcomeChannel:
    """Outcome-channel result that still unpacks as ``(is_valid, outcomes)``."""

    is_valid: bool
    outcomes: tuple[DQRuleOutcome, ...]
    violations: tuple[AttributedDQViolation, ...]

    def __iter__(self) -> Iterator[bool | list[DQRuleOutcome]]:
        yield self.is_valid
        yield list(self.outcomes)


def record_identity(
    record: Mapping[str, object],
    source_index: int,
) -> DQRecordIdentity:
    """Bind one normalized record to its batch position.

    The key is read only from ``CANONICAL_RECORD_KEY_FIELDS``. Column names
    carried by a rule's ``affected_fields`` are not identifiers.
    """
    return DQRecordIdentity(
        source_index=source_index,
        record_key=_canonical_record_key(record),
    )


def attributed_violation_sort_key(
    violation: AttributedDQViolation,
) -> tuple[object, ...]:
    """Stable order: unattributable violations, then source index, then rule."""
    record = violation.record
    outcome = violation.outcome
    return (
        0 if record is None else 1,
        -1 if record is None else record.source_index,
        outcome.rule_id,
        outcome.violation_kind.value,
        outcome.severity,
        ",".join(outcome.affected_fields),
        outcome.config_path or "",
        "" if record is None or record.record_key is None else record.record_key,
    )


def sort_attributed_violations(
    violations: list[AttributedDQViolation],
) -> tuple[AttributedDQViolation, ...]:
    """Return violations in replay-stable order."""
    return tuple(sorted(violations, key=attributed_violation_sort_key))


def _canonical_record_key(record: Mapping[str, object]) -> str | None:
    for field in CANONICAL_RECORD_KEY_FIELDS:
        if field not in record:
            continue
        value = record[field]
        text = _identifier_text(value)
        if text is not None:
            return text
    return None


def _identifier_text(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and value != value:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text
