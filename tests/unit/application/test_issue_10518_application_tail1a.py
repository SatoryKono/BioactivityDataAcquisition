"""Behavior-focused unit tests for GitHub issue #10518 (application layer, tail1a).

Covers batch slice indices 0..31 of ``/tmp/batch_tail1.json``: the first 32
application-layer modules and their missing-line branches.
"""

from __future__ import annotations

import inspect
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit


# --- 0: bioetl.application.composite.column_service_support ---


def test_extract_field_two_part_qualified_name() -> None:
    from bioetl.application.composite.column_service_support import (
        extract_field_from_qualified_name,
    )

    assert extract_field_from_qualified_name("crossref.title") == "title"


def test_collect_pattern_columns_invalid_regex_warns_and_returns_empty() -> None:
    from bioetl.application.composite import column_service_support

    logger = MagicMock()
    group = SimpleNamespace(name="g", pattern="[invalid", provider_order=())
    result = column_service_support.collect_pattern_columns(
        {"col_a"}, set(), group, lambda cols, order: sorted(cols), logger
    )
    assert result == []
    logger.warning.assert_called_once()


def test_collect_alias_matches_skips_used_columns() -> None:
    from bioetl.application.composite.column_service_support import (
        _collect_alias_matches,
    )

    used = {"a"}
    matches = _collect_alias_matches(
        field_to_cols={"t": ["a", "b"]}, aliases={"t"}, used=used
    )
    assert matches == ["b"]
    assert used == {"a", "b"}


# --- 1: bioetl.application.composite.deduplication ---


def test_record_deduplicated_emits_accounting_removal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bioetl.application.composite.deduplication as dedup_module
    from bioetl.application.composite.deduplication import (
        EnricherDeduplicatorService,
    )

    accounting = MagicMock()
    monkeypatch.setattr(dedup_module, "get_stage_accounting", lambda: accounting)
    EnricherDeduplicatorService._record_deduplicated(3)
    accounting.record_removal.assert_called_once_with(
        "silver",
        outcome="deduplicated",
        reason_code="DEDUP_KEY_COLLISION",
        count=3,
    )


def test_classify_columns_empty_frame_returns_all_non_key() -> None:
    import polars as pl

    from bioetl.application.composite.deduplication import (
        EnricherDeduplicatorService,
    )

    service = EnricherDeduplicatorService(logger=MagicMock())
    df = pl.DataFrame({"k": [], "v": []}, schema={"k": pl.String, "v": pl.String})
    assert service._classify_columns(df, ["k"], ["v"]) == ([], ["v"])


def test_classify_columns_no_non_key_columns() -> None:
    import polars as pl

    from bioetl.application.composite.deduplication import (
        EnricherDeduplicatorService,
    )

    service = EnricherDeduplicatorService(logger=MagicMock())
    df = pl.DataFrame({"k": ["a", "b"], "v": ["x", "y"]})
    assert service._classify_columns(df, ["k"], []) == ([], [])


def test_classify_columns_second_early_return() -> None:
    import polars as pl

    from bioetl.application.composite.deduplication import (
        EnricherDeduplicatorService,
    )

    class _SinglePassList(list):
        """List truthy on its first truthiness check, falsy afterwards."""

        def __init__(self, *args: object) -> None:
            super().__init__(*args)  # type: ignore[arg-type]
            self._checks = 0

        def __bool__(self) -> bool:
            self._checks += 1
            return self._checks == 1

    service = EnricherDeduplicatorService(logger=MagicMock())
    df = pl.DataFrame({"k": ["a", "b"], "v": ["x", "y"]})
    assert service._classify_columns(df, ["k"], _SinglePassList(["v"])) == (
        [],
        [],
    )


def test_to_string_expr_list_dtype_stringifies() -> None:
    import polars as pl

    from bioetl.application.composite.deduplication import (
        EnricherDeduplicatorService,
    )

    service = EnricherDeduplicatorService(logger=MagicMock())
    df = pl.DataFrame({"c": [["a", "b"], ["c"]]})
    out = df.select(service._to_string_expr("c", df.schema["c"]).alias("c"))
    assert out.schema["c"] == pl.String
    values = out["c"].to_list()
    assert len(values) == 2
    assert all(isinstance(value, str) for value in values)
    assert values[0] != values[1]


def test_to_string_expr_datetime_formats_utc() -> None:
    import polars as pl
    from datetime import datetime

    from bioetl.application.composite.deduplication import (
        EnricherDeduplicatorService,
    )

    service = EnricherDeduplicatorService(logger=MagicMock())
    df = pl.DataFrame({"c": [datetime(2024, 1, 2, 3, 4, 5)]})
    out = df.select(service._to_string_expr("c", df.schema["c"]).alias("c"))
    assert out["c"].to_list() == ["2024-01-02T03:04:05Z"]


# --- 2: bioetl.application.core._batch_write_support ---


def test_emit_domain_event_logs_emitter_failure() -> None:
    from bioetl.application.core._batch_write_support import emit_domain_event

    emitter = MagicMock()
    emitter.emit_domain_event.side_effect = OSError("bus down")
    logger = MagicMock()
    emit_domain_event(emitter, MagicMock(), logger=logger)
    logger.warning.assert_called_once()


