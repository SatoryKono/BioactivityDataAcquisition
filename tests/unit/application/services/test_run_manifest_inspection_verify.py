"""Split verify/control-plane-chain owner tests for RunManifestInspectionService."""

from __future__ import annotations

from tests.unit.application.services.test_run_manifest_inspection_service import *  # noqa: F401,F403

def test_verify_confirms_cross_store_effective_config_replay_evidence() -> None:
    manifest_store = _InMemoryRunManifestStore()
    effective_config_store = _InMemoryEffectiveConfigArtifactStore()
    created_at = datetime(2025, 1, 1, tzinfo=UTC)
    left_run_id = RunID(UUID("00000000-0000-0000-0000-000000000231"))
    right_run_id = RunID(UUID("00000000-0000-0000-0000-000000000232"))
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=left_run_id,
        execution_fingerprint="fingerprint-same",
        created_at=created_at,
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=right_run_id,
        execution_fingerprint="fingerprint-same",
        created_at=created_at,
    )
    artifact_payload = {
        "semantic_artifact": {
            "artifact_id": "eca-123",
            "pipeline_name": "chembl_activity",
            "effective_config_hash": _VALID_EFFECTIVE_CONFIG_HASH,
        },
    }
    manifest_store.save(left)
    manifest_store.save(right)
    effective_config_store.save(
        artifact_id="eca-123",
        run_id=left_run_id,
        payload=artifact_payload,
        occurrence={"artifact_id": "eca-123", "run_id": str(left_run_id)},
    )
    effective_config_store.save(
        artifact_id="eca-123",
        run_id=right_run_id,
        payload=artifact_payload,
        occurrence={"artifact_id": "eca-123", "run_id": str(right_run_id)},
    )
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        effective_config_artifact_port=effective_config_store,
    )

    result = service.verify("manifest-left", "manifest-right")

    assert result.verified is True
    assert result.verdict == "occurrence_only_replay_verified"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is True
    assert result.missing_evidence == ()
    assert result.effective_config["semantic_equivalent"] is True
    assert result.effective_config["anchor_matches"] == {
        "left_artifact_id": True,
        "right_artifact_id": True,
        "left_effective_config_hash": True,
        "right_effective_config_hash": True,
    }
    payload = result.to_dict()
    assert payload["manifest_diff"]["classification"] == "occurrence_only"
    assert payload["left_authoritative_replay_dossier"]["manifest_id"] == (
        "manifest-left"
    )
    assert payload["right_authoritative_replay_dossier"]["manifest_id"] == (
        "manifest-right"
    )

def test_verify_reports_missing_effective_config_evidence() -> None:
    manifest_store = _InMemoryRunManifestStore()
    effective_config_store = _InMemoryEffectiveConfigArtifactStore()
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000233")),
        execution_fingerprint="fingerprint-same",
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000234")),
        execution_fingerprint="fingerprint-same",
    )
    manifest_store.save(left)
    manifest_store.save(right)
    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        effective_config_artifact_port=effective_config_store,
    )

    result = service.verify("manifest-left", "manifest-right")

    assert result.verified is False
    assert result.verdict == "missing_replay_evidence"
    assert result.semantic_equivalent is False
    assert result.missing_evidence == (
        "left_effective_config_artifact_missing",
        "right_effective_config_artifact_missing",
        "left_effective_config_occurrence_missing",
        "right_effective_config_occurrence_missing",
    )

