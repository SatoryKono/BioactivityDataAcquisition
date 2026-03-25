"""Control-plane run ledger models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import UUID

from bioetl.domain.types import RunID

__all__ = ["RunLedgerEntry"]

_LEDGER_EVENT_FAMILY_EXACT: dict[str, str] = {
    "manifest_created": "diagnostic",
    "run_started": "pipeline.lifecycle",
    "run_finished": "pipeline.lifecycle",
    "run_failed": "pipeline.lifecycle",
    "run_shutdown": "pipeline.lifecycle",
    "stage_completed": "pipeline.phase",
    "artifact_published": "artifact",
}
_LEDGER_EVENT_FAMILY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("dq_", "dq"),
    ("lineage_", "lineage"),
    ("checkpoint_", "checkpoint"),
    ("composite_", "composite"),
    ("artifact_", "artifact"),
)
_LEDGER_EVENT_FAMILY_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("_started", "pipeline.phase"),
    ("_completed", "pipeline.phase"),
)


def _normalize_ledger_value(value: object) -> object:
    """Normalize nested values into JSON-safe primitives."""
    if isinstance(value, dict):
        return {str(key): _normalize_ledger_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_normalize_ledger_value(item) for item in value]
    return _normalize_ledger_scalar(value)


def _normalize_ledger_scalar(value: object) -> object:
    """Normalize scalar ledger values into JSON-safe primitives."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _match_ledger_event_family_by_suffix(event_type: str) -> str | None:
    for suffix, family in _LEDGER_EVENT_FAMILY_SUFFIXES:
        if event_type.endswith(suffix):
            return family
    return None


def _match_ledger_event_family_by_prefix(event_type: str) -> str | None:
    for prefix, family in _LEDGER_EVENT_FAMILY_PREFIXES:
        if event_type.startswith(prefix):
            return family
    return None


def infer_ledger_event_family(event_type: str) -> str:
    """Infer stable event-family taxonomy for ledger entries."""
    normalized_event_type = event_type.strip().lower()
    if not normalized_event_type:
        return "diagnostic"
    exact_match = _LEDGER_EVENT_FAMILY_EXACT.get(normalized_event_type)
    if exact_match is not None:
        return exact_match
    suffix_match = _match_ledger_event_family_by_suffix(normalized_event_type)
    if suffix_match is not None:
        return suffix_match
    prefix_match = _match_ledger_event_family_by_prefix(normalized_event_type)
    if prefix_match is not None:
        return prefix_match
    return "diagnostic"


@dataclass(frozen=True, slots=True)
class RunLedgerEntry:
    """Append-only control-plane event linked to one manifest/run pair."""

    entry_id: str
    manifest_id: str
    run_id: RunID
    event_type: str
    occurred_at: datetime
    event_family: str | None = None
    status: str | None = None
    stage: str | None = None
    message: str | None = None
    error_type: str | None = None
    dataset_ref: str | None = None
    lineage_fragment_id: str | None = None
    metrics_snapshot: dict[str, int] | None = None
    details: dict[str, object] | None = None

    def __post_init__(self) -> None:
        """Ensure taxonomy and event-type payload are canonicalized."""
        normalized_event_type = str(self.event_type).strip().lower()
        if not normalized_event_type:
            normalized_event_type = "unknown_event"
        object.__setattr__(self, "event_type", normalized_event_type)
        if self.event_family is None:
            object.__setattr__(
                self,
                "event_family",
                infer_ledger_event_family(normalized_event_type),
            )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable ledger payload."""
        return {
            key: _normalize_ledger_value(value)
            for key, value in asdict(self).items()
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> RunLedgerEntry:
        """Hydrate a ledger entry from serialized JSON payload."""
        return cls(
            entry_id=str(payload["entry_id"]),
            manifest_id=str(payload["manifest_id"]),
            run_id=RunID(UUID(str(payload["run_id"]))),
            event_type=str(payload["event_type"]),
            event_family=_load_optional_str(payload, "event_family"),
            occurred_at=datetime.fromisoformat(str(payload["occurred_at"])),
            status=_load_optional_str(payload, "status"),
            stage=None if payload.get("stage") is None else str(payload["stage"]),
            message=_load_optional_str(payload, "message"),
            error_type=_load_optional_str(payload, "error_type"),
            dataset_ref=_load_optional_str(payload, "dataset_ref"),
            lineage_fragment_id=_load_optional_str(payload, "lineage_fragment_id"),
            metrics_snapshot=_load_metrics_snapshot(payload.get("metrics_snapshot")),
            details=_load_details(payload.get("details")),
        )


def _load_optional_str(payload: dict[str, object], key: str) -> str | None:
    """Extract an optional string field from a serialized mapping."""
    value = payload.get(key)
    return None if value is None else str(value)


def _load_metrics_snapshot(raw_metrics: object) -> dict[str, int] | None:
    """Deserialize metrics snapshot payload safely."""
    if not isinstance(raw_metrics, dict):
        return None
    return {str(key): int(value) for key, value in raw_metrics.items()}


def _load_details(raw_details: object) -> dict[str, object] | None:
    """Deserialize arbitrary details payload safely."""
    if not isinstance(raw_details, dict):
        return None
    return {str(key): value for key, value in raw_details.items()}