def test_emit_batch_failed_without_run_id_is_noop() -> None:
    from datetime import UTC, datetime

    from bioetl.application.core._batch_write_support import emit_batch_failed

    emitter = MagicMock()
    emit_batch_failed(
        emitter=emitter,
        run_id=None,
        batch_id="b1",  # type: ignore[arg-type]
        layer="silver",
        error=RuntimeError("x"),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    emitter.emit_domain_event.assert_not_called()


async def test_safe_write_layer_rejects_unknown_layer() -> None:
    from datetime import UTC, datetime

    from bioetl.application.core._batch_write_support import safe_write_layer

    with pytest.raises(ValueError, match="supports only 'silver' or 'gold'"):
        await safe_write_layer(
            execute_with_span=MagicMock(),
            writer=MagicMock(),
            quarantine_manager=MagicMock(),
            logger=MagicMock(),
            run_id=None,
            domain_event_emitter=None,
            layer="bronze",
            records=[],
            batch_id="b1",  # type: ignore[arg-type]
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
            bronze_refs=None,
            operation_errors=(RuntimeError,),
        )


# --- 3: bioetl.application.core.lifecycle.checkpoint_load_validation ---


def _load_validation_kwargs(statuses: list[str], result: object | None):
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

    return {
        "logger": MagicMock(),
        "pipeline_name": "pipe",
        "compatibility_policy": MagicMock(),
        "checkpoint_metadata": CheckpointMetadata(records_processed=0),
        "current_metadata": None,
        "service_available": True,
        "operation_errors": (RuntimeError,),
        "emit_checkpoint_load_status": statuses.append,
        "_result": result,
    }


def test_missing_context_result_none_reports_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bioetl.application.core.lifecycle.checkpoint_load_validation as module

    monkeypatch.setattr(module, "resolve_missing_disposition", lambda **_: "x")
    monkeypatch.setattr(
        module, "handle_missing_compatibility_context", lambda **_: None
    )
    statuses: list[str] = []
    kwargs = _load_validation_kwargs(statuses, None)
    kwargs.pop("_result")
    assert (
        module._handle_missing_compatibility_context_result(**kwargs) is None  # type: ignore[arg-type]
    )
    assert statuses == ["missing_compatibility_context"]


def test_missing_context_result_loaded_reports_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bioetl.application.core.lifecycle.checkpoint_load_validation as module
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

    loaded = CheckpointMetadata(records_processed=5)
    monkeypatch.setattr(module, "resolve_missing_disposition", lambda **_: "x")
    monkeypatch.setattr(
        module, "handle_missing_compatibility_context", lambda **_: loaded
    )
    statuses: list[str] = []
    kwargs = _load_validation_kwargs(statuses, loaded)
    kwargs.pop("_result")
    assert (
        module._handle_missing_compatibility_context_result(**kwargs)  # type: ignore[arg-type]
        is loaded
    )
    assert statuses == ["loaded"]


# --- 4: bioetl.application.core.runner_flow ---


def test_extract_checkpoint_offset_from_dataclass() -> None:
    from bioetl.application.core.runner_flow import extract_checkpoint_offset

    assert extract_checkpoint_offset(SimpleNamespace(records_processed=7)) == 7


def test_extract_checkpoint_offset_from_mapping() -> None:
    from bioetl.application.core.runner_flow import extract_checkpoint_offset

    assert extract_checkpoint_offset({"records_processed": 3}) == 3  # type: ignore[arg-type]
    assert extract_checkpoint_offset(None) is None


def test_emit_pipeline_start_and_completion() -> None:
    from bioetl.application.core.runner_flow import (
        emit_pipeline_completion,
        emit_pipeline_start,
    )

    host = SimpleNamespace(
        _logger=MagicMock(),
        _config=SimpleNamespace(pipeline_name="pipe"),
        _runtime=SimpleNamespace(run_type=SimpleNamespace(value="incremental")),
        _executor=SimpleNamespace(records_fetched=9),
    )
    emit_pipeline_start(host)  # type: ignore[arg-type]
    emit_pipeline_completion(host)  # type: ignore[arg-type]
    host._logger.info.assert_called_once()
    host._logger.debug.assert_called_once()


def test_record_run_shutdown_invariants_failure_warns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bioetl.application.core.runner_flow as flow_module
    from bioetl.application.core.runner_flow import record_run_shutdown

    def _boom(host: object, current_time_fn: object) -> None:
        raise ArithmeticError("invariants down")

    monkeypatch.setattr(flow_module, "_record_flow_invariants_impl", _boom)
    host = SimpleNamespace(
        _logger=MagicMock(),
        _context=SimpleNamespace(run_id="run-1"),
        _run_ledger_service=None,
        execution_diagnostics={},
        execution_metrics={},
    )
    record_run_shutdown(host)  # type: ignore[arg-type]
    host._logger.warning.assert_called_once()
    assert host._logger.warning.call_args.args[0] == "shutdown_flow_invariants_failed"


# --- 5: lineage_identity ---


def test_identity_gaps_reports_anchor_mismatches() -> None:
    from bioetl.domain.lineage import (
        LineageEdge,
        LineageEdgeType,
        LineageGraphFragment,
        LineageNodeRef,
        LineageNodeType,
    )
    from bioetl.application.observability.control_plane_evidence.lineage_identity import (
        identity_gaps,
    )

    manifest = SimpleNamespace(run_id="run-1", manifest_id="m-1")
    source = LineageNodeRef(node_type=LineageNodeType.SOURCE_SYSTEM, node_id="s")
    target = LineageNodeRef(node_type=LineageNodeType.DATASET, node_id="d")
    fragment = LineageGraphFragment(
        fragment_id="f1",
        run_id="other-run",
        manifest_id="other-manifest",
        nodes=(
            LineageNodeRef(
                node_type=LineageNodeType.RUN,
                node_id="run:nope",
                attributes={},
            ),
        ),
        edges=(
            LineageEdge(
                edge_type=LineageEdgeType.DERIVED_FROM,
                source=source,
                target=target,
                run_id="other-run",
                manifest_id="other-manifest",
            ),
        ),
    )
    gaps = identity_gaps(manifest=manifest, fragments=(fragment,))  # type: ignore[arg-type]
    assert "fragment_run:f1" in gaps
    assert "fragment_manifest:f1" in gaps
    assert "edge_run:s" in gaps
    assert "edge_manifest:s" in gaps
    assert "run_node:run:nope" in gaps


# --- 6: retention ---


def _retention_manifest(config_id: str | None):
    from bioetl.domain.control_plane import RunCodeProvenance, RunManifest

    return RunManifest(
        code_provenance=RunCodeProvenance(effective_config_artifact_id=config_id)
    )


def _retention_artifact(artifact_id: str):
    from bioetl.domain.control_plane import (
        ControlPlaneArtifactLifecycleDecision,
        ControlPlaneArtifactRef,
        ControlPlaneArtifactSurface,
    )

    return ControlPlaneArtifactRef(
        surface=ControlPlaneArtifactSurface.CHECKPOINT,
        path="p",
        artifact_id=artifact_id,
        decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
        reason="r",
        protected_by=(),
    )


def test_artifact_matches_effective_config() -> None:
    from bioetl.application.observability.control_plane_evidence.retention import (
        _artifact_matches_manifest,
    )

    assert (
        _artifact_matches_manifest(
            _retention_artifact("cfg1"), _retention_manifest("cfg1")
        )
        is True
    )


def test_artifact_without_match_falls_through_to_snapshots() -> None:
    from bioetl.application.observability.control_plane_evidence.retention import (
        _artifact_matches_manifest,
        _manifest_snapshot_ids,
    )

    manifest = _retention_manifest(None)
    assert _manifest_snapshot_ids(manifest) == set()
    assert _artifact_matches_manifest(_retention_artifact("zzz"), manifest) is False


# --- 7: base_chembl_transformer ---


def _transformer_dependencies():
    from bioetl.application.core.base_transformer.types import (
        TransformerDependencyContext,
    )

    return TransformerDependencyContext(
        tracer=MagicMock(),
        metrics=MagicMock(),
        identity_service=MagicMock(),
        pii_hasher=MagicMock(),
        data_normalizer=MagicMock(),
        contract_policy=MagicMock(),
        structural_policy=MagicMock(),
    )


def _make_chembl_transformer():
    from bioetl.application.pipelines.chembl.base_chembl_transformer import (
        BaseChemblTransformer,
    )

    class ConcreteChembl(BaseChemblTransformer):
        primary_id_field = "chembl_id"

        def _extract_business_data(self, record, primary_id):  # type: ignore[no-untyped-def]
            return {"chembl_id": str(primary_id)}

    transformer = ConcreteChembl(dependencies=_transformer_dependencies())
    transformer._prepare_record = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda record: record
    )
    transformer._resolve_primary_id = MagicMock(return_value="CHEMBL1")  # type: ignore[method-assign]
    transformer._extract_business_data = MagicMock(  # type: ignore[method-assign]
        return_value={"chembl_id": "CHEMBL1"}
    )
    transformer._stage_identity_business_data = MagicMock(  # type: ignore[method-assign]
        return_value={"staged": True}
    )
    return transformer


