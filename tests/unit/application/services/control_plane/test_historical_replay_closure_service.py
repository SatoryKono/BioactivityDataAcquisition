# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for retained-corpus historical replay closure workflows."""

from __future__ import annotations

from collections.abc import Callable
from itertools import count

import pytest

from dataclasses import replace
from datetime import UTC, datetime

from bioetl.application.services.control_plane.replay.historical_closure_service import (
    HistoricalReplayClosureService,
    HistoricalReplayResidualDisposition,
)
from bioetl.application.services.control_plane.replay.historical_corpus_service import (
    HistoricalReplayBulkCertificationSpec,
    HistoricalReplayCorpusService,
)
from bioetl.application.services.control_plane.replay.historical_certification_service import (
    HistoricalReplayCertificationService,
    HistoricalReplaySnapshotCertification,
)
from bioetl.domain.control_plane import RunManifest, RunSourceRef
from bioetl.domain.types import RunID
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore
from tests.helpers.deterministic_ids import deterministic_uuid_value
from tests.unit.application.services.run_manifest_test_support import (
    make_run_manifest as _build_manifest,
)


pytestmark = pytest.mark.unit
_FIXED_CLOSURE_TIME = datetime(2026, 1, 4, 12, 0, tzinfo=UTC)


def _fixed_closure_time() -> datetime:
    return _FIXED_CLOSURE_TIME


def _closure_entry_id_factory(prefix: str = "entry-historical") -> Callable[[], str]:
    sequence = count(1)
    return lambda: f"{prefix}-{next(sequence)}"


def _make_source_manifest() -> RunManifest:
    return _build_manifest(
        manifest_id="closure-source-manifest",
        execution_fingerprint="closure-source-fingerprint",
        run_id=RunID(deterministic_uuid_value("historical.closure.source")),
        created_at=datetime(2026, 1, 3, 9, 0, tzinfo=UTC),
    )


def _make_composite_manifest() -> RunManifest:
    manifest = _build_manifest(
        manifest_id="closure-composite-manifest",
        execution_fingerprint="closure-composite-fingerprint",
        run_id=RunID(deterministic_uuid_value("historical.closure.composite")),
        created_at=datetime(2026, 1, 3, 9, 30, tzinfo=UTC),
    )
    return replace(
        manifest,
        pipeline_name="composite_activity",
        provider="composite",
        entity="activity",
        launch_context={
            **manifest.launch_context,
            "execution_context": "composite",
        },
        runtime_config={
            **manifest.runtime_config,
            "execution_context": "composite",
        },
        resolved_config={
            **manifest.resolved_config,
            "execution_context": "composite",
        },
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query=None,
            ),
        ),
        code_provenance=replace(
            manifest.code_provenance,
            contract_ref="composite.activity",
            contract_version="1.0.0",
            pipeline_version="1.0.0",
        ),
    )


def test_closure_report_blocks_claim_without_explicit_residual_dispositions() -> None:
    source_manifest = _make_source_manifest()
    composite_manifest = _make_composite_manifest()
    manifest_store = InMemoryRunManifestStore()
    manifest_store.save(source_manifest)
    manifest_store.save(composite_manifest)
    ledger_store = InMemoryRunLedgerStore()
    closure_service = HistoricalReplayClosureService(
        corpus_service=HistoricalReplayCorpusService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            certification_service=HistoricalReplayCertificationService(
                manifest_port=manifest_store,
                ledger_port=ledger_store,
                entry_id_factory=_closure_entry_id_factory("entry-closure-gap"),
            ),
        ),
        now_factory=_fixed_closure_time,
    )

    report = closure_service.build_closure_report()

    assert report.closure_verdict == "residual_disposition_required"
    assert report.global_universal_historical_replay_claim["claimed"] is False
    assert report.global_universal_historical_replay_claim["reason"] == (
        "residual_historical_runs_lack_explicit_resolution_disposition"
    )
    assert report.retained_corpus_claim["claimed"] is False
    assert len(report.suggested_resolution_queue) == 2


