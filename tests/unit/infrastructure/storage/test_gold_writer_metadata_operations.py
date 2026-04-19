"""Unit tests for Gold writer metadata operations."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from bioetl.application.services.lineage import MetadataLineageBundle
from bioetl.domain.lineage import LineageGraphFragment
from bioetl.infrastructure.storage.gold.metadata_operations import (
    _GoldMergedMetadataWriteRequest,
    _GoldMetadataWriteRequest,
    _PreparedGoldMetadataWrite,
    _extract_delta_table_version,
    _maybe_prepare_gold_merged_metadata_write,
    _normalize_delta_version_value,
    _persist_gold_metadata_write,
    _prepare_gold_metadata_write,
)
from tests.unit.infrastructure.storage._lineage_fragment_helpers import (
    make_produced_artifact_fragment,
)

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-gold-writer-metadata-ops-"))
GOLD_CHEMBL_COMPOUND_PATH = str(TEST_ROOT / "gold" / "chembl_compound")
GOLD_COMPOSITE_PUBLICATION_PATH = str(TEST_ROOT / "gold" / "composite" / "publication")
GOLD_MERGED_PATH = str(TEST_ROOT / "gold" / "merged")


def _make_bundle_safe_metadata(run_id: str = "test-run") -> MagicMock:
    """Create metadata mocks compatible with MetadataLineageBundle identity checks."""
    metadata = MagicMock()
    metadata.runtime = SimpleNamespace(run_id=run_id, manifest_id=None)
    metadata.output = SimpleNamespace(lineage_fragment_id=None, artifact_id=None)
    return metadata


@pytest.mark.unit
class TestNormalizeDeltaVersionValue:
    """Tests for Delta version normalization."""

    def test_int_value_passthrough(self) -> None:
        """Integer values should be returned as-is."""
        assert _normalize_delta_version_value(42) == 42

    def test_string_digit_converts_to_int(self) -> None:
        """String digits should be converted to int."""
        assert _normalize_delta_version_value("7") == 7
        assert _normalize_delta_version_value("  12  ") == 12

    def test_non_digit_string_returns_none(self) -> None:
        """Non-digit strings should return None."""
        assert _normalize_delta_version_value("abc") is None

    def test_none_input_returns_none(self) -> None:
        """None input should return None."""
        assert _normalize_delta_version_value(None) is None


@pytest.mark.unit
class TestExtractDeltaTableVersion:
    """Tests for DeltaTable version extraction."""

    def test_extracts_version_from_callable(self) -> None:
        """Should call .version() and return normalized value."""
        table = MagicMock()
        table.version.return_value = 5
        assert _extract_delta_table_version(table) == 5

    def test_returns_none_when_no_version_attr(self) -> None:
        """Should return None when object has no version attribute."""
        table = object()
        assert _extract_delta_table_version(table) is None

    def test_returns_none_when_version_not_callable(self) -> None:
        """Should return None when version is not callable."""
        table = MagicMock()
        table.version = "not_callable_string"
        # version is now a string, but MagicMock makes it callable
        # Use a plain object instead
        table2 = MagicMock(spec=[])
        table2.version = 42  # int, not callable
        assert _extract_delta_table_version(table2) is None


@pytest.mark.unit
class TestPrepareGoldMetadataWrite:
    """Tests for standard Gold metadata preparation."""

    def test_resolves_provider_entity_and_builds_metadata(self) -> None:
        """Should call host methods to resolve provider/entity and build metadata."""
        metadata = _make_bundle_safe_metadata()

        class _Coordinator:
            def create_gold_metadata_bundle(
                self,
                input_data: object,
            ) -> MetadataLineageBundle:
                _ = input_data
                return MetadataLineageBundle(
                    metadata=metadata,
                    lineage_fragment=make_produced_artifact_fragment(
                        fragment_id="gold:prepared-fragment",
                        layer="gold",
                        logical_name="chembl.compound",
                    ),
                )

        host = MagicMock()
        host._metadata_coordinator = _Coordinator()
        host._transform_version = "1.0.0"
        host._transform_steps = ("normalize",)

        from bioetl.domain.medallion import GoldWriteMode

        request = _GoldMetadataWriteRequest(
            table_path=GOLD_CHEMBL_COMPOUND_PATH,
            table_name="chembl_compound",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        )
        prepared = _prepare_gold_metadata_write(host, request)

        assert isinstance(prepared, _PreparedGoldMetadataWrite)
        assert prepared.provider_name == "chembl"
        assert prepared.entity_name == "compound"
        assert prepared.metadata is metadata

    def test_raises_when_coordinator_bundle_is_missing(self) -> None:
        host = MagicMock()
        host._metadata_coordinator = None
        host._transform_version = "1.0.0"
        host._transform_steps = ()

        from bioetl.domain.medallion import GoldWriteMode

        request = _GoldMetadataWriteRequest(
            table_path=GOLD_CHEMBL_COMPOUND_PATH,
            table_name="chembl_compound",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        )

        with pytest.raises(
            RuntimeError,
            match="create_gold_metadata_bundle is required for Gold metadata publication",
        ):
            _prepare_gold_metadata_write(host, request)

    def test_uses_bundle_when_concrete_coordinator_supports_lineage(self) -> None:
        """Concrete coordinators with bundle seam should surface lineage fragments."""

        class _Coordinator:
            def create_gold_metadata_bundle(
                self,
                input_data: object,
            ) -> MetadataLineageBundle:
                _ = input_data
                return MetadataLineageBundle(
                    metadata=metadata,
                    lineage_fragment=fragment,
                )

            def create_gold_metadata(self, input_data: object) -> object:
                _ = input_data
                return metadata

        metadata = _make_bundle_safe_metadata()
        fragment = make_produced_artifact_fragment(
            fragment_id="gold:fragment-1",
            layer="gold",
            logical_name="chembl.compound",
        )
        host = MagicMock()
        host._metadata_coordinator = _Coordinator()
        host._transform_version = "1.0.0"
        host._transform_steps = ("normalize",)

        from bioetl.domain.medallion import GoldWriteMode

        request = _GoldMetadataWriteRequest(
            table_path=GOLD_CHEMBL_COMPOUND_PATH,
            table_name="chembl_compound",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        )

        prepared = _prepare_gold_metadata_write(host, request)

        assert prepared.metadata is metadata
        assert prepared.lineage_fragment == fragment


@pytest.mark.unit
class TestPersistGoldMetadataWrite:
    """Tests for Gold metadata persistence."""

    @pytest.mark.asyncio
    async def test_calls_write_gold_metadata_file(self) -> None:
        """Should delegate to host._write_gold_metadata_file."""
        host = AsyncMock()
        host._metrics = None
        metadata = _make_bundle_safe_metadata()

        from bioetl.domain.medallion import GoldWriteMode

        request = _GoldMetadataWriteRequest(
            table_path=GOLD_CHEMBL_COMPOUND_PATH,
            table_name="chembl_compound",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        )
        prepared = _PreparedGoldMetadataWrite(
            request=request,
            provider_name="chembl",
            entity_name="compound",
            metadata=metadata,
        )
        await _persist_gold_metadata_write(host, prepared)
        host._write_gold_metadata_file.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persists_lineage_fragment_when_store_is_configured(self) -> None:
        """Prepared lineage fragments should be written after metadata handoff."""
        host = AsyncMock()
        host._lineage_store = MagicMock()
        host._metrics = None
        metadata = _make_bundle_safe_metadata()
        fragment = LineageGraphFragment(
            fragment_id="gold:fragment-2",
            created_at=datetime.now(UTC),
        )

        from bioetl.domain.medallion import GoldWriteMode

        request = _GoldMetadataWriteRequest(
            table_path=GOLD_CHEMBL_COMPOUND_PATH,
            table_name="chembl_compound",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
        )
        prepared = _PreparedGoldMetadataWrite(
            request=request,
            provider_name="chembl",
            entity_name="compound",
            metadata=metadata,
            lineage_fragment=fragment,
        )

        await _persist_gold_metadata_write(host, prepared)

        host._lineage_store.save.assert_called_once_with(fragment)

    @pytest.mark.asyncio
    async def test_emits_missing_silver_refs_metric_for_standard_write(self) -> None:
        host = AsyncMock()
        host._lineage_store = None
        host._metrics = MagicMock()
        metadata = _make_bundle_safe_metadata()

        from bioetl.domain.medallion import GoldWriteMode

        request = _GoldMetadataWriteRequest(
            table_path="/tmp/gold/chembl_compound",
            table_name="chembl_compound",
            records=[{"id": 1}],
            mode=GoldWriteMode.APPEND,
            scd_config=None,
            ingestion_ts=None,
            run_id=None,
            silver_refs=None,
        )
        prepared = _PreparedGoldMetadataWrite(
            request=request,
            provider_name="chembl",
            entity_name="compound",
            metadata=metadata,
        )

        await _persist_gold_metadata_write(host, prepared)

        host._metrics.increment_counter.assert_called_once_with(
            "bioetl_lineage_refs_missing_total",
            1,
            {
                "pipeline": "chembl_compound",
                "layer": "gold",
                "ref_type": "silver_dataset",
            },
        )

    @pytest.mark.asyncio
    async def test_emits_composite_source_selection_metrics_for_merged_write(
        self,
    ) -> None:
        host = AsyncMock()
        host._lineage_store = None
        host._metrics = MagicMock()
        metadata = _make_bundle_safe_metadata()
        request = _GoldMergedMetadataWriteRequest(
            table_path=GOLD_COMPOSITE_PUBLICATION_PATH,
            table_name="composite.publication",
            records=[
                {
                    "id": 1,
                    "_source_providers": ["chembl", "pubchem"],
                    "_field_sources": {"title": "chembl", "score": "pubchem"},
                },
                {
                    "id": 2,
                    "_source_providers": ["chembl"],
                    "_field_sources": {"summary": "chembl"},
                },
            ],
        )
        prepared = _PreparedGoldMetadataWrite(
            request=request,
            provider_name="composite",
            entity_name="publication",
            metadata=metadata,
        )

        await _persist_gold_metadata_write(host, prepared)

        host._metrics.increment_counter.assert_has_calls(
            [
                call(
                    "bioetl_composite_source_selection_total",
                    1,
                    {
                        "pipeline": "composite_publication",
                        "decision_type": "gold_source_included",
                        "selected_source": "chembl",
                    },
                ),
                call(
                    "bioetl_composite_source_selection_total",
                    1,
                    {
                        "pipeline": "composite_publication",
                        "decision_type": "gold_source_included",
                        "selected_source": "pubchem",
                    },
                ),
                call(
                    "bioetl_composite_source_selection_total",
                    2,
                    {
                        "pipeline": "composite_publication",
                        "decision_type": "gold_field_selected",
                        "selected_source": "chembl",
                    },
                ),
                call(
                    "bioetl_composite_source_selection_total",
                    1,
                    {
                        "pipeline": "composite_publication",
                        "decision_type": "gold_field_selected",
                        "selected_source": "pubchem",
                    },
                ),
            ],
            any_order=False,
        )


@pytest.mark.unit
class TestMaybePrepareGoldMergedMetadataWrite:
    """Tests for conditional merged metadata preparation."""

    def test_returns_none_when_records_empty(self) -> None:
        """Should skip when records list is empty."""
        host = MagicMock()
        request = _GoldMergedMetadataWriteRequest(
            table_path=GOLD_MERGED_PATH,
            table_name="merged_table",
            records=[],
        )
        result = _maybe_prepare_gold_merged_metadata_write(host, request)
        assert result is None

    def test_raises_when_coordinator_is_none(self) -> None:
        """Merged Gold metadata must fail closed without a coordinator."""
        host = MagicMock()
        host._metadata_coordinator = None
        host._transform_version = "1.0.0"
        host._transform_steps = ()
        request = _GoldMergedMetadataWriteRequest(
            table_path=GOLD_MERGED_PATH,
            table_name="merged_table",
            records=[{"id": 1}],
        )
        with pytest.raises(
            RuntimeError,
            match="create_gold_metadata_bundle is required for Gold metadata publication",
        ):
            _maybe_prepare_gold_merged_metadata_write(host, request)

    def test_prepares_merged_metadata_via_module_helper(self) -> None:
        metadata = _make_bundle_safe_metadata()

        class _Coordinator:
            def create_gold_metadata_bundle(
                self,
                input_data: object,
            ) -> MetadataLineageBundle:
                self.last_input = input_data
                return MetadataLineageBundle(
                    metadata=metadata,
                    lineage_fragment=make_produced_artifact_fragment(
                        fragment_id="gold:merged-fragment",
                        layer="gold",
                        logical_name="composite.publication",
                    ),
                )

        host = MagicMock()
        host._metadata_coordinator = _Coordinator()
        host._transform_version = "2.0.0"
        host._transform_steps = ("normalize",)
        request = _GoldMergedMetadataWriteRequest(
            table_path=GOLD_MERGED_PATH,
            table_name="composite.publication",
            records=[{"id": 1}],
        )

        prepared = _maybe_prepare_gold_merged_metadata_write(host, request)

        assert prepared is not None
        input_arg = host._metadata_coordinator.last_input
        assert input_arg.transform_version == "2.0.0"
        assert prepared.provider_name == "composite"
        assert prepared.entity_name == "publication"
