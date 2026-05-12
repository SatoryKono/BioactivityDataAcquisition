"""Unit tests for BatchTransformer."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.batch_transformer import BatchTransformer, TransformResult
from bioetl.application.core.transformer_runtime.finalization import (
    finalize_batch_transform_result,
    finalize_stream_transform_result,
)
from bioetl.application.core.transformer_runtime import (
    orchestration as batch_transformer_orchestration,
)
from bioetl.application.core.transformer_runtime.state import (
    RecordTransformOutcome,
    TransformedRecord,
    apply_stream_transform_result_to_state,
    apply_transform_outcome_to_state,
    build_transform_result,
    create_transform_aggregation_state,
)
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.quarantine_manager import (
    FilteredQuarantineEntry,
)
from bioetl.domain.config import DQConfig
from bioetl.domain.config.validation import FieldValidation
from bioetl.domain.exceptions import DataQualityError, DataQualityThresholdError
from bioetl.domain.transformations import generate_content_hash
from bioetl.domain.types import BatchID

pytest_plugins = ("tests.unit.application.core.transformer_test_support",)


@pytest.mark.unit
class TestBatchTransformerTransform:
    """Tests for BatchTransformer.transform_batch method."""

    async def test_transform_batch_returns_silver_and_gold_records(
        self, batch_transformer
    ):
        """Test successful transformation returns correct records."""
        records = [
            {"id": "1", "value": 10},  # Goes to gold (value > 5)
            {"id": "2", "value": 3},  # Not in gold
        ]
        batch_id = BatchID(uuid4())

        result = await batch_transformer.transform_batch(records, batch_id)

        assert isinstance(result, TransformResult)
        assert len(result.silver_records) == 2
        assert len(result.gold_records) == 1
        assert result.quarantined_count == 0

    async def test_transform_batch_empty_records(self, batch_transformer):
        """Test transformation with empty records list."""
        result = await batch_transformer.transform_batch([], BatchID(uuid4()))

        assert result.silver_records == []
        assert result.gold_records == []
        assert result.quarantined_count == 0

    async def test_transform_batch_cooperatively_yields_to_event_loop(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
        monkeypatch,
    ) -> None:
        """Long-running transform loops should yield so heartbeat tasks can run."""
        marker_event = asyncio.Event()
        saw_background_progress = False

        async def marker() -> None:
            await asyncio.sleep(0)
            marker_event.set()

        async def blocking_transform(ctx, record, index):
            nonlocal saw_background_progress
            await asyncio.sleep(0)
            if index > 0 and marker_event.is_set():
                saw_background_progress = True
            deadline = time.perf_counter() + 0.003
            while time.perf_counter() < deadline:
                continue
            return {"entity_id": record.get("id"), "value": record.get("value")}

        monkeypatch.setattr(
            batch_transformer_orchestration,
            "YIELD_INTERVAL_SECONDS",
            0.001,
        )
        transformer = BatchTransformer(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
            ),
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=blocking_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )
        marker_task = asyncio.create_task(marker())

        await transformer.transform_batch(
            [{"id": str(i), "value": i} for i in range(12)],
            BatchID(uuid4()),
        )
        await marker_task

        assert saw_background_progress is True

    async def test_transform_batch_binds_source_batch_id_into_record_context(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ) -> None:
        """Per-record transform context should carry the active batch identifier."""

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            return {
                "entity_id": record.get("id", "unknown"),
                "value": record.get("value", 0),
                "_source_batch_id": str(ctx.source_batch_id),
            }

        transformer = BatchTransformer(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
            ),
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )
        batch_id = BatchID(uuid4())

        result = await transformer.transform_batch([{"id": "1", "value": 1}], batch_id)

        assert result.silver_records[0].get("_source_batch_id") == str(batch_id)

    async def test_transform_batch_quarantines_dq_errors(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that data quality errors result in quarantine."""

        async def failing_transform(ctx, record, index):
            await asyncio.sleep(0)
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=failing_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        records = [
            {"id": "good", "value": 10},
            {"id": "bad", "value": 5},
        ]
        batch_id = BatchID(uuid4())

        result = await transformer.transform_batch(records, batch_id)

        assert len(result.silver_records) >= 1
        assert result.quarantined_count >= 0

    async def test_transform_batch_normalizes_before_gold_filter(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_transform_callback,
    ) -> None:
        """Gold filter should see finalized staged payloads after normalization."""

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            return PreSilverRecord(
                entity_id="crossref:10.1000/abc",
                business_data={
                    "publication_doi": " HTTPS://doi.org/10.1000/ABC ",
                    "publication_date": "2024-02",
                    "title": "  Example Title  ",
                },
                build_silver_record=build_silver_record,
            )

        def build_silver_record(context, entity_id, content_hash, index, business_data):
            return {
                "entity_id": "crossref:raw",
                "content_hash": content_hash,
                **business_data,
                "_run_id": str(context.run_id),
            }

        seen_record: dict[str, object] = {}

        def filter_gold(ctx, record):
            seen_record.update(record)
            return True

        transformer = BatchTransformer(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="crossref_publication",
                provider="crossref",
                entity_type="publication",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
            ),
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=transform,
            gold_filter_callback=filter_gold,
            gold_transform_callback=gold_transform_callback,
        )

        result = await transformer.transform_batch([{"id": "1"}], BatchID(uuid4()))

        assert len(result.gold_records) == 1
        assert seen_record.get("publication_doi") == "10.1000/abc"
        assert seen_record.get("publication_date") == "2024-02-29"
        assert seen_record.get("title") == "Example Title"
        assert seen_record.get("_run_id") == str(mock_context.run_id)
        assert seen_record.get("content_hash") == str(
            generate_content_hash(
                {
                    "publication_doi": "10.1000/abc",
                    "publication_date": "2024-02-29",
                    "title": "Example Title",
                },
                "crossref",
                exclude_none=True,
            )
        )
        mock_quarantine_manager.quarantine_records.assert_not_called()

    async def test_transform_batch_staged_normalization_preserves_cardinality_and_quarantine(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_transform_callback,
    ) -> None:
        """Normalization should not change batch counts or quarantine semantics."""

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            if record["id"] == "bad":
                raise DataQualityError("Invalid data")
            return PreSilverRecord(
                entity_id=f"crossref:{record['id']}",
                business_data={
                    "publication_doi": record["doi"],
                    "title": record["title"],
                },
                build_silver_record=build_silver_record,
            )

        def build_silver_record(context, entity_id, content_hash, index, business_data):
            return {
                "entity_id": entity_id,
                "content_hash": content_hash,
                **business_data,
                "_run_id": str(context.run_id),
            }

        def filter_gold(ctx, record):
            return True

        transformer = BatchTransformer(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="crossref_publication",
                provider="crossref",
                entity_type="publication",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
            ),
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=transform,
            gold_filter_callback=filter_gold,
            gold_transform_callback=gold_transform_callback,
        )

        result = await transformer.transform_batch(
            [
                {"id": "1", "doi": " HTTPS://doi.org/10.1000/ABC ", "title": "  A  "},
                {"id": "bad", "doi": "10.1000/bad", "title": "Bad"},
                {"id": "2", "doi": "10.1000/xyz", "title": "  B  "},
            ],
            BatchID(uuid4()),
        )

        assert len(result.silver_records) == 2
        assert len(result.gold_records) == 2
        assert result.quarantined_count == 1
        assert result.filtered_out_count == 0
        mock_quarantine_manager.quarantine_records.assert_called_once()

    async def test_transform_batch_raises_non_dq_errors(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that non-DQ errors are re-raised."""
        from bioetl.domain.exceptions import LockLostError

        async def failing_transform(ctx, record, index):
            await asyncio.sleep(0)
            raise LockLostError("resource_key", "test_run_id")

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=failing_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        records = [{"id": "test", "value": 5}]
        batch_id = BatchID(uuid4())

        with pytest.raises(LockLostError):
            await transformer.transform_batch(records, batch_id)

    async def test_transform_batch_quarantines_filtered_out(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that filter exclusions are captured in quarantine storage."""
        from bioetl.application.core.base_transformer import FilteredOutError

        async def filtered_transform(ctx, record, index):
            await asyncio.sleep(0)
            if record.get("id") == "filtered":
                raise FilteredOutError(
                    "Record excluded by silver filters",
                    details={
                        "reason_code": "required_field_missing",
                        "rule_type": "required_fields",
                        "field": "publication_year",
                    },
                )
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=filtered_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        records = [
            {"id": "good", "value": 10},
            {"id": "filtered", "value": 5},
        ]
        batch_id = BatchID(uuid4())

        result = await transformer.transform_batch(records, batch_id)

        assert len(result.silver_records) >= 1
        assert result.quarantined_count == 0
        assert result.filtered_out_count >= 0
        mock_quarantine_manager.quarantine_filtered_records.assert_called_once()
        assert (
            mock_quarantine_manager.quarantine_filtered_records.call_args.kwargs[
                "run_id"
            ]
            == mock_context.run_id
        )
        mock_batch_metrics.track_silver_filter_rejection.assert_called_once_with(
            {
                "reason_code": "required_field_missing",
                "rule_type": "required_fields",
                "field": "publication_year",
            }
        )

    async def test_transform_batch_continues_when_bulk_filtered_quarantine_fails(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ) -> None:
        """Bulk quarantine failure should not fail batch transformation."""
        from bioetl.application.core.base_transformer import FilteredOutError

        async def filtered_transform(ctx, record, index):
            await asyncio.sleep(0)
            raise FilteredOutError("Record excluded by silver filters")

        mock_quarantine_manager.quarantine_filtered_records.side_effect = RuntimeError(
            "disk full"
        )
        transformer = BatchTransformer(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
            ),
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=filtered_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        result = await transformer.transform_batch(
            [{"id": "filtered", "value": 5}],
            BatchID(uuid4()),
        )

        assert result.filtered_out_count >= 0
        assert result.records_quarantine_failed >= 0
        mock_context.logger.error.assert_called()

    async def test_transform_batch_continues_when_bulk_dq_quarantine_fails(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ) -> None:
        """DQ quarantine write failure should not fail batch transformation."""

        async def failing_transform(ctx, record, index):
            await asyncio.sleep(0)
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        mock_quarantine_manager.quarantine_records.side_effect = RuntimeError(
            "disk full"
        )
        transformer = BatchTransformer(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
            ),
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=failing_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        result = await transformer.transform_batch(
            [{"id": "good", "value": 10}, {"id": "bad", "value": 5}],
            BatchID(uuid4()),
        )

        assert len(result.silver_records) >= 1
        assert result.quarantined_count >= 0
        assert result.records_quarantine_failed >= 0
        mock_context.logger.error.assert_called()

    async def test_transform_batch_runtime_dq_quarantines_invalid_record(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ) -> None:
        """Runtime DQ field rules should quarantine invalid normalized records."""

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            return {"entity_id": record.get("id"), "value": record.get("value")}

        transformer = BatchTransformer(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
                dq_config=DQConfig(
                    soft_fail_threshold=0.75,
                    hard_fail_threshold=1.0,
                    field_validations=(
                        FieldValidation(
                            field="value",
                            validation_type="range",
                            min_value=0,
                        ),
                    ),
                    invalid_record_policy="quarantine",
                ),
            ),
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        result = await transformer.transform_batch(
            [{"id": "good", "value": 1}, {"id": "bad", "value": -1}],
            BatchID(uuid4()),
        )

        assert len(result.silver_records) == 1
        assert len(result.gold_records) == 0
        assert result.quarantined_count == 1
        mock_quarantine_manager.quarantine_records.assert_called_once()

    async def test_transform_batch_runtime_dq_skip_policy_drops_invalid_record(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ) -> None:
        """Runtime DQ should honor skip disposition for invalid records."""

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            return {"entity_id": record.get("id"), "value": record.get("value")}

        transformer = BatchTransformer(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
                dq_config=DQConfig(
                    field_validations=(
                        FieldValidation(
                            field="value",
                            validation_type="range",
                            min_value=0,
                        ),
                    ),
                    invalid_record_policy="skip",
                ),
            ),
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        result = await transformer.transform_batch(
            [{"id": "bad", "value": -1}],
            BatchID(uuid4()),
        )

        assert result.silver_records == []
        assert result.gold_records == []
        assert result.quarantined_count == 0
        mock_quarantine_manager.quarantine_records.assert_not_called()

    async def test_transform_batch_runtime_dq_fail_policy_raises(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ) -> None:
        """Runtime DQ should hard-fail when policy is set to fail."""

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            return {"entity_id": record.get("id"), "value": record.get("value")}

        transformer = BatchTransformer(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
                dq_config=DQConfig(
                    field_validations=(
                        FieldValidation(
                            field="value",
                            validation_type="range",
                            min_value=0,
                        ),
                    ),
                    invalid_record_policy="fail",
                ),
            ),
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        with pytest.raises(DataQualityError, match="Runtime DQ validation failed"):
            await transformer.transform_batch(
                [{"id": "bad", "value": -1}],
                BatchID(uuid4()),
            )

    async def test_transform_batch_filtered_skip_policy_drops_record(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ) -> None:
        """Filtered-out records should obey skip invalid-record policy."""
        from bioetl.application.core.base_transformer import FilteredOutError

        async def filtered_transform(ctx, record, index):
            await asyncio.sleep(0)
            raise FilteredOutError("Record excluded by silver filters")

        transformer = BatchTransformer(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
                dq_config=DQConfig(invalid_record_policy="skip"),
            ),
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=filtered_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        result = await transformer.transform_batch(
            [{"id": "filtered", "value": 5}],
            BatchID(uuid4()),
        )

        assert result.filtered_out_count == 0
        mock_quarantine_manager.quarantine_filtered_records.assert_not_called()


@pytest.mark.unit
class TestBatchTransformerAggregationHelpers:
    """Tests for batch-transform aggregation helpers."""

    def test_apply_transform_outcome_updates_state_and_builds_result(self) -> None:
        """Batch aggregation helper should track quarantined and filtered counts."""
        state = create_transform_aggregation_state()

        apply_transform_outcome_to_state(
            state=state,
            attempt=RecordTransformOutcome(
                silver_record=None,
                gold_record=None,
                filtered_entry=FilteredQuarantineEntry({"id": "filtered"}, "why"),
            ),
        )
        apply_transform_outcome_to_state(
            state=state,
            attempt=RecordTransformOutcome(
                silver_record=None,
                gold_record=None,
                dq_entry=({"id": "bad"}, MagicMock(), "error"),
            ),
        )

        state.records_quarantine_failed = 3
        result = build_transform_result(state)

        assert len(state.filtered_records) == 1
        assert len(state.dq_records) == 1
        assert result.quarantined_count == 1
        assert result.filtered_out_count == 1
        assert result.records_quarantine_failed == 3

    async def test_finalize_batch_transform_result_flushes_and_builds_result(
        self,
        mock_context,
        mock_quarantine_manager,
        mock_batch_metrics,
    ) -> None:
        """Batch finalizer should flush quarantine state and build result."""
        state = create_transform_aggregation_state()
        state.filtered_records.append(
            FilteredQuarantineEntry({"id": "filtered"}, "why")
        )
        state.dq_records.append(({"id": "bad"}, MagicMock(), "error"))
        state.filtered_out_count = 1
        state.quarantined_count = 1
        mock_quarantine_manager.quarantine_filtered_records.return_value = 0
        mock_quarantine_manager.quarantine_records.return_value = 0

        result = await finalize_batch_transform_result(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="test_provider_test_entity",
                provider="test_provider",
                entity_type="test_entity",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
            ),
            batch_metrics=mock_batch_metrics,
            state=state,
            records=[{"id": "filtered"}, {"id": "bad"}],
            flush_filtered_records=lambda: (
                mock_quarantine_manager.quarantine_filtered_records()
            ),
            flush_dq_records=lambda: mock_quarantine_manager.quarantine_records(),
        )

        mock_quarantine_manager.quarantine_filtered_records.assert_called_once()
        mock_quarantine_manager.quarantine_records.assert_called_once()
        assert result.filtered_out_count >= 0
        assert result.quarantined_count >= 0
        assert result.records_quarantine_failed == 0

    def test_apply_stream_transform_result_updates_state(self) -> None:
        """Stream aggregation helper should accumulate counters and records."""
        state = create_transform_aggregation_state()

        apply_stream_transform_result_to_state(
            state=state,
            result=TransformedRecord(
                silver_record={"entity_id": "1"},
                gold_record={"entity_id": "1"},
                is_quarantined=False,
            ),
        )
        apply_stream_transform_result_to_state(
            state=state,
            result=TransformedRecord(
                silver_record=None,
                gold_record=None,
                is_quarantined=True,
                quarantine_write_failed=True,
            ),
        )

        result = build_transform_result(state)
        assert len(result.silver_records) == 1
        assert len(result.gold_records) == 1
        assert result.quarantined_count == 1
        assert result.records_quarantine_failed == 1

    @pytest.mark.asyncio
    async def test_finalize_stream_transform_result_builds_result(
        self, mock_context
    ) -> None:
        """Stream finalizer should validate thresholds and build result."""
        state = create_transform_aggregation_state()
        apply_stream_transform_result_to_state(
            state=state,
            result=TransformedRecord(
                silver_record={"entity_id": "1"},
                gold_record=None,
                is_quarantined=False,
            ),
        )

        result = await finalize_stream_transform_result(
            context=mock_context,
            config=RecordProcessorConfig(
                pipeline_name="test_provider_test_entity",
                provider="test_provider",
                entity_type="test_entity",
                silver_schema=MagicMock(),
                gold_schema=MagicMock(),
            ),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
            state=state,
            records=[{"id": "1"}],
            flush_filtered_records=lambda: asyncio.sleep(0),  # No-op async function
            flush_dq_records=lambda: asyncio.sleep(0),  # No-op async function
        )

        assert len(result.silver_records) == 1
        assert result.filtered_out_count == 0
        assert result.quarantined_count == 0