async def test_chembl_transform_pre_silver_orchestrates_steps() -> None:
    transformer = _make_chembl_transformer()
    record = {"chembl_id": "CHEMBL1"}
    result = await transformer.transform_pre_silver(
        MagicMock(),
        record,
        0,  # type: ignore[arg-type]
    )
    assert result == {"staged": True}
    transformer._prepare_record.assert_called_once_with(record)
    transformer._resolve_primary_id.assert_called_once_with(record)
    transformer._extract_business_data.assert_called_once_with(record, "CHEMBL1")
    transformer._stage_identity_business_data.assert_called_once_with(
        source_id="CHEMBL1",
        identity_field="chembl_id",
        business_data={"chembl_id": "CHEMBL1"},
    )


# --- 8: crossref transformer ---


@dataclass
class _FakeCrossrefEntity:
    issn: object = None


def _make_crossref_transformer():
    from bioetl.application.pipelines.crossref.transformer import (
        CrossRefPublicationTransformer,
    )

    transformer = object.__new__(CrossRefPublicationTransformer)
    transformer._contract_policy = SimpleNamespace(rename_map={})  # type: ignore[attr-defined]
    return transformer


def test_crossref_issn_list_splits_scalar_and_json() -> None:
    from bioetl.application.pipelines.crossref.transformer import (
        CrossRefPublicationTransformer,
    )

    transformer = _make_crossref_transformer()
    record = CrossRefPublicationTransformer.entity_to_silver_record(
        transformer, _FakeCrossrefEntity(issn=["1234-5678", "8765-4321"])
    )
    assert record["issn"] == "1234-5678"
    assert record["issn_list"] == '["1234-5678","8765-4321"]'


def test_crossref_issn_comma_string_splits_scalar_and_json() -> None:
    from bioetl.application.pipelines.crossref.transformer import (
        CrossRefPublicationTransformer,
    )

    transformer = _make_crossref_transformer()
    record = CrossRefPublicationTransformer.entity_to_silver_record(
        transformer, _FakeCrossrefEntity(issn="1234-5678, 8765-4321")
    )
    assert record["issn"] == "1234-5678"
    assert record["issn_list"] == '["1234-5678","8765-4321"]'


# --- 9: pubmed _block_helpers ---


def test_build_authors_skips_author_without_name() -> None:
    from bioetl.application.pipelines.pubmed._block_helpers import (
        build_authors_with_affiliations,
    )

    result = build_authors_with_affiliations([{}], None)  # type: ignore[list-item]
    assert result == []


def test_resolve_author_name_last_name_only_and_collective() -> None:
    from bioetl.application.pipelines.pubmed._block_helpers import (
        _resolve_author_name,
    )

    assert _resolve_author_name({"last_name": "Smith"}) == "Smith"  # type: ignore[typeddict-item]
    assert (
        _resolve_author_name({"collective_name": "Consortium"})  # type: ignore[typeddict-item]
        == "Consortium"
    )


def test_parse_month_numeric_fallback() -> None:
    from bioetl.application.pipelines.pubmed._block_helpers import parse_month

    assert parse_month("07", {}) == 7


def test_parse_month_day_empty_raw_date() -> None:
    import xml.etree.ElementTree as ET

    from bioetl.application.pipelines.pubmed._block_helpers import parse_month_day

    extractor = MagicMock()
    extractor.extract.return_value = {}
    node = ET.fromstring("<PubDate><Year>2020</Year></PubDate>")
    assert parse_month_day(node, date_extractor=extractor, month_map={}) == (None, None)


# --- 10: _checkpoint_compatibility_execution_validation ---


def _checkpoint_pair(**overrides: object):
    from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

    current_kwargs: dict[str, object] = {"records_processed": 0}
    checkpoint_kwargs: dict[str, object] = {"records_processed": 0}
    for key, value in overrides.items():
        if key.startswith("current_"):
            current_kwargs[key[len("current_") :]] = value
        else:
            checkpoint_kwargs[key] = value
    return (
        CheckpointMetadata(**current_kwargs),  # type: ignore[arg-type]
        CheckpointMetadata(**checkpoint_kwargs),  # type: ignore[arg-type]
    )


