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
"""Unit tests for bounded historical replay certification workflows."""

from __future__ import annotations

from collections.abc import Callable
from itertools import count

import pytest

from dataclasses import replace
from datetime import UTC, datetime

from bioetl.application.services.control_plane.replay.historical_certification_service import (
    HistoricalReplayCertificationService,
    HistoricalReplaySnapshotCertification,
)
from bioetl.application.services.control_plane.manifest.diagnostics import (
    build_diagnostics_summary,
)
from bioetl.domain.control_plane import RunManifest, RunSourceRef
from bioetl.domain.types import RunID
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore
from tests.helpers.deterministic_ids import deterministic_uuid_value
from tests.unit.application.services.run_manifest_test_support import (
    make_run_manifest as _build_manifest,
)


pytestmark = pytest.mark.unit


def _certification_entry_id_factory(
    prefix: str = "entry-historical",
) -> Callable[[], str]:
    sequence = count(1)
    return lambda: f"{prefix}-{next(sequence)}"


def _make_source_manifest() -> RunManifest:
    return _build_manifest(
        manifest_id="historical-source-manifest",
        execution_fingerprint="historical-source-fingerprint",
        run_id=RunID(deterministic_uuid_value("historical.certification.source")),
        created_at=datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
    )


def _make_composite_manifest() -> RunManifest:
    manifest = _build_manifest(
        manifest_id="historical-composite-manifest",
        execution_fingerprint="historical-composite-fingerprint",
        run_id=RunID(deterministic_uuid_value("historical.certification.composite")),
        created_at=datetime(2026, 1, 2, 9, 30, tzinfo=UTC),
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
                input_snapshots=(),
            ),
        ),
        code_provenance=replace(
            manifest.code_provenance,
            contract_ref="composite.activity",
            contract_version="1.0.0",
            pipeline_version="1.0.0",
        ),
    )


def test_certify_historical_source_run_appends_certified_snapshot_evidence() -> None:
    manifest = _make_source_manifest()
    manifest_store = InMemoryRunManifestStore()
    manifest_store.save(manifest)
    ledger_store = InMemoryRunLedgerStore()
    service = HistoricalReplayCertificationService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        entry_id_factory=_certification_entry_id_factory("entry-source-certification"),
    )

    result = service.certify_historical_source_run(
        manifest_id=manifest.manifest_id,
        certifications=(
            HistoricalReplaySnapshotCertification(
                provider=manifest.provider,
                entity=manifest.entity,
                pipeline_name=manifest.pipeline_name,
                snapshot_id="snapshot-certified-1",
                content_hash="sha256:source-certified-1",
                immutable_uri="file:///historical/source/snapshot-1.jsonl",
                bronze_batch_ref="bronze://historical/source/batch-1.jsonl",
                certification_artifact_ref=(
                    "control://historical/source-certification-1.json"
                ),
            ),
        ),
    )

    diagnostics = build_diagnostics_summary(
        manifest,
        tuple(ledger_store.list_entries(manifest.manifest_id)),
    )

    assert result.replay_occurrence_kind == "historical_source_replay_certified_parent"
    assert (
        result.broader_historical_exact_replay_state
        == "historical_source_replay_certified"
    )
    assert diagnostics["input_snapshot_materialization_mode"] == (
        "historical_source_snapshot_certified"
    )
    assert diagnostics["source_posture"] == (
        "historical_source_replay_certified_envelope"
    )
    assert diagnostics["replay_occurrence_kind"] == (
        "historical_source_replay_certified_parent"
    )
    assert diagnostics["broader_historical_exact_replay_state"] == (
        "historical_source_replay_certified"
    )


def test_certify_historical_composite_run_requires_certified_upstream_lineage() -> None:
    source_manifest = _make_source_manifest()
    composite_manifest = _make_composite_manifest()
    manifest_store = InMemoryRunManifestStore()
    manifest_store.save(source_manifest)
    manifest_store.save(composite_manifest)
    ledger_store = InMemoryRunLedgerStore()
    service = HistoricalReplayCertificationService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
        entry_id_factory=_certification_entry_id_factory(
            "entry-composite-certification"
        ),
    )

    service.certify_historical_source_run(
        manifest_id=source_manifest.manifest_id,
        certifications=(
            HistoricalReplaySnapshotCertification(
                provider=source_manifest.provider,
                entity=source_manifest.entity,
                pipeline_name=source_manifest.pipeline_name,
                snapshot_id="snapshot-certified-upstream-1",
                content_hash="sha256:source-certified-upstream-1",
                immutable_uri="file:///historical/source/upstream-1.jsonl",
                bronze_batch_ref="bronze://historical/source/upstream-1.jsonl",
                certification_artifact_ref="control://historical/source-upstream.json",
            ),
        ),
    )

    result = service.certify_historical_composite_run(
        manifest_id=composite_manifest.manifest_id,
        certifications=(
            HistoricalReplaySnapshotCertification(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                snapshot_id="snapshot-certified-composite-1",
                content_hash="sha256:composite-certified-1",
                immutable_uri="file:///historical/composite/snapshot-1.jsonl",
                bronze_batch_ref="bronze://historical/composite/batch-1.jsonl",
                certification_artifact_ref=(
                    "control://historical/composite-certification-1.json"
                ),
                upstream_run_id=str(source_manifest.run_id),
                upstream_manifest_id=source_manifest.manifest_id,
            ),
        ),
    )

    diagnostics = build_diagnostics_summary(
        composite_manifest,
        tuple(ledger_store.list_entries(composite_manifest.manifest_id)),
    )

    assert result.replay_occurrence_kind == (
        "historical_composite_replay_certified_parent"
    )
    assert (
        result.broader_historical_exact_replay_state
        == "historical_composite_replay_certified"
    )
    assert diagnostics["input_snapshot_materialization_mode"] == (
        "historical_composite_replay_envelope_certified"
    )
    assert diagnostics["source_posture"] == (
        "historical_composite_replay_certified_envelope"
    )
    assert diagnostics["replay_occurrence_kind"] == (
        "historical_composite_replay_certified_parent"
    )
    assert diagnostics["broader_historical_exact_replay_state"] == (
        "historical_composite_replay_certified"
    )
