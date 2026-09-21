"""Behavior-focused unit tests for GitHub issue #10518 (application layer, tail1b).

Covers batch slice indices 32..62 of ``/tmp/batch_tail1.json`` (31 modules,
``observer_context_mixin`` through ``_crossref_go``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

pytestmark = pytest.mark.unit

from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


# ---------------------------------------------------------------------------
# observer_context_mixin.py [153, 268, 269, 270]
# ---------------------------------------------------------------------------

from bioetl.application.observability.observer_context_mixin import (
    _ObserverContextManagerMixin,
)


def _make_observer(**overrides: object) -> _ObserverContextManagerMixin:
    host = object.__new__(_ObserverContextManagerMixin)
    host.pipeline_name = "chembl"
    host.run_id = "run-1"
    host.run_type = "incremental"
    host.manifest_id = "m-1"
    host.effective_config_hash = "hash-1"
    host.contract_ref = None
    host.contract_version = None
    host.composite_run_id = None
    host.span = None
    host._tracer = None
    for key, value in overrides.items():
        setattr(host, key, value)
    return host


class TestBuildTraceAttributes:
    def test_optional_values_propagated_and_nones_skipped(self) -> None:
        attrs = _make_observer()._build_trace_attributes()
        assert attrs["bioetl.pipeline"] == "chembl"
        assert attrs["bioetl.manifest_id"] == "m-1"
        assert attrs["bioetl.effective_config_hash"] == "hash-1"
        assert "bioetl.contract_ref" not in attrs
        assert "bioetl.contract_version" not in attrs
        assert "bioetl.composite_run_id" not in attrs


class TestCloseSpanSafely:
    def test_failed_status_records_exception_and_error_flag(self) -> None:
        span = MagicMock()
        host = _make_observer(span=span, _tracer=MagicMock())
        error = ValueError("boom")
        host._close_span_safely("failed", 0.5, None, error, None)
        span.record_exception.assert_called_once_with(error)
        span.set_attribute.assert_any_call("error", True)
        span.__exit__.assert_called_once_with(None, error, None)


# ---------------------------------------------------------------------------
# chembl/target_transformer.py [194, 195, 196, 197]
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer


def _make_target_transformer() -> TargetTransformer:
    return TargetTransformer(
        provider="chembl", dependencies=build_test_transformer_dependencies()
    )


class TestTargetTransformForGold:
    def test_renames_target_description_to_description(self) -> None:
        gold = _make_target_transformer().transform_for_gold(
            MagicMock(), {"target_description": "kinase", "other": 1}
        )
        assert gold["description"] == "kinase"
        assert "target_description" not in gold
        assert gold["other"] == 1

    def test_missing_description_projects_none(self) -> None:
        gold = _make_target_transformer().transform_for_gold(MagicMock(), {"a": 1})
        assert gold["description"] is None


# ---------------------------------------------------------------------------
# crossref/author_extractors.py [43, 68, 139, 165]
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.crossref.author_extractors import (
    _extract_author_affiliations_list,
    _normalize_orcid,
    extract_author_details,
    extract_author_orcids,
)


class TestCrossrefAuthorEdgeCases:
    def test_blank_orcid_normalizes_to_none(self) -> None:
        assert _normalize_orcid("   ") is None

    def test_non_list_affiliation_returns_empty(self) -> None:
        assert _extract_author_affiliations_list({"affiliation": "not-a-list"}) == []

    def test_non_dict_authors_skipped_in_details(self) -> None:
        assert extract_author_details({"author": ["junk", 42]}) == []

    def test_non_dict_authors_skipped_in_orcids(self) -> None:
        assert extract_author_orcids({"author": [None, "junk"]}) == []


# ---------------------------------------------------------------------------
# pubmed/extractors/identifier.py [162, 238, 272, 276]
# ---------------------------------------------------------------------------

from xml.etree.ElementTree import Element, SubElement

from bioetl.application.pipelines.pubmed.extractors.identifier import (
    IdentifierExtractor,
)


class TestPubmedIdentifierBlanks:
    def test_elocation_whitespace_text_skipped(self) -> None:
        extractor = IdentifierExtractor()
        article = Element("Article")
        eloc = SubElement(article, "ELocationID")
        eloc.set("EIdType", "doi")
        eloc.text = "   "
        result: dict[str, str | None] = {"doi": None, "pii": None}
        extractor._scan_elocation_ids(article, result)
        assert result == {"doi": None, "pii": None}

    def test_article_id_whitespace_text_skipped(self) -> None:
        root = Element("PubmedArticle")
        id_list = SubElement(root, "ArticleIdList")
        aid = SubElement(id_list, "ArticleId")
        aid.set("IdType", "doi")
        aid.text = "  "
        out = IdentifierExtractor.parse_all_article_ids(root)
        assert out["doi"] is None

    def test_elocation_missing_type_and_blank_text_skipped(self) -> None:
        root = Element("PubmedArticle")
        article = SubElement(root, "Article")
        SubElement(article, "ELocationID")
        blank = SubElement(article, "ELocationID")
        blank.set("EIdType", "pii")
        blank.text = " "
        out = IdentifierExtractor.extract_elocation_ids(root)
        assert out == {"doi": None, "pii": None}


# ---------------------------------------------------------------------------
# uniprot/extractors/_comment_structured_facets.py [47, 70, 90, 93]
# ---------------------------------------------------------------------------

import bioetl.application.pipelines.uniprot.extractors._comment_structured_facets as facets


class TestCommentStructuredFacetsGuards:
    def test_non_list_subcellular_locations_skipped(self) -> None:
        index = {facets._SUBCELLULAR_LOCATION: [{"subcellularLocations": "nope"}]}
        assert facets._extract_subcellular_locations_raw(index) == []

    def test_non_list_isoforms_skipped(self) -> None:
        index = {facets._ALTERNATIVE_PRODUCTS: [{"isoforms": {}}]}
        products, count, _sections = facets._extract_alternative_products_family_raw(
            index
        )
        assert products == [] and count is None

    def test_non_list_cofactors_skipped(self) -> None:
        index = {facets._COFACTOR: [{"cofactors": "nope"}]}
        assert facets._extract_cofactors_raw(index) == []

    def test_non_dict_cofactor_skipped(self) -> None:
        index = {facets._COFACTOR: [{"cofactors": ["nope"]}]}
        assert facets._extract_cofactors_raw(index) == []


# ---------------------------------------------------------------------------
# control_plane/manifest/_inspection_support.py [29, 127, 129, 138]
# ---------------------------------------------------------------------------

from bioetl.application.services.control_plane.manifest._inspection_support import (
    RunManifestInspectionDiffClassificationMixin as DiffMixin,
)
from bioetl.application.services.control_plane.manifest.inspection_models import (
    RunManifestDiffEntry,
)
from bioetl.domain.control_plane import RunManifest


class TestManifestDiffClassification:
    def test_empty_diff_is_identical(self) -> None:
        payload = DiffMixin._classify_manifest_diff(
            left_manifest=RunManifest(),
            right_manifest=RunManifest(),
            differences=(),
        )
        assert payload["classification"] == "identical"
        assert payload["replay_relationship"] == "none"

    def test_mutual_replay_cycle(self) -> None:
        left = RunManifest(manifest_id="L", replay_of_manifest_id="R")
        right = RunManifest(manifest_id="R", replay_of_manifest_id="L")
        assert (
            DiffMixin._resolve_replay_relationship(
                left_manifest=left, right_manifest=right
            )
            == "mutual_replay_cycle"
        )

    def test_left_is_exact_replay_of_right(self) -> None:
        left = RunManifest(manifest_id="L", replay_of_manifest_id="R")
        right = RunManifest(manifest_id="R")
        assert (
            DiffMixin._resolve_replay_relationship(
                left_manifest=left, right_manifest=right
            )
            == "left_is_exact_replay_of_right"
        )

    def test_external_replay_parentage_present(self) -> None:
        left = RunManifest(manifest_id="L", replay_of_run_id="some-external-run")
        right = RunManifest(manifest_id="R")
        assert (
            DiffMixin._resolve_replay_relationship(
                left_manifest=left, right_manifest=right
            )
            == "external_replay_parentage_present"
        )

    def test_diff_entry_shape(self) -> None:
        entry = RunManifestDiffEntry(field="run_id", left="a", right="b")
        assert entry.to_dict() == {"field": "run_id", "left": "a", "right": "b"}


# ---------------------------------------------------------------------------
# control_plane/replay/historical_closure_models.py [45, 75, 76, 81]
# ---------------------------------------------------------------------------

from bioetl.application.services.control_plane.replay.historical_closure_models import (
    HistoricalReplayClosureReportRecord,
    HistoricalReplayResidualDispositionRecord,
)


def _make_closure_report(inventory: object) -> HistoricalReplayClosureReportRecord:
    return HistoricalReplayClosureReportRecord(
        generated_at=datetime(2024, 1, 1, tzinfo=UTC),
        report_id="rep-1",
        inventory=inventory,
        residual_dispositions=(),
        suggested_resolution_queue=(),
        closure_verdict="blocked",
        closure_reason="missing evidence",
        claim_scope_mode="all_retained_historical_runs",
        global_universal_historical_replay_claim={},
        retained_corpus_claim={},
    )


class TestHistoricalClosureModels:
    def test_unsupported_disposition_rejected(self) -> None:
        with pytest.raises(ValueError, match="Unsupported historical replay"):
            HistoricalReplayResidualDispositionRecord(
                manifest_id="m", disposition="bogus", rationale="r"
            )

    def test_report_uses_inventory_dict_when_available(self) -> None:
        inventory = SimpleNamespace(to_dict=lambda: {"total": 2})
        payload = _make_closure_report(inventory).to_dict()
        assert payload["inventory"] == {"total": 2}
        assert payload["report_id"] == "rep-1"

    def test_report_falls_back_to_empty_inventory(self) -> None:
        payload = _make_closure_report(object()).to_dict()
        assert payload["inventory"] == {}


# ---------------------------------------------------------------------------
# control_plane/replay/historical_corpus_policy.py [39, 48, 59, 81]
# ---------------------------------------------------------------------------

import bioetl.application.services.control_plane.replay.historical_corpus_policy as corpus


class TestHistoricalCorpusPolicy:
    def test_unsupported_broader_policy_outside_scope(self) -> None:
        status, reasons = corpus.classify_certification_status(
            broader_policy="something-else",
            replay_occurrence_kind="k",
            broader_state="s",
        )
        assert status == "outside_certified_historical_scope"
        assert reasons == ("broader_historical_exact_replay_not_supported",)

    def test_replayable_state_classified(self) -> None:
        state = next(iter(corpus.ALREADY_REPLAYABLE_STATES))
        status, reasons = corpus.classify_certification_status(
            broader_policy=corpus.SUPPORTED_BROADER_POLICY,
            replay_occurrence_kind="plain-run",
            broader_state=state,
        )
        assert (status, reasons) == ("already_replayable", ())

    def test_unknown_state_needs_operator_review(self) -> None:
        status, reasons = corpus.classify_certification_status(
            broader_policy=corpus.SUPPORTED_BROADER_POLICY,
            replay_occurrence_kind="plain-run",
            broader_state="mystery-state",
        )
        assert status == "needs_operator_review"
        assert reasons == ("replay_certifiability_state_requires_review",)

    def test_empty_context_has_no_scope(self) -> None:
        assert corpus.certification_scope_for_context("") is None
        assert (
            corpus.certification_scope_for_context("composite")
            == "historical_composite_replay"
        )


# ---------------------------------------------------------------------------
# services/dq/_checks_integrity.py [81, 83, 94, 246]
# ---------------------------------------------------------------------------

import polars as pl

from bioetl.application.services.dq._checks_integrity import (
    _count_scd_overlaps,
    _materialize_entity_key,
    _normalize_scd_config,
)
from bioetl.domain.types import ScdConfig


class TestScdIntegrityHelpers:
    def test_overlap_count_returns_zero_on_malformed_frame(self) -> None:
        df = pl.DataFrame({"a": [1, 2]})
        assert (
            _count_scd_overlaps(
                df=df, entity_key="missing", valid_from="vf", valid_to="vt"
            )
            == 0
        )

    def test_composite_keys_materialize_struct_key(self) -> None:
        df = pl.DataFrame({"a": ["x"], "b": ["y"]})
        out, key = _materialize_entity_key(df, entity_keys=("a", "b"))
        assert key == "__scd_entity_key"
        assert "__scd_entity_key" in out.columns

    def test_config_without_business_keys_normalizes_to_none(self) -> None:
        df = pl.DataFrame({"a": ["x"]})
        assert _normalize_scd_config(df, ScdConfig(business_key=None)) is None


# ---------------------------------------------------------------------------
# services/execution/pipeline_runner_service.py [381, 382, 383, 384]
# ---------------------------------------------------------------------------

from bioetl.application.services.execution.pipeline_runner_service import (
    PipelineRunnerService,
)


def _make_runner_service() -> PipelineRunnerService:
    return object.__new__(PipelineRunnerService)


class TestArchiveControlPlane:
    def test_missing_hook_is_noop(self) -> None:
        svc = _make_runner_service()
        svc.archive_control_plane = None
        assert svc._archive_control_plane(MagicMock(), None) is None

    def test_operator_errors_are_swallowed(self) -> None:
        svc = _make_runner_service()

        def _boom(result: object, options: object) -> None:
            raise OSError("disk gone")

        svc.archive_control_plane = _boom
        assert svc._archive_control_plane(MagicMock(), None) is None

    def test_successful_archive_is_invoked(self) -> None:
        svc = _make_runner_service()
        calls: list[tuple[object, object]] = []
        svc.archive_control_plane = lambda r, o: calls.append((r, o))
        result = MagicMock()
        svc._archive_control_plane(result, None)
        assert calls == [(result, None)]


# ---------------------------------------------------------------------------
# services/export_lineage/debug_export_service.py [135, 156, 161, 172]
# ---------------------------------------------------------------------------

import bioetl.application.services.export_lineage.debug_export_service as dbg_mod
from bioetl.application.services.export_lineage.debug_export_service import (
    DebugExportConfig,
    DebugExportService,
)
from bioetl.domain.types import DebugExportResult


def _make_debug_service(
    *, enabled: bool, writer: object | None = None
) -> DebugExportService:
    return DebugExportService(
        config=DebugExportConfig(enabled=enabled),
        run_id=UUID(int=3001),
        pipeline_id="pipe",
        provider_id="chembl",
        writer=writer,  # type: ignore[arg-type]
    )


class TestDebugExportService:
    def test_set_debug_root_selects_output_root(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured: dict[str, object] = {}
        monkeypatch.setattr(
            dbg_mod,
            "build_debug_export_pack",
            lambda **kwargs: (captured.update(kwargs), MagicMock())[1],
        )
        svc = _make_debug_service(enabled=True)
        svc.set_debug_root(Path("/tmp/dbg-root"))
        svc.build_pack()
        assert captured["output_root"] == "/tmp/dbg-root"

    async def test_persist_without_writer_raises(self) -> None:
        with pytest.raises(RuntimeError, match="not enabled"):
            await _make_debug_service(enabled=False).persist()

    async def test_persist_returns_synchronous_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(dbg_mod, "build_debug_export_pack", lambda **k: MagicMock())
        expected = DebugExportResult(
            root_path="r", manifest_path="m", debug_export_hash="h"
        )
        writer = MagicMock()
        writer.write_pack.return_value = expected
        assert (
            await _make_debug_service(enabled=True, writer=writer).persist() is expected
        )

    def test_finalize_without_writer_returns_none(self) -> None:
        assert (
            _make_debug_service(enabled=False).finalize(
                status="complete", manifest_id=None
            )
            is None
        )


# ---------------------------------------------------------------------------
# services/lineage/metadata_assembler_support.py [56, 208, 209, 226]
# ---------------------------------------------------------------------------

from bioetl.application.services.lineage import metadata_assembler_support as mas
from bioetl.domain.types.dq_contracts import DQDisposition, DQRuleProvenance


class TestMetadataAssemblerSupport:
    def test_non_sequence_text_returns_empty(self) -> None:
        assert mas._stable_unique_text("nope") == []
        assert mas._stable_unique_text([" b ", "a", "b", " "]) == ["a", "b"]

    def test_object_provenance_normalized(self) -> None:
        provenance = DQRuleProvenance(
            rule_id="r",
            contract_version="v",
            severity="error",
            disposition=DQDisposition.WARN,
        )
        out = mas.normalize_rule_provenance_entries([{"k": 1, "n": None}, provenance])
        assert out[0] == {"k": "1", "n": None}
        assert out[1]["rule_id"] == "r"
        assert out[1]["disposition"] == str(DQDisposition.WARN)

    def test_non_list_provenance_coerced_to_empty(self) -> None:
        assert mas.coerce_rule_provenance_mappings("nope") == []
        assert mas.coerce_rule_provenance_mappings([{"a": 1}, "junk"]) == [{"a": 1}]


# ---------------------------------------------------------------------------
# services/quality/_quarantine_service_status_sync.py [130, 131, 135, 140]
# ---------------------------------------------------------------------------

from bioetl.application.services.quality._quarantine_service_status_sync import (
    QuarantineServiceStatusSyncMixin,
)
from bioetl.domain.types import QuarantineRecordStatus


def _make_quarantine_host() -> SimpleNamespace:
    return SimpleNamespace(
        logger=MagicMock(),
        quarantine_port=MagicMock(),
        _derive_operator_completion=lambda **k: (k["started_at"], 0.05),
        _record_operator_metrics=MagicMock(),
    )


class TestQuarantineStatusSync:
    def test_operator_error_records_metrics_and_reraises(self) -> None:
        host = _make_quarantine_host()
        host.quarantine_port.update_status.side_effect = OSError("store down")
        started_at = datetime(2026, 1, 1, tzinfo=UTC)
        with pytest.raises(OSError, match="store down"):
            QuarantineServiceStatusSyncMixin._update_status_impl(
                host,
                payload_hash="h",
                new_status=QuarantineRecordStatus.IGNORED,
                started_at=started_at,
                started_monotonic=1.0,
            )
        host._record_operator_metrics.assert_called_once_with(
            operation="update_status", status="failed", duration_seconds=0.05
        )


# ---------------------------------------------------------------------------
# services/workflow/_observability_workflow_next_steps_support.py [29, 32, 39, 60]
# ---------------------------------------------------------------------------

from bioetl.application.services.control_plane.manifest.inspection_result_model import (
    RunManifestInspectionResult,
)
from bioetl.application.services.workflow._observability_workflow_next_steps_support import (
    _degraded_evidence_steps,
    _manifest_next_steps,
    _missing_evidence_steps,
)


class TestNextStepsSupport:
    def test_missing_manifest_yields_no_steps(self) -> None:
        assert _manifest_next_steps(None) == ()

    def test_non_list_diagnostics_yields_no_steps(self) -> None:
        result = RunManifestInspectionResult(
            manifest=RunManifest(), diagnostics={"next_steps": "do stuff"}
        )
        assert _manifest_next_steps(result) == ()

    def test_missing_manifest_evidence_step(self) -> None:
        assert _missing_evidence_steps(("run_manifest",)) == (
            "Persist and inspect run-manifest/ledger artifacts for this run.",
        )
        assert _missing_evidence_steps(()) == ()

    def test_composite_correlation_gap_step(self) -> None:
        steps = _degraded_evidence_steps(("composite_correlation_policy_gap",))
        assert any("composite_run_id" in step for step in steps)


# ---------------------------------------------------------------------------
# services/workflow/_observability_workflow_quarantine_support.py [36, 39, 82, 83]
# ---------------------------------------------------------------------------

from bioetl.application.services.workflow import (
    _observability_workflow_quarantine_support as quarantine_support,
)


def _ledger_manifest(*snapshots: object) -> RunManifestInspectionResult:
    return RunManifestInspectionResult(
        manifest=RunManifest(),
        ledger_entries=tuple(
            SimpleNamespace(metrics_snapshot=snapshot) for snapshot in snapshots
        ),  # type: ignore[arg-type]
    )


class TestQuarantineWorkflowSupport:
    def test_bronze_count_skips_invalid_snapshots(self) -> None:
        manifest = _ledger_manifest(
            "junk", {"records_bronze": 0}, {"records_bronze": 5}
        )
        assert quarantine_support.resolve_bronze_record_count(manifest) == 5

    async def test_failing_stats_service_resolves_none(self) -> None:
        service = AsyncMock()
        service.get_filtered_stats.side_effect = OSError("boom")
        assert (
            await quarantine_support.resolve_quarantine_summary_for_run(
                quarantine_service=service,
                run_id="r",
                pipeline_name="pipe",
                run_manifest=None,
            )
            is None
        )


# ---------------------------------------------------------------------------
# services/workflow/observability_workflow_service.py [76, 117, 171, 195]
# ---------------------------------------------------------------------------

import bioetl.application.services.workflow.observability_workflow_service as ows_mod
from bioetl.application.services.workflow.observability_workflow_service import (
    ObservabilityWorkflowService,
)


def _make_workflow_service(**overrides: object) -> ObservabilityWorkflowService:
    args: dict[str, object] = {
        "audit_service": MagicMock(),
        "checkpoint_service": MagicMock(),
        "run_manifest_service": MagicMock(),
        "lineage_service": None,
        "quarantine_service": None,
        "tracer": None,
    }
    args.update(overrides)
    return ObservabilityWorkflowService(**args)  # type: ignore[arg-type]


class TestObservabilityWorkflowService:
    async def test_audit_run_without_tracer_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            ows_mod, "inspect_audit_run_impl", AsyncMock(return_value="AUDIT")
        )
        assert await _make_workflow_service().inspect_audit_run("run-1") == "AUDIT"

    async def test_run_dossier_without_tracer_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            ows_mod, "inspect_run_dossier_impl", AsyncMock(return_value="DOSSIER")
        )
        assert await _make_workflow_service().inspect_run_dossier("run-1") == "DOSSIER"

    async def test_manifest_dossier_requires_service(self) -> None:
        with pytest.raises(ValueError, match="run manifest service is required"):
            await _make_workflow_service(
                run_manifest_service=None
            ).inspect_manifest_dossier("m-1")

    async def test_checkpoint_workflow_rejects_both_ids(self) -> None:
        with pytest.raises(ValueError, match="either run_id or manifest_id"):
            await _make_workflow_service().inspect_checkpoint_workflow(
                "pipe", run_id="r", manifest_id="m"
            )


# ---------------------------------------------------------------------------
# composite/checkpoint/_checkpoint_warnings.py [44, 70, 71]
# ---------------------------------------------------------------------------

import bioetl.application.composite.checkpoint._checkpoint_warnings as warn_mod
from bioetl.application.composite.checkpoint._checkpoint_warnings import (
    warn_if_checkpoint_exists_with_progress,
)
from bioetl.domain.exceptions import BioETLError


def _warn_call(monkeypatch: pytest.MonkeyPatch, *, content: str | None) -> MagicMock:
    monkeypatch.setattr(warn_mod, "latest_checkpoint_filename", lambda **k: "ckpt.json")
    storage = MagicMock()
    storage.exists.return_value = True
    storage.read.return_value = content
    logger = MagicMock()
    warn_if_checkpoint_exists_with_progress(
        storage=storage, logger=logger, composite_name="c", glob_pattern="*.json"
    )
    return logger


class TestCheckpointWarnings:
    def test_empty_content_returns_silently(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        logger = _warn_call(monkeypatch, content=None)
        logger.warning.assert_not_called()
        logger.debug.assert_not_called()

    def test_domain_error_warns(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _BadState:
            @classmethod
            def from_dict(cls, payload: object) -> object:
                raise BioETLError("bad state")

        monkeypatch.setattr(warn_mod, "CompositeCheckpointState", _BadState)
        logger = _warn_call(monkeypatch, content='{"x": 1}')
        logger.warning.assert_called_once()


# ---------------------------------------------------------------------------
# composite/coordinator_result_mixin.py [36, 86, 92]
# ---------------------------------------------------------------------------

from bioetl.application.composite.coordinator_result_mixin import (
    EnrichmentCoordinatorResultMixin,
)
from bioetl.domain.composite import CompositeDQConfig, EnricherConfig
from bioetl.domain.composite.result import EnrichmentStatus


def _make_coordinator_host() -> EnrichmentCoordinatorResultMixin:
    host = object.__new__(EnrichmentCoordinatorResultMixin)
    host._logger = MagicMock()
    host._dq_config = CompositeDQConfig()
    return host


class TestCoordinatorThresholdFailure:
    def test_excessive_dq_rate_builds_failure_result(self) -> None:
        host = _make_coordinator_host()
        runner = SimpleNamespace(
            execution_metrics={"records_silver": 5, "records_quarantined": 95}
        )
        now = datetime(2024, 1, 1)
        result = host._build_enricher_result(
            enricher=EnricherConfig(pipeline="enr", join_keys=("chembl_id",)),
            runner=runner,  # type: ignore[arg-type]
            records_input=100,
            started_at=now,
            completed_at=now,
            duration=1.0,
        )
        assert result.status is EnrichmentStatus.FAILED
        assert "exceeds threshold" in (result.error_message or "")
        host._logger.warning.assert_called_once()


# ---------------------------------------------------------------------------
# composite/runner_pkg/runner_merge_stage_mixin.py [130, 161, 171]
# ---------------------------------------------------------------------------

import bioetl.application.composite.runner_pkg.runner_merge_stage_execution_mixin as merge_exec_mod
from bioetl.application.composite.runner_pkg.runner_merge_stage_mixin import (
    CompositeRunnerMergeStageMixin,
)


class TestMergeStageMixinDelegation:
    async def test_start_merge_phase_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            merge_exec_mod, "start_merge_phase", AsyncMock(return_value="MERGING")
        )
        host = CompositeRunnerMergeStageMixin()
        assert await host._start_merge_phase(MagicMock()) == "MERGING"

    async def test_run_prepared_merge_request_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            merge_exec_mod,
            "run_prepared_merge_request",
            AsyncMock(return_value="MERGED"),
        )
        host = CompositeRunnerMergeStageMixin()
        assert await host._run_prepared_merge_request(MagicMock()) == "MERGED"

    async def test_execute_started_merge_phase_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            merge_exec_mod,
            "execute_started_merge_phase",
            AsyncMock(return_value="DONE"),
        )
        host = CompositeRunnerMergeStageMixin()
        assert (
            await host._execute_started_merge_phase(
                MagicMock(), enrichment_results={}, dependency_results=None
            )
            == "DONE"
        )


# ---------------------------------------------------------------------------
# composite/runner_pkg/runner_stage_support_mixin.py [128, 142, 149]
# ---------------------------------------------------------------------------

from bioetl.application.composite.runner_pkg.runner_stage_support_mixin import (
    _CompositeRunnerStageSupportMixin,
)


class TestStageSupportNoops:
    def test_default_seams_are_noops(self) -> None:
        host = _CompositeRunnerStageSupportMixin()
        assert host._record_dependencies_stage_started(["a"]) is None
        assert host._record_dependencies_stage_completed({"a": MagicMock()}) is None
        assert host._record_enrichment_stage_started(["e"]) is None
        assert host._record_enrichment_stage_completed({"e": MagicMock()}) is None


# ---------------------------------------------------------------------------
# core/_record_normalization_runtime_support.py [34, 38, 76]
# ---------------------------------------------------------------------------

from bioetl.application.core._record_normalization_contract import (
    _NormalizationFinding,
)
from bioetl.application.core._record_normalization_runtime_support import (
    profile_json_runtime_finding,
    project_normalization_findings,
)


class TestRecordNormalizationRuntime:
    def test_empty_findings_return_record_unchanged(self) -> None:
        record = {"a": 1}
        assert (
            project_normalization_findings(
                (),
                record,
                context=None,
                index=0,
                provider="chembl",
                entity_type=None,
            )
            is record
        )

    def test_findings_without_context_flag_record(self) -> None:
        finding = _NormalizationFinding(
            field_name="payload", reason_code="rc", action_taken="set_null_and_warn"
        )
        out = project_normalization_findings(
            (finding,),
            {"a": 1},
            context=None,
            index=2,
            provider="chembl",
            entity_type="assay",
        )
        assert out == {"a": 1, "_dq_warn": True}

    def test_valid_json_produces_no_finding(self) -> None:
        rule = SimpleNamespace(notes="expects JSON object", normalizer=len)
        assert (
            profile_json_runtime_finding(
                rule,  # type: ignore[arg-type]
                field_name="payload",
                raw_value='{"a": 1}',
                normalized_value=None,
                finding_factory=_NormalizationFinding,
            )
            is None
        )


# ---------------------------------------------------------------------------
# core/base_transformer/_structural_policy_events.py [65, 67, 108]
# ---------------------------------------------------------------------------

from bioetl.application.core.base_transformer._structural_policy_events import (
    build_structural_details,
    preview_value,
)
from bioetl.application.core.base_transformer._structural_policy_types import (
    StructuralFieldSpec,
)


def _make_spec(**overrides: object) -> StructuralFieldSpec:
    args: dict[str, object] = {
        "field_name": "note",
        "logical_type": "string",
        "physical_type": "TEXT",
        "nullable": True,
        "optional": False,
        "optional_sources": (),
        "empty_as_missing": None,
        "coercion_policy": "default",
        "boolean_true_values": (),
        "boolean_false_values": (),
    }
    args.update(overrides)
    return StructuralFieldSpec(**args)  # type: ignore[arg-type]


class TestStructuralPolicyEvents:
    def test_boolean_value_sets_reported(self) -> None:
        details = build_structural_details(
            reason_code="rc",
            contract=_make_spec(
                boolean_true_values=("Y",), boolean_false_values=("N",)
            ),
            actual_value="maybe",
            action_taken="warn",
        )
        assert details["boolean_true_values"] == ["Y"]
        assert details["boolean_false_values"] == ["N"]

    def test_long_preview_truncated(self) -> None:
        preview = preview_value("x" * 200, field_name="note")
        assert preview.endswith("...")
        assert len(preview) == 120


# ---------------------------------------------------------------------------
# core/batch_executor_runtime_state.py [131, 139, 155]
# ---------------------------------------------------------------------------

from bioetl.application.core.batch_executor_runtime_state import (
    BatchExecutorRuntimeState,
    BatchExecutorRuntimeStateMixin,
)


class _StateHost(BatchExecutorRuntimeStateMixin):
    def __init__(self) -> None:
        self._runtime_state = BatchExecutorRuntimeState()


class TestRuntimeStateSetters:
    def test_dq_buffer_setters_round_trip(self) -> None:
        host = _StateHost()
        host._silver_records_for_dq = [{"a": 1}]  # type: ignore[assignment]
        host._gold_records_for_dq = [{"g": 1}]  # type: ignore[assignment]
        host._dq_reservoir_ranks = {"k": ["a"]}
        assert host._runtime_state.silver_records_for_dq == [{"a": 1}]
        assert host._runtime_state.gold_records_for_dq == [{"g": 1}]
        assert host._runtime_state.dq_reservoir_ranks == {"k": ["a"]}


# ---------------------------------------------------------------------------
# core/batch_transformer_attempt_failures.py [108, 118, 178]
# ---------------------------------------------------------------------------

from bioetl.application.core.base_transformer import FilteredOutError
from bioetl.application.core.batch_transformer_attempt_failures import (
    _FilteredOutHandlingContext,
    handle_data_quality_transform_error,
    handle_filtered_out_error,
)
from bioetl.domain.config import DQConfig
from bioetl.domain.types import ErrorType


def _failure_context(
    *, policy: str | None = "quarantine", debug: object | None = None
) -> _FilteredOutHandlingContext:
    return _FilteredOutHandlingContext(
        batch_metrics=MagicMock(),
        dq_config=None if policy is None else DQConfig(invalid_record_policy=policy),  # type: ignore[arg-type]
        raw_record={"id": 1},
        debug_export_service=debug,  # type: ignore[arg-type]
        index=3,
    )


class TestAttemptFailures:
    def test_filtered_out_records_debug_export(self) -> None:
        debug = MagicMock()
        error = FilteredOutError("filtered", details={"reason": "x"})
        outcome = handle_filtered_out_error(error, _failure_context(debug=debug))
        debug.record_filtered_out.assert_called_once()
        assert outcome.filtered_entry is not None

    def test_filtered_out_fail_policy_reraises(self) -> None:
        error = FilteredOutError("filtered")
        with pytest.raises(FilteredOutError):
            handle_filtered_out_error(error, _failure_context(policy="fail"))

    def test_dq_error_records_debug_export(self) -> None:
        debug = MagicMock()
        outcome = handle_data_quality_transform_error(
            ValueError("bad value"),
            error_type=ErrorType.DATA_QUALITY,
            batch_metrics=MagicMock(),
            dq_config=None,
            raw_record={"id": 1},
            debug_export_service=debug,
            index=0,
        )
        debug.record_data_quality_failure.assert_called_once()
        assert outcome.dq_entry is not None


# ---------------------------------------------------------------------------
# core/data_sources/subcellular_fraction.py [89, 93, 100]
# ---------------------------------------------------------------------------

import bioetl.application.core.subcellular_fraction_support as fraction_support
from bioetl.application.core.data_sources.subcellular_fraction import (
    SubcellularFractionDataSource,
)


class TestSubcellularFractionDelegation:
    def test_normalize_fraction_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(fraction_support, "normalize_fraction", lambda v: "NORM")
        assert SubcellularFractionDataSource._normalize_fraction("raw") == "NORM"

    def test_compute_entity_id_delegates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(fraction_support, "compute_entity_id", lambda v: "ID-1")
        assert SubcellularFractionDataSource._compute_entity_id("fraction") == "ID-1"

    def test_create_fraction_record_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            fraction_support, "create_fraction_record", lambda a, f: {"ok": True}
        )
        source = object.__new__(SubcellularFractionDataSource)
        assert source._create_fraction_record({"a": 1}, "f") == {"ok": True}


# ---------------------------------------------------------------------------
# core/runner.py [104, 123, 124]
# ---------------------------------------------------------------------------

from bioetl.application.core.runner import PipelineRunner


def _make_runner() -> PipelineRunner:
    runner = object.__new__(PipelineRunner)
    runner._contract_evidence_context = None
    runner._context = SimpleNamespace(run_id="run-1", manifest_id="ctx-manifest")
    runner._contract_evidence_recorder = None
    return runner


class TestPipelineRunnerManifest:
    def test_manifest_id_prefers_contract_context(self) -> None:
        runner = _make_runner()
        runner._contract_evidence_context = SimpleNamespace(manifest_id="ctx-9")
        assert runner.manifest_id == "ctx-9"

    def test_manifest_id_falls_back_to_context(self) -> None:
        assert _make_runner().manifest_id == "ctx-manifest"

    def test_attach_recorder_stores_both(self) -> None:
        runner = _make_runner()
        recorder = MagicMock()
        launch_context = SimpleNamespace(manifest_id="m-10")
        runner.attach_contract_evidence_recorder(
            recorder, launch_context=launch_context
        )
        assert runner._contract_evidence_recorder is recorder
        assert runner._contract_evidence_context is launch_context


# ---------------------------------------------------------------------------
# pipelines/chembl/assay_transformer.py [248, 249, 250]
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer


class TestAssayTransformForGold:
    def test_renames_assay_description_to_description(self) -> None:
        transformer = AssayTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )
        gold = transformer.transform_for_gold(
            MagicMock(), {"assay_description": "binding assay", "x": 1}
        )
        assert gold["description"] == "binding assay"
        assert "assay_description" not in gold


# ---------------------------------------------------------------------------
# pipelines/chembl/protein_class_transformer.py [85, 86, 87]
# ---------------------------------------------------------------------------

import bioetl.application.pipelines.chembl.base_chembl_transformer as chembl_base
from bioetl.application.pipelines.chembl.protein_class_transformer import (
    ProteinClassTransformer,
)


class TestProteinClassPreSilver:
    async def test_root_classification_skipped(self) -> None:
        transformer = ProteinClassTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )
        assert (
            await transformer.transform_pre_silver(
                MagicMock(), {"protein_class_id": 0}, 0
            )
            is None
        )

    async def test_valid_classification_delegates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async def _fake(
            self: object, context: object, record: object, index: int
        ) -> object:
            return {"delegated": True}

        monkeypatch.setattr(
            chembl_base.BaseChemblTransformer, "transform_pre_silver", _fake
        )
        transformer = ProteinClassTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )
        assert await transformer.transform_pre_silver(
            MagicMock(), {"protein_class_id": 5}, 1
        ) == {"delegated": True}


# ---------------------------------------------------------------------------
# pipelines/openalex/_extractors_publication_fields.py [61, 85, 91]
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.openalex._extractors_publication_fields import (
    extract_journal_info,
    reconstruct_abstract,
)


class TestOpenalexPublicationFields:
    def test_non_dict_source_returns_nones(self) -> None:
        assert extract_journal_info({"source": "nope"}) == {
            "journal": None,
            "issn": None,
            "publisher": None,
        }

    def test_non_list_positions_skipped_to_none(self) -> None:
        assert reconstruct_abstract({"hello": "not-a-list"}) is None  # type: ignore[dict-item]

    def test_empty_positions_return_none(self) -> None:
        assert reconstruct_abstract({"hello": []}) is None


# ---------------------------------------------------------------------------
# pipelines/pubchem/transformer.py [102, 103, 108]
# ---------------------------------------------------------------------------

from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer


class TestPubchemPreSilverFailure:
    async def test_validation_failure_warns_and_skips(self) -> None:
        transformer = object.__new__(PubChemCompoundTransformer)

        def _boom(context: object, record: object, index: int) -> object:
            raise FilteredOutError("no compound id")

        transformer._build_compound_business_data = _boom  # type: ignore[method-assign]
        context = MagicMock()
        assert await transformer.transform_pre_silver(context, {"x": 1}, 0) is None
        context.logger.warning.assert_called_once()


# ---------------------------------------------------------------------------
# pipelines/uniprot/extractors/_crossref_go.py [31, 54, 89]
# ---------------------------------------------------------------------------

import bioetl.application.pipelines.uniprot.extractors._crossref_go as go_mod


class _OddStr(str):
    """String whose containment and split disagree, to reach the length guard."""

    def __contains__(self, item: object) -> bool:
        return True

    def split(self, *args: object, **kwargs: object) -> list[str]:  # type: ignore[override]
        return ["only-one-part"]


class TestCrossrefGo:
    def test_malformed_split_returns_nones(self) -> None:
        assert go_mod.parse_go_term_value(_OddStr("whatever")) == (None, None)

    def test_go_xref_without_id_skipped(self) -> None:
        assert go_mod.extract_go_terms([{"database": "GO"}]) is None

    def test_aspect_filter_without_id_skipped(self) -> None:
        assert (
            go_mod.extract_go_by_aspect([{"database": "GO", "id": None}], "F") is None
        )
