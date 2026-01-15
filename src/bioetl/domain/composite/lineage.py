"""Composite pipeline lineage models.

Defines value objects for tracking data provenance in composite pipelines.
Lineage metadata is embedded in every merged record to enable traceability.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FieldSource:
    """Source information for a single field.

    Tracks which provider contributed the value for a specific field
    in a merged record.

    Attributes:
        field_name: Name of the field.
        source_provider: Provider that contributed the value.
        source_pipeline: Full pipeline name.
        extraction_timestamp: When the value was extracted.

    Example:
        >>> source = FieldSource(
        ...     field_name="citations_count",
        ...     source_provider="crossref",
        ...     source_pipeline="crossref_publication",
        ... )
    """

    field_name: str
    source_provider: str
    source_pipeline: str
    extraction_timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class EnrichmentStatusRecord:
    """Per-record enrichment status.

    Tracks the status of each enricher for a specific record,
    enabling detailed debugging and analysis.

    Attributes:
        provider: Provider/enricher name.
        status: Status string (success, not_found, error, skipped).
        timestamp: When enrichment was attempted.
        error_message: Error message if status is error.

    Example:
        >>> status = EnrichmentStatusRecord(
        ...     provider="pubmed",
        ...     status="not_found",
        ...     timestamp=datetime.now(),
        ... )
    """

    provider: str
    status: str  # success, not_found, error, skipped
    timestamp: datetime | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Validate status value."""
        valid_statuses = {"success", "not_found", "error", "skipped"}
        if self.status not in valid_statuses:
            raise ValueError(
                f"Invalid status: {self.status}. Valid: {valid_statuses}"
            )


