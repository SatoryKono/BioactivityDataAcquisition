"""Stream B APP: leftover chained-key, TPC, write-support, and runner-stage branches."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pyarrow as pa
import pytest

from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.helpers.dependency_chained_key_resolver import (
    ChainedKeyResolver,
)
from bioetl.application.composite.runner_pkg.runner_stage_mixin import (
    CompositeRunnerStageMixin,
)
from bioetl.application.core._batch_write_support import (
    emit_batch_failed,
    emit_domain_event,
    safe_write_layer,
)
from bioetl.application.pipelines.chembl.target_protein_classification_summary import (
    summarize_target_protein_classification_dependency,
)
from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)
from bioetl.domain.composite import DependencyConfig
from bioetl.domain.exceptions import BioETLError

pytestmark = pytest.mark.unit


def test_tpc_summary_missing_and_empty_target_id() -> None:
    raw = pl.DataFrame({"other": [1]})
    assert summarize_target_protein_classification_dependency(raw).columns == ["other"]
    empty = pl.DataFrame({"target_id": []})
    summarized = summarize_target_protein_classification_dependency(empty)
    assert "target_id" in summarized.columns
    skipped = pl.DataFrame({"target_id": [None]})
    out = summarize_target_protein_classification_dependency(skipped)
    assert out.is_empty() or "target_id" in out.columns


def test_crossref_issn_list_and_csv_string(monkeypatch: pytest.MonkeyPatch) -> None:
    from dataclasses import dataclass

    @dataclass
    class _Entity:
        issn: object

    host = CrossRefPublicationTransformer.__new__(CrossRefPublicationTransformer)
    host.serialize_json_list = lambda values: "|".join(str(v) for v in values)  # type: ignore[method-assign]
    monkeypatch.setattr(
        CrossRefPublicationTransformer,
        "entity_to_silver_record",
        CrossRefPublicationTransformer.entity_to_silver_record,
    )
    monkeypatch.setattr(
        "bioetl.application.core.base_transformer_dependency_helpers_mixin._BaseTransformerDependencyHelpersMixin.entity_to_silver_record",
        lambda self, entity: {"issn": entity.issn},
    )
    listed = CrossRefPublicationTransformer.entity_to_silver_record(
        host, _Entity(["1234-567X", "1111-2222"])
    )
    assert listed["issn"] == "1234-567X"
    csv = CrossRefPublicationTransformer.entity_to_silver_record(
        host, _Entity("1234-567X, 1111-2222")
    )
    assert csv["issn"] == "1234-567X"
    assert csv["issn_list"]


def test_dedup_record_and_string_expr_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    accounting = SimpleNamespace(record_removal=MagicMock())
    monkeypatch.setattr(
        "bioetl.application.composite.deduplication.get_stage_accounting",
        lambda: accounting,
    )
    EnricherDeduplicatorService._record_deduplicated(3)
    accounting.record_removal.assert_called_once()
    service = EnricherDeduplicatorService(logger=MagicMock())
    bool_expr = service._to_string_expr("flag", pl.Boolean)
    assert bool_expr is not None
    dt_expr = service._to_string_expr("ts", pl.Datetime)
    assert dt_expr is not None


def test_emit_domain_event_logs_and_invalid_layer() -> None:
    logger = MagicMock()
    emitter = SimpleNamespace(
        emit_domain_event=lambda _event: (_ for _ in ()).throw(ValueError("down"))
    )
    emit_domain_event(emitter, SimpleNamespace(), logger=logger)  # type: ignore[arg-type]
    logger.warning.assert_called_once()
    emit_batch_failed(
        emitter=SimpleNamespace(emit_domain_event=lambda _e: None),
        run_id="r1",  # type: ignore[arg-type]
        batch_id="b1",  # type: ignore[arg-type]
        layer="gold",
        error=RuntimeError("x"),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        logger=logger,
    )


@pytest.mark.asyncio
async def test_safe_write_rejects_unknown_layer() -> None:
    with pytest.raises(ValueError, match="silver"):
        await safe_write_layer(
            execute_with_span=AsyncMock(),
            writer=SimpleNamespace(),  # type: ignore[arg-type]
            quarantine_manager=SimpleNamespace(),  # type: ignore[arg-type]
            logger=MagicMock(),
            run_id="r1",  # type: ignore[arg-type]
            domain_event_emitter=None,
            layer="bronze",
            records=[],
            batch_id="b1",  # type: ignore[arg-type]
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
            bronze_refs=None,
            operation_errors=(ValueError,),
        )


@pytest.mark.asyncio
async def test_chained_resolver_read_fallbacks_and_key_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = SimpleNamespace(
        log_warning=MagicMock(),
        log_error=MagicMock(),
        log_info=MagicMock(),
        _normalization_policies=(),
    )
    resolver = ChainedKeyResolver(resolver_helper=helper)  # type: ignore[arg-type]
    dependency = DependencyConfig(
        pipeline="chembl_activity",
        join_keys=("id",),
        key_source="chembl_molecule",
        silver_table="chembl/activity",
        key_filter="id = 1",
    )
    source = DependencyConfig(
        pipeline="chembl_molecule",
        join_keys=("id",),
        silver_table="chembl/molecule",
    )
    seed = pl.DataFrame({"id": [1]})
    reader = SimpleNamespace(read_table=AsyncMock(side_effect=FileNotFoundError("missing")))
    out = await resolver.resolve(dependency, seed, {"chembl_molecule": source}, reader)  # type: ignore[arg-type]
    assert out.equals(seed)

    reader.read_table = AsyncMock(return_value=None)
    out = await resolver.resolve(dependency, seed, {"chembl_molecule": source}, reader)  # type: ignore[arg-type]
    assert out.equals(seed)

    reader.read_table = AsyncMock(return_value=object())
    with pytest.raises(TypeError, match="PyArrow"):
        await resolver.resolve(dependency, seed, {"chembl_molecule": source}, reader)  # type: ignore[arg-type]

    reader.read_table = AsyncMock(side_effect=BioETLError("io"))
    with pytest.raises(ValueError, match="Failed to read keys"):
        await resolver.resolve(dependency, seed, {"chembl_molecule": source}, reader)  # type: ignore[arg-type]

    table = pa.table({"id": [1, 2]})
    reader.read_table = AsyncMock(return_value=table)
    monkeypatch.setattr(
        "bioetl.application.composite.helpers.dependency_chained_key_resolver.normalize_join_key_dataframe_columns",
        lambda df, **_k: df,
    )
    filtered = await resolver.resolve(dependency, seed, {"chembl_molecule": source}, reader)  # type: ignore[arg-type]
    assert "id" in filtered.columns
    helper.log_info.assert_called()

    monkeypatch.setattr(
        "polars.sql_expr",
        lambda _expr: (_ for _ in ()).throw(ValueError("bad sql")),
    )
    fallback = resolver._apply_key_filter(seed, dependency)
    assert fallback.equals(seed)
    helper.log_warning.assert_called()


@pytest.mark.asyncio
async def test_runner_stage_skips_and_handles_dependency_errors() -> None:
    class _Host(CompositeRunnerStageMixin):
        async def _skip_dependencies_phase(self, state: object) -> tuple[object, dict[str, object]]:
            return state, {}

        def _has_dependencies_configured(self) -> bool:
            return False

        async def _handle_dependencies_phase_exception(
            self, state: object, error: Exception
        ) -> None:
            self.seen = type(error).__name__

    host = _Host()
    state, results = await host._execute_dependencies_phase("state", pl.DataFrame())  # type: ignore[arg-type]
    assert results == {}
    assert state == "state"

    class _FailHost(CompositeRunnerStageMixin):
        def _has_dependencies_configured(self) -> bool:
            return True

        def _prepare_dependencies_run_context(self) -> object:
            return object()

        async def _start_dependencies_phase(self, state: object, *, context: object) -> object:
            del context
            return state

        async def _run_dependencies(self, **_k: object) -> dict[str, object]:
            raise ValueError("dep-fail")

        async def _handle_dependencies_phase_exception(
            self, state: object, error: Exception
        ) -> None:
            self.seen = str(error)

    failing = _FailHost()
    with pytest.raises(ValueError, match="dep-fail"):
        await failing._execute_started_dependencies_phase(  # type: ignore[misc]
            "state",
            context=object(),  # type: ignore[arg-type]
            keys_df=pl.DataFrame(),
        )
    assert failing.seen == "dep-fail"
