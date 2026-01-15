"""Composite pipeline lineage models.

Defines value objects for tracking data provenance in composite pipelines.
See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


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
class LineageMetadata:
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
        """Check if record has successful enrichment from provider."""
        status = self.enrichment_status.get(provider)
        return status is not None and status.status == "success"

    @property
    def successful_enrichers(self) -> tuple[str, ...]:
        """Get providers with successful enrichment."""
        return tuple(
            p for p, s in self.enrichment_status.items() if s.status == "success"
        )

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for storage/serialization."""
        return {
            "_composite_run_id": self.composite_run_id,
            "_composite_name": self.composite_name,
            "_source_providers": list(self.source_providers),
            "_enrichment_status": {
                p: s.status for p, s in self.enrichment_status.items()
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
    def from_dict(cls, data: dict[str, object]) -> LineageMetadata:
        """Create LineageMetadata from dictionary."""
        enrichment_status = _parse_enrichment_status(data.get("_enrichment_status", {}))
        enrichment_timestamps = _parse_timestamps(
            data.get("_enrichment_timestamps", {})
        )
        raw_providers = data.get("_source_providers", [])
        source_providers: tuple[str, ...] = (
            tuple(str(p) for p in raw_providers)
            if isinstance(raw_providers, (list, tuple))
            else ()
        )
        raw_field_sources = data.get("_field_sources", {})
        field_sources: dict[str, str] = (
            {str(k): str(v) for k, v in raw_field_sources.items()}
            if isinstance(raw_field_sources, dict)
            else {}
        )
        created_at = _parse_datetime(data.get("_lineage_created_at"))
        raw_seed_id = data.get("_seed_record_id")
        seed_record_id: str | None = str(raw_seed_id) if raw_seed_id else None

        return cls(
            composite_run_id=str(data.get("_composite_run_id", "")),
            composite_name=str(data.get("_composite_name", "")),
            source_providers=source_providers,
            enrichment_status=enrichment_status,
            enrichment_timestamps=enrichment_timestamps,
            field_sources=field_sources,
            seed_record_id=seed_record_id,
            created_at=created_at,
        )


def _parse_enrichment_status(
    raw: object,
) -> dict[str, EnrichmentStatusRecord]:
    """Parse enrichment status from raw dict."""
    result: dict[str, EnrichmentStatusRecord] = {}
    if not isinstance(raw, dict):
        return result
    for provider, status in raw.items():
        result[provider] = EnrichmentStatusRecord(
            provider=provider,
            status=status if isinstance(status, str) else "error",
        )
    return result


def _parse_timestamps(raw: object) -> dict[str, datetime]:
    """Parse timestamps from raw dict."""
    result: dict[str, datetime] = {}
    if not isinstance(raw, dict):
        return result
    for provider, ts in raw.items():
        if isinstance(ts, str):
            result[provider] = datetime.fromisoformat(ts)
        elif isinstance(ts, datetime):
            result[provider] = ts
    return result


def _parse_datetime(raw: object) -> datetime | None:
    """Parse optional datetime from raw value."""
    if isinstance(raw, str):
        return datetime.fromisoformat(raw)
    if isinstance(raw, datetime):
        return raw
    return None