def test_mismatch_reasons_fallback_appends_fingerprints() -> None:
    from bioetl.application.services.checkpoint._checkpoint_compatibility_execution_validation import (
        _validate_mismatch_reasons,
    )

    current, checkpoint = _checkpoint_pair(
        current_execution_fingerprint="a", execution_fingerprint="b"
    )
    messages: list[str] = []
    _validate_mismatch_reasons(
        current,
        checkpoint,
        {"reason": "checkpoint_execution_identity_fallback_mismatch"},
        messages,
    )
    assert messages == [
        "Checkpoint execution identity fallback mismatch: current=a, checkpoint=b"
    ]


def test_exact_replay_mismatch_marks_incompatible() -> None:
    from bioetl.application.services.checkpoint._checkpoint_compatibility_execution_validation import (
        _validate_exact_replay_and_snapshots,
    )

    current, checkpoint = _checkpoint_pair(
        current_exact_replay=True, exact_replay=False
    )
    messages: list[str] = []
    assert (
        _validate_exact_replay_and_snapshots(current, checkpoint, messages, True)
        is False
    )
    assert any("Exact replay mismatch" in message for message in messages)


def test_snapshot_identity_mismatch_marks_incompatible() -> None:
    from bioetl.application.services.checkpoint._checkpoint_compatibility_execution_validation import (
        _validate_exact_replay_and_snapshots,
    )

    current, checkpoint = _checkpoint_pair(
        current_exact_replay=True,
        current_input_snapshot_fingerprint="fp",
        exact_replay=True,
        input_snapshot_fingerprint="fp",
        current_input_snapshot_ids=("s1",),
        input_snapshot_ids=("s2",),
    )
    messages: list[str] = []
    assert (
        _validate_exact_replay_and_snapshots(current, checkpoint, messages, True)
        is False
    )
    assert any("Input snapshot identity mismatch" in message for message in messages)


# --- 11: checkpoint_compatibility_policy ---


def test_rule_bundle_equal_versions_are_compatible() -> None:
    from bioetl.application.services.checkpoint.checkpoint_compatibility_policy import (
        validate_rule_bundle_compatibility,
    )

    current, checkpoint = _checkpoint_pair(
        current_dq_rule_bundle_version="v1", dq_rule_bundle_version="v1"
    )
    assert validate_rule_bundle_compatibility(current, checkpoint) == [
        "DQ rule bundle versions are compatible"
    ]


def test_lenient_dq_missing_hashes_are_compatible() -> None:
    from bioetl.application.services.checkpoint.checkpoint_compatibility_policy import (
        DQ_CONTRACTS_COMPATIBLE_MESSAGE,
        validate_lenient_dq_compatibility,
    )

    current, checkpoint = _checkpoint_pair()
    assert validate_lenient_dq_compatibility(current, checkpoint) == (
        True,
        [DQ_CONTRACTS_COMPATIBLE_MESSAGE],
    )


def test_lenient_pipeline_version_short_parts_are_compatible() -> None:
    from bioetl.application.services.checkpoint.checkpoint_compatibility_policy import (
        PIPELINE_VERSIONS_COMPATIBLE_MESSAGE,
        lenient_pipeline_version_message,
    )

    assert lenient_pipeline_version_message("1", "1") == (
        True,
        PIPELINE_VERSIONS_COMPATIBLE_MESSAGE,
    )


def test_lenient_pipeline_version_patch_change_message() -> None:
    from bioetl.application.services.checkpoint.checkpoint_compatibility_policy import (
        lenient_pipeline_version_message,
    )

    compatible, message = lenient_pipeline_version_message("1.2.3", "1.2.4")
    assert compatible is True
    assert "Patch pipeline version changed" in message


def test_lenient_pipeline_missing_versions_return_empty() -> None:
    from bioetl.application.services.checkpoint.checkpoint_compatibility_policy import (
        validate_lenient_pipeline_compatibility,
    )

    current, checkpoint = _checkpoint_pair()
    assert validate_lenient_pipeline_compatibility(current, checkpoint) == (
        True,
        [],
    )


# --- 12: replay_taxonomy ---


def test_resolve_replay_next_action_degraded() -> None:
    from bioetl.application.services.control_plane.manifest.replay_taxonomy import (
        resolve_replay_next_action,
    )

    assert (
        resolve_replay_next_action("resume_only_degraded")
        == "Resume is best-effort/degraded; collect missing anchors before replay claims."
    )


def test_has_missing_anchors_branches() -> None:
    from bioetl.application.services.control_plane.manifest.replay_taxonomy import (
        _has_missing_anchors,
    )

    assert _has_missing_anchors({"a": 1}) is True
    assert _has_missing_anchors("  ") is False
    assert _has_missing_anchors(0) is False
    assert _has_missing_anchors(5) is True


def test_copy_projection_value_copies_list() -> None:
    from bioetl.application.services.control_plane.manifest.replay_taxonomy import (
        _copy_projection_value,
    )

    value = [1, 2]
    copied = _copy_projection_value("definitely_not_a_taxonomy_field", value)
    assert copied == [1, 2]
    assert copied is not value


# --- 13: closure_claims ---


def test_record_manifest_id_without_attribute() -> None:
    from bioetl.application.services.control_plane.replay.closure_claims import (
        _record_manifest_id,
    )

    assert _record_manifest_id(object()) is None


def test_narrowed_scope_claim_with_blockers() -> None:
    from bioetl.application.services.control_plane.replay.closure_claims import (
        build_narrowed_scope_global_claim,
    )

    claim = build_narrowed_scope_global_claim(
        unresolved_records=(), narrowed_scope_blockers=("b1",)
    )
    assert claim["claimed"] is False
    assert (
        claim["reason"] == "retained_certifiable_scope_still_contains_in_scope_blockers"
    )


def test_universal_block_reason_unsupported_scope() -> None:
    from bioetl.application.services.control_plane.replay.closure_claims import (
        universal_scope_claim_block_reason,
    )

    assert (
        universal_scope_claim_block_reason(
            unresolved_records=(),
            has_irrecoverable=False,
            unsupported_count=2,
        )
        == "some_retained_runs_remain_outside_supported_historical_scope"
    )


