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
"""DQ alert and traceability tests for RunManifestInspectionService."""

from __future__ import annotations

from datetime import UTC, datetime

from uuid import UUID

import pytest

from bioetl.application.services.control_plane import RunLedgerService
from bioetl.application.services.control_plane.effective_config.service import (
    EffectiveConfigService,
)
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionService,
)
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestCreateSpec as RunManifestCreateRequest,
    RunManifestService,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane import RunLedgerEntry, RunSourceRef
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.domain.types import RunID, RunType
from bioetl.domain.types.dq_contracts import DQDisposition
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore

pytestmark = pytest.mark.unit


def test_control_plane_chain_surfaces_dq_failure_traceability() -> None:
    manifest_store = InMemoryRunManifestStore()
    ledger_store = InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000102"))

    effective_config_service = EffectiveConfigService()
    artifact = effective_config_service.create_effective_config_artifact(
        pipeline_name="chembl_activity",
        pipeline_kind="standard",
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        runtime_overrides={
            "cli": {"limit": 25},
            "env": {
                "execution_environment": {
                    "settings.env": "test",
                }
            },
        },
        source_refs=[
            ConfigSourceRef(
                source_type="fixture",
                source_path="tests/fixtures/bronze/chembl/activity/sample.jsonl",
                source_hash="fixture-hash-1",
                priority=1,
            )
        ],
        dq_config=DQConfig(
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            rule_bundle_version="dq-rules.v1",
            default_disposition_policy=DQDisposition.FAIL,
        ),
        artifact_id="eca-chain-2",
    )
    manifest_service = RunManifestService(
        manifest_port=manifest_store,
        _manifest_id_factory=lambda: "manifest-chain-2",
    )
    manifest = manifest_service.create_manifest(
        RunManifestCreateRequest(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={
                "fixture_path": "tests/fixtures/bronze/chembl/activity/sample.jsonl"
            },
            runtime_config={"run_type": "incremental", "limit": 25},
            resolved_config=artifact.effective_execution_config.config_data,
            source_refs=(
                RunSourceRef(
                    provider="chembl",
                    entity="activity",
                    pipeline_name="chembl_activity",
                    query="fixture://sample",
                ),
            ),
            pipeline_version="1.0.0",
            git_commit="abc1234",
            source_revision_state="clean",
            dependency_lock_hash="sha256:deps-chain-2",
            config_hash=artifact.resolved_config_hash,
            resolved_config_hash=artifact.resolved_config_hash,
            effective_config_hash=artifact.effective_config_hash,
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            dq_policy_ref="chembl.activity.dq",
            rule_bundle_version="dq-rules.v1",
            dq_contract_compatibility_hash=artifact.dq_contract_compatibility_hash,
            effective_config_artifact_id=artifact.artifact_id,
        )
    )
    ledger_service = RunLedgerService(
        ledger_port=ledger_store,
        manifest_id=manifest.manifest_id,
        run_id=run_id,
        _entry_id_factory=lambda: "entry-chain-2",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    ledger_service.record_dq_policy_applied(
        stage="gold",
        rule_id="gold.not_null.id",
        disposition=DQDisposition.FAIL,
        dq_report_path="data/output/gold/chembl/activity/_dq.json",
    )

    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )
    result = service.show(manifest.manifest_id)

    assert result.manifest.code_provenance.config_hash == artifact.resolved_config_hash
    assert (
        result.manifest.code_provenance.effective_config_hash
        == artifact.effective_config_hash
    )
    assert result.diagnostics["contract_version"] == "1.0.0"
    assert result.diagnostics["dq_policy_ref"] == "chembl.activity.dq"
    assert result.diagnostics["rule_bundle_version"] == "dq-rules.v1"
    assert result.diagnostics["effective_config_artifact_id"] == "eca-chain-2"
    assert result.diagnostics["dq_rule_ids"] == ["gold.not_null.id"]
    assert result.diagnostics["dq_dispositions"] == ["fail"]
    assert result.diagnostics["dq_report_paths"] == [
        "data/output/gold/chembl/activity/_dq.json"
    ]
    assert result.diagnostics["dq_violation_kinds"] == []
    assert result.diagnostics["cross_validation_rule_ids"] == []
    assert result.diagnostics["cross_validation_config_paths"] == []
    assert result.diagnostics["alert_signals"] == {
        "run_failed": True,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": True,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "produced_artifact_trace_gap": True,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": True,
        "replay_ready_gap": True,
        "forensic_grade_gap": True,
        "dq_signal_present": True,
        "cross_validation_signal_present": False,
    }
    assert result.diagnostics["next_steps"] == [
        "Inspect failure classification and decide retry/quarantine/escalation.",
        "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
        "Resolve concrete produced artifacts from the run ledger before claiming replay-ready reproducibility.",
        "Current persisted surfaces do not satisfy the declared required persistence profile for this run.",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
        "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation.",
    ]


def test_show_collects_dq_trace_anchors() -> None:
    from tests.unit.application.services.test_run_manifest_inspection_service import (
        GOLD_DQ_REPORT_PATH,
        _FIXED_TIME,
        _InMemoryRunLedgerStore,
        _InMemoryRunManifestStore,
        _make_manifest,
        _run_id,
    )

    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = _run_id("effective-config-occurrence-diff")
    manifest_store.save(_make_manifest(manifest_id="manifest-dq", run_id=run_id))
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-1",
            manifest_id="manifest-dq",
            run_id=run_id,
            event_type="dq_policy_applied",
            occurred_at=_FIXED_TIME,
            event_family="dq",
            status="failed",
            stage="gold",
            details={
                "rule_id": "gold.not_null.id",
                "disposition": "fail",
                "dq_report_path": GOLD_DQ_REPORT_PATH,
            },
        )
    )
    result = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    ).show("manifest-dq")

    assert result.diagnostics["dq_rule_ids"] == ["gold.not_null.id"]
    assert result.diagnostics["dq_dispositions"] == ["fail"]
    assert result.diagnostics["dq_report_paths"] == [GOLD_DQ_REPORT_PATH]
    assert result.diagnostics["dq_policy_ref"] == "chembl_activity.gold"
    assert result.diagnostics["rule_bundle_version"] == "2026.03"
    assert result.diagnostics["effective_config_artifact_id"] == "eca-123"
    assert result.diagnostics["dq_violation_kinds"] == []
    assert result.diagnostics["cross_validation_rule_ids"] == []
    assert result.diagnostics["cross_validation_config_paths"] == []
    assert result.diagnostics["alert_signals"] == {
        "run_failed": True,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": False,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "produced_artifact_trace_gap": True,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": True,
        "replay_ready_gap": True,
        "forensic_grade_gap": True,
        "dq_signal_present": True,
        "cross_validation_signal_present": False,
    }
    assert result.diagnostics["next_steps"] == [
        "Inspect failure classification and decide retry/quarantine/escalation.",
        "Resolve concrete produced artifacts from the run ledger before claiming replay-ready reproducibility.",
        "Current persisted surfaces do not satisfy the declared required persistence profile for this run.",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
        "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation.",
    ]