def test_control_plane_chain_surfaces_effective_config_and_artifact_links() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000101"))

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
            default_disposition_policy=DQDisposition.WARN,
        ),
        artifact_id="eca-chain-1",
    )
    manifest_service = RunManifestService(
        manifest_port=manifest_store,
        _manifest_id_factory=lambda: "manifest-chain-1",
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
            planned_artifacts=(
                RunArtifactRef(
                    layer="silver",
                    path="data/output/silver/chembl/activity",
                ),
            ),
            pipeline_version="1.0.0",
            git_commit="abc1234",
            source_revision_state="clean",
            dependency_lock_hash="sha256:deps-chain-1",
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
        _entry_id_factory=lambda: "entry-chain-1",
    )
    ledger_service.record_manifest_created(manifest)
    ledger_service.record_artifact_published(
        layer="silver",
        artifact_path="data/output/silver/chembl/activity",
        dataset_ref="silver:chembl.activity@1",
        lineage_fragment_id="silver:fragment-chain-1",
        details={
            "dq_report_path": "data/output/silver/chembl/activity/_dq.json",
            "metadata_path": "data/output/silver/chembl/activity/_metadata.yaml",
        },
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
    assert result.identity_graph == result.diagnostics["identity_graph"]
    assert result.diagnostics["config_hash"] == artifact.resolved_config_hash
    assert result.diagnostics["resolved_config_hash"] == artifact.resolved_config_hash
    assert result.diagnostics["effective_config_hash"] == artifact.effective_config_hash
    assert result.diagnostics["effective_config_artifact_id"] == "eca-chain-1"
    assert result.diagnostics["artifact_refs"] == [
        {
            "event_type": "artifact_published",
            "publication_status": "published",
            "stage": "silver",
            "artifact_id": "silver:chembl.activity@1",
            "dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-chain-1",
            "artifact_path": "data/output/silver/chembl/activity",
            "metadata_path": "data/output/silver/chembl/activity/_metadata.yaml",
        }
    ]
    assert result.diagnostics["correlation_anchor_gaps"] == {
        "effective_config_hash": 0,
        "resolved_config_hash": 0,
        "contract_ref": 0,
        "contract_version": 0,
        "composite_run_id": 0,
    }
    assert result.diagnostics["dq_report_paths"] == [
        "data/output/silver/chembl/activity/_dq.json"
    ]

def test_control_plane_chain_surfaces_lifecycle_smoke_summary() -> None:
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000103"))

    manifest_service = RunManifestService(
        manifest_port=manifest_store,
        _manifest_id_factory=lambda: "manifest-chain-smoke",
    )
    manifest = manifest_service.create_manifest(
        RunManifestCreateRequest(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={"limit": 25},
            runtime_config={"run_type": "incremental", "limit": 25},
            resolved_config={"provider": "chembl", "entity_type": "activity"},
            pipeline_version="1.0.0",
            git_commit="abc1234",
            source_revision_state="clean",
            dependency_lock_hash="sha256:deps-chain-smoke",
            config_hash="a" * 64,
            resolved_config_hash="b" * 64,
            effective_config_hash="c" * 64,
            contract_ref="chembl.activity",
            contract_version="1.0.0",
            dq_policy_ref="chembl.activity.dq",
            rule_bundle_version="dq-rules.v1",
            dq_contract_compatibility_hash="compat-hash-smoke",
            effective_config_artifact_id="eca-smoke-1",
        )
    )
    ledger_service = RunLedgerService(
        ledger_port=ledger_store,
        manifest_id=manifest.manifest_id,
        run_id=run_id,
        _entry_id_factory=lambda: f"entry-smoke-{len(ledger_store.items) + 1}",
    )
    ledger_service.record_manifest_created(manifest)
    ledger_service.record_run_started()
    ledger_service.record_stage_started(
        stage="execute_pipeline",
        details={"records": 5},
    )
    ledger_service.record_stage_completed(
        stage="execute_pipeline",
        metrics_snapshot={"records_bronze": 5},
        details={"result": "ok"},
    )
    ledger_service.record_artifact_published(
        layer="silver",
        artifact_path="data/output/silver/chembl/activity",
        dataset_ref="silver:chembl.activity@1",
        lineage_fragment_id="silver:fragment-smoke-1",
    )
    ledger_service.record_run_finished(metrics_snapshot={"records_silver": 5})

    service = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    )
    result = service.show(manifest.manifest_id)

    assert result.diagnostics["total_events"] == 6
    assert result.diagnostics["latest_event_type"] == "run_finished"
    assert result.diagnostics["latest_status"] == "success"
    assert result.diagnostics["event_family_counts"] == {
        "artifact": 1,
        "diagnostic": 1,
        "pipeline.lifecycle": 2,
        "pipeline.phase": 2,
    }
    assert result.diagnostics["event_type_counts"] == {
        "artifact_published": 1,
        "manifest_created": 1,
        "run_finished": 1,
        "run_started": 1,
        "stage_completed": 1,
        "stage_started": 1,
    }
    assert result.diagnostics["missing_artifact_links"] == 0
    assert result.diagnostics["alert_signals"] == {
        "run_failed": False,
        "run_shutdown": False,
        "artifact_linkage_gap": False,
        "lineage_gap": False,
        "immutable_input_snapshot_gap": True,
        "strict_replay_boundary_gap": False,
        "lineage_closure_boundary_gap": False,
        "reproducible_semantic_output_mode_gap": False,
        "produced_artifact_trace_gap": False,
        "composite_resume_reconstructability_gap": False,
        "required_persistence_profile_gap": True,
        "replay_ready_gap": True,
        "forensic_grade_gap": True,
        "dq_signal_present": False,
        "cross_validation_signal_present": False,
    }
    assert result.diagnostics["next_steps"] == [
        "Persist immutable cached Bronze input snapshots before treating this run as strict exact-replay capable.",
        "Current persisted surfaces do not satisfy the declared required persistence profile for this run.",
        "Review replay-ready persistence requirements before treating this run as exact-replay capable.",
        "Review forensic-grade persistence requirements before using this run for full trace/debug reconstruction.",
    ]
    assert result.diagnostics["correlation_anchor_gaps"] == {
        "effective_config_hash": 0,
        "resolved_config_hash": 0,
        "contract_ref": 0,
        "contract_version": 0,
        "composite_run_id": 0,
    }