def test_universal_block_reason_default() -> None:
    from bioetl.application.services.control_plane.replay.closure_claims import (
        universal_scope_claim_block_reason,
    )

    assert (
        universal_scope_claim_block_reason(
            unresolved_records=(),
            has_irrecoverable=False,
            unsupported_count=0,
        )
        == "historical_replay_closure_program_not_yet_completed"
    )


# --- 14: historical_closure_policy ---


def test_validate_residual_dispositions_duplicate_raises() -> None:
    from bioetl.application.services.control_plane.replay.historical_closure_models import (
        HistoricalReplayResidualDispositionRecord,
    )
    from bioetl.application.services.control_plane.replay.historical_closure_policy import (
        validate_residual_dispositions,
    )

    blocked = (SimpleNamespace(manifest_id="m1"),)
    disposition = HistoricalReplayResidualDispositionRecord(
        manifest_id="m1",
        disposition="reconstruct_immutable_evidence",
        rationale="r",
    )
    with pytest.raises(ValueError, match="Duplicate historical replay"):
        validate_residual_dispositions(
            blocked_records=blocked,  # type: ignore[arg-type]
            residual_dispositions=(disposition, disposition),
        )


def _closure_inventory(**kwargs: object) -> object:
    base: dict[str, object] = {
        "manifest_count": 2,
        "certified_count": 0,
        "replayable_count": 0,
        "unsupported_count": 2,
        "remaining_uncertified_count": 2,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_resolve_closure_verdict_outside_supported_scope() -> None:
    from bioetl.application.services.control_plane.replay.historical_closure_policy import (
        resolve_closure_verdict,
    )

    assert resolve_closure_verdict(
        inventory=_closure_inventory(),  # type: ignore[arg-type]
        unresolved_records=(),
        disposition_map={},
        claim_scope_mode="all_retained_historical_runs",
    ) == (
        "outside_supported_scope_present",
        "some_retained_runs_remain_outside_the_current_supported_historical_replay_scope",
    )


def test_resolve_closure_verdict_resolution_in_progress() -> None:
    from bioetl.application.services.control_plane.replay.historical_closure_models import (
        HistoricalReplayResidualDispositionRecord,
    )
    from bioetl.application.services.control_plane.replay.historical_closure_policy import (
        resolve_closure_verdict,
    )

    disposition = HistoricalReplayResidualDispositionRecord(
        manifest_id="m1",
        disposition="reconstruct_immutable_evidence",
        rationale="r",
    )
    assert resolve_closure_verdict(
        inventory=_closure_inventory(manifest_count=1, unsupported_count=0),  # type: ignore[arg-type]
        unresolved_records=(),
        disposition_map={"m1": disposition},
        claim_scope_mode="all_retained_historical_runs",
    ) == (
        "residual_resolution_program_in_progress",
        "all_remaining_blocked_runs_have_explicit_resolution_tracks_but_not_yet_closed",
    )


def test_suggested_disposition_unknown_status() -> None:
    from bioetl.application.services.control_plane.replay.historical_closure_policy import (
        _suggested_disposition,
    )

    record = SimpleNamespace(certification_status="something_else")
    assert _suggested_disposition(record) == "manual_review_required"  # type: ignore[arg-type]


# --- 15: debug_export_collector_transform_mixin ---


def test_gold_filter_message_none_uses_default() -> None:
    from bioetl.application.services.export_lineage.debug_export_collector_transform_mixin import (
        _GOLD_SEMANTIC_FILTER_EXCLUDED_MSG,
        _gold_filter_message,
    )

    assert _gold_filter_message(None) == _GOLD_SEMANTIC_FILTER_EXCLUDED_MSG


def test_gold_filter_rule_id_none_is_empty() -> None:
    from bioetl.application.services.export_lineage.debug_export_collector_transform_mixin import (
        _gold_filter_rule_id,
    )

    assert _gold_filter_rule_id(None) == ""


def test_gold_filter_reason_code_passthrough() -> None:
    from bioetl.application.services.export_lineage.debug_export_collector_transform_mixin import (
        _gold_filter_reason_code,
    )

    assert (
        _gold_filter_reason_code({"reason_code": "gold_semantic_custom"})
        == "gold_semantic_custom"
    )


def test_gold_filter_reason_code_profile_scope() -> None:
    from bioetl.application.services.export_lineage.debug_export_collector_transform_mixin import (
        _gold_filter_reason_code,
    )
    from bioetl.domain.types import GoldRejectReasonCode

    assert (
        _gold_filter_reason_code(
            {"reason_code": "other", "semantic_scope": "profile filter"}
        )
        == GoldRejectReasonCode.SEMANTIC_PROFILE_EXCLUSION.value
    )


def test_gold_filter_contract_version_none_is_unknown() -> None:
    from bioetl.application.services.export_lineage.debug_export_collector_transform_mixin import (
        _gold_filter_contract_version,
    )
    from bioetl.domain.types import GOLD_CONTRACT_VERSION_UNKNOWN

    assert _gold_filter_contract_version(None) == GOLD_CONTRACT_VERSION_UNKNOWN


# --- 16: admin_runtime_api ---


def test_admin_runtime_api_reexports_core_services() -> None:
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointRuntimeService as CoreCheckpointService,
    )
    from bioetl.application.core.lifecycle.cleanup_service import (
        CleanupService as CoreCleanupService,
    )
    from bioetl.application.core.quarantine_manager import (
        QuarantineRuntimeService as CoreQuarantineService,
    )
    from bioetl.application.services.ops import admin_runtime_api

    assert admin_runtime_api.CheckpointRuntimeService is CoreCheckpointService
    assert admin_runtime_api.CleanupService is CoreCleanupService
    assert admin_runtime_api.QuarantineRuntimeService is CoreQuarantineService
    assert set(admin_runtime_api.__all__) == {
        "CheckpointRuntimeService",
        "CleanupService",
        "QuarantineRuntimeService",
    }


# --- 17: error_handler ---


def test_increment_counter_uses_canonical_api() -> None:
    from bioetl.application.services.ops.error_handler import ErrorHandlerService

    handler = ErrorHandlerService(
        logger=MagicMock(), metrics=MagicMock(), service_name="test"
    )
    handler._increment_counter("errors_total", 2, labels={"kind": "value"})
    handler._metrics.increment_counter.assert_called_once_with(
        "errors_total", 2, labels={"kind": "value"}
    )


