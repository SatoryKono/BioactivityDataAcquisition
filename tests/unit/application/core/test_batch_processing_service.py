"""Unit tests for BatchProcessingService.

Tests extract/transform/write orchestration for one ETL batch, including
bronze/silver/gold writes, transform stage, source metadata collection,
error propagation through spans, and batch ID factory delegation.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.batch_processing_service import (
    BatchProcessingComponents,
    BatchProcessingOutcome,
    BatchProcessingService,
)
from bioetl.application.core.batch_processing_support import (
    BatchProcessingSupportService,
)
from bioetl.application.core.batch_transformer import TransformResult
from bioetl.domain.aggregates.events import BatchCreated, BatchFailed, BatchSealed
from bioetl.domain.exceptions import BioETLError, SchemaViolationError
from bioetl.domain.types import BatchID, BronzeRecord, RunType
from bioetl.domain.value_objects.silver_result import SilverWriteResult


# ---------------------------------------------------------------------------
# Shared helpers and fixtures
# ---------------------------------------------------------------------------


def _make_transform_result(
    *,
    silver: list | None = None,
    gold: list | None = None,
    quarantined: int = 0,
    filtered_out: int = 0,
) -> TransformResult:
    return TransformResult(
        silver_records=silver or [],
        gold_records=gold or [],
        quarantined_count=quarantined,
        filtered_out_count=filtered_out,
    )


@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.run_id = uuid4()
    ctx.run_type = RunType.INCREMENTAL
    ctx.started_at = MagicMock()
    ctx.logger = MagicMock()
    return ctx


@pytest.fixture
def mock_services():
    svc = MagicMock()
    svc.data_source = MagicMock()

    # fetch yields nothing by default
    async def _empty_fetch(**kwargs):
        await asyncio.sleep(0)
        for _ in ():
            yield _  # pragma: no cover

    svc.data_source.fetch = _empty_fetch
    return svc


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.entity_type = "test_entity"
    return cfg


@pytest.fixture
def mock_logger():
    return MagicMock()


@pytest.fixture
def mock_batch_metrics():
    m = MagicMock()
    m.track_batch_size = MagicMock()
    m.track_processed_records = MagicMock()
    return m


@pytest.fixture
def mock_transformer():
    t = MagicMock()
    t.transform_batch = AsyncMock(
        return_value=_make_transform_result(
            silver=[{"entity_id": "1"}],
            gold=[{"entity_id": "1"}],
        )
    )
    return t


@pytest.fixture
def mock_writer():
    w = MagicMock()
    w.write_bronze = AsyncMock(return_value=MagicMock(name="bronze_result"))
    w.write_silver = AsyncMock(return_value=MagicMock(name="silver_result"))
    w.write_gold = AsyncMock(return_value=None)
    w.log_and_track_write_error = MagicMock()
    return w


@pytest.fixture
def mock_tracing():
    t = MagicMock()
    t.start_batch_span = MagicMock(return_value=MagicMock(name="batch_span"))
    t.start_layer_span = MagicMock(return_value=MagicMock(name="layer_span"))
    t.end_span = MagicMock()
    t.set_batch_result = MagicMock()
    t.set_transform_result = MagicMock()
    return t


@pytest.fixture
def mock_batch_id_factory():
    factory = MagicMock()
    factory.create = MagicMock(return_value=BatchID(uuid4()))
    return factory


def _make_service(
    context,
    services,
    config,
    logger,
    batch_metrics,
    transformer,
    writer,
    tracing,
    batch_id_factory,
) -> BatchProcessingService:
    from bioetl.application.core.batch_processing_service import (
        BatchProcessingComponents,
    )

    return BatchProcessingService(
        services=services,
        context=context,
        config=config,
        components=BatchProcessingComponents(
            batch_metrics=batch_metrics,
            transformer=transformer,
            writer=writer,
        ),
        tracing_manager=tracing,
        batch_id_factory=batch_id_factory,
        support_service=BatchProcessingSupportService(
            services=services,
            logger=logger,
            batch_metrics=batch_metrics,
            transformer=transformer,
            writer=writer,
            tracing=tracing,
            quarantine_manager=MagicMock(),
            run_id=context.run_id,
        ),
    )


# ---------------------------------------------------------------------------
# BatchProcessingOutcome dataclass
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBatchProcessingOutcome:
    """Tests for the BatchProcessingOutcome frozen dataclass."""

    def test_is_frozen(self):
        """BatchProcessingOutcome instances are immutable."""
        batch_id = BatchID(uuid4())
        output = BatchProcessingOutcome(
            batch_id=batch_id,
            bronze_result=MagicMock(),
            silver_records=[],
            gold_records=[],
            quarantined_count=0,
            filtered_out_count=0,
        )
        with pytest.raises(AttributeError):
            output.quarantined_count = 1  # type: ignore[misc]

    def test_fields_accessible(self):
        """All fields are accessible after construction."""
        batch_id = BatchID(uuid4())
        bronze = MagicMock()
        output = BatchProcessingOutcome(
            batch_id=batch_id,
            bronze_result=bronze,
            silver_records=[{"a": 1}],
            gold_records=[{"b": 2}],
            quarantined_count=3,
            filtered_out_count=1,
        )
        assert output.batch_id is batch_id
        assert output.bronze_result is bronze
        assert output.silver_records == [{"a": 1}]
        assert output.gold_records == [{"b": 2}]
        assert output.quarantined_count == 3
        assert output.filtered_out_count == 1


# ---------------------------------------------------------------------------
# process_batch — happy path
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProcessBatchHappyPath:
    """Tests for BatchProcessingService.process_batch — successful flow."""

    async def test_calls_write_bronze(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """process_batch calls write_bronze with the raw records."""
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )
        records: list[BronzeRecord] = [{"id": "1", "val": 10}]

        await svc.process_batch(records=records, start_index=0, query_string=None)

        mock_writer.write_bronze.assert_awaited_once()
        call_args = mock_writer.write_bronze.call_args
        assert call_args[0][0] == records  # positional arg: records

    async def test_calls_transform_batch(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """process_batch calls transformer.transform_batch with the records."""
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )
        records: list[BronzeRecord] = [{"id": "2"}]

        await svc.process_batch(records=records, start_index=0, query_string=None)

        mock_transformer.transform_batch.assert_awaited_once()

    async def test_emits_batch_created_and_sealed_events(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """process_batch emits typed batch lifecycle events through the support seam."""
        event_emitter = MagicMock()
        service = BatchProcessingService(
            services=mock_services,
            context=mock_context,
            config=mock_config,
            components=BatchProcessingComponents(
                batch_metrics=mock_batch_metrics,
                transformer=mock_transformer,
                writer=mock_writer,
            ),
            tracing_manager=mock_tracing,
            batch_id_factory=mock_batch_id_factory,
            support_service=BatchProcessingSupportService(
                services=mock_services,
                logger=mock_logger,
                batch_metrics=mock_batch_metrics,
                transformer=mock_transformer,
                writer=mock_writer,
                tracing=mock_tracing,
                quarantine_manager=MagicMock(),
                run_id=mock_context.run_id,
                domain_event_emitter=event_emitter,
            ),
        )

        await service.process_batch(
            records=[{"id": "1", "val": 10}],
            start_index=0,
            query_string=None,
        )

        emitted_events = [
            call.args[0] for call in event_emitter.emit_domain_event.call_args_list
        ]
        assert any(isinstance(event, BatchCreated) for event in emitted_events)
        assert any(isinstance(event, BatchSealed) for event in emitted_events)

    async def test_calls_write_silver_when_silver_records_present(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """write_silver is called when transform produces silver records."""
        mock_transformer.transform_batch = AsyncMock(
            return_value=_make_transform_result(
                silver=[{"entity_id": "s1"}],
                gold=[],
            )
        )
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        await svc.process_batch(records=[{"id": "1"}], start_index=0, query_string=None)

        mock_writer.write_silver.assert_awaited_once()

    async def test_skips_write_silver_when_no_silver_records(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """write_silver is NOT called when transform produces no silver records."""
        mock_transformer.transform_batch = AsyncMock(
            return_value=_make_transform_result(silver=[], gold=[])
        )
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        await svc.process_batch(records=[{"id": "1"}], start_index=0, query_string=None)

        mock_writer.write_silver.assert_not_awaited()

    async def test_calls_write_gold_when_gold_records_present(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """write_gold is called when transform produces gold records."""
        mock_transformer.transform_batch = AsyncMock(
            return_value=_make_transform_result(silver=[], gold=[{"entity_id": "g1"}])
        )
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        await svc.process_batch(records=[{"id": "1"}], start_index=0, query_string=None)

        mock_writer.write_gold.assert_awaited_once()

    async def test_passes_silver_refs_to_gold_write_when_silver_present(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """Gold write receives SilverWriteResult lineage from the preceding Silver write."""
        silver_result = SilverWriteResult(
            table_name="chembl.publication",
            table_path="/tmp/silver/chembl/publication",
            delta_version=129,
            record_count=1,
        )
        mock_writer.write_silver = AsyncMock(return_value=silver_result)
        mock_transformer.transform_batch = AsyncMock(
            return_value=_make_transform_result(
                silver=[{"entity_id": "s1"}],
                gold=[{"entity_id": "g1"}],
            )
        )
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        await svc.process_batch(records=[{"id": "1"}], start_index=0, query_string=None)

        mock_writer.write_gold.assert_awaited_once_with(
            [{"entity_id": "g1"}],
            silver_refs=[silver_result],
        )

    async def test_skips_write_gold_when_no_gold_records(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """write_gold is NOT called when transform produces no gold records."""
        mock_transformer.transform_batch = AsyncMock(
            return_value=_make_transform_result(silver=[], gold=[])
        )
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        await svc.process_batch(records=[{"id": "1"}], start_index=0, query_string=None)

        mock_writer.write_gold.assert_not_awaited()

    async def test_returns_batch_processing_output(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """process_batch returns a BatchProcessingOutcome instance."""
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        output = await svc.process_batch(
            records=[{"id": "1"}], start_index=0, query_string=None
        )

        assert isinstance(output, BatchProcessingOutcome)

    async def test_tracks_bronze_metrics(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """batch_metrics.track_batch_size and track_processed_records called for bronze."""
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )
        records: list[BronzeRecord] = [{"id": "1"}, {"id": "2"}]

        await svc.process_batch(records=records, start_index=0, query_string=None)

        mock_batch_metrics.track_batch_size.assert_called_with("bronze", 2)
        mock_batch_metrics.track_processed_records.assert_any_call("bronze", 2)

    async def test_output_quarantined_count_matches_transform_result(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """BatchProcessingOutcome.quarantined_count matches transform result."""
        mock_transformer.transform_batch = AsyncMock(
            return_value=_make_transform_result(
                silver=[{"entity_id": "s1"}],
                gold=[{"entity_id": "g1"}],
                quarantined=5,
            )
        )
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        output = await svc.process_batch(
            records=[{"id": "1"}], start_index=0, query_string=None
        )

        assert output.quarantined_count == 5


# ---------------------------------------------------------------------------
# process_batch — error propagation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProcessBatchErrorPropagation:
    """Tests for BatchProcessingService.process_batch — error paths."""

    async def test_reraises_bioetl_error_from_write_bronze(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """BioETLError from write_bronze propagates out of process_batch."""
        mock_writer.write_bronze = AsyncMock(side_effect=BioETLError("bronze fail"))
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        with pytest.raises(BioETLError):
            await svc.process_batch(
                records=[{"id": "1"}], start_index=0, query_string=None
            )

    async def test_reraises_runtime_error_from_transform(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """RuntimeError from transform stage propagates out of process_batch."""
        mock_transformer.transform_batch = AsyncMock(
            side_effect=RuntimeError("transform crashed")
        )
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        with pytest.raises(RuntimeError):
            await svc.process_batch(
                records=[{"id": "1"}], start_index=0, query_string=None
            )

    async def test_ends_span_on_error(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """Tracing span is ended (with error) when process_batch raises."""
        mock_writer.write_bronze = AsyncMock(side_effect=ValueError("bad"))
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        with pytest.raises(ValueError):
            await svc.process_batch(
                records=[{"id": "1"}], start_index=0, query_string=None
            )

        mock_tracing.end_span.assert_called()

    async def test_calls_log_and_track_write_error_on_silver_failure(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """log_and_track_write_error called when write_silver raises."""
        mock_transformer.transform_batch = AsyncMock(
            return_value=_make_transform_result(silver=[{"entity_id": "s1"}], gold=[])
        )
        mock_writer.write_silver = AsyncMock(side_effect=OSError("disk error"))
        svc = _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        with pytest.raises(OSError):
            await svc.process_batch(
                records=[{"id": "1"}], start_index=0, query_string=None
            )

        mock_writer.log_and_track_write_error.assert_called_once()
        call_args = mock_writer.log_and_track_write_error.call_args[0]
        assert call_args[0] == "silver"

    async def test_quarantines_schema_violations_and_emits_batch_failed(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """Schema-violating Silver writes should quarantine records and keep flow alive."""
        mock_transformer.transform_batch = AsyncMock(
            return_value=_make_transform_result(silver=[{"entity_id": "s1"}], gold=[])
        )
        mock_writer.write_silver = AsyncMock(
            side_effect=SchemaViolationError("silver", ["bad field"])
        )
        quarantine_manager = MagicMock()
        quarantine_manager.quarantine_records = AsyncMock()
        event_emitter = MagicMock()
        service = BatchProcessingService(
            services=mock_services,
            context=mock_context,
            config=mock_config,
            components=BatchProcessingComponents(
                batch_metrics=mock_batch_metrics,
                transformer=mock_transformer,
                writer=mock_writer,
            ),
            tracing_manager=mock_tracing,
            batch_id_factory=mock_batch_id_factory,
            support_service=BatchProcessingSupportService(
                services=mock_services,
                logger=mock_logger,
                batch_metrics=mock_batch_metrics,
                transformer=mock_transformer,
                writer=mock_writer,
                tracing=mock_tracing,
                quarantine_manager=quarantine_manager,
                run_id=mock_context.run_id,
                domain_event_emitter=event_emitter,
            ),
        )

        output = await service.process_batch(
            records=[{"id": "1"}],
            start_index=0,
            query_string=None,
        )

        assert output.silver_records == [{"entity_id": "s1"}]
        quarantine_manager.quarantine_records.assert_awaited_once()
        mock_logger.warning.assert_called_once()
        emitted_events = [
            call.args[0] for call in event_emitter.emit_domain_event.call_args_list
        ]
        assert any(isinstance(event, BatchFailed) for event in emitted_events)


# ---------------------------------------------------------------------------
# _get_source_metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetSourceMetadata:
    """Tests for BatchProcessingService._get_source_metadata."""

    def _make_svc(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ) -> BatchProcessingService:
        return _make_service(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

    def test_returns_none_when_no_get_source_metadata_method(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """Returns None when data_source has no get_source_metadata method."""
        del mock_services.data_source.get_source_metadata
        svc = self._make_svc(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        result = svc._get_source_metadata(None)

        assert result is None

    def test_creates_source_metadata_from_query_string_when_no_data_source_meta(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """Creates a minimal SourceMetadata from query_string when data_source returns None."""
        mock_services.data_source.get_source_metadata = MagicMock(return_value=None)
        svc = self._make_svc(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        result = svc._get_source_metadata("CHEMBL25")

        assert result is not None
        assert result.query_string == "CHEMBL25"

    def test_logs_warning_when_get_source_metadata_raises(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """A warning is logged when get_source_metadata raises a known error."""
        mock_services.data_source.get_source_metadata = MagicMock(
            side_effect=RuntimeError("source meta error")
        )
        svc = self._make_svc(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        result = svc._get_source_metadata(None)

        assert result is None
        mock_logger.warning.assert_called_once()

    def test_returns_none_when_query_string_is_none_and_no_metadata(
        self,
        mock_context,
        mock_services,
        mock_config,
        mock_logger,
        mock_batch_metrics,
        mock_transformer,
        mock_writer,
        mock_tracing,
        mock_batch_id_factory,
    ):
        """Returns None when query_string is None and data source provides no metadata."""
        mock_services.data_source.get_source_metadata = MagicMock(return_value=None)
        svc = self._make_svc(
            mock_context,
            mock_services,
            mock_config,
            mock_logger,
            mock_batch_metrics,
            mock_transformer,
            mock_writer,
            mock_tracing,
            mock_batch_id_factory,
        )

        result = svc._get_source_metadata(None)

        assert result is None