@dataclass(frozen=True, slots=True)
class LineageMetadata:
    """Complete lineage metadata for a merged record.

    Embedded in every Gold record to provide full traceability
    of data provenance across all sources.

    Attributes:
        composite_run_id: UUID of the composite pipeline run.
        composite_name: Name of the composite pipeline.
        source_providers: List of all providers that contributed data.
        enrichment_status: Per-provider enrichment status.
        enrichment_timestamps: When each provider was queried.
        field_sources: Mapping of field to source provider.
        seed_record_id: Primary key from seed record.
        created_at: When this lineage record was created.

    Example:
        >>> lineage = LineageMetadata(
        ...     composite_run_id="abc-123",
        ...     composite_name="composite_publication",
        ...     source_providers=("chembl", "crossref", "pubmed"),
        ...     enrichment_status={
        ...         "crossref": EnrichmentStatusRecord("crossref", "success"),
        ...         "pubmed": EnrichmentStatusRecord("pubmed", "not_found"),
        ...     },
        ...     field_sources={"title": "chembl", "citations": "crossref"},
        ... )
        >>> lineage.has_enrichment("crossref")
        True
    """

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
        if status is None:
            return False
        return status.status == "success"

    def get_field_source(self, field_name: str) -> str | None:
        """Get the source provider for a field."""
        return self.field_sources.get(field_name)

    @property
    def successful_enrichers(self) -> tuple[str, ...]:
        """Get providers with successful enrichment."""
        return tuple(
            provider
            for provider, status in self.enrichment_status.items()
            if status.status == "success"
        )

    @property
    def failed_enrichers(self) -> tuple[str, ...]:
        """Get providers with failed enrichment."""
        return tuple(
            provider
            for provider, status in self.enrichment_status.items()
            if status.status == "error"
        )

    @property
    def not_found_enrichers(self) -> tuple[str, ...]:
        """Get providers where record was not found."""
        return tuple(
            provider
            for provider, status in self.enrichment_status.items()
            if status.status == "not_found"
        )

    @property
    def enrichment_rate(self) -> float:
        """Calculate ratio of successful enrichments to total attempted."""
        if not self.enrichment_status:
            return 0.0
        successful = len(self.successful_enrichers)
        total = len(self.enrichment_status)
        return successful / total

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for storage/serialization.

        Returns:
            Dictionary suitable for embedding in record metadata.
        """
        return {
            "_composite_run_id": self.composite_run_id,
            "_composite_name": self.composite_name,
            "_source_providers": list(self.source_providers),
            "_enrichment_status": {
                provider: status.status
                for provider, status in self.enrichment_status.items()
            },
            "_enrichment_timestamps": {
                provider: ts.isoformat()
                for provider, ts in self.enrichment_timestamps.items()
            },
            "_field_sources": self.field_sources,
            "_seed_record_id": self.seed_record_id,
            "_lineage_created_at": (
                self.created_at.isoformat() if self.created_at else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> LineageMetadata:
        """Create LineageMetadata from dictionary.

        Args:
            data: Dictionary with lineage fields (prefixed with _).

        Returns:
            LineageMetadata instance.
        """
        enrichment_status = {}
        raw_status = data.get("_enrichment_status", {})
        if isinstance(raw_status, dict):
            for provider, status in raw_status.items():
                enrichment_status[provider] = EnrichmentStatusRecord(
                    provider=provider,
                    status=status if isinstance(status, str) else "error",
                )

        enrichment_timestamps = {}
        raw_timestamps = data.get("_enrichment_timestamps", {})
        if isinstance(raw_timestamps, dict):
            for provider, ts in raw_timestamps.items():
                if isinstance(ts, str):
                    enrichment_timestamps[provider] = datetime.fromisoformat(ts)
                elif isinstance(ts, datetime):
                    enrichment_timestamps[provider] = ts

        source_providers = data.get("_source_providers", [])
        if isinstance(source_providers, list):
            source_providers = tuple(source_providers)

        field_sources = data.get("_field_sources", {})
        if not isinstance(field_sources, dict):
            field_sources = {}

        created_at = None
        raw_created = data.get("_lineage_created_at")
        if isinstance(raw_created, str):
            created_at = datetime.fromisoformat(raw_created)
        elif isinstance(raw_created, datetime):
            created_at = raw_created

        return cls(
            composite_run_id=str(data.get("_composite_run_id", "")),
            composite_name=str(data.get("_composite_name", "")),
            source_providers=source_providers,
            enrichment_status=enrichment_status,
            enrichment_timestamps=enrichment_timestamps,
            field_sources=field_sources,
            seed_record_id=data.get("_seed_record_id"),
            created_at=created_at,
        )


@dataclass(frozen=True, slots=True)
class LineageBuilder:
    """Builder for constructing LineageMetadata incrementally.

    Used during composite pipeline execution to accumulate
    lineage information as each enricher completes.

    Example:
        >>> builder = LineageBuilder(
        ...     composite_run_id="abc-123",
        ...     composite_name="composite_publication",
        ... )
        >>> builder = builder.with_seed_record("doc_123")
        >>> builder = builder.with_enrichment_success("crossref", datetime.now())
        >>> lineage = builder.build()
    """

    composite_run_id: str
    composite_name: str
    _source_providers: tuple[str, ...] = ()
    _enrichment_status: tuple[tuple[str, EnrichmentStatusRecord], ...] = ()
    _enrichment_timestamps: tuple[tuple[str, datetime], ...] = ()
    _field_sources: tuple[tuple[str, str], ...] = ()
    _seed_record_id: str | None = None

    def with_seed_record(self, record_id: str) -> LineageBuilder:
        """Set the seed record ID."""
        return LineageBuilder(
            composite_run_id=self.composite_run_id,
            composite_name=self.composite_name,
            _source_providers=self._source_providers,
            _enrichment_status=self._enrichment_status,
            _enrichment_timestamps=self._enrichment_timestamps,
            _field_sources=self._field_sources,
            _seed_record_id=record_id,
        )

    def with_source_provider(self, provider: str) -> LineageBuilder:
        """Add a source provider."""
        providers = self._source_providers + (provider,)
        return LineageBuilder(
            composite_run_id=self.composite_run_id,
            composite_name=self.composite_name,
            _source_providers=providers,
            _enrichment_status=self._enrichment_status,
            _enrichment_timestamps=self._enrichment_timestamps,
            _field_sources=self._field_sources,
            _seed_record_id=self._seed_record_id,
        )

    def with_enrichment_success(
        self, provider: str, timestamp: datetime
    ) -> LineageBuilder:
        """Record successful enrichment."""
        status = EnrichmentStatusRecord(provider, "success", timestamp)
        return self._with_enrichment(provider, status, timestamp)

    def with_enrichment_not_found(
        self, provider: str, timestamp: datetime
    ) -> LineageBuilder:
        """Record not-found enrichment."""
        status = EnrichmentStatusRecord(provider, "not_found", timestamp)
        return self._with_enrichment(provider, status, timestamp)

    def with_enrichment_error(
        self, provider: str, timestamp: datetime, error: str
    ) -> LineageBuilder:
        """Record failed enrichment."""
        status = EnrichmentStatusRecord(provider, "error", timestamp, error)
        return self._with_enrichment(provider, status, timestamp)

    def with_enrichment_skipped(self, provider: str) -> LineageBuilder:
        """Record skipped enrichment."""
        status = EnrichmentStatusRecord(provider, "skipped")
        statuses = self._enrichment_status + ((provider, status),)
        return LineageBuilder(
            composite_run_id=self.composite_run_id,
            composite_name=self.composite_name,
            _source_providers=self._source_providers,
            _enrichment_status=statuses,
            _enrichment_timestamps=self._enrichment_timestamps,
            _field_sources=self._field_sources,
            _seed_record_id=self._seed_record_id,
        )

    def _with_enrichment(
        self, provider: str, status: EnrichmentStatusRecord, timestamp: datetime
    ) -> LineageBuilder:
        """Internal helper to add enrichment status and timestamp."""
        statuses = self._enrichment_status + ((provider, status),)
        timestamps = self._enrichment_timestamps + ((provider, timestamp),)
        return LineageBuilder(
            composite_run_id=self.composite_run_id,
            composite_name=self.composite_name,
            _source_providers=self._source_providers,
            _enrichment_status=statuses,
            _enrichment_timestamps=timestamps,
            _field_sources=self._field_sources,
            _seed_record_id=self._seed_record_id,
        )

    def with_field_source(self, field_name: str, provider: str) -> LineageBuilder:
        """Record source provider for a field."""
        sources = self._field_sources + ((field_name, provider),)
        return LineageBuilder(
            composite_run_id=self.composite_run_id,
            composite_name=self.composite_name,
            _source_providers=self._source_providers,
            _enrichment_status=self._enrichment_status,
            _enrichment_timestamps=self._enrichment_timestamps,
            _field_sources=sources,
            _seed_record_id=self._seed_record_id,
        )

    def build(self) -> LineageMetadata:
        """Build the final LineageMetadata object."""
        return LineageMetadata(
            composite_run_id=self.composite_run_id,
            composite_name=self.composite_name,
            source_providers=self._source_providers,
            enrichment_status=dict(self._enrichment_status),
            enrichment_timestamps=dict(self._enrichment_timestamps),
            field_sources=dict(self._field_sources),
            seed_record_id=self._seed_record_id,
            created_at=datetime.now(),
        )