def test_increment_counter_without_metrics_api_is_noop() -> None:
    from bioetl.application.services.ops.error_handler import ErrorHandlerService

    handler = ErrorHandlerService(
        logger=MagicMock(), metrics=SimpleNamespace(), service_name="test"
    )
    handler._increment_counter("errors_total", 1)


def test_legacy_increment_kwargs_signature_failure_inspect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import inspect as inspect_module

    from bioetl.application.services.ops.error_handler import (
        _legacy_increment_kwargs,
    )

    def _boom(func: object) -> object:
        raise ValueError("no signature")

    monkeypatch.setattr(inspect_module, "signature", _boom)
    assert _legacy_increment_kwargs(MagicMock(), 1, None) == {}


# --- 18: run_reports paths ---


def test_source_identity_path_non_run_reports_root(tmp_path: Path) -> None:
    from bioetl.application.services.run_reports.paths import (
        REPORT_ROOT_SOURCE_IDENTITY_NAME,
        report_root_source_identity_path,
    )

    root = tmp_path / "other"
    assert report_root_source_identity_path(report_root=root) == (
        root / REPORT_ROOT_SOURCE_IDENTITY_NAME
    )


def test_inspect_source_identity_missing_expected(tmp_path: Path) -> None:
    from bioetl.application.services.run_reports.paths import (
        inspect_report_root_source_identity,
    )

    payload = inspect_report_root_source_identity(
        report_root=tmp_path, expected_source_id=None
    )
    assert payload["source_identity"] == "expected_missing"
    assert payload["source_identity_status"] == "unhealthy"


def test_read_identity_preview_store_failure() -> None:
    from bioetl.application.services.run_reports.paths import (
        IdentityIndexPreview,
        read_identity_preview,
    )

    store = MagicMock()
    store.read_text.side_effect = OSError("unreadable")
    assert read_identity_preview(Path("r.json"), store=store) == (
        IdentityIndexPreview(None, None, None, None, None, None)
    )


def test_read_identity_preview_missing_identity() -> None:
    from bioetl.application.services.run_reports.paths import (
        IdentityIndexPreview,
        read_identity_preview,
    )

    store = MagicMock()
    store.read_text.return_value = '{"runs": []}'
    assert read_identity_preview(Path("r.json"), store=store) == (
        IdentityIndexPreview(None, None, None, None, None, None)
    )


# --- 19: composite __init__ ---


def test_composite_lazy_export_resolves_and_caches() -> None:
    import bioetl.application.composite as composite_pkg

    first = composite_pkg.__getattr__("ColumnOrderService")
    second = composite_pkg.__getattr__("ColumnOrderService")
    assert first is second
    assert first.__name__ == "ColumnOrderService"


def test_composite_dir_exposes_lazy_exports() -> None:
    import bioetl.application.composite as composite_pkg

    assert "ColumnOrderService" in composite_pkg.__dir__()


def test_composite_getattr_unknown_raises() -> None:
    import bioetl.application.composite as composite_pkg

    with pytest.raises(AttributeError):
        composite_pkg.__getattr__("NoSuchExport10518")


# --- 20: _preflight_field_priority ---


def test_normalization_profile_mismatch_issue() -> None:
    from bioetl.application.composite._preflight_field_priority import (
        normalization_profile_mismatch_issue,
    )

    issue = normalization_profile_mismatch_issue(
        field_name="title",
        priorities=("a", "b"),
        field_profile_hashes={"a": "h1", "b": "h2"},
        compatibility_overrides={},
    )
    assert issue is not None
    assert issue.issue_type == "normalization_profile_mismatch"
    assert issue.severity == "error"


def test_record_field_profile_hash() -> None:
    from bioetl.application.composite._preflight_field_priority import (
        _record_field_profile_hash,
    )
    from bioetl.application.composite._preflight_types import ProfileInfo

    hashes: dict[str, str] = {}
    _record_field_profile_hash(
        field_name="title",
        source="ChemBL",
        source_lower="chembl",
        source_profiles={
            "chembl": ProfileInfo(
                source="chembl",
                profile_name="p",
                profile_version="1",
                profile_hash="ph",
                field_hashes={"title": "h1"},
            )
        },
        field_profile_hashes=hashes,
    )
    assert hashes == {"ChemBL": "h1"}


# --- 21: aggregator ---


