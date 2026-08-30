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
"""Restore per-module coverage holes exposed by SHA-bound candidate (#9793)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


def test_aggregate_check_status_fail_outranks_warn() -> None:
    from bioetl.application.services.dq.silver_check_executor import (
        _aggregate_check_status,
    )
    from bioetl.domain.value_objects.dq_report import DQCheckStatus

    assert (
        _aggregate_check_status([DQCheckStatus.WARN, DQCheckStatus.FAIL])
        == DQCheckStatus.FAIL
    )
    assert _aggregate_check_status([DQCheckStatus.WARN]) == DQCheckStatus.WARN
    assert _aggregate_check_status([DQCheckStatus.PASS]) == DQCheckStatus.PASS


def test_require_checkpoint_metadata_rejects_wrong_type() -> None:
    from bioetl.application.core.lifecycle.checkpoint_identity_overrides import (
        _require_checkpoint_metadata,
    )

    with pytest.raises(TypeError, match="CheckpointMetadata"):
        _require_checkpoint_metadata("not-metadata")


def test_require_dq_rule_outcome_rejects_wrong_type() -> None:
    from bioetl.domain.behavior.dq_rule_evaluator import _require_dq_rule_outcome

    with pytest.raises(TypeError, match="DQRuleOutcome"):
        _require_dq_rule_outcome("not-outcome")


def test_batch_mixin_validate_seal_counts_rejects_invalid_partitions() -> None:
    from bioetl.domain.aggregates._batch_mixins import _BatchLifecycleMixin

    with pytest.raises(ValueError, match="non-negative"):
        _BatchLifecycleMixin._validate_seal_counts(-1, 0, 0)
    with pytest.raises(ValueError, match="inconsistent"):
        _BatchLifecycleMixin._validate_seal_counts(2, 1, 0)


@pytest.mark.asyncio
async def test_fetch_multi_column_requires_loaded_filter_ids() -> None:
    from bioetl.application.core._filtered_data_source_fetch_support import (
        fetch_multi_column,
    )

    state = SimpleNamespace(
        _data_source=MagicMock(),
        _multi_filter_ids=None,
        _ensure_filterable_adapter=lambda mode: None,
    )
    with pytest.raises(ValueError, match="multi_filter_ids must be loaded"):
        async for _record in fetch_multi_column(state, "activity", limit=1):
            raise AssertionError("no records expected")


@pytest.mark.asyncio
async def test_record_processor_span_tracks_baseexception() -> None:
    from bioetl.application.core._record_processor_span_support import (
        RecordProcessorSpanExecutor,
    )

    class _Boom(BaseException):
        pass

    class _Harness(RecordProcessorSpanExecutor):
        def __init__(self) -> None:
            self._tracer = None
            self.ended: tuple[object, type[BaseException] | None] | None = None

        async def _transform_records(self, **kwargs: Any) -> Any:
            raise _Boom()

        def _end_span(self, span: object, error: BaseException | None = None) -> None:
            self.ended = (span, type(error) if error is not None else None)

    harness = _Harness()
    with pytest.raises(_Boom):
        await harness.execute_transform_with_span(
            transformer=MagicMock(),
            records=[],
            batch_id="batch",
            start_index=0,
        )
    assert harness.ended is not None
    assert harness.ended[1] is _Boom


def test_config_helpers_reject_non_mapping_model_dump() -> None:
    from bioetl.composition.bootstrap.cli.config_helpers import get_pipeline_yaml_for_dq

    class _BadDump:
        def model_dump(self) -> list[str]:
            return ["not-a-mapping"]

    with pytest.raises(TypeError, match="must return a mapping"):
        get_pipeline_yaml_for_dq(
            "chembl_activity", pipeline_config_loader=lambda _: _BadDump()
        )


def test_default_registry_method_requires_objtype_on_class_access() -> None:
    from bioetl.composition.providers._default_registry import DefaultRegistryMethod

    descriptor = DefaultRegistryMethod(lambda _self: None)
    with pytest.raises(AssertionError, match="objtype is required"):
        descriptor.__get__(None, None)


def test_compute_file_hashes_returns_nones_for_missing_path(tmp_path: Any) -> None:
    from bioetl.composition.runtime_builders._effective_config_source_refs_support import (
        _compute_file_hashes,
    )

    missing = tmp_path / "absent.yaml"
    assert _compute_file_hashes(relative_path="absent.yaml", path=missing) == (
        None,
        None,
        None,
        None,
        None,
    )


def test_replay_timestamp_anchor_uses_unix_epoch_when_date_omitted() -> None:
    from datetime import UTC, datetime

    from bioetl.application.core.base import _resolve_replay_timestamp_anchor
    from bioetl.domain.config.runtime import RuntimeConfig
    from bioetl.domain.types import RunType

    runtime = RuntimeConfig(run_type=RunType.REBUILD, exact_replay=True)
    assert _resolve_replay_timestamp_anchor(runtime) == datetime(1970, 1, 1, tzinfo=UTC)


def test_exact_replay_mismatch_when_checkpoint_was_not_replay() -> None:
    from bioetl.application.services.checkpoint._checkpoint_compatibility_message_helpers import (
        exact_replay_mismatch_messages,
    )
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

    current = CheckpointMetadata(records_processed=1, exact_replay=True)
    checkpoint = CheckpointMetadata(records_processed=1, exact_replay=False)
    messages = exact_replay_mismatch_messages(current, checkpoint)
    assert any("exact replay" in item.lower() for item in messages)


def test_default_pii_hasher_uses_configured_salt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.composition.factories.pipeline import transformer_dependencies as mod

    monkeypatch.setattr(
        mod,
        "load_settings",
        lambda: SimpleNamespace(pii_salt_current="unit-test-salt"),
    )
    monkeypatch.setattr(
        mod,
        "Sha256PiiHasher",
        SimpleNamespace(
            from_settings=lambda settings: f"hasher:{settings.pii_salt_current}"
        ),
    )
    assert mod._default_pii_hasher() == "hasher:unit-test-salt"


def test_create_metrics_rejects_non_port_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.composition.factories.services import port_factories as mod

    monkeypatch.setattr(mod, "resolve_metrics_port", lambda **_kwargs: object())
    with pytest.raises(TypeError, match="MetricsPort"):
        mod.create_metrics(MagicMock())


def test_forensic_preflight_flags_noop_logger() -> None:
    from bioetl.composition.bootstrap.runtime._observability_preflight_support import (
        validate_forensic_grade_observability_evidence,
    )
    from bioetl.domain.ports.noop import NoOpAudit, NoOpMetrics, NoOpTracing
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger

    logger = NoOpLogger()
    with pytest.raises(Exception, match="forensic_grade"):
        validate_forensic_grade_observability_evidence(
            tracer=NoOpTracing(),
            metrics=NoOpMetrics(),
            logger=logger,
            audit=NoOpAudit(),
        )


def test_build_lock_manager_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    from bioetl.composition.factories.pipeline import runner_assembly as mod

    monkeypatch.setattr(
        mod,
        "_build_lock_runtime_service",
        lambda context, checkpoint_manager, context_holder: "lock-runtime",
    )
    assert (
        mod._build_lock_manager(
            MagicMock(),
            checkpoint_manager=MagicMock(),
            context_holder=MagicMock(),
        )
        == "lock-runtime"
    )


def test_build_postrun_service_for_pipeline_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.composition.factories.pipeline import _runner_assembly_support as mod

    monkeypatch.setattr(mod, "build_postrun_service", lambda **_kwargs: "postrun")
    context = SimpleNamespace(
        dq_configs_extractor=lambda _yaml: {"dq": True},
        yaml_config={},
        pipeline=object(),
        logger_port=object(),
        observability=SimpleNamespace(tracer=object()),
    )
    assert (
        mod.build_postrun_service_for_pipeline(context, lifecycle_service=object())
        == "postrun"
    )


def test_snapshot_summary_indexes_and_detects_hash_conflicts() -> None:
    from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_summary import (
        _index_existing_snapshots,
        _merge_ledger_snapshots_by_id,
    )

    assert _index_existing_snapshots("not-a-list") == {}
    existing = {"snap-1": {"snapshot_id": "snap-1", "content_hash": "aaa"}}
    conflicts = _merge_ledger_snapshots_by_id(
        existing,
        [{"snapshot_id": "snap-1", "content_hash": "bbb"}],
    )
    assert conflicts[0]["ledger_content_hash"] == "bbb"


def test_require_workflow_result_rejects_wrong_type() -> None:
    from bioetl.application.services.workflow.workflow_runner_service import (
        _require_workflow_result,
    )

    with pytest.raises(TypeError, match="WorkflowRunExecutionResult"):
        _require_workflow_result("not-a-result")


def test_require_runner_inputs_and_bind_replace_fallback() -> None:
    from bioetl.composition.observability import (
        ObservabilityBundle,
        _require_runner_inputs,
        bind_manifest_logger_context,
    )
    from bioetl.domain.ports.noop import NoOpAudit, NoOpMetrics, NoOpTracing
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger

    with pytest.raises(TypeError, match="RunnerInputs"):
        _require_runner_inputs("not-inputs")

    rebound = ObservabilityBundle(
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        tracer=NoOpTracing(),
        audit=NoOpAudit(),
    )

    class _Bindable:
        def bind(self, **_kwargs: object) -> ObservabilityBundle:
            return rebound

    result = bind_manifest_logger_context(
        SimpleNamespace(observability=_Bindable()),
        "manifest-1",
    )
    assert result is not None


def test_apply_convention_defaults_skips_incomplete_identity() -> None:
    from bioetl.infrastructure.config.pipeline_payload_normalization import (
        apply_convention_defaults,
        load_source_section,
    )
    from pathlib import Path

    payload = {"provider": None, "entity_type": "activity"}
    assert apply_convention_defaults(payload) is payload
    load_source_section({"provider": 123}, Path("configs/entities/x.yaml"))
    load_source_section(
        {"provider": "chembl", "source": "not-a-mapping"},
        Path("configs/entities/x.yaml"),
    )


def test_reject_unknown_pipeline_source_keys() -> None:
    from bioetl.infrastructure.config.pipeline_payload_normalization import (
        _reject_invalid_entity_source,
    )

    with pytest.raises(ValueError, match="unsupported keys"):
        _reject_invalid_entity_source({"email": "a@b.c", "unexpected": 1})


def test_legacy_increment_kwargs_and_error_handler_fallback() -> None:
    from bioetl.application.services.ops.error_handler import (
        ErrorHandlerService,
        _legacy_increment_kwargs,
    )

    assert _legacy_increment_kwargs(list.append, 1, {"k": "v"}) == {}

    def _increment(
        name: str, value: float, _tags: dict[str, str] | None = None
    ) -> None:
        captured.append((name, value, _tags))

    captured: list[tuple[str, float, dict[str, str] | None]] = []
    kwargs = _legacy_increment_kwargs(_increment, 3, {"stage": "x"})
    assert kwargs["value"] == 3.0
    assert kwargs["_tags"] == {"stage": "x"}

    class _LegacyMetrics:
        def increment(self, name: str, **kwargs: object) -> None:
            captured.append((name, float(kwargs.get("value", 0)), kwargs.get("_tags")))  # type: ignore[arg-type]

    handler = ErrorHandlerService(logger=MagicMock(), metrics=_LegacyMetrics())  # type: ignore[arg-type]
    handler._increment_counter("errors_total", 2, {"code": "x"})
    assert captured[-1][0] == "errors_total"


def test_structural_policy_coercion_fallbacks() -> None:
    from bioetl.application.core.base_transformer._structural_policy_coercion import (
        _coerce_boolean,
        _coerce_float,
        _coerce_integer,
    )

    assert _coerce_integer(object(), allow_string_coercion=True) is None
    assert _coerce_float("inf", allow_string_coercion=True) is None
    assert (
        _coerce_boolean(
            object(),
            allow_string_coercion=True,
            true_values=("true",),
            false_values=("false",),
        )
        is None
    )


def test_require_dependency_context_rejects_wrong_type() -> None:
    from bioetl.application.core.base_transformer.base import (
        _require_dependency_context,
    )

    with pytest.raises(TypeError, match="TransformerDependencyContext"):
        _require_dependency_context("not-context")


def test_registry_iter_entity_files_empty_when_missing(tmp_path: Any) -> None:
    from bioetl.composition.factories.pipeline_support.registry_validation_helpers import (
        _iter_entity_files,
    )

    assert _iter_entity_files(tmp_path) == []


def test_foreign_key_reconciliation_validators() -> None:
    from bioetl.domain.workflow.foreign_key_reconciliation import (
        ForeignKeyReconciliationResult,
        normalize_layer,
        require_equal_key_tuple_lengths,
        require_first_keys_match,
        require_non_empty_keys_tuples,
        require_non_empty_primary_keys,
        require_non_empty_str,
        require_optional_str,
        require_source_scope,
        validate_optional_source_reference_keys_pair,
        normalize_request_layers,
    )

    with pytest.raises(ValueError, match="silver"):
        normalize_layer("bronze", "source_layer")
    with pytest.raises(ValueError, match="cannot be empty"):
        require_non_empty_str("  ", "source_table")
    with pytest.raises(ValueError, match="cannot be empty"):
        require_optional_str("  ", "alias")
    with pytest.raises(ValueError, match="primary_keys"):
        require_non_empty_primary_keys(())
    with pytest.raises(ValueError, match="cannot be empty"):
        require_non_empty_keys_tuples((), ("id",))
    with pytest.raises(ValueError, match="same length"):
        require_equal_key_tuple_lengths(("a",), ("a", "b"))
    with pytest.raises(ValueError, match="first source_keys"):
        require_first_keys_match(
            source_keys=("a",),
            reference_keys=("b",),
            source_key="x",
            reference_key="b",
        )
    with pytest.raises(ValueError, match="first reference_keys"):
        require_first_keys_match(
            source_keys=("a",),
            reference_keys=("b",),
            source_key="a",
            reference_key="x",
        )
    with pytest.raises(ValueError, match="provided together"):
        validate_optional_source_reference_keys_pair(
            source_keys=None,
            reference_keys=("id",),
            source_key="id",
            reference_key="id",
        )
    with pytest.raises(ValueError, match="provided together"):
        validate_optional_source_reference_keys_pair(
            source_keys=("id",),
            reference_keys=None,
            source_key="id",
            reference_key="id",
        )
    with pytest.raises(ValueError, match="mutation_layer"):
        normalize_request_layers("silver", "gold", "gold")
    with pytest.raises(ValueError, match="source_scope"):
        require_source_scope("yesterday")
    with pytest.raises(ValueError, match="action must be"):
        ForeignKeyReconciliationResult(
            source_table="s",
            reference_table="r",
            source_key="id",
            reference_key="id",
            action="drop_everything",  # type: ignore[arg-type]
            scanned_rows=0,
            retained_rows=0,
            orphan_rows_deleted=0,
            mutated=False,
        )
    with pytest.raises(ValueError, match="mutation_mode"):
        ForeignKeyReconciliationResult(
            source_table="s",
            reference_table="r",
            source_key="id",
            reference_key="id",
            action="delete_orphans",
            scanned_rows=0,
            retained_rows=0,
            orphan_rows_deleted=0,
            mutated=False,
            mutation_mode="explode",  # type: ignore[arg-type]
        )


def test_file_artifact_lifecycle_uri_and_planned_bronze(tmp_path: Any) -> None:
    from datetime import UTC, datetime

    from bioetl.infrastructure.control_plane._file_artifact_lifecycle_refs import (
        _append_latest_checkpoint_if_matching,
        _append_planned_bronze_candidate,
        _append_snapshot_bronze_candidate,
        iter_artifact_refs_for_manifest,
        resolve_bronze_uri,
    )
    from bioetl.infrastructure.control_plane.file_artifact_lifecycle_types import (
        _ProtectedRefs,
    )
    from bioetl.domain.control_plane import ControlPlaneArtifactSurface

    bronze_root = tmp_path / "bronze"
    assert resolve_bronze_uri(bronze_root, "file://nope") is None
    assert resolve_bronze_uri(bronze_root, "bronze://") is None
    assert resolve_bronze_uri(bronze_root, "bronze://../escape") is None

    candidates: list[tuple[object, object]] = []
    issues: list[object] = []
    _append_snapshot_bronze_candidate(
        candidates,  # type: ignore[arg-type]
        issues,  # type: ignore[arg-type]
        bronze_root=bronze_root,
        snapshot=SimpleNamespace(immutable_uri=None, snapshot_id="s1"),
        seen=set(),
    )
    _append_snapshot_bronze_candidate(
        candidates,  # type: ignore[arg-type]
        issues,  # type: ignore[arg-type]
        bronze_root=bronze_root,
        snapshot=SimpleNamespace(immutable_uri="s3://bucket/key", snapshot_id="s2"),
        seen=set(),
    )
    _append_planned_bronze_candidate(
        candidates,  # type: ignore[arg-type]
        base_path=tmp_path / "control-plane",
        artifact=SimpleNamespace(layer="gold", path="x.parquet"),
        seen=set(),
    )
    planned = tmp_path / "planned.parquet"
    planned.write_bytes(b"x")
    seen: set[object] = set()
    _append_planned_bronze_candidate(
        candidates,  # type: ignore[arg-type]
        base_path=tmp_path / "control-plane",
        artifact=SimpleNamespace(layer="bronze", path=str(planned)),
        seen=seen,  # type: ignore[arg-type]
    )

    checkpoint = tmp_path / "chembl_activity.json"
    checkpoint.write_text("{not-json", encoding="utf-8")
    _append_latest_checkpoint_if_matching(
        candidates,  # type: ignore[arg-type]
        tmp_path,
        SimpleNamespace(pipeline_name="chembl_activity", run_id="run-1"),  # type: ignore[arg-type]
        read_json_file=lambda _path: (_ for _ in ()).throw(ValueError("bad json")),
    )

    empty_refs = _ProtectedRefs(
        manifest_ids=frozenset(),
        run_ids=frozenset(),
        input_snapshot_ids=frozenset(),
        effective_config_artifact_ids=frozenset(),
        lineage_fragment_ids=frozenset(),
        evidence_floor_manifest_ids=frozenset(),
        evidence_floor_run_ids=frozenset(),
        evidence_floor_input_snapshot_ids=frozenset(),
        evidence_floor_effective_config_artifact_ids=frozenset(),
        evidence_floor_lineage_fragment_ids=frozenset(),
    )
    manifest = SimpleNamespace(
        manifest_id="m1",
        run_id="r1",
        pipeline_name="chembl_activity",
        code_provenance=SimpleNamespace(effective_config_artifact_id=None),
        source_refs=(),
        planned_artifacts=(),
    )
    refs = iter_artifact_refs_for_manifest(
        base_path=tmp_path,
        cutoff=datetime(2026, 1, 1, tzinfo=UTC),
        protected_refs=empty_refs,
        manifest=manifest,  # type: ignore[arg-type]
    )
    assert refs == ()
    assert ControlPlaneArtifactSurface.CACHED_BRONZE


@pytest.mark.asyncio
async def test_publication_term_offset_skips_then_limits() -> None:
    from bioetl.application.core.data_sources.publication_term import (
        PublicationTermDataSource,
    )

    class _Harness(PublicationTermDataSource):
        def __init__(self) -> None:
            self._data_source = MagicMock()

        async def _fetch_publication_terms(self, *args: object, **kwargs: object):
            for item in ({"id": "a"}, {"id": "b"}, {"id": "c"}):
                yield item

    records = [
        item async for item in _Harness()._fetch_target_records(limit=1, offset=1)
    ]
    assert records == [{"id": "b"}]


def test_bronze_io_mixin_rejects_divergent_existing_payload(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bioetl.infrastructure.storage.bronze.io_mixin import BronzeWriterIOMixin

    class _Host(BronzeWriterIOMixin):
        COMPRESSION_THREADS = 1
        COMPRESSION_LEVEL = 1
        COMPRESSION_CHUNK_SIZE = 4
        _flat_structure = True

    host = _Host()
    target = tmp_path / "batch.jsonl.zst"
    temp = tmp_path / "batch.tmp"
    target.write_bytes(b"old")
    temp.write_bytes(b"new")
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.bronze.io_mixin._publish_new_file_exclusive",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileExistsError("exists")),
    )
    monkeypatch.setattr(host, "_compressed_payload_matches", lambda *_args: False)
    with pytest.raises(FileExistsError, match="different payload"):
        host._finalize_atomic_stream_write(
            target_path=target, temp_path=temp, record_count=1
        )

    host.base_path = tmp_path
    host._resolve_bronze_path = lambda *_args: "copy.jsonl"
    json_target = tmp_path / "copy.jsonl"
    json_target.write_bytes(b"old-json")

    async def _run() -> None:
        await host._write_json_copy(
            records=[b"new-json\n"],
            provider="chembl",
            entity="activity",
            date_str="2026-01-01",
            batch_id="b1",  # type: ignore[arg-type]
        )

    with pytest.raises(FileExistsError, match="JSON copy"):
        import asyncio

        asyncio.run(_run())

    host.COMPRESSION_CHUNK_SIZE = 1
    host._build_stream_compressor = lambda: (_ for _ in ()).throw(RuntimeError("oom"))
    with pytest.raises(RuntimeError, match="oom"):
        host._write_atomic_stream(iter([b"abc", b"def"]), tmp_path / "out.zst")
