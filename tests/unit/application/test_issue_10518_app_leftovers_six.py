"""Stream B APP: leftover 3-line diagnostics, identity, and payload branches."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType, SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.checkpoint._checkpoint_warnings import (
    warn_if_checkpoint_exists_with_progress,
)
from bioetl.application.composite.helpers.join_planner_identity import (
    infer_silver_table,
    resolve_field_aliases_from_registry,
    table_path_to_name,
)
from bioetl.application.core._record_normalization_contract import _NormalizationFinding
from bioetl.application.core._record_normalization_runtime_support import (
    profile_json_runtime_finding,
    project_normalization_findings,
)
from bioetl.application.core.base_transformer._structural_policy_contracts import (
    is_missing_value,
    resolve_pandera_schema,
)
from bioetl.application.core.data_sources.subcellular_fraction import (
    SubcellularFractionDataSource,
)
from bioetl.application.pipelines.openalex._extractors_publication_fields import (
    extract_journal_info,
    reconstruct_abstract,
)
from bioetl.application.services.control_plane.ledger.rich_events import (
    RunLedgerRichEventRecordingMixin,
)
from bioetl.application.services.control_plane.manifest.diagnostics import (
    _as_str_object_dict,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_blockers import (
    _collect_append_mode_semantic_sinks,
    _is_append_enabled_sink,
    _normalize_declared_append_mode_sinks,
)
from bioetl.application.services.control_plane.replay.reproducibility_score_cards_category_scores import (
    score_lineage_completeness,
)
from bioetl.application.services.workflow.control_plane.execution_recording_payloads import (
    _artifact_refs,
    build_step_completion_details,
)
from bioetl.domain.exceptions import BioETLError

pytestmark = pytest.mark.unit


def test_diagnostics_mapping_and_lineage_score() -> None:
    assert _as_str_object_dict(MappingProxyType({"k": 1})) == {"k": 1}
    with pytest.raises(TypeError, match="expected mapping"):
        _as_str_object_dict("nope")
    card = score_lineage_completeness(
        {
            "identity_graph_complete": True,
            "lineage_closure_boundary": {"supported": False},
            "lineage_fragment_ids": ["f1"],
        }
    )
    assert "lineage_closure_boundary_unsupported" in card.evidence


def test_openalex_journal_and_abstract_fallbacks() -> None:
    assert extract_journal_info({"source": "not-a-dict"}) == {
        "journal": None,
        "issn": None,
        "publisher": None,
    }
    assert reconstruct_abstract({"word": "not-list"}) is None
    assert reconstruct_abstract({"word": []}) is None


def test_schema_missing_join_identity_and_sinks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert resolve_pandera_schema(None) is None
    schema = SimpleNamespace(columns={"id": object()})
    assert resolve_pandera_schema(schema) is schema
    built = SimpleNamespace(to_schema=lambda: schema)
    assert resolve_pandera_schema(built) is schema
    assert is_missing_value({}, logical_type="object", empty_as_missing=True) is True
    monkeypatch.setattr(
        "bioetl.application.composite.helpers.join_planner_identity.get_alias_map_for_provider",
        lambda _provider: {},
    )
    assert resolve_field_aliases_from_registry("chembl_activity") is None
    assert infer_silver_table("nounderscore") == "silver/nounderscore"
    assert table_path_to_name("plain") == "plain"
    assert _normalize_declared_append_mode_sinks("nope") == []
    assert _is_append_enabled_sink(1, {}) is False
    manifest = SimpleNamespace(
        launch_context={"append_mode_semantic_sinks": [" gold "]},
        runtime_config={},
        resolved_config={},
    )
    assert _collect_append_mode_semantic_sinks(manifest) == ["gold"]  # type: ignore[arg-type]


def test_rich_events_and_checkpoint_warning_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []
    monkeypatch.setattr(
        "bioetl.application.services.control_plane.ledger.rich_events.record_composite_dependency_completed",
        lambda *_a, **_k: seen.append("dep") or "dep",
    )
    monkeypatch.setattr(
        "bioetl.application.services.control_plane.ledger.rich_events.record_composite_enricher_completed",
        lambda *_a, **_k: seen.append("enr") or "enr",
    )
    monkeypatch.setattr(
        "bioetl.application.services.control_plane.ledger.rich_events.record_composite_merge_completed",
        lambda *_a, **_k: seen.append("merge") or "merge",
    )

    class _Host(RunLedgerRichEventRecordingMixin):
        pass

    host = _Host()
    host.record_composite_dependency_completed(dependency_name="d", result={})
    host.record_composite_enricher_completed(enricher_name="e", result={})
    host.record_composite_merge_completed(result={})
    assert seen == ["dep", "enr", "merge"]

    storage = MagicMock()
    storage.exists.return_value = True
    storage.read.return_value = None
    monkeypatch.setattr(
        "bioetl.application.composite.checkpoint._checkpoint_warnings.latest_checkpoint_filename",
        lambda **_k: "cp.json",
    )
    warn_if_checkpoint_exists_with_progress(
        storage=storage,
        logger=MagicMock(),
        composite_name="chembl_activity",
        glob_pattern="cp-*.json",
    )
    storage.read.side_effect = BioETLError("bio")
    logger = MagicMock()
    warn_if_checkpoint_exists_with_progress(
        storage=storage,
        logger=logger,
        composite_name="chembl_activity",
        glob_pattern="cp-*.json",
    )
    logger.warning.assert_called()


def test_normalization_subcellular_and_step_payloads() -> None:
    finding = _NormalizationFinding(
        field_name="payload",
        reason_code="malformed_json_normalized_to_null",
        action_taken="set_null_and_warn",
    )
    projected = project_normalization_findings(
        (finding,),
        {"id": 1},
        context=None,
        index=0,
        provider="chembl",
        entity_type="activity",
    )
    assert projected["_dq_warn"] is True
    rule = SimpleNamespace(notes="json", normalizer=SimpleNamespace(__name__="as_json"))
    malformed = profile_json_runtime_finding(
        rule,  # type: ignore[arg-type]
        field_name="payload",
        raw_value="{bad",
        normalized_value=None,
        finding_factory=_NormalizationFinding,
    )
    assert malformed is not None
    assert SubcellularFractionDataSource._normalize_fraction(" cytosol ")
    assert SubcellularFractionDataSource._compute_entity_id("cytosol")
    record = SubcellularFractionDataSource.__new__(
        SubcellularFractionDataSource
    )._create_fraction_record({"assay_id": 1}, "cytosol")
    assert record
    pipeline = SimpleNamespace(
        step_kind="pipeline",
        status="success",
        payload={},
        child_run_id="run-2",
        child_manifest_id="m-2",
    )
    assert build_step_completion_details(pipeline) is not None  # type: ignore[arg-type]
    other = SimpleNamespace(
        step_kind="transform",
        status="success",
        payload={"output": "nope", "fingerprint": "fp"},
    )
    assert build_step_completion_details(other) == {"fingerprint": "fp"}  # type: ignore[arg-type]
    assert _artifact_refs({"artifact_refs": "nope"}) is None