def test_deduplicate_columns_first_seen_order() -> None:
    from bioetl.application.composite.aggregator import _deduplicate_columns

    assert _deduplicate_columns(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_sort_for_deterministic_aggregation_missing_columns() -> None:
    import polars as pl

    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.domain.composite.aggregation import (
        AggregationConfig,
        AggregationFieldSpec,
        AggregationFunction,
    )

    service = EnricherAggregator(logger=MagicMock())
    config = AggregationConfig(
        group_by="missing_key",
        fields=(
            AggregationFieldSpec(
                source_field="v", agg_function=AggregationFunction.FIRST
            ),
        ),
        order_by=("missing_col",),
    )
    df = pl.DataFrame({"k": ["a"], "v": ["x"]})
    assert service._sort_for_deterministic_aggregation(df, config) is df


def test_build_aggregation_expr_unknown_function_passthrough() -> None:
    import polars as pl

    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.domain.composite.aggregation import AggregationFieldSpec

    service = EnricherAggregator(logger=MagicMock())
    spec = object.__new__(AggregationFieldSpec)
    object.__setattr__(spec, "source_field", "v")
    object.__setattr__(spec, "agg_function", "bogus_function")
    object.__setattr__(spec, "filter_condition", None)
    object.__setattr__(spec, "output_field", None)
    df = pl.DataFrame({"v": ["x", "y"]})
    out = df.select(service._build_aggregation_expr(spec))
    assert out.columns == ["v"]
    assert out["v"].to_list() == ["x", "y"]


# --- 22: checkpoint persistence_service ---


def test_emit_saved_at_without_timestamps_is_noop() -> None:
    from bioetl.application.composite.checkpoint.persistence_service import (
        CompositeCheckpointPersistenceService,
    )
    from bioetl.application.composite.checkpoint.state import (
        CompositeCheckpointState,
    )

    service = CompositeCheckpointPersistenceService(
        composite_name="c",
        checkpoint_filename="ckpt.json",
        glob_pattern="ckpt*",
        storage=MagicMock(),
        logger=MagicMock(),
        metrics=MagicMock(),
    )
    state = CompositeCheckpointState(
        composite_name="c", run_id="r", created_at=None, updated_at=None
    )
    service._emit_checkpoint_saved_at_from_state(state)
    service._metrics.set_gauge.assert_not_called()


def test_save_unexpected_domain_error_reraises() -> None:
    from bioetl.application.composite.checkpoint.persistence_service import (
        CompositeCheckpointPersistenceService,
    )
    from bioetl.application.composite.checkpoint.state import (
        CompositeCheckpointState,
    )
    from bioetl.domain.exceptions import BioETLError

    service = CompositeCheckpointPersistenceService(
        composite_name="c",
        checkpoint_filename="ckpt.json",
        glob_pattern="ckpt*",
        storage=MagicMock(),
        logger=MagicMock(),
    )
    service._storage.write_atomic.side_effect = BioETLError("boom")
    state = CompositeCheckpointState(composite_name="c", run_id="r")
    with pytest.raises(BioETLError):
        service.save(state)
    service._logger.error.assert_called_once()


# --- 23: cross_validator_helpers ---


def test_compare_field_skip_matches_everything() -> None:
    import polars as pl

    from bioetl.application.composite.cross_validator_helpers import (
        _compare_field,
    )
    from bioetl.domain.composite.cross_validation import ComparisonMethod

    df = pl.DataFrame({"s": ["a", "b"], "e": ["x", "y"]})
    result = _compare_field(df, "s", "e", ComparisonMethod.SKIP, 0.5)
    assert result.to_list() == [True, True]


def test_build_enricher_detail_empty_fields() -> None:
    import polars as pl

    from bioetl.application.composite.cross_validator_helpers import (
        _build_enricher_detail,
    )

    result = _build_enricher_detail("pipe", {}, pl.Series([0, 1]))
    assert result.to_list() == [None, None]


def test_combine_cv_details_empty() -> None:
    import polars as pl

    from bioetl.application.composite.cross_validator_helpers import (
        _combine_cv_details,
    )

    result = _combine_cv_details([], 2)
    assert result.to_list() == [None, None]


def test_compare_fuzzy_null_values_match() -> None:
    import polars as pl

    from bioetl.application.composite.cross_validator_helpers import (
        _compare_fuzzy,
    )

    df = pl.DataFrame({"s": [None], "e": ["x"]})
    assert _compare_fuzzy(df, "s", "e", 0.9).to_list() == [True]


# --- 24: runner_control_plane_mixin ---


def _ledger_mixin_host():
    from bioetl.application.composite.runner_pkg.runner_control_plane_mixin import (
        _CompositeRunnerLedgerLifecycleMixin,
    )

    class Host(_CompositeRunnerLedgerLifecycleMixin):
        pass

    return object.__new__(Host)


def test_ledger_mixin_delegates_with_ledger_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bioetl.application.composite.runner_pkg.runner_control_plane_mixin as mixin_module

    calls: list[str] = []
    monkeypatch.setattr(
        mixin_module,
        "record_with_ledger_service",
        lambda host, recorder: calls.append("with_ledger"),
    )
    host = _ledger_mixin_host()
    host._record_with_ledger_service(lambda service: "ok")
    assert calls == ["with_ledger"]


def test_ledger_mixin_delegates_metrics_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bioetl.application.composite.runner_pkg.runner_control_plane_mixin as mixin_module

    calls: list[str] = []
    monkeypatch.setattr(
        mixin_module,
        "record_run_metrics_event",
        lambda host, **_: calls.append("metrics"),
    )
    host = _ledger_mixin_host()
    host._record_run_metrics_event(metrics_snapshot={}, recorder=lambda *args: None)
    assert calls == ["metrics"]


def test_ledger_mixin_delegates_stage_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bioetl.application.composite.runner_pkg.runner_control_plane_mixin as mixin_module

    calls: list[str] = []
    monkeypatch.setattr(
        mixin_module,
        "record_stage_started",
        lambda host, **_: calls.append("started"),
    )
    monkeypatch.setattr(
        mixin_module,
        "record_stage_completed",
        lambda host, **_: calls.append("completed"),
    )
    host = _ledger_mixin_host()
    host._record_stage_started(stage="seed")
    host._record_stage_completed(stage="seed", metrics_snapshot={})
    assert calls == ["started", "completed"]


# --- 25: _structural_policy_contracts ---


def test_resolve_pandera_schema_with_columns() -> None:
    from bioetl.application.core.base_transformer._structural_policy_contracts import (
        resolve_pandera_schema,
    )

    schema = SimpleNamespace(columns={"a": 1})
    assert resolve_pandera_schema(schema) is schema


def test_resolve_pandera_schema_without_builder() -> None:
    from bioetl.application.core.base_transformer._structural_policy_contracts import (
        resolve_pandera_schema,
    )

    assert resolve_pandera_schema(object()) is None


def test_is_missing_value_string_branches() -> None:
    from bioetl.application.core.base_transformer._structural_policy_contracts import (
        is_missing_value,
    )

    assert (
        is_missing_value("hello", logical_type="string", empty_as_missing=None) is False
    )
    assert is_missing_value([], logical_type="string", empty_as_missing=True) is True


# --- 26: base_transformer base ---


def _concrete_base_transformer(**kwargs: object):
    from bioetl.application.core.base_transformer.base import BaseTransformer

    class ConcreteTransformer(BaseTransformer):
        async def _transform_impl(self, context, record, index):  # type: ignore[no-untyped-def]
            return None

    if "dependencies" not in kwargs:
        kwargs["dependencies"] = _transformer_dependencies()
    return ConcreteTransformer(provider="p", **kwargs)  # type: ignore[arg-type]


def test_base_transformer_unexpected_kwarg_raises() -> None:
    with pytest.raises(TypeError, match="unexpected keyword"):
        _concrete_base_transformer(bogus_kwarg=1)


def test_should_write_silver_delegates_to_filters() -> None:
    filters = MagicMock()
    filters.is_empty.return_value = False
    filters.should_include.return_value = True
    transformer = _concrete_base_transformer(silver_filters=filters)
    assert transformer.should_write_silver(MagicMock(), {"a": 1}) is True
    filters.should_include.assert_called_once_with({"a": 1})


# --- 27: batch_executor_dq_mixin ---


def test_serialize_dq_sample_item_undecodable_bytes() -> None:
    from bioetl.application.core.batch_executor_dq_mixin import (
        _BatchExecutorDQMixin,
    )

    raw = b"\xff\xd8\xff"
    assert _BatchExecutorDQMixin._serialize_dq_sample_item(raw) == raw.hex()


def test_dataframe_error_types_returns_tuple() -> None:
    from bioetl.application.core.batch_executor_dq_mixin import (
        _BatchExecutorDQMixin,
    )

    error_types = _BatchExecutorDQMixin._dataframe_error_types()
    assert isinstance(error_types, tuple)
    assert all(
        isinstance(item, type) and issubclass(item, Exception) for item in error_types
    )


def test_stringify_value_delegates_to_helper() -> None:
    from bioetl.application.core.batch_executor_dq_helpers import stringify_value
    from bioetl.application.core.batch_executor_dq_mixin import (
        _BatchExecutorDQMixin,
    )

    assert _BatchExecutorDQMixin._stringify_value("v", {"k"}, "k") == stringify_value(
        "v", {"k"}, "k"
    )


# --- 28: batch_writer_columns_mixin ---


def test_apply_renames_to_schema_none_passthrough() -> None:
    from bioetl.application.core.batch_writer_columns_mixin import (
        BatchWriterColumnsMixin,
    )

    mixin = object.__new__(BatchWriterColumnsMixin)
    assert mixin._apply_renames_to_schema(None, {"a": "b"}) is None


def test_apply_renames_to_schema_identity_passthrough() -> None:
    from bioetl.application.core.batch_writer_columns_mixin import (
        BatchWriterColumnsMixin,
    )

    mixin = object.__new__(BatchWriterColumnsMixin)
    schema = SimpleNamespace(
        names=["a"], rename_columns=MagicMock(return_value="renamed")
    )
    assert mixin._apply_renames_to_schema(schema, {"a": "a"}) is schema


def test_apply_renames_to_schema_rename_failure_passthrough() -> None:
    from bioetl.application.core.batch_writer_columns_mixin import (
        BatchWriterColumnsMixin,
    )

    mixin = object.__new__(BatchWriterColumnsMixin)
    schema = SimpleNamespace(
        names=["a"],
        rename_columns=MagicMock(side_effect=OSError("rename down")),
    )
    assert mixin._apply_renames_to_schema(schema, {"a": "b"}) is schema


# --- 29: postrun _phase_runtime ---


def test_resolve_postrun_phase_log_level_failed() -> None:
    from bioetl.application.core.postrun._phase_runtime import (
        resolve_postrun_phase_log_level,
    )

    assert resolve_postrun_phase_log_level("failed") == "error"
    assert resolve_postrun_phase_log_level("warning") == "warning"
    assert resolve_postrun_phase_log_level("ok") == "info"


async def test_run_async_postrun_phase_failure_emits_and_reraises() -> None:
    from bioetl.application.core.postrun._phase_runtime import (
        run_async_postrun_phase,
    )

    async def _failing() -> str:
        raise RuntimeError("phase down")

    emitted: list[dict[str, object]] = []

    def _emit(**kwargs: object) -> None:
        emitted.append(kwargs)

    with pytest.raises(RuntimeError, match="phase down"):
        await run_async_postrun_phase(
            span_factory=lambda name: nullcontext(MagicMock()),
            phase="compaction",  # type: ignore[arg-type]
            operation=_failing,
            operation_errors=(RuntimeError,),
            emit_phase_observability=_emit,
            on_success=MagicMock(),
        )
    assert emitted and emitted[0]["status"] == "failed"


# --- 30: medallion_validator_runtime ---


def _medallion_policy(clear_policy: object):
    from bioetl.domain.medallion import MedallionPolicy

    return MedallionPolicy(clear_policy=clear_policy)  # type: ignore[arg-type]


def test_medallion_rebuild_requires_clear() -> None:
    from bioetl.application.core.preflight.medallion_validator_runtime import (
        validate_medallion_policy_consistency,
    )
    from bioetl.domain.medallion import ClearPolicy
    from bioetl.domain.types import RunType

    errors = validate_medallion_policy_consistency(
        run_type=RunType.REBUILD, policy=_medallion_policy(ClearPolicy.NEVER)
    )
    fields = [error.field for error in errors]
    assert "medallion_policy.should_clear_silver" in fields
    assert "medallion_policy.should_clear_gold" in fields


def test_medallion_incremental_forbids_clear() -> None:
    from bioetl.application.core.preflight.medallion_validator_runtime import (
        validate_medallion_policy_consistency,
    )
    from bioetl.domain.medallion import ClearPolicy
    from bioetl.domain.types import RunType

    errors = validate_medallion_policy_consistency(
        run_type=RunType.INCREMENTAL,
        policy=_medallion_policy(ClearPolicy.SILVER_AND_GOLD),
    )
    fields = [error.field for error in errors]
    assert "medallion_policy.should_clear_silver" in fields
    assert "medallion_policy.should_clear_gold" in fields


# --- 31: manifest_validation ---


def test_raw_manifest_checks_parse_failure() -> None:
    from bioetl.application.observability.control_plane_evidence.manifest_validation import (
        _raw_manifest_checks,
    )
    from bioetl.domain.ports import RawManifestInspection

    checks = _raw_manifest_checks(
        RawManifestInspection(parse_ok=False, schema_errors=("boom",))
    )
    assert checks[0].check == "parse"
    assert checks[0].status == "ERROR"
    assert checks[0].reason == "boom"


def test_raw_manifest_checks_schema_errors() -> None:
    from bioetl.application.observability.control_plane_evidence.manifest_validation import (
        _raw_manifest_checks,
    )
    from bioetl.domain.ports import RawManifestInspection

    checks = _raw_manifest_checks(
        RawManifestInspection(parse_ok=True, schema_errors=("e1", "e2"))
    )
    assert checks[0].reason == "manifest_parse_ok"
    assert [check.reason for check in checks[1:]] == ["e1", "e2"]