@pytest.mark.unit
class TestBatchTransformerDQThresholds:
    """Tests for DQ threshold checking."""

    async def test_hard_threshold_exceeded_raises_error(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that exceeding hard threshold raises DataQualityThresholdError."""

        async def failing_transform(ctx, record, index):
            await asyncio.sleep(0)
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(soft_fail_threshold=0.1, hard_fail_threshold=0.4),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=failing_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        # 50% error rate (1/2) > hard_fail_threshold (0.4)
        records = [
            {"id": "good", "value": 10},
            {"id": "bad", "value": 5},
        ]
        batch_id = BatchID(uuid4())

        with pytest.raises(DataQualityThresholdError):
            await transformer.transform_batch(records, batch_id)

    async def test_soft_threshold_logs_warning(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that exceeding soft threshold logs warning but doesn't raise."""

        async def failing_transform(ctx, record, index):
            await asyncio.sleep(0)
            if record.get("id") == "bad":
                raise DataQualityError("Invalid data")
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(soft_fail_threshold=0.1, hard_fail_threshold=0.9),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=failing_transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        # 50% error rate > soft_fail_threshold (0.1) but < hard_fail_threshold (0.9)
        records = [
            {"id": "good", "value": 10},
            {"id": "bad", "value": 5},
        ]
        batch_id = BatchID(uuid4())

        result = await transformer.transform_batch(records, batch_id)

        assert len(result.silver_records) == 1
        assert result.quarantined_count == 1
        mock_context.logger.warning.assert_called_once()

    async def test_below_thresholds_no_warning(
        self,
        mock_context,
        mock_error_classifier,
        mock_quarantine_manager,
        mock_batch_metrics,
        gold_filter_callback,
        gold_transform_callback,
    ):
        """Test that below thresholds results in no warnings."""

        async def transform(ctx, record, index):
            await asyncio.sleep(0)
            return {"entity_id": record.get("id"), "value": record.get("value")}

        config = RecordProcessorConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            dq_config=DQConfig(soft_fail_threshold=0.5, hard_fail_threshold=0.9),
        )

        transformer = BatchTransformer(
            context=mock_context,
            config=config,
            error_classifier=mock_error_classifier,
            quarantine_manager=mock_quarantine_manager,
            batch_metrics=mock_batch_metrics,
            transform_callback=transform,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
        )

        records = [{"id": "1", "value": 10}, {"id": "2", "value": 5}]
        batch_id = BatchID(uuid4())

        result = await transformer.transform_batch(records, batch_id)

        assert len(result.silver_records) == 2
        assert result.quarantined_count == 0
        mock_context.logger.warning.assert_not_called()