def test_closure_report_supports_global_claim_after_bulk_certification() -> None:
    source_manifest = _make_source_manifest()
    composite_manifest = _make_composite_manifest()
    manifest_store = InMemoryRunManifestStore()
    manifest_store.save(source_manifest)
    manifest_store.save(composite_manifest)
    ledger_store = InMemoryRunLedgerStore()
    corpus_service = HistoricalReplayCorpusService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        certification_service=HistoricalReplayCertificationService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            entry_id_factory=_closure_entry_id_factory("entry-closure-certification"),
        ),
    )
    closure_service = HistoricalReplayClosureService(
        corpus_service=corpus_service,
        now_factory=_fixed_closure_time,
    )

    corpus_service.certify_retained_corpus(
        specs=(
            HistoricalReplayBulkCertificationSpec(
                manifest_id=composite_manifest.manifest_id,
                certifications=(
                    HistoricalReplaySnapshotCertification(
                        provider="chembl",
                        entity="activity",
                        pipeline_name="chembl_activity",
                        snapshot_id="closure-composite-snapshot-1",
                        content_hash="sha256:closure-composite-certified-1",
                        immutable_uri="file:///closure/composite/snapshot-1.jsonl",
                        bronze_batch_ref="bronze://closure/composite/batch-1.jsonl",
                        certification_artifact_ref=(
                            "control://closure/composite-certification-1.json"
                        ),
                        upstream_run_id=str(source_manifest.run_id),
                        upstream_manifest_id=source_manifest.manifest_id,
                    ),
                ),
            ),
            HistoricalReplayBulkCertificationSpec(
                manifest_id=source_manifest.manifest_id,
                certifications=(
                    HistoricalReplaySnapshotCertification(
                        provider=source_manifest.provider,
                        entity=source_manifest.entity,
                        pipeline_name=source_manifest.pipeline_name,
                        snapshot_id="closure-source-snapshot-1",
                        content_hash="sha256:closure-source-certified-1",
                        immutable_uri="file:///closure/source/snapshot-1.jsonl",
                        bronze_batch_ref="bronze://closure/source/batch-1.jsonl",
                        certification_artifact_ref=(
                            "control://closure/source-certification-1.json"
                        ),
                    ),
                ),
            ),
        )
    )

    report = closure_service.build_closure_report()

    assert report.closure_verdict == "fully_closed"
    assert report.closure_reason == (
        "all_retained_historical_runs_are_already_replayable_or_certified"
    )
    assert report.global_universal_historical_replay_claim == {
        "claimed": True,
        "verdict": "claim_supported",
        "reason": (
            "all_retained_historical_runs_have_exact_replay_evidence_or_certified_parent_state"
        ),
        "scope": "all_retained_historical_runs",
        "blocked_manifest_ids": [],
    }
    assert report.retained_corpus_claim == {
        "claimed": True,
        "verdict": "claim_supported",
        "reason": "retained_corpus_has_no_remaining_uncertified_or_out_of_scope_runs",
        "scope": "retained_control_plane_corpus",
    }
    assert report.suggested_resolution_queue == ()


def test_closure_report_classifies_irrecoverable_legacy_subset() -> None:
    source_manifest = _make_source_manifest()
    manifest_store = InMemoryRunManifestStore()
    manifest_store.save(source_manifest)
    ledger_store = InMemoryRunLedgerStore()
    closure_service = HistoricalReplayClosureService(
        corpus_service=HistoricalReplayCorpusService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            certification_service=HistoricalReplayCertificationService(
                manifest_port=manifest_store,
                ledger_port=ledger_store,
                entry_id_factory=_closure_entry_id_factory("entry-closure-residual"),
            ),
        ),
        now_factory=_fixed_closure_time,
    )

    report = closure_service.build_closure_report(
        residual_dispositions=(
            HistoricalReplayResidualDisposition(
                manifest_id=source_manifest.manifest_id,
                disposition="irrecoverable_missing_immutable_evidence",
                rationale="legacy bronze payload was deleted before immutable snapshot publication",
                evidence_refs=("ops://historical-replay/inventory-2026-05-12.json",),
            ),
        )
    )

    assert report.closure_verdict == "residual_irrecoverable_subset_present"
    assert report.global_universal_historical_replay_claim["claimed"] is False
    assert report.global_universal_historical_replay_claim["reason"] == (
        "irrecoverable_legacy_runs_block_universal_historical_claim"
    )


def test_closure_report_can_flip_claim_for_narrowed_certifiable_scope() -> None:
    source_manifest = _make_source_manifest()
    manifest_store = InMemoryRunManifestStore()
    manifest_store.save(source_manifest)
    ledger_store = InMemoryRunLedgerStore()
    closure_service = HistoricalReplayClosureService(
        corpus_service=HistoricalReplayCorpusService(
            manifest_port=manifest_store,
            ledger_port=ledger_store,
            certification_service=HistoricalReplayCertificationService(
                manifest_port=manifest_store,
                ledger_port=ledger_store,
                entry_id_factory=_closure_entry_id_factory("entry-closure-complete"),
            ),
        ),
        now_factory=_fixed_closure_time,
    )

    report = closure_service.build_closure_report(
        residual_dispositions=(
            HistoricalReplayResidualDisposition(
                manifest_id=source_manifest.manifest_id,
                disposition="irrecoverable_missing_immutable_evidence",
                rationale="legacy corpus no longer retains trustworthy immutable snapshot evidence",
                evidence_refs=("ops://historical-replay/closure-campaign.json",),
            ),
        ),
        claim_scope_mode="retained_certifiable_historical_runs",
    )

    assert report.claim_scope_mode == "retained_certifiable_historical_runs"
    assert report.closure_verdict == "scope_narrowed_closed"
    assert report.global_universal_historical_replay_claim == {
        "claimed": True,
        "verdict": "claim_supported",
        "reason": "retained_certifiable_historical_scope_has_no_remaining_unresolved_runs",
        "scope": "retained_certifiable_historical_runs",
        "blocked_manifest_ids": [],
    }
    assert report.retained_corpus_claim["claimed"] is False
