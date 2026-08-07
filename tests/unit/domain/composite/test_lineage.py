# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
# tests/unit/domain/composite/test_lineage.py
"""Unit tests for composite pipeline lineage models.

Tests for CompositeLineageMetadata, FieldSource, EnrichmentStatusRecord and helper functions.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.composite.lineage import (
    CompositeLineageMetadata,
    EnrichmentStatusRecord,
    FieldSource,
    _ensure_utc,
    _parse_datetime,
    _parse_enrichment_status,
    _parse_field_sources,
    _parse_providers,
    _parse_seed_id,
    _parse_timestamps,
)

pytestmark = pytest.mark.unit


class TestFieldSource:
    """Tests for FieldSource dataclass."""

    def test_create_field_source_minimal(self) -> None:
        """Create FieldSource with minimal required fields."""
        source = FieldSource(
            field_name="doi",
            source_provider="crossref",
            source_pipeline="crossref_publication",
        )
        assert source.field_name == "doi"
        assert source.source_provider == "crossref"
        assert source.source_pipeline == "crossref_publication"
        assert source.extraction_timestamp is None

    def test_create_field_source_with_timestamp(self) -> None:
        """Create FieldSource with extraction timestamp."""
        ts = datetime(2024, 5, 15, 10, 30, 0, tzinfo=UTC)
        source = FieldSource(
            field_name="title",
            source_provider="pubmed",
            source_pipeline="pubmed_article",
            extraction_timestamp=ts,
        )
        assert source.extraction_timestamp == ts

    def test_field_source_is_frozen(self) -> None:
        """FieldSource is frozen (immutable)."""
        source = FieldSource(
            field_name="doi",
            source_provider="crossref",
            source_pipeline="crossref_publication",
        )
        with pytest.raises(AttributeError):
            source.field_name = "new_name"  # type: ignore[misc]


class TestEnrichmentStatusRecord:
    """Tests for EnrichmentStatusRecord dataclass."""

    def test_create_enrichment_status_success(self) -> None:
        """Create EnrichmentStatusRecord with success status."""
        record = EnrichmentStatusRecord(
            provider="crossref",
            status="success",
        )
        assert record.provider == "crossref"
        assert record.status == "success"
        assert record.timestamp is None
        assert record.error_message is None

    def test_create_enrichment_status_error(self) -> None:
        """Create EnrichmentStatusRecord with error status."""
        ts = datetime(2024, 5, 15, 10, 30, 0, tzinfo=UTC)
        record = EnrichmentStatusRecord(
            provider="pubmed",
            status="error",
            timestamp=ts,
            error_message="Connection timeout",
        )
        assert record.provider == "pubmed"
        assert record.status == "error"
        assert record.timestamp == ts
        assert record.error_message == "Connection timeout"

    def test_create_enrichment_status_not_found(self) -> None:
        """Create EnrichmentStatusRecord with not_found status."""
        record = EnrichmentStatusRecord(
            provider="uniprot",
            status="not_found",
        )
        assert record.status == "not_found"

    def test_create_enrichment_status_skipped(self) -> None:
        """Create EnrichmentStatusRecord with skipped status."""
        record = EnrichmentStatusRecord(
            provider="openalex",
            status="skipped",
        )
        assert record.status == "skipped"

    def test_enrichment_status_record_is_frozen(self) -> None:
        """EnrichmentStatusRecord is frozen (immutable)."""
        record = EnrichmentStatusRecord(
            provider="crossref",
            status="success",
        )
        with pytest.raises(AttributeError):
            record.status = "error"  # type: ignore[misc]


class TestCompositeLineageMetadata:
    """Tests for CompositeLineageMetadata dataclass."""

    def test_create_lineage_metadata_minimal(self) -> None:
        """Create CompositeLineageMetadata with minimal required fields."""
        metadata = CompositeLineageMetadata(
            composite_run_id="run-123",
            composite_name="unified_publication",
        )
        assert metadata.composite_run_id == "run-123"
        assert metadata.composite_name == "unified_publication"
        assert metadata.source_providers == ()
        assert metadata.enrichment_status == {}
        assert metadata.enrichment_timestamps == {}
        assert metadata.field_sources == {}
        assert metadata.seed_record_id is None
        assert metadata.created_at is None

    def test_create_lineage_metadata_full(self) -> None:
        """Create CompositeLineageMetadata with all fields."""
        ts = datetime(2024, 5, 15, 10, 30, 0, tzinfo=UTC)
        enrichment_ts = datetime(2024, 5, 15, 10, 35, 0, tzinfo=UTC)

        metadata = CompositeLineageMetadata(
            composite_run_id="run-456",
            composite_name="unified_publication",
            source_providers=("chembl", "crossref", "pubmed"),
            enrichment_status={
                "crossref": EnrichmentStatusRecord(
                    provider="crossref", status="success"
                ),
                "pubmed": EnrichmentStatusRecord(provider="pubmed", status="not_found"),
            },
            enrichment_timestamps={"crossref": enrichment_ts},
            field_sources={"doi": "crossref", "title": "pubmed"},
            seed_record_id="chembl-doc-123",
            created_at=ts,
        )
        assert metadata.source_providers == ("chembl", "crossref", "pubmed")
        assert len(metadata.enrichment_status) == 2
        assert metadata.seed_record_id == "chembl-doc-123"
        assert metadata.created_at == ts

    def test_source_providers_list_converted_to_tuple(self) -> None:
        """Lists should be converted to tuples for immutability."""
        metadata = CompositeLineageMetadata(
            composite_run_id="run-123",
            composite_name="test",
            source_providers=["chembl", "crossref"],  # type: ignore
        )
        assert isinstance(metadata.source_providers, tuple)
        assert metadata.source_providers == ("chembl", "crossref")


class TestCompositeLineageMetadataHasEnrichment:
    """Tests for CompositeLineageMetadata.has_enrichment method."""

    def test_has_enrichment_success(self) -> None:
        """has_enrichment returns True for successful enrichment."""
        metadata = CompositeLineageMetadata(
            composite_run_id="run-123",
            composite_name="test",
            enrichment_status={
                "crossref": EnrichmentStatusRecord(
                    provider="crossref", status="success"
                ),
            },
        )
        assert metadata.has_enrichment("crossref") is True

    def test_has_enrichment_not_found(self) -> None:
        """has_enrichment returns False for not_found status."""
        metadata = CompositeLineageMetadata(
            composite_run_id="run-123",
            composite_name="test",
            enrichment_status={
                "pubmed": EnrichmentStatusRecord(provider="pubmed", status="not_found"),
            },
        )
        assert metadata.has_enrichment("pubmed") is False

    def test_has_enrichment_error(self) -> None:
        """has_enrichment returns False for error status."""
        metadata = CompositeLineageMetadata(
            composite_run_id="run-123",
            composite_name="test",
            enrichment_status={
                "uniprot": EnrichmentStatusRecord(provider="uniprot", status="error"),
            },
        )
        assert metadata.has_enrichment("uniprot") is False

    def test_has_enrichment_missing_provider(self) -> None:
        """has_enrichment returns False for missing provider."""
        metadata = CompositeLineageMetadata(
            composite_run_id="run-123",
            composite_name="test",
            enrichment_status={},
        )
        assert metadata.has_enrichment("crossref") is False


class TestCompositeLineageMetadataSuccessfulEnrichers:
    """Tests for CompositeLineageMetadata.successful_enrichers property."""

    def test_successful_enrichers_multiple(self) -> None:
        """successful_enrichers returns all providers with success status."""
        metadata = CompositeLineageMetadata(
            composite_run_id="run-123",
            composite_name="test",
            enrichment_status={
                "crossref": EnrichmentStatusRecord(
                    provider="crossref", status="success"
                ),
                "pubmed": EnrichmentStatusRecord(provider="pubmed", status="success"),
                "uniprot": EnrichmentStatusRecord(provider="uniprot", status="error"),
            },
        )
        successful = metadata.successful_enrichers
        assert "crossref" in successful
        assert "pubmed" in successful
        assert "uniprot" not in successful

    def test_successful_enrichers_none(self) -> None:
        """successful_enrichers returns empty tuple when none successful."""
        metadata = CompositeLineageMetadata(
            composite_run_id="run-123",
            composite_name="test",
            enrichment_status={
                "crossref": EnrichmentStatusRecord(
                    provider="crossref", status="not_found"
                ),
                "pubmed": EnrichmentStatusRecord(provider="pubmed", status="error"),
            },
        )
        assert metadata.successful_enrichers == ()

    def test_successful_enrichers_empty_status(self) -> None:
        """successful_enrichers returns empty tuple when no enrichments."""
        metadata = CompositeLineageMetadata(
            composite_run_id="run-123",
            composite_name="test",
            enrichment_status={},
        )
        assert metadata.successful_enrichers == ()


class TestCompositeLineageMetadataToDict:
    """Tests for CompositeLineageMetadata.to_dict method."""

    def test_to_dict_minimal(self) -> None:
        """to_dict serializes minimal metadata."""
        metadata = CompositeLineageMetadata(
            composite_run_id="run-123",
            composite_name="test",
        )
        result = metadata.to_dict()

        assert result["_composite_run_id"] == "run-123"
        assert result["_composite_name"] == "test"
        assert result["_source_providers"] == []
        assert result["_enrichment_status"] == {}
        assert result["_enrichment_timestamps"] == {}
        assert result["_field_sources"] == {}
        assert result["_seed_record_id"] is None
        assert result["_lineage_created_at"] is None

    def test_to_dict_full(self) -> None:
        """to_dict serializes full metadata."""
        ts = datetime(2024, 5, 15, 10, 30, 0, tzinfo=UTC)
        enrichment_ts = datetime(2024, 5, 15, 10, 35, 0, tzinfo=UTC)

        metadata = CompositeLineageMetadata(
            composite_run_id="run-456",
            composite_name="unified_publication",
            source_providers=("chembl", "crossref"),
            enrichment_status={
                "crossref": EnrichmentStatusRecord(
                    provider="crossref", status="success"
                ),
            },
            enrichment_timestamps={"crossref": enrichment_ts},
            field_sources={"doi": "crossref"},
            seed_record_id="chembl-doc-123",
            created_at=ts,
        )
        result = metadata.to_dict()

        assert result["_source_providers"] == ["chembl", "crossref"]
        assert result["_enrichment_status"] == {
            "crossref": {
                "status": "success",
                "timestamp": None,
                "error_message": None,
            }
        }
        assert "crossref" in result["_enrichment_timestamps"]
        assert result["_field_sources"] == {"doi": "crossref"}
        assert result["_seed_record_id"] == "chembl-doc-123"
        assert result["_lineage_created_at"] == ts.isoformat()


class TestCompositeLineageMetadataFromDict:
    """Tests for CompositeLineageMetadata.from_dict classmethod."""

    def test_from_dict_minimal(self) -> None:
        """from_dict deserializes minimal data."""
        data = {
            "_composite_run_id": "run-123",
            "_composite_name": "test",
        }
        metadata = CompositeLineageMetadata.from_dict(data)

        assert metadata.composite_run_id == "run-123"
        assert metadata.composite_name == "test"
        assert metadata.source_providers == ()
        assert metadata.enrichment_status == {}

    def test_from_dict_full(self) -> None:
        """from_dict deserializes full data."""
        data = {
            "_composite_run_id": "run-456",
            "_composite_name": "unified_publication",
            "_source_providers": ["chembl", "crossref"],
            "_enrichment_status": {"crossref": "success", "pubmed": "not_found"},
            "_enrichment_timestamps": {"crossref": "2024-05-15T10:35:00+00:00"},
            "_field_sources": {"doi": "crossref"},
            "_seed_record_id": "chembl-doc-123",
            "_lineage_created_at": "2024-05-15T10:30:00+00:00",
        }
        metadata = CompositeLineageMetadata.from_dict(data)

        assert metadata.source_providers == ("chembl", "crossref")
        assert len(metadata.enrichment_status) == 2
        assert metadata.enrichment_status["crossref"].status == "success"
        assert metadata.enrichment_status["pubmed"].status == "not_found"
        assert "crossref" in metadata.enrichment_timestamps
        assert metadata.field_sources == {"doi": "crossref"}
        assert metadata.seed_record_id == "chembl-doc-123"
        assert metadata.created_at is not None

    def test_from_dict_roundtrip(self) -> None:
        """to_dict followed by from_dict preserves data."""
        ts = datetime(2024, 5, 15, 10, 30, 0, tzinfo=UTC)
        original = CompositeLineageMetadata(
            composite_run_id="run-789",
            composite_name="test_pipeline",
            source_providers=("a", "b"),
            enrichment_status={
                "a": EnrichmentStatusRecord(provider="a", status="success"),
            },
            enrichment_timestamps={"a": ts},
            field_sources={"field1": "a"},
            seed_record_id="seed-123",
            created_at=ts,
        )

        serialized = original.to_dict()
        restored = CompositeLineageMetadata.from_dict(serialized)

        assert restored.composite_run_id == original.composite_run_id
        assert restored.composite_name == original.composite_name
        assert restored.source_providers == original.source_providers
        assert restored.field_sources == original.field_sources
        assert restored.seed_record_id == original.seed_record_id


class TestEnsureUtc:
    """Tests for _ensure_utc helper function."""

    def test_ensure_utc_naive_datetime(self) -> None:
        """_ensure_utc adds UTC to naive datetime."""
        naive_dt = datetime(2024, 5, 15, 10, 30, 0)
        result = _ensure_utc(naive_dt)
        assert result.tzinfo == UTC

    def test_ensure_utc_aware_datetime(self) -> None:
        """_ensure_utc preserves aware datetime."""
        aware_dt = datetime(2024, 5, 15, 10, 30, 0, tzinfo=UTC)
        result = _ensure_utc(aware_dt)
        assert result.tzinfo == UTC
        assert result == aware_dt


class TestParseEnrichmentStatus:
    """Tests for _parse_enrichment_status helper function."""

    def test_parse_enrichment_status_valid(self) -> None:
        """_parse_enrichment_status parses valid dict."""
        raw = {"crossref": "success", "pubmed": "not_found"}
        result = _parse_enrichment_status(raw)

        assert len(result) == 2
        assert result["crossref"].provider == "crossref"
        assert result["crossref"].status == "success"
        assert result["pubmed"].status == "not_found"

    def test_parse_enrichment_status_non_string(self) -> None:
        """_parse_enrichment_status handles non-string status."""
        raw = {"crossref": 123}  # type: ignore
        result = _parse_enrichment_status(raw)

        assert result["crossref"].status == "error"

    def test_parse_enrichment_status_not_dict(self) -> None:
        """_parse_enrichment_status returns empty dict for non-dict input."""
        result = _parse_enrichment_status("not a dict")
        assert result == {}

    def test_parse_enrichment_status_none(self) -> None:
        """_parse_enrichment_status returns empty dict for None."""
        result = _parse_enrichment_status(None)  # type: ignore
        assert result == {}


class TestParseTimestamps:
    """Tests for _parse_timestamps helper function."""

    def test_parse_timestamps_iso_string(self) -> None:
        """_parse_timestamps parses ISO string timestamps."""
        raw = {"crossref": "2024-05-15T10:30:00+00:00"}
        result = _parse_timestamps(raw)

        assert "crossref" in result
        assert result["crossref"].tzinfo == UTC

    def test_parse_timestamps_datetime(self) -> None:
        """_parse_timestamps handles datetime objects."""
        ts = datetime(2024, 5, 15, 10, 30, 0)
        raw = {"crossref": ts}
        result = _parse_timestamps(raw)

        assert "crossref" in result
        assert result["crossref"].tzinfo == UTC

    def test_parse_timestamps_not_dict(self) -> None:
        """_parse_timestamps returns empty dict for non-dict input."""
        result = _parse_timestamps("not a dict")
        assert result == {}

    def test_parse_timestamps_invalid_values(self) -> None:
        """_parse_timestamps ignores invalid timestamp values."""
        raw = {"crossref": 123, "pubmed": "2024-05-15T10:30:00+00:00"}
        result = _parse_timestamps(raw)

        assert "crossref" not in result
        assert "pubmed" in result


class TestParseDatetime:
    """Tests for _parse_datetime helper function."""

    def test_parse_datetime_iso_string(self) -> None:
        """_parse_datetime parses ISO string."""
        result = _parse_datetime("2024-05-15T10:30:00+00:00")
        assert result is not None
        assert result.tzinfo == UTC

    def test_parse_datetime_naive_string(self) -> None:
        """_parse_datetime parses naive string and adds UTC."""
        result = _parse_datetime("2024-05-15T10:30:00")
        assert result is not None
        assert result.tzinfo == UTC

    def test_parse_datetime_datetime_object(self) -> None:
        """_parse_datetime handles datetime object."""
        ts = datetime(2024, 5, 15, 10, 30, 0)
        result = _parse_datetime(ts)
        assert result is not None
        assert result.tzinfo == UTC

    def test_parse_datetime_none(self) -> None:
        """_parse_datetime returns None for None input."""
        result = _parse_datetime(None)
        assert result is None

    def test_parse_datetime_invalid(self) -> None:
        """_parse_datetime returns None for invalid input."""
        result = _parse_datetime(123)
        assert result is None


class TestParseProviders:
    """Tests for _parse_providers helper function."""

    def test_parse_providers_list(self) -> None:
        """_parse_providers parses list to tuple."""
        result = _parse_providers(["a", "b", "c"])
        assert result == ("a", "b", "c")

    def test_parse_providers_tuple(self) -> None:
        """_parse_providers preserves tuple."""
        result = _parse_providers(("a", "b"))
        assert result == ("a", "b")

    def test_parse_providers_not_list(self) -> None:
        """_parse_providers returns empty tuple for non-list."""
        result = _parse_providers("not a list")
        assert result == ()

    def test_parse_providers_converts_to_strings(self) -> None:
        """_parse_providers converts elements to strings."""
        result = _parse_providers([1, 2, 3])  # type: ignore
        assert result == ("1", "2", "3")


class TestParseFieldSources:
    """Tests for _parse_field_sources helper function."""

    def test_parse_field_sources_valid(self) -> None:
        """_parse_field_sources parses valid dict."""
        raw = {"doi": "crossref", "title": "pubmed"}
        result = _parse_field_sources(raw)
        assert result == {"doi": "crossref", "title": "pubmed"}

    def test_parse_field_sources_not_dict(self) -> None:
        """_parse_field_sources returns empty dict for non-dict."""
        result = _parse_field_sources("not a dict")
        assert result == {}

    def test_parse_field_sources_converts_to_strings(self) -> None:
        """_parse_field_sources converts keys and values to strings."""
        raw = {1: 2, "a": "b"}  # type: ignore
        result = _parse_field_sources(raw)
        assert "1" in result
        assert result["1"] == "2"
        assert result["a"] == "b"


class TestParseSeedId:
    """Tests for _parse_seed_id helper function."""

    def test_parse_seed_id_string(self) -> None:
        """_parse_seed_id parses string."""
        result = _parse_seed_id("seed-123")
        assert result == "seed-123"

    def test_parse_seed_id_none(self) -> None:
        """_parse_seed_id returns None for None."""
        result = _parse_seed_id(None)
        assert result is None

    def test_parse_seed_id_empty_string(self) -> None:
        """_parse_seed_id returns None for empty string."""
        result = _parse_seed_id("")
        assert result is None

    def test_parse_seed_id_converts_to_string(self) -> None:
        """_parse_seed_id converts non-string to string."""
        result = _parse_seed_id(123)  # type: ignore
        assert result == "123"
