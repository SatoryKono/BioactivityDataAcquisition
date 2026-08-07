"""Composite pipeline lineage models.

Defines value objects for tracking data provenance in composite pipelines.
See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

__all__ = [
    "CompositeLineageMetadata",
    "EnrichmentStatusRecord",
    "FieldSource",
]


@dataclass(frozen=True, slots=True)
class FieldSource:
    """Source information for a single field."""

    field_name: str
    source_provider: str
    source_pipeline: str
    extraction_timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class EnrichmentStatusRecord:
    """Per-record enrichment status."""

    provider: str
    status: str  # success, not_found, error, skipped
    timestamp: datetime | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class CompositeLineageMetadata:
    """Complete lineage metadata for a merged record."""

    composite_run_id: str
    composite_name: str
    source_providers: tuple[str, ...] = ()
    enrichment_status: dict[str, EnrichmentStatusRecord] = field(default_factory=dict)
    enrichment_timestamps: dict[str, datetime] = field(default_factory=dict)
    field_sources: dict[str, str] = field(default_factory=dict)
    seed_record_id: str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Convert types for immutability."""
        if isinstance(self.source_providers, list):
            object.__setattr__(self, "source_providers", tuple(self.source_providers))

    def has_enrichment(self, provider: str) -> bool:
        """Check if record has successful enrichment from provider.

        Args:
            provider: Data provider name.

        Returns:
            True if the condition is met, False otherwise.
        """
        status = self.enrichment_status.get(provider)
        return status is not None and status.status == "success"

    @property
    def successful_enrichers(self) -> tuple[str, ...]:
        """Get providers with successful enrichment."""
        return tuple(
            p for p, s in self.enrichment_status.items() if s.status == "success"
        )

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for storage/serialization.

        Returns:
            Dictionary representation.
        """
        return {
            "_composite_run_id": self.composite_run_id,
            "_composite_name": self.composite_name,
            "_source_providers": list(self.source_providers),
            "_enrichment_status": {
                p: {
                    "status": s.status,
                    "timestamp": (
                        s.timestamp.isoformat() if s.timestamp is not None else None
                    ),
                    "error_message": s.error_message,
                }
                for p, s in self.enrichment_status.items()
            },
            "_enrichment_timestamps": {
                p: ts.isoformat() for p, ts in self.enrichment_timestamps.items()
            },
            "_field_sources": self.field_sources,
            "_seed_record_id": self.seed_record_id,
            "_lineage_created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CompositeLineageMetadata:
        """Create CompositeLineageMetadata from dictionary.

        Args:
            data: Input data.

        Returns:
            New instance constructed from the input.
        """
        enrichment_status = _parse_enrichment_status(data.get("_enrichment_status", {}))
        enrichment_timestamps = _parse_timestamps(
            data.get("_enrichment_timestamps", {})
        )

        return cls(
            composite_run_id=str(data.get("_composite_run_id", "")),
            composite_name=str(data.get("_composite_name", "")),
            source_providers=_parse_providers(data.get("_source_providers", [])),
            enrichment_status=enrichment_status,
            enrichment_timestamps=enrichment_timestamps,
            field_sources=_parse_field_sources(data.get("_field_sources", {})),
            seed_record_id=_parse_seed_id(data.get("_seed_record_id")),
            created_at=_parse_datetime(data.get("_lineage_created_at")),
        )


def _status_error_message(status: dict[str, object]) -> str | None:
    raw_message = status.get("error_message")
    if raw_message is None:
        return None
    return str(raw_message)


def _status_record_from_mapping(
    provider_key: str,
    status: dict[str, object],
) -> EnrichmentStatusRecord:
    return EnrichmentStatusRecord(
        provider=provider_key,
        status=str(status.get("status") or "error"),
        timestamp=_parse_datetime(status.get("timestamp")),
        error_message=_status_error_message(status),
    )


def _status_record_from_value(
    provider_key: str,
    status: object,
) -> EnrichmentStatusRecord:
    if isinstance(status, str):
        return EnrichmentStatusRecord(provider=provider_key, status=status)
    if isinstance(status, dict):
        return _status_record_from_mapping(provider_key, status)
    return EnrichmentStatusRecord(provider=provider_key, status="error")


def _parse_enrichment_status(
    raw: object,
) -> dict[str, EnrichmentStatusRecord]:
    """Parse enrichment status from raw dict.

    Accepts legacy plain-string values and nested mapping payloads with
    ``status`` / ``timestamp`` / ``error_message``.
    """
    if not isinstance(raw, dict):
        return {}
    return {
        str(provider): _status_record_from_value(str(provider), status)
        for provider, status in raw.items()
    }


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is UTC-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _parse_one_timestamp(ts: object) -> datetime | None:
    if isinstance(ts, datetime):
        return _ensure_utc(ts)
    if not isinstance(ts, str):
        return None
    try:
        return _ensure_utc(datetime.fromisoformat(ts))
    except ValueError:
        return None


def _parse_timestamps(raw: object) -> dict[str, datetime]:
    """Parse timestamps from raw dict, skipping malformed ISO strings."""
    if not isinstance(raw, dict):
        return {}
    result: dict[str, datetime] = {}
    for provider, ts in raw.items():
        parsed = _parse_one_timestamp(ts)
        if parsed is not None:
            result[str(provider)] = parsed
    return result


def _parse_datetime(raw: object) -> datetime | None:
    """Parse optional datetime from raw value, returning None on invalid ISO."""
    if isinstance(raw, str):
        try:
            return _ensure_utc(datetime.fromisoformat(raw))
        except ValueError:
            return None
    if isinstance(raw, datetime):
        return _ensure_utc(raw)
    return None


def _parse_providers(raw: object) -> tuple[str, ...]:
    """Parse source providers from raw value."""
    if isinstance(raw, (list, tuple)):
        return tuple(str(p) for p in raw)
    return ()


def _parse_field_sources(raw: object) -> dict[str, str]:
    """Parse field sources from raw value."""
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    return {}


def _parse_seed_id(raw: object) -> str | None:
    """Parse seed record ID from raw value."""
    return str(raw) if raw else None
