"""Stream B APP: runner skip/error, debug-export disabled, evidence branches."""

from __future__ import annotations

from types import SimpleNamespace
from xml.etree.ElementTree import Element

import polars as pl
import pytest

from bioetl.application.composite.runner_pkg.runner_stage_mixin import (
    CompositeRunnerStageMixin,
)
from bioetl.application.core import batch_memory_decision_policy as mem
from bioetl.application.core.publication_term_extraction_mixin import (
    PublicationTermExtractionMixin,
    normalize_publication_term_limit,
)
from bioetl.application.observability.control_plane_evidence.checkpoint_validation import (
    build_checkpoint_checks,
)
from bioetl.application.pipelines.chembl import (
    target_protein_classification_transformer as tpc,
)
from bioetl.application.pipelines.common.publication_transformer_context import (
    BasePublicationTransformerContext,
    build_runtime_publication_transformer_init,
    coerce_publication_transformer_init,
)
from bioetl.application.pipelines.openalex import _extractors_authors as oa
from bioetl.application.pipelines.pubmed.extractors.classification import (
    ClassificationExtractor,
)
from bioetl.application.pipelines.semanticscholar import _author_extractors as s2
from bioetl.application.pipelines.uniprot.extractors import (
    _comment_facets_extractors as facets,
)
from bioetl.application.services.control_plane.replay._historical_certification_support import (
    HistoricalReplayCertificationValidator,
)
from bioetl.application.services.export_lineage.debug_export_service_recording_mixin import (
    DebugExportServiceRecordingMixin,
)
from bioetl.application.services.workflow import (
    _observability_workflow_evidence_support as evidence,
)
from bioetl.domain.exceptions import BioETLError

pytestmark = pytest.mark.unit


class _DisabledDebug(DebugExportServiceRecordingMixin):
    @property
    def enabled(self) -> bool:
        return False


class _TermHost(PublicationTermExtractionMixin):
    SOURCE_ENTITY_TYPE = "publication"
    PUBLICATION_LIMIT_MULTIPLIER = 2
    _data_source = SimpleNamespace()

    def _extract_terms_from_publication(
        self, record: object, publication_id: str
    ) -> list[object]:
        del record, publication_id
        return []


def test_debug_export_recording_is_noop_when_disabled() -> None:
    host = _DisabledDebug()
    host.record_bronze_batch(records=[], batch_id="b", start_index=0)
    host.record_transform_success(raw_record={}, record_index=0, silver_record={})
    host.record_transform_failure(raw_record={}, record_index=0)
    host.record_filtered_out(
        raw_record={}, record_index=0, reason="r", details=None, policy=None
    )
    host.record_data_quality_failure(
        raw_record={},
        record_index=0,
        error_type=None,
        error_details="e",
        policy=None,
    )
    host.record_gold_filter(records=[], reason_code="x")
    host.record_gold_validation_failure(records=[], errors=[])
    host.record_lineage(fragment_id="f", edge_type="e", node_id="n", raw_record={})


def test_comment_facet_extractors_return_empty_on_missing_index() -> None:
    assert facets.extract_text_values([], "FUNCTION") == []
    assert facets.extract_by_type(None, "FUNCTION") is None
    assert facets.extract_catalytic_activity(None) is None
    assert facets.extract_subcellular_locations(None) is None
    assert facets.extract_alternative_products(None) is None
    assert facets.count_isoforms(None) is None
    assert facets.extract_cofactors(None) is None
    assert facets.extract_biophysicochemical_properties(None) is None
    assert facets.extract_reactions(None) is None
    assert facets.extract_reaction_ec_numbers(None) is None
    details = facets.extract_isoform_details(None)
    assert all(
        value is None or value == "[]" or value == "" or value is not None
        for value in details.values()
    )


def test_tpc_transformer_helpers_cover_reject_and_bool_paths() -> None:
    with pytest.raises(ValueError, match="component_id"):
        tpc._target_classification_entity_id(
            {"target_id": "T1", "classification_status": "resolved"}
        )
    assert (
        tpc._target_classification_entity_id(
            {"target_id": "T1", "classification_status": "quarantined"}
        )
        == "T1:quarantined"
    )
    with pytest.raises(ValueError, match="Invalid classification_status"):
        tpc._classification_status("nope")
    assert tpc._optional_bool(None) is None
    assert tpc._optional_bool(True) is True
    assert tpc._optional_bool(1) is True
    assert tpc._optional_bool(" yes ") is True
    assert tpc._optional_bool("0") is False
    assert tpc._optional_bool("maybe") is None


