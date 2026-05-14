"""Unit tests for BasePublicationTransformer.

Tests the Template Method pattern and common transformation flow.
Uses a concrete test implementation to verify base class behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.common import BasePublicationTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.types import RunID, RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# =============================================================================
# Helper Entity for BasePublicationTransformer tests
# =============================================================================


@dataclass(frozen=True, kw_only=True)
class StubPublicationEntity(BaseEntity):
    """Stub entity for BasePublicationTransformer tests."""

    # Required field
    test_id: str

    # Optional fields
    title: str | None = None
    abstract: str | None = None
    year: int | None = None
    publication_doi: str | None = None
    publication_date: str | None = None
    _lookup_method: str | None = None
    _original_id: str | None = None

    # Data source identifier
    _source: str = "test_provider"


# =============================================================================
# Concrete Stub Implementation
# =============================================================================


class StubPublicationTransformer(BasePublicationTransformer):
    """Concrete stub implementation for testing BasePublicationTransformer."""

    def _extract_business_data(self, record: BronzeRecord) -> dict[str, Any]:
        """Extract test fields from record."""
        return {
            "test_id": record.get("id"),
            "title": record.get("title"),
            "abstract": record.get("abstract"),
            "year": record.get("year"),
            "publication_doi": record.get("publication_doi"),
            "publication_date": record.get("publication_date"),
            "_source": "test_provider",
            "_lookup_method": record.get("_lookup_method"),
            "_original_id": record.get("_original_id"),
        }

    def _get_primary_id_field(self) -> str:
        """Return primary ID field name."""
        return "test_id"

    def _get_entity_class(self) -> type[BaseEntity]:
        """Return test entity class."""
        return StubPublicationEntity


class StubWithPreValidation(StubPublicationTransformer):
    """Stub transformer with pre-extraction validation for testing."""

    def _pre_extract_validation(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> None:
        """Validate required raw fields."""
        if not record.get("id"):
            raise ValueError("ID is required for test publication")


class StubWithoutFallbackLogging(StubPublicationTransformer):
    """Stub transformer that disables fallback logging."""

    def _should_log_fallback_lookup(self) -> bool:
        """Disable fallback logging."""
        return False


@cache
def _shared_transformer_dependencies() -> Any:
    """Reuse immutable test collaborator wiring within this module."""
    return build_test_transformer_dependencies()


def _create_stub_transformer(
    transformer_class: type[StubPublicationTransformer] = StubPublicationTransformer,
    *,
    provider: str = "test_provider",
    entity_type: str = "publication",
    metrics: object | None = None,
) -> StubPublicationTransformer:
    """Construct a stub transformer with shared immutable dependencies."""
    dependencies = (
        build_test_transformer_dependencies(metrics=metrics)
        if metrics is not None
        else _shared_transformer_dependencies()
    )
    return transformer_class(
        provider=provider,
        entity_type=entity_type,
        dependencies=dependencies,
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def transformer() -> StubPublicationTransformer:
    """Create a stub transformer instance."""
    return _create_stub_transformer()


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    return PipelineContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        logger=mock_logger,
    )


@pytest.fixture
def sample_record() -> dict[str, Any]:
    """Create a sample test record."""
    return {
        "id": "test-12345",
        "title": "Test Publication Title",
        "abstract": "This is a test abstract.",
        "year": 2024,
        "_lookup_method": "doi",
    }


# =============================================================================
# Base Class Behavior Tests
# =============================================================================


class TestBasePublicationTransformerBasics:
    """Tests for basic transformation flow."""

    @pytest.mark.asyncio
    async def test_transform_basic_record(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Should transform a basic record successfully."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert result["test_id"] == "test-12345"
        assert result["title"] == "Test Publication Title"
        assert result["abstract"] == "This is a test abstract."
        assert result["year"] == 2024
        assert result["_source"] == "test_provider"

    @pytest.mark.asyncio
    async def test_transform_generates_entity_id(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Should generate entity ID from primary ID."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert "entity_id" in result
        assert "test_provider" in result["entity_id"]
        assert "test-12345" in result["entity_id"]

    @pytest.mark.asyncio
    async def test_transform_generates_content_hash(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Should generate content hash for versioning."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert "content_hash" in result
        assert len(result["content_hash"]) == 64  # SHA256 hex

    @pytest.mark.asyncio
    async def test_transform_pre_silver_returns_staged_payload(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Application runtime should be able to request staged publication payloads."""
        result = await transformer.transform_pre_silver(mock_context, sample_record, 0)

        assert isinstance(result, PreSilverRecord)
        assert result.entity_id == "test_provider:test-12345"
        assert result.business_data["test_id"] == "test-12345"
        assert "content_hash" not in result.business_data

    @pytest.mark.asyncio
    async def test_transform_matches_staged_finalization_for_normalized_fields(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Legacy transform should match staged finalization after normalization."""
        record = {
            "id": "test-12345",
            "title": "  Test Publication Title  ",
            "abstract": "This is a test abstract.",
            "publication_doi": " HTTPS://doi.org/10.1000/ABC123 ",
            "publication_date": "2024-05",
            "_lookup_method": "doi",
        }

        pre_silver = await transformer.transform_pre_silver(mock_context, record, 0)
        assert isinstance(pre_silver, PreSilverRecord)
        staged_result = RecordNormalizationProcessor(
            provider=transformer.provider,
        ).finalize_pre_silver(pre_silver, mock_context, 0)
        legacy_result = await transformer.transform(mock_context, record, 0)

        assert staged_result is not None
        assert legacy_result is not None
        assert legacy_result["publication_doi"] == staged_result["publication_doi"]
        assert legacy_result["publication_date"] == staged_result["publication_date"]
        assert legacy_result["title"] == staged_result["title"]
        assert legacy_result["entity_id"] == staged_result["entity_id"]
        assert legacy_result["content_hash"] == staged_result["content_hash"]
        assert legacy_result["publication_doi"] == "10.1000/abc123"
        assert legacy_result["publication_date"] == "2024-05-31"

    @pytest.mark.asyncio
    async def test_transform_adds_lineage_fields(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Should add lineage fields from context."""
        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert "_run_id" in result
        assert "_run_type" in result
        assert "_ingestion_ts" in result
        assert "_index" in result
        assert "_run_type" in result
        assert result["_index"] == 0

    @pytest.mark.asyncio
    async def test_transform_content_hash_excludes_metadata(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Content hash should exclude fields starting with underscore."""
        record1 = {
            "id": "test-1",
            "title": "Same Title",
            "_lookup_method": "doi",
        }
        record2 = {
            "id": "test-1",
            "title": "Same Title",
            "_lookup_method": "title_fallback",  # Different metadata
            "_original_id": "10.1234/failed",
        }

        result1 = await transformer.transform(mock_context, record1, 0)
        result2 = await transformer.transform(mock_context, record2, 0)

        assert result1 is not None
        assert result2 is not None
        # Content hash should be the same (metadata excluded)
        assert result1["content_hash"] == result2["content_hash"]


# =============================================================================
# Missing Primary ID Tests
# =============================================================================


class TestMissingPrimaryId:
    """Tests for handling missing primary ID."""

    @pytest.mark.asyncio
    async def test_missing_id_raises_filtered_out_error(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Missing primary ID should use runtime disposition, not silent drop."""
        record = {
            "id": None,
            "title": "No ID Record",
        }

        with pytest.raises(FilteredOutError) as exc_info:
            await transformer.transform(mock_context, record, 0)

        assert exc_info.value.details["policy_stage"] == "structural"
        assert exc_info.value.details["reason_code"] == (
            "missing_publication_primary_id"
        )
        assert exc_info.value.details["rule_type"] == "required_fields"

    @pytest.mark.asyncio
    async def test_missing_id_logs_warning(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Should log warning when primary ID is missing."""
        record = {
            "id": None,
            "title": "No ID Record",
            "_lookup_method": "title_fallback",
        }

        with pytest.raises(FilteredOutError) as exc_info:
            await transformer.transform(mock_context, record, 0)

        mock_context.logger.warning.assert_called_once()
        call_args = mock_context.logger.warning.call_args
        assert call_args[0][0] == "record_skipped_no_id"
        assert exc_info.value.details["lookup_method"] == "title_fallback"

    @pytest.mark.asyncio
    async def test_empty_string_id_raises_filtered_out_error(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Empty-string primary ID should not disappear silently."""
        record = {
            "id": "",
            "title": "Empty ID Record",
        }

        with pytest.raises(FilteredOutError) as exc_info:
            await transformer.transform(mock_context, record, 0)

        assert exc_info.value.details["reason_code"] == (
            "missing_publication_primary_id"
        )


# =============================================================================
# Fallback Lookup Logging Tests
# =============================================================================


class TestFallbackLookupLogging:
    """Tests for fallback lookup logging behavior."""

    @pytest.mark.asyncio
    async def test_logs_title_fallback(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Should log info when title_fallback is used."""
        record = {
            "id": "test-123",
            "title": "Fallback Record",
            "_lookup_method": "title_fallback",
            "_original_id": "10.1234/failed",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        mock_context.logger.info.assert_called()
        call_args = mock_context.logger.info.call_args
        assert call_args[0][0] == "fallback_lookup_used"

    @pytest.mark.asyncio
    async def test_logs_title_only(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Should log info when title_only is used."""
        record = {
            "id": "test-123",
            "title": "Title Only Record",
            "_lookup_method": "title_only",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        mock_context.logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_no_log_for_doi_lookup(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Should not log fallback info for regular DOI lookup."""
        sample_record["_lookup_method"] = "doi"

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        # info should not be called for fallback_lookup_used
        for call in mock_context.logger.info.call_args_list:
            assert call[0][0] != "fallback_lookup_used"

    @pytest.mark.asyncio
    async def test_disabled_fallback_logging(
        self,
        mock_context: PipelineContext,
    ) -> None:
        """Should not log fallback when disabled."""
        transformer = _create_stub_transformer(StubWithoutFallbackLogging)
        record = {
            "id": "test-123",
            "title": "Title",
            "_lookup_method": "title_fallback",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        # info should not be called for fallback_lookup_used
        for call in mock_context.logger.info.call_args_list:
            assert call[0][0] != "fallback_lookup_used"


# =============================================================================
# Pre-Extraction Validation Tests
# =============================================================================


class TestPreExtractValidation:
    """Tests for pre-extraction validation hook."""

    @pytest.mark.asyncio
    async def test_pre_validation_raises_value_error(
        self,
        mock_context: PipelineContext,
    ) -> None:
        """Direct transform() must re-raise pre-validation ValueError."""
        transformer = _create_stub_transformer(StubWithPreValidation)
        record = {
            "id": None,  # Will fail pre-validation
            "title": "Test",
        }

        with pytest.raises(ValueError, match="ID is required for test publication"):
            await transformer.transform(mock_context, record, 0)

    @pytest.mark.asyncio
    async def test_pre_validation_passes(
        self,
        mock_context: PipelineContext,
        sample_record: dict[str, Any],
    ) -> None:
        """Should proceed with transformation when pre-validation passes."""
        transformer = _create_stub_transformer(StubWithPreValidation)

        result = await transformer.transform(mock_context, sample_record, 0)

        assert result is not None
        assert result["test_id"] == "test-12345"


class TestPublicationVocabularyObservability:
    """Tests for bounded publication vocabulary drift metrics."""

    def test_unknown_crossref_publication_type_emits_metric(self) -> None:
        metrics = MagicMock()
        transformer = _create_stub_transformer(provider="crossref", metrics=metrics)
        context = PipelineContext(
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            logger=MagicMock(),
            pipeline_name="crossref_publication",
        )

        transformer._emit_unknown_publication_vocab_metrics(
            context,
            {"publication_type": "future-article"},
        )

        metrics.increment_counter.assert_called_once_with(
            name="bioetl_publication_raw_vocab_unknown_total",
            value=1,
            labels={
                "pipeline": "crossref_publication",
                "provider": "crossref",
                "field": "publication_type",
                "handling": "preserved_unknown",
            },
        )

    def test_known_publication_vocab_does_not_emit_metric(self) -> None:
        metrics = MagicMock()
        transformer = _create_stub_transformer(provider="openalex", metrics=metrics)
        context = PipelineContext(
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            logger=MagicMock(),
            pipeline_name="openalex_publication",
        )

        transformer._emit_unknown_publication_vocab_metrics(
            context,
            {
                "publication_type": "article",
                "type_crossref": "journal-article",
            },
        )

        metrics.increment_counter.assert_not_called()

    def test_unknown_openalex_vocab_counts_each_unknown_field(self) -> None:
        metrics = MagicMock()
        transformer = _create_stub_transformer(provider="openalex", metrics=metrics)
        context = PipelineContext(
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            logger=MagicMock(),
            pipeline_name="openalex_publication",
        )

        transformer._emit_unknown_publication_vocab_metrics(
            context,
            {
                "publication_type": "future-openalex-type",
                "type_crossref": "future-crossref-type",
            },
        )

        assert metrics.increment_counter.call_count == 2
        assert {
            call.kwargs["labels"]["field"]
            for call in metrics.increment_counter.call_args_list
        } == {"publication_type", "type_crossref"}

    def test_unknown_pubmed_vocab_counts_each_field(self) -> None:
        metrics = MagicMock()
        transformer = _create_stub_transformer(provider="pubmed", metrics=metrics)
        context = PipelineContext(
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            logger=MagicMock(),
            pipeline_name="pubmed_publication",
        )

        transformer._emit_unknown_publication_vocab_metrics(
            context,
            {
                "publication_types": '["Journal Article","Future Type"]',
                "publication_status": "future-status",
            },
        )

        assert metrics.increment_counter.call_count == 2

    def test_unknown_semanticscholar_publication_types_emit_metric(self) -> None:
        metrics = MagicMock()
        transformer = _create_stub_transformer(
            provider="semanticscholar",
            metrics=metrics,
        )
        context = PipelineContext(
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            logger=MagicMock(),
            pipeline_name="semanticscholar_publication",
        )

        transformer._emit_unknown_publication_vocab_metrics(
            context,
            {"publication_types": ["JournalArticle", "FutureSemanticType"]},
        )

        metrics.increment_counter.assert_called_once_with(
            name="bioetl_publication_raw_vocab_unknown_total",
            value=1,
            labels={
                "pipeline": "semanticscholar_publication",
                "provider": "semanticscholar",
                "field": "publication_types",
                "handling": "preserved_unknown",
            },
        )


# =============================================================================
# Lookup Metadata Preservation Tests
# =============================================================================


class TestLookupMetadataPreservation:
    """Tests for preserving lookup metadata in output."""

    @pytest.mark.asyncio
    async def test_preserves_lookup_method(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Should preserve _lookup_method in Silver record."""
        record = {
            "id": "test-123",
            "title": "Test",
            "_lookup_method": "title_fallback",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["_lookup_method"] == "title_fallback"

    @pytest.mark.asyncio
    async def test_preserves_original_id(
        self,
        transformer: StubPublicationTransformer,
        mock_context: PipelineContext,
    ) -> None:
        """Should preserve _original_id in Silver record."""
        record = {
            "id": "test-123",
            "title": "Test",
            "_lookup_method": "title_fallback",
            "_original_id": "10.1234/original",
        }

        result = await transformer.transform(mock_context, record, 0)

        assert result is not None
        assert result["_original_id"] == "10.1234/original"


# =============================================================================
# Provider Configuration Tests
# =============================================================================


class TestProviderConfiguration:
    """Tests for provider and entity type configuration."""

    def test_provider_attribute(self) -> None:
        """Should set provider attribute correctly."""
        transformer = _create_stub_transformer(provider="custom_provider")
        assert transformer.provider == "custom_provider"

    def test_entity_type_attribute(self) -> None:
        """Should set entity_type attribute correctly."""
        transformer = _create_stub_transformer(
            provider="test", entity_type="custom_type"
        )
        assert transformer.entity_type == "custom_type"

    def test_default_entity_type(self) -> None:
        """Should use 'publication' as default entity_type."""
        transformer = _create_stub_transformer(provider="test")
        assert transformer.entity_type == "publication"


# =============================================================================
# Abstract Method Contract Tests
# =============================================================================


class TestAbstractMethodContracts:
    """Tests verifying abstract method contracts."""

    def test_get_primary_id_field_returns_string(
        self,
        transformer: StubPublicationTransformer,
    ) -> None:
        """_get_primary_id_field should return a string."""
        result = transformer._get_primary_id_field()
        assert isinstance(result, str)
        assert result == "test_id"

    def test_get_entity_class_returns_type(
        self,
        transformer: StubPublicationTransformer,
    ) -> None:
        """_get_entity_class should return a type."""
        result = transformer._get_entity_class()
        assert isinstance(result, type)
        assert issubclass(result, BaseEntity)

    def test_should_log_fallback_default_true(
        self,
        transformer: StubPublicationTransformer,
    ) -> None:
        """_should_log_fallback_lookup should default to True."""
        assert transformer._should_log_fallback_lookup() is True

    def test_should_log_fallback_can_be_overridden(self) -> None:
        """_should_log_fallback_lookup can be overridden to False."""
        transformer = _create_stub_transformer(
            StubWithoutFallbackLogging,
            provider="test",
        )
        assert transformer._should_log_fallback_lookup() is False
