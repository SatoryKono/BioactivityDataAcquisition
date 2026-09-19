"""Stream B APP: leftover 4-line workflow, pubmed, target, and 3-line resume branches."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from xml.etree.ElementTree import Element

import pytest

from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.pipelines.pubmed.extractors.identifier import (
    IdentifierExtractor,
)
from bioetl.application.services.control_plane.manifest.diagnostics.source_refs import (
    _attach_rich_composite_replay_support,
)
from bioetl.application.services.control_plane.manifest.validation_provenance import (
    _validate_documented_code_provenance,
    _validate_production_provenance_gate,
)
from bioetl.application.services.control_plane.replay._historical_certification_upstream import (
    load_upstream_manifest,
    validate_upstream_certification_state,
    validate_upstream_run_id_match,
)
from bioetl.application.services.control_plane.workflow.ledger_service import (
    WorkflowLedgerService,
    _missing_occurred_at_factory,
)
from bioetl.application.services.export_lineage.audit_inspection_service import (
    AuditInspectionService,
)
from bioetl.application.services.export_lineage.export_execution import (
    _retained_export_columns,
    _should_redact_columns,
)
from bioetl.application.services.export_lineage.export_models import ExportOptions
from bioetl.application.services.lineage.lineage_inspection_service import (
    LineageInspectionService,
)
from bioetl.application.services.quality._quarantine_service_filtered_mixin import (
    QuarantineServiceFilteredMixin,
)
from bioetl.application.services.workflow.control_plane._execution_resume_support import (
    _validate_step_integrity,
    _validate_workflow_name,
    load_resume_state,
)
from bioetl.application.services.workflow.observability_workflow_service import (
    ObservabilityWorkflowService,
)
from bioetl.application.services.workflow.workflow_runner_support import (
    _workflow_expected_provider,
    workflow_status_to_gauge_value,
)
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    COMPOSITE_ENRICHER_COMPLETED_EVENT,
    COMPOSITE_MERGE_COMPLETED_EVENT,
)
from bioetl.domain.types import RunID

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_observability_workflow_untraced_and_guardrails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audit = AsyncMock(return_value="audit")
    dossier = AsyncMock(return_value="dossier")
    monkeypatch.setattr(
        "bioetl.application.services.workflow.observability_workflow_service.inspect_audit_run_impl",
        audit,
    )
    monkeypatch.setattr(
        "bioetl.application.services.workflow.observability_workflow_service.inspect_run_dossier_impl",
        dossier,
    )
    service = ObservabilityWorkflowService(
        audit_service=MagicMock(),
        checkpoint_service=MagicMock(),
        tracer=None,
    )
    assert await service.inspect_audit_run("run-1") == "audit"
    assert await service.inspect_run_dossier("run-1") == "dossier"
    with pytest.raises(ValueError, match="run manifest service"):
        await service.inspect_manifest_dossier("m1")
    with pytest.raises(ValueError, match="either run_id or manifest_id"):
        await service.inspect_checkpoint_workflow(
            "chembl_activity", run_id="run-1", manifest_id="m1"
        )


def test_pubmed_identifier_empty_and_other_ids() -> None:
    extractor = IdentifierExtractor()
    article = Element("Article")
    blank = Element("ELocationID")
    article.append(blank)
    whitespace = Element("ELocationID", {"EIdType": "doi"})
    whitespace.text = "   "
    article.append(whitespace)
    result: dict[str, str | None] = {"doi": None, "pii": None}
    extractor._scan_elocation_ids(article, result)
    assert result["doi"] is None

    root = Element("PubmedArticle")
    article_ids = Element("ArticleIdList")
    unknown = Element("ArticleId", {"IdType": "custom"})
    unknown.text = "X1"
    article_ids.append(unknown)
    empty = Element("ArticleId", {"IdType": "doi"})
    empty.text = "  "
    article_ids.append(empty)
    root.append(article_ids)
    parsed = IdentifierExtractor.parse_all_article_ids(root)
    assert parsed["other_ids"]["custom"] == "X1"

    loc_root = Element("PubmedArticle")
    loc_article = Element("Article")
    loc = Element("ELocationID", {"EIdType": "doi"})
    loc.text = "  "
    loc_article.append(loc)
    loc_root.append(loc_article)
    assert IdentifierExtractor.extract_elocation_ids(loc_root)["doi"] is None


def test_target_transformer_gold_description_projection() -> None:
    host = TargetTransformer.__new__(TargetTransformer)
    gold = host.transform_for_gold(
        object(),  # type: ignore[arg-type]
        {"target_description": "kinase", "target_id": "CHEMBL1"},
    )
    assert gold["description"] == "kinase"
    assert "target_description" not in gold


def test_workflow_provider_gauge_and_resume_errors() -> None:
    assert (
        _workflow_expected_provider(
            SimpleNamespace(pipeline_steps=(), workflow_context_labels={})  # type: ignore[arg-type]
        )
        == "unknown"
    )
    assert (
        _workflow_expected_provider(
            SimpleNamespace(  # type: ignore[arg-type]
                pipeline_steps=(),
                workflow_context_labels={"provider_context": "chembl"},
            )
        )
        == "chembl"
    )
    assert workflow_status_to_gauge_value("failed") == 2.0
    port = MagicMock()
    port.get_by_run_id.return_value = None
    with pytest.raises(RuntimeError, match="resume-run-id"):
        load_resume_state(
            workflow_state_port=port,
            workflow_name="wf",
            resume_manifest_id=None,
            resume_run_id=str(uuid4()),
        )
    with pytest.raises(RuntimeError, match="different workflow"):
        _validate_workflow_name(SimpleNamespace(workflow_name="other"), "expected")  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="step identities"):
        _validate_step_integrity(SimpleNamespace(steps=()))  # type: ignore[arg-type]


def test_audit_lineage_export_and_filtered(monkeypatch: pytest.MonkeyPatch) -> None:
    assert AuditInspectionService._parse_run_id(None) is None
    with pytest.raises(ValueError, match="Invalid audit layer"):
        AuditInspectionService._resolve_layer("nope")
    store = MagicMock()
    store.list_by_manifest_id.return_value = ()
    service = LineageInspectionService(lineage_store=store, manifest_port=None)
    monkeypatch.setattr(
        LineageInspectionService, "_parse_run_id", lambda self, ident: None
    )
    assert service._resolve_via_direct_indexes("missing") is None
    options = ExportOptions(role="admin")
    assert _should_redact_columns(("email",), options=options) is False
    with pytest.raises(PermissionError, match="only sensitive"):
        _retained_export_columns(
            column_names=("email",),
            sensitive_columns=("email",),
            role="viewer",
        )


@pytest.mark.asyncio
async def test_filtered_quarantine_not_found_and_success() -> None:
    class _Host(QuarantineServiceFilteredMixin):
        def __init__(self) -> None:
            self.logger = MagicMock()
            self.quarantine_port = AsyncMock()

        def _record_operator_metrics(self, **_kwargs: object) -> None:
            return None

    host = _Host()
    host.quarantine_port.get_filtered_record.return_value = None
    assert (
        await host.get_filtered_record(payload_hash="h", pipeline="chembl_activity")
        is None
    )
    host.quarantine_port.get_filtered_record.return_value = {
        "pipeline": "chembl_activity"
    }
    found = await host.get_filtered_record(payload_hash="h", pipeline="chembl_activity")
    assert found == {"pipeline": "chembl_activity"}


def test_ledger_provenance_source_refs_and_upstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(RuntimeError, match="occurred_at_factory"):
        _missing_occurred_at_factory()
    monkeypatch.setattr(WorkflowLedgerService, "_append", lambda self, **kwargs: kwargs)
    ledger = WorkflowLedgerService(
        ledger_port=MagicMock(),
        manifest_id="m1",
        workflow_run_id=RunID(uuid4()),
        workflow_name="wf",
        _entry_id_factory=lambda: "e1",
        _occurred_at_factory=lambda: datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
    )
    failed = ledger.record_workflow_failed(message="boom", error_type="Error")
    assert failed["status"] == "failed"
    forced = ledger.record_force_requested(step_ids=("s1",))
    assert forced["details"] == {"step_ids": ["s1"]}
    monkeypatch.setattr(
        "bioetl.application.services.control_plane.manifest.validation_provenance.validate_production_provenance",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("gate")),
    )
    with pytest.raises(RuntimeError, match="gate"):
        _validate_production_provenance_gate(
            SimpleNamespace(launch_context={"env": "production"}),  # type: ignore[arg-type]
            MagicMock(),
        )
    with pytest.raises(RuntimeError, match="git_unavailable"):
        _validate_documented_code_provenance(
            SimpleNamespace(source_revision_state="git_unavailable", git_commit="abc")  # type: ignore[arg-type]
        )
    attached = _attach_rich_composite_replay_support(
        {"ok": True},
        (
            SimpleNamespace(event_type=COMPOSITE_DEPENDENCY_COMPLETED_EVENT),
            SimpleNamespace(event_type=COMPOSITE_ENRICHER_COMPLETED_EVENT),
            SimpleNamespace(event_type=COMPOSITE_MERGE_COMPLETED_EVENT),
        ),
    )
    assert attached["composite_resume_rich_replay_supported"] is True
    port = MagicMock()
    port.get.return_value = None
    with pytest.raises(ValueError, match="was not found"):
        load_upstream_manifest(
            manifest_port=port,
            certification=SimpleNamespace(upstream_manifest_id="missing"),  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="upstream_run_id"):
        validate_upstream_run_id_match(
            certification=SimpleNamespace(upstream_run_id="a"),  # type: ignore[arg-type]
            upstream_manifest=SimpleNamespace(run_id="b"),  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="historical_source_replay_certified"):
        validate_upstream_certification_state(
            ledger_port=MagicMock(list_entries=lambda _mid: ()),
            upstream_manifest=SimpleNamespace(manifest_id="m1"),  # type: ignore[arg-type]
            summary_builder=lambda *_a, **_k: {
                "broader_historical_exact_replay_state": "open"
            },
        )