def test_memory_policy_budget_and_status_branches() -> None:
    assert mem.config_budget_exceeded(None, 10) is False
    assert mem.estimate_from_config(None, 7) == 7
    assert (
        mem.decision_status(old_size=1, new_size=2, pressure_state=None) == "recovered"
    )
    assert (
        mem.decision_status(old_size=2, new_size=2, pressure_state=True) == "pressure"
    )
    assert mem.decision_status(old_size=2, new_size=2, pressure_state=False) == "stable"
    assert (
        mem.decision_status(old_size=2, new_size=2, pressure_state=None) == "disabled"
    )


def test_publication_term_mixin_zero_limit_and_helpers() -> None:
    assert normalize_publication_term_limit(None) is None
    host = _TermHost()
    record = host._create_term_record("p", "term", "keyword", None, None)
    assert record["term"] == "term"
    assert host._compute_entity_id("p", "keyword", "term")


@pytest.mark.asyncio
async def test_publication_term_zero_limit_closes_stream() -> None:
    closed: list[str] = []

    class _Stream:
        async def __aiter__(self) -> _Stream:
            return self

        async def __anext__(self) -> dict[str, str]:
            raise StopAsyncIteration

        async def aclose(self) -> None:
            closed.append("closed")

    host = _TermHost()
    items = [item async for item in host._yield_terms_from_publications(_Stream(), 0)]
    assert items == []
    assert closed == ["closed"]

    async def _filtered() -> None:
        async for _item in host._fetch_filtered_publication_terms(
            SimpleNamespace(fetch_filtered=lambda **_k: _Stream()),  # type: ignore[arg-type]
            ["id"],
            "field",
            0,
        ):
            raise AssertionError("limit 0 must not yield")

    await _filtered()


def test_publication_transformer_init_rejects_and_builds_runtime() -> None:
    ctx = BasePublicationTransformerContext(provider="pubmed")
    with pytest.raises(TypeError, match="unexpected"):
        coerce_publication_transformer_init(ctx, tracer=object())
    with pytest.raises(TypeError, match="provider"):
        coerce_publication_transformer_init(None)
    built = build_runtime_publication_transformer_init(default_provider="pubmed")
    assert callable(built)


def test_pubmed_classification_none_roots_and_normalize() -> None:
    extractor = ClassificationExtractor()
    assert extractor.extract(None) is None
    empty = Element("PubmedArticle")
    raw = extractor.extract(empty)
    assert raw is not None
    assert raw["keywords"] == []
    normalized = extractor.normalize(
        {"keywords": [" a ", None], "mesh_terms": [], "publication_types": []}
    )
    assert normalized["keywords"] == ["a"]
    assert extractor._extract_pub_types_raw(None) == []


def test_s2_and_openalex_author_id_edge_paths() -> None:
    assert s2.extract_author_ids(None) == []
    assert s2.extract_author_ids([{"authorId": "123"}, {"name": "x"}]) == ["123"]
    assert oa.extract_affiliations(
        [{"institutions": "bad"}, {"institutions": ["x", {"display_name": "MIT"}]}]
    ) == ["MIT"]
    assert (
        oa.extract_institution_ids(
            [{"institutions": "bad"}, {"institutions": [{"id": None}]}]
        )
        == []
    )
    assert oa.extract_institution_ror_ids(
        [{"institutions": "bad"}, {"institutions": [{"ror": "https://ror.org/abc"}]}]
    ) == ["https://ror.org/abc"]


def test_evidence_support_critical_and_traceability_gaps() -> None:
    assert evidence.requires_critical_dossier_evidence(None) is False
    manifest = SimpleNamespace(diagnostics={"critical_pipeline": True})
    assert evidence.requires_critical_dossier_evidence(manifest) is True  # type: ignore[arg-type]
    assert (
        evidence.resolve_required_evidence_profile(
            {"persistence_profile": {"required_profile": "forensic_grade"}}
        )
        == "forensic_grade"
    )
    assert (
        evidence.resolve_required_evidence_profile(
            {"required_persistence_profile": "replay_ready"}
        )
        == "replay_ready"
    )
    degraded = evidence.collect_traceability_degradation(
        {
            "persistence_profile": {
                "attained_profile": "replay_ready",
                "required_profile_missing_requirements": ["x"],
            },
            "correlation_anchor_gaps": {"run_id": 1},
            "composite_projection": {
                "composite_run_id_consistent": True,
                "correlation_policy": {"status": "gap"},
            },
            "trace_identifiers_available": False,
        }
    )
    assert "correlation_anchor_gaps" in degraded
    assert "composite_correlation_policy_gap" in degraded
    missing, flags = evidence.classify_evidence_status(
        run_manifest=None,
        checkpoint=None,
        lineage=None,
        quarantine_summary=None,
        traceability={},
    )
    assert missing == ("run_manifest",)
    assert "checkpoint" in flags


def test_checkpoint_validation_unknown_scope_and_invalid_saved_at() -> None:
    unknown = build_checkpoint_checks(
        manifest=None, checkpoint=None, aggregate_scope_unknown=True
    )
    assert unknown[0].reason == "aggregate_scope_requires_exact_pipeline"
    missing = build_checkpoint_checks(
        manifest=None, checkpoint=None, aggregate_scope_unknown=False
    )
    assert missing[0].reason == "checkpoint_not_found"
    schema = build_checkpoint_checks(
        manifest=None,
        checkpoint=("run", {"checkpoint_saved_at_epoch_seconds": object()}),
        aggregate_scope_unknown=False,
    )
    reasons = [item.reason for item in schema]
    assert "checkpoint_saved_at_invalid" in reasons
    anchors = build_checkpoint_checks(
        manifest=None,
        checkpoint=("run", {"records_processed": 1}),
        aggregate_scope_unknown=False,
    )
    assert any(
        item.reason == "manifest_unavailable_for_anchor_validation" for item in anchors
    )


def test_historical_certification_validator_context_guards() -> None:
    validator = HistoricalReplayCertificationValidator(
        manifest_port=SimpleNamespace(
            get=lambda _i: None, get_by_run_id=lambda _i: None
        ),  # type: ignore[arg-type]
        ledger_port=SimpleNamespace(),  # type: ignore[arg-type]
        summary_builder=SimpleNamespace(),  # type: ignore[arg-type]
    )
    with pytest.raises(ValueError, match="exactly one"):
        validator.load_manifest(manifest_id=None, run_id=None)
    with pytest.raises(ValueError, match="not found"):
        validator.load_manifest(manifest_id="m", run_id=None)
    composite = SimpleNamespace(
        launch_context={"execution_context": "composite"}, provider="chembl"
    )
    with pytest.raises(ValueError, match="source context"):
        validator.validate_source_context(composite)  # type: ignore[arg-type]
    source = SimpleNamespace(launch_context={}, provider="chembl")
    with pytest.raises(ValueError, match="composite context"):
        validator.validate_composite_context(source)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="At least one"):
        validator.validate_certification_coverage(
            manifest=SimpleNamespace(),  # type: ignore[arg-type]
            certifications=(),
        )


@pytest.mark.asyncio
async def test_runner_stage_skip_and_execution_error() -> None:
    class _Host(CompositeRunnerStageMixin):
        def _has_dependencies_configured(self) -> bool:
            return False

        async def _skip_dependencies_phase(
            self, state: object
        ) -> tuple[object, dict[str, object]]:
            return await CompositeRunnerStageMixin._skip_dependencies_phase(self, state)  # type: ignore[arg-type]

    host = _Host()
    state, results = await host._execute_dependencies_phase(  # type: ignore[misc]
        SimpleNamespace(),
        pl.DataFrame({"id": [1]}),
    )
    assert results == {}
    assert state is not None

    class _Failing(CompositeRunnerStageMixin):
        def _has_dependencies_configured(self) -> bool:
            return True

        def _prepare_dependencies_run_context(self) -> SimpleNamespace:
            return SimpleNamespace()

        async def _start_dependencies_phase(
            self, state: object, *, context: object
        ) -> object:
            del context
            return state

        async def _run_dependencies(self, **_k: object) -> dict[str, object]:
            raise BioETLError("boom")

        async def _handle_dependencies_phase_exception(
            self, state: object, error: Exception
        ) -> None:
            del state
            self.seen = type(error).__name__

    failing = _Failing()
    with pytest.raises(BioETLError, match="boom"):
        await failing._execute_started_dependencies_phase(  # type: ignore[misc]
            SimpleNamespace(),
            context=SimpleNamespace(),
            keys_df=pl.DataFrame({"id": [1]}),
        )
    assert failing.seen == "BioETLError"
