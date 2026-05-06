"""Unit tests for run-manifest CLI commands."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from click.testing import CliRunner

from bioetl.application.services.run_manifest_inspection_service import (
    RunManifestDiffEntry,
    RunManifestDiffResult,
    RunManifestInspectionCorruptionError,
    RunManifestInspectionResult,
    RunManifestVerifyResult,
)
from bioetl.domain.control_plane import (
    RunCodeProvenance,
    RunLedgerEntry,
    RunManifest,
)
from bioetl.domain.types import RunID, RunType
from bioetl.interfaces.cli.main import cli

_SNAPSHOT_IDENTITY_FINGERPRINT = (
    "f29f1a5c18e94a4fe614b59ae8e68c5c65afd078155b95d1e7c4aa32f6291dcd"
)
TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-run-manifest-cli-"))
BRONZE_BATCH_URI = (TEST_ROOT / "bronze" / "batch_1.jsonl.zst").as_uri()
GOLD_ARTIFACT_PATH = str(TEST_ROOT / "output" / "gold" / "chembl" / "activity")
GOLD_METADATA_PATH = str(Path(GOLD_ARTIFACT_PATH) / "_metadata.yaml")
GOLD_DQ_REPORT_PATH = str(TEST_ROOT / "reports" / "gold_dq.json")


class _FakeRunManifestService:
    def __init__(self) -> None:
        run_id = RunID(uuid4())
        self._run_id = run_id
        created_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        self._manifest = RunManifest(
            manifest_id="manifest-1",
            execution_fingerprint="fingerprint-1",
            schema_version="1.0",
            created_at=created_at,
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={"limit": 100},
            runtime_config={"run_type": "incremental", "limit": 100},
            resolved_config={"provider": "chembl", "entity_type": "activity"},
            replay_of_run_id="00000000-0000-0000-0000-000000000099",
            replay_of_manifest_id="manifest-parent",
            code_provenance=RunCodeProvenance(
                pipeline_version="1.0.0",
                git_commit="abc1234",
                config_hash="deadbeef",
            ),
        )
        self._ledger_entry = RunLedgerEntry(
            entry_id="entry-1",
            manifest_id="manifest-1",
            run_id=run_id,
            event_type="run_finished",
            occurred_at=created_at,
            status="success",
        )

    def show(self, identifier: str) -> RunManifestInspectionResult:
        if identifier == "missing":
            raise ValueError("missing")
        return RunManifestInspectionResult(
            manifest=self._manifest,
            ledger_entries=(self._ledger_entry,),
            diagnostics={
                "total_events": 1,
                "latest_event_type": "run_finished",
                "latest_status": "success",
                "execution_fingerprint": "fingerprint-1",
                "config_hash": "deadbeef",
                "contract_ref": "chembl_activity",
                "contract_version": "1.2.0",
                "dq_policy_ref": "chembl_activity.gold",
                "rule_bundle_version": "2026.03",
                "effective_config_artifact_id": "eca-123",
                "dq_contract_compatibility_hash": "compat-hash-1",
                "operator_replay_mode": "Exact Replay",
                "requested_exact_replay": True,
                "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
                "replay_capability_reason": "immutable_input_snapshots_present",
                "exact_replay_blockers": [],
                "snapshot_status": "full",
                "input_snapshot_ids": ["snapshot-1"],
                "input_snapshot_content_hashes": ["sha256:snapshot-1"],
                "input_snapshot_identity_fingerprint": _SNAPSHOT_IDENTITY_FINGERPRINT,
                "replay_mode": "exact_replay",
                "replay_of_run_id": "00000000-0000-0000-0000-000000000099",
                "replay_of_manifest_id": "manifest-parent",
                "replay_parentage": {
                    "is_exact_replay": True,
                    "replay_of_run_id": "00000000-0000-0000-0000-000000000099",
                    "replay_of_manifest_id": "manifest-parent",
                },
                "input_snapshot_count": 1,
                "input_snapshots": [
                    {
                        "provider": "chembl",
                        "entity": "activity",
                        "pipeline_name": "chembl_activity",
                        "query": None,
                        "snapshot_id": "snapshot-1",
                        "content_hash": "sha256:snapshot-1",
                        "immutable_uri": BRONZE_BATCH_URI,
                        "query_fingerprint": None,
                        "etag": None,
                        "last_modified": None,
                        "captured_at": None,
                    }
                ],
                "event_family_counts": {"pipeline.lifecycle": 1},
                "event_type_counts": {"run_finished": 1},
                "artifact_refs": [
                    {
                        "event_type": "artifact_published",
                        "stage": "gold",
                        "dataset_ref": "gold:chembl.activity@1",
                        "artifact_id": "gold:chembl.activity@1",
                        "lineage_fragment_id": "gold:fragment-1",
                        "artifact_path": GOLD_ARTIFACT_PATH,
                        "metadata_path": GOLD_METADATA_PATH,
                        "run_id": str(self._run_id),
                        "manifest_id": "manifest-1",
                    }
                ],
                "planned_artifact_count": 1,
                "published_artifact_count": 1,
                "lineage_fragment_ids": ["gold:fragment-1"],
                "missing_artifact_links": 0,
                "identity_graph_complete": True,
                "identity_graph": {
                    "run_id": str(self._run_id),
                    "manifest_id": "manifest-1",
                    "execution_fingerprint": "fingerprint-1",
                    "effective_config_hash": "deadbeef",
                    "contract_ref": "chembl_activity",
                    "contract_version": "1.2.0",
                    "replay_capability": "exact_replay_supported",
                    "operator_replay_mode": "Exact Replay",
                    "requested_exact_replay": True,
                    "exact_replay_support_boundary": "snapshot_backed_source_runs_only",
                    "replay_capability_reason": "immutable_input_snapshots_present",
                    "exact_replay_eligible": True,
                    "exact_replay_blockers": [],
                    "snapshot_status": "full",
                    "input_snapshot_ids": ["snapshot-1"],
                    "input_snapshot_content_hashes": ["sha256:snapshot-1"],
                    "input_snapshot_identity_fingerprint": (
                        _SNAPSHOT_IDENTITY_FINGERPRINT
                    ),
                    "replay_mode": "exact_replay",
                    "replay_of_run_id": "00000000-0000-0000-0000-000000000099",
                    "replay_of_manifest_id": "manifest-parent",
                    "replay_parentage": {
                        "is_exact_replay": True,
                        "replay_of_run_id": "00000000-0000-0000-0000-000000000099",
                        "replay_of_manifest_id": "manifest-parent",
                    },
                    "input_snapshot_count": 1,
                    "input_snapshots": [
                        {
                            "provider": "chembl",
                            "entity": "activity",
                            "pipeline_name": "chembl_activity",
                            "query": None,
                            "snapshot_id": "snapshot-1",
                            "content_hash": "sha256:snapshot-1",
                            "immutable_uri": BRONZE_BATCH_URI,
                            "query_fingerprint": None,
                            "etag": None,
                            "last_modified": None,
                            "captured_at": None,
                        }
                    ],
                    "planned_artifacts": [
                        {
                            "layer": "gold",
                            "path": GOLD_ARTIFACT_PATH,
                        }
                    ],
                    "published_artifacts": [
                        {
                            "event_type": "artifact_published",
                            "stage": "gold",
                            "dataset_ref": "gold:chembl.activity@1",
                            "artifact_id": "gold:chembl.activity@1",
                            "lineage_fragment_id": "gold:fragment-1",
                            "artifact_path": GOLD_ARTIFACT_PATH,
                            "metadata_path": GOLD_METADATA_PATH,
                            "run_id": str(self._run_id),
                            "manifest_id": "manifest-1",
                        }
                    ],
                },
                "dq_rule_ids": ["gold.not_null.id"],
                "dq_dispositions": ["fail"],
                "dq_report_paths": [GOLD_DQ_REPORT_PATH],
                "dq_violation_kinds": ["cross_validation_mismatch"],
                "cross_validation_rule_ids": ["composite.cross_validation.quarantine"],
                "cross_validation_config_paths": ["cross_validation"],
                "cross_validation_signal_present": True,
                "correlation_anchor_gaps": {
                    "effective_config_hash": 0,
                    "contract_ref": 0,
                    "contract_version": 0,
                    "composite_run_id": 0,
                },
                "persistence_profile": {
                    "attained_profile": "forensic_grade",
                    "claims": {
                        "degraded_observable": True,
                        "replay_ready": True,
                        "forensic_grade": True,
                    },
                    "surfaces": {
                        "control_plane_manifest": True,
                        "effective_config_artifact": True,
                        "immutable_input_snapshots": True,
                        "exact_replay_capability": True,
                        "run_ledger_history": True,
                        "artifact_lineage_links": True,
                    },
                    "replay_ready_missing_requirements": [],
                    "forensic_grade_missing_requirements": [],
                    "composite_resume_reconstructability": {
                        "scope": "coarse_grained_composite_resume",
                        "resume_model": "checkpoint_snapshot_plus_ledger_suffix",
                        "reconstructs": [
                            "state",
                            "seed_completed",
                            "merge_completed",
                            "last_event_id",
                            "last_event_occurred_at",
                        ],
                        "does_not_reconstruct": [
                            "per_provider_result_maps",
                            "rich_checkpoint_payloads",
                        ],
                    },
                },
                "reproducibility_policy_assessment": {
                    "required_persistence_profile": "replay_ready",
                    "replay_capability": "exact_replay_supported",
                    "strict_requirement_requested": True,
                    "strict_exact_replay_supported": True,
                    "required_profile_satisfied": True,
                    "blocking_gaps": [],
                    "snapshot_envelope": {
                        "source_count": 1,
                        "sources_with_snapshots": 1,
                        "any_input_snapshots": True,
                        "full_snapshot_envelope": True,
                        "require_full_snapshot_envelope": False,
                    },
                },
                "reproducibility_diagnostics": {
                    "policy": {
                        "required_persistence_profile": "replay_ready",
                        "attained_profile": "forensic_grade",
                        "replay_capability": "exact_replay_supported",
                        "operator_replay_mode": "Exact Replay",
                        "continuation_mode": "exact_replay",
                        "replay_capability_reason": (
                            "immutable_input_snapshots_present"
                        ),
                        "policy_assessment": {
                            "required_profile_satisfied": True,
                            "blocking_gaps": [],
                        },
                    },
                    "semantic_identity": {
                        "execution_fingerprint": "fingerprint-1",
                        "legacy_config_hash": "deadbeef",
                        "legacy_config_hash_alias_of": "resolved_config_hash",
                        "legacy_config_hash_replay_identity_anchor": False,
                        "config_hash_compatibility_anchor": "deadbeef",
                    },
                    "effective_config": {
                        "semantic": {
                            "legacy_config_hash": "deadbeef",
                            "legacy_config_hash_alias_of": "resolved_config_hash",
                            "effective_config_artifact_id": "eca-123",
                            "effective_config_hash": "deadbeef",
                        },
                        "diff_policy": {
                            "semantic_anchor": "effective_config_hash",
                            "occurrence_fields": [
                                "run_id",
                                "manifest_id",
                                "manifest_created_at",
                            ],
                            "legacy_config_hash_display_only": True,
                        },
                    },
                    "checkpoint_anchors": {
                        "resume_contract": {"resume_requested": False},
                        "resume_anchor_comparison": {
                            "checkpoint_identity_present": True,
                            "matching_fields": ["execution_fingerprint"],
                            "mismatched_fields": [],
                            "missing_current_fields": [],
                            "missing_checkpoint_fields": ["input_snapshot_ids"],
                        },
                    },
                },
                "alert_signals": {
                    "run_failed": False,
                    "run_shutdown": False,
                    "artifact_linkage_gap": False,
                    "lineage_gap": False,
                    "immutable_input_snapshot_gap": False,
                    "strict_replay_boundary_gap": False,
                    "composite_resume_reconstructability_gap": False,
                    "dq_signal_present": True,
                    "cross_validation_signal_present": True,
                },
                "next_steps": [
                    "Review DQ report artifacts, rule IDs, and contract policy anchors before retry or escalation.",
                    (
                        "Review cross-validation mismatch outcomes and composite"
                        " policy anchors before retry or quarantine changes."
                    ),
                ],
                "reproducibility_audit_score": {
                    "schema_version": "2.0",
                    "contract_version": "1.2.0",
                    "scale": "0-10",
                    "score_scope": "supported_boundary_run",
                    "overall_score": 9.4,
                    "blockers": [],
                    "evidence_refs": [
                        "diagnostics.git_commit",
                        "diagnostics.source_revision_state",
                    ],
                    "supported_boundary_verdict": {
                        "scope": "supported_boundary_run",
                        "supported_boundary_satisfied": True,
                        "verdict": "supported_boundary_satisfied",
                        "reason": "supported_boundary_requirements_met",
                        "exact_replay_support_boundary": (
                            "snapshot_backed_source_runs_only"
                        ),
                    },
                    "global_reproducibility_claim": {
                        "scope": "project_wide_exact_replay",
                        "claimed": False,
                        "verdict": "universal_exact_replay_not_claimed",
                        "reason": (
                            "published_contract_limits_exact_replay_to_"
                            "supported_boundary"
                        ),
                    },
                    "scored_at": self._manifest.created_at.isoformat(),
                    "source": "run_manifest_diagnostics",
                    "category_scores": {
                        "run_identity": {
                            "score": 10,
                            "evidence": [
                                "git_commit_present",
                                "source_revision_state_present",
                            ],
                            "blockers": [],
                            "evidence_refs": [
                                "diagnostics.git_commit",
                                "diagnostics.source_revision_state",
                            ],
                            "confidence": "high",
                        }
                    },
                },
            },
            identity_graph={
                "run_id": str(self._run_id),
                "manifest_id": "manifest-1",
                "execution_fingerprint": "fingerprint-1",
                "effective_config_hash": "deadbeef",
                "contract_ref": "chembl_activity",
                "contract_version": "1.2.0",
                "replay_capability": "exact_replay_supported",
                "operator_replay_mode": "Exact Replay",
                "requested_exact_replay": True,
                "replay_capability_reason": "immutable_input_snapshots_present",
                "exact_replay_eligible": True,
                "exact_replay_blockers": [],
                "snapshot_status": "full",
                "input_snapshot_ids": ["snapshot-1"],
                "input_snapshot_content_hashes": ["sha256:snapshot-1"],
                "input_snapshot_identity_fingerprint": _SNAPSHOT_IDENTITY_FINGERPRINT,
                "replay_mode": "exact_replay",
                "input_snapshot_count": 1,
                "input_snapshots": [
                    {
                        "provider": "chembl",
                        "entity": "activity",
                        "pipeline_name": "chembl_activity",
                        "query": None,
                        "snapshot_id": "snapshot-1",
                        "content_hash": "sha256:snapshot-1",
                        "immutable_uri": BRONZE_BATCH_URI,
                        "query_fingerprint": None,
                        "etag": None,
                        "last_modified": None,
                        "captured_at": None,
                    }
                ],
                "planned_artifacts": [
                    {
                        "layer": "gold",
                        "path": GOLD_ARTIFACT_PATH,
                    }
                ],
                "published_artifacts": [
                    {
                        "event_type": "artifact_published",
                        "stage": "gold",
                        "dataset_ref": "gold:chembl.activity@1",
                        "lineage_fragment_id": "gold:fragment-1",
                        "artifact_path": GOLD_ARTIFACT_PATH,
                        "metadata_path": GOLD_METADATA_PATH,
                        "run_id": str(self._run_id),
                        "manifest_id": "manifest-1",
                    }
                ],
            },
        )

    def diff(
        self, left_identifier: str, right_identifier: str
    ) -> RunManifestDiffResult:
        if "missing" in {left_identifier, right_identifier}:
            raise ValueError("missing")
        return RunManifestDiffResult(
            left_manifest_id="manifest-1",
            right_manifest_id="manifest-2",
            replay_relationship="right_is_exact_replay_of_left",
            classification="semantic_equivalent_with_noncanonical_differences",
            semantic_equivalent=True,
            cross_surface_replay_diff={
                "verdict": "semantic_equivalent_replay",
                "effective_config": {"semantic_equivalent": True},
                "checkpoint_anchors": {
                    "compatible": True,
                    "matching_fields": ["execution_fingerprint"],
                    "mismatched_fields": [],
                },
                "lineage": {"planned_artifacts_match": True},
            },
            differences=(
                RunManifestDiffEntry(
                    field="runtime_config",
                    left={"limit": 100},
                    right={"limit": 500},
                ),
            ),
        )

    def verify(
        self,
        left_identifier: str,
        right_identifier: str,
    ) -> RunManifestVerifyResult:
        if "missing" in {left_identifier, right_identifier}:
            raise ValueError("missing")
        return RunManifestVerifyResult(
            left_manifest_id="manifest-1",
            right_manifest_id="manifest-2",
            left_run_id=str(self._run_id),
            right_run_id="00000000-0000-0000-0000-000000000002",
            verdict="cross_store_replay_verified",
            verified=True,
            semantic_equivalent=True,
            occurrence_only=False,
            missing_evidence=(),
            manifest_diff={
                "classification": "identical",
                "semantic_equivalent": True,
            },
            effective_config={
                "available": True,
                "semantic_equivalent": True,
                "occurrence_only": False,
                "anchor_matches": {
                    "left_artifact_id": True,
                    "right_artifact_id": True,
                    "left_effective_config_hash": True,
                    "right_effective_config_hash": True,
                },
                "missing_evidence": [],
            },
        )


class _CorruptRunManifestService:
    def show(self, identifier: str) -> RunManifestInspectionResult:
        raise RunManifestInspectionCorruptionError(
            identifier,
            "Run manifest index corruption: indexed manifest mismatch",
        )

    def diff(
        self,
        left_identifier: str,
        right_identifier: str,
    ) -> RunManifestDiffResult:
        raise RunManifestInspectionCorruptionError(
            left_identifier,
            "Run manifest index corruption: indexed manifest mismatch",
        )


class _FakeForensicRunDiffResult:
    def to_dict(self) -> dict[str, object]:
        return {
            "left_manifest_id": "manifest-1",
            "right_manifest_id": "manifest-2",
            "classification": "semantic_drift",
            "semantic_equivalent": False,
            "occurrence_only": False,
            "semantic_difference_fields": ["execution_fingerprint"],
            "occurrence_difference_fields": ["run_id"],
            "noncanonical_difference_fields": [],
            "replay_relationship": "unrelated",
            "forensic_diff": {
                "verdict": "semantic_drift",
                "checkpoint_anchors": {
                    "compatible": False,
                    "matching_fields": [],
                    "mismatched_fields": ["execution_fingerprint"],
                },
            },
            "replay_capability": {
                "capability_match": False,
                "left": {"replay_capability": "exact_replay_supported"},
                "right": {"replay_capability": "rebuild_only"},
            },
            "checkpoint_compatibility": {
                "available": True,
                "compatible": False,
                "matching_fields": [],
                "mismatched_fields": ["execution_fingerprint"],
            },
            "artifact_byte_equivalence": {
                "available": True,
                "equivalent": False,
                "compared_artifacts": ["left == right"],
                "missing_artifacts": [],
                "mismatched_artifacts": ["left == right"],
                "comparison_scope": "artifact_and_metadata_paths",
            },
            "artifact_completeness": {
                "left": {"complete": True, "published_artifact_count": 1},
                "right": {"complete": False, "published_artifact_count": 0},
            },
            "lineage_closure": {
                "left": {"status": "supported"},
                "right": {"status": "supported"},
            },
            "missing_evidence": {
                "left": [],
                "right": [
                    "run_ledger_entries_missing",
                    "published_artifacts_missing",
                ],
            },
            "manifest_diff": {"classification": "semantic_drift"},
        }


class _FakeForensicRunDiffService:
    def compare(self, left_identifier: str, right_identifier: str) -> object:
        if "missing" in {left_identifier, right_identifier}:
            raise ValueError("missing")
        return _FakeForensicRunDiffResult()


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def _patch_run_manifest_service(monkeypatch: Any, service: object) -> None:
    import bioetl.interfaces.cli.commands.run_manifest as run_manifest_cmd

    monkeypatch.setattr(
        run_manifest_cmd,
        "get_run_manifest_service",
        lambda: service,
        raising=True,
    )


def _patch_forensic_diff_service(monkeypatch: Any, service: object) -> None:
    import bioetl.interfaces.cli.commands.run_manifest as run_manifest_cmd

    monkeypatch.setattr(
        run_manifest_cmd,
        "get_forensic_run_diff_service",
        lambda: service,
        raising=True,
    )


@pytest.mark.unit
class TestRunManifestCommands:
    def test_run_manifest_help_shows_subcommands(self, cli_runner: CliRunner) -> None:
        result = cli_runner.invoke(cli, ["run-manifest", "--help"])

        assert result.exit_code == 0
        assert "show" in result.output
        assert "diff" in result.output
        assert "forensic-diff" in result.output
        assert "score" in result.output
        assert "verify" in result.output

    def test_run_manifest_help_avoids_eager_registry_build(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        import importlib

        def _fail_registry_build() -> None:
            raise AssertionError("registry should stay lazy")

        registry_helpers = importlib.import_module(
            "bioetl.interfaces.cli.registry_helpers"
        )

        monkeypatch.setattr(
            registry_helpers,
            "build_cli_registry",
            _fail_registry_build,
        )

        result = cli_runner.invoke(cli, ["run-manifest", "--help"])

        assert result.exit_code == 0
        assert (
            "Inspect control-plane run manifests and ledger history." in result.output
        )

    def test_show_json_outputs_manifest_and_ledger(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            ["run-manifest", "show", "manifest-1", "--format", "json"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["manifest"]["manifest_id"] == "manifest-1"
        assert payload["manifest"]["replay_of_manifest_id"] == "manifest-parent"
        assert payload["ledger_entries"][0]["event_type"] == "run_finished"
        assert payload["diagnostics"]["latest_status"] == "success"
        assert payload["diagnostics"]["replay_parentage"]["is_exact_replay"] is True
        assert payload["identity_graph"]["manifest_id"] == "manifest-1"
        assert payload["identity_graph"]["replay_mode"] == "exact_replay"
        assert payload["diagnostics"]["contract_version"] == "1.2.0"
        assert (
            payload["diagnostics"]["reproducibility_policy_assessment"][
                "required_profile_satisfied"
            ]
            is True
        )
        assert payload["diagnostics"]["dq_rule_ids"] == ["gold.not_null.id"]
        assert payload["diagnostics"]["cross_validation_rule_ids"] == [
            "composite.cross_validation.quarantine"
        ]
        assert "alert_signals" in payload["diagnostics"]

    def test_score_json_outputs_machine_readable_audit_score(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            ["run-manifest", "score", "manifest-1"],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        score = payload["reproducibility_audit_score"]
        assert payload["manifest_id"] == "manifest-1"
        assert score["schema_version"] == "2.0"
        assert score["contract_version"] == "1.2.0"
        assert score["score_scope"] == "supported_boundary_run"
        assert score["supported_boundary_verdict"]["scope"] == (
            "supported_boundary_run"
        )
        assert score["global_reproducibility_claim"]["claimed"] is False
        assert score["blockers"] == []
        assert "diagnostics.git_commit" in score["evidence_refs"]

    def test_score_text_labels_boundary_and_global_claim(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            ["run-manifest", "score", "manifest-1", "--format", "text"],
        )

        assert result.exit_code == 0
        assert "Run Manifest Score" in result.output
        assert "run_scoped_score: 9.4" in result.output
        assert "score_scope: supported_boundary_run" in result.output
        assert "supported_boundary_verdict:" in result.output
        assert "verdict: supported_boundary_satisfied" in result.output
        assert "global_reproducibility_claim:" in result.output
        assert "claimed: false" in result.output
        assert "verdict: universal_exact_replay_not_claimed" in result.output

    def test_show_yaml_outputs_manifest_and_diagnostics(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            ["run-manifest", "show", "manifest-1", "--format", "yaml"],
        )

        assert result.exit_code == 0
        assert "manifest:" in result.output
        assert "ledger_entries:" in result.output
        assert "diagnostics:" in result.output
        assert "latest_status: success" in result.output
        assert "cross_validation_signal_present: true" in result.output

    def test_show_defaults_to_human_readable_text(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(cli, ["run-manifest", "show", "manifest-1"])

        assert result.exit_code == 0
        assert "Manifest" in result.output
        assert "manifest_id: manifest-1" in result.output
        assert "replay_of_manifest_id: manifest-parent" in result.output
        assert "Code Provenance" in result.output
        assert "Ledger" in result.output
        assert "Diagnostics" in result.output
        assert "latest_status: success" in result.output
        assert "contract_version: 1.2.0" in result.output
        assert "dq_policy_ref: chembl_activity.gold" in result.output
        assert "requested_exact_replay: true" in result.output
        assert "mode: Exact Replay" in result.output
        assert "snapshot_status: full" in result.output
        assert (
            "exact_replay_support_boundary: snapshot_backed_source_runs_only"
            in result.output
        )
        assert (
            "replay_capability_reason: immutable_input_snapshots_present"
            in result.output
        )
        assert "replay_parentage" in result.output
        assert "input_snapshot_ids" in result.output
        assert "input_snapshot_identity_fingerprint" in result.output
        assert "event_family_counts" in result.output
        assert "event_type_counts" in result.output
        assert "planned_artifact_count: 1" in result.output
        assert "published_artifact_count: 1" in result.output
        assert "artifact_refs" in result.output
        assert "identity_graph_complete: true" in result.output
        assert "Identity Graph" in result.output
        assert "lineage_fragment_ids" in result.output
        assert "missing_artifact_links: 0" in result.output
        assert "gold.not_null.id" in result.output
        assert "cross_validation_mismatch" in result.output
        assert "composite.cross_validation.quarantine" in result.output
        assert "cross_validation_config_paths" in result.output
        assert "correlation_anchor_gaps" in result.output
        assert "persistence_profile" in result.output
        assert "reproducibility_policy_assessment" in result.output
        assert "reproducibility_diagnostics" in result.output
        assert "Reproducibility" in result.output
        assert "required_profile_satisfied: true" in result.output
        assert (
            "effective_config_semantic_anchor: effective_config_hash" in result.output
        )
        assert "effective_config_occurrence_fields" in result.output
        assert '"legacy_config_hash_display_only": true' in result.output
        assert "checkpoint_identity_present: true" in result.output
        assert "checkpoint_matching_fields" in result.output
        assert "checkpoint_missing_checkpoint_fields" in result.output
        assert '"legacy_config_hash_replay_identity_anchor": false' in result.output
        assert "config_hash_compatibility_anchor" in result.output
        assert "attained_profile" in result.output
        assert "forensic_grade" in result.output
        assert "composite_resume_reconstructability" in result.output
        assert GOLD_DQ_REPORT_PATH in result.output
        assert GOLD_ARTIFACT_PATH in result.output
        assert GOLD_METADATA_PATH in result.output
        assert (
            "Review DQ report artifacts, rule IDs, and contract policy anchors "
            "before retry or escalation." in result.output
        )
        assert (
            "Review cross-validation mismatch outcomes and composite policy anchors "
            "before retry or quarantine changes." in result.output
        )
        assert "run_finished" in result.output

    def test_show_missing_manifest_prints_error(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(cli, ["run-manifest", "show", "missing"])

        assert result.exit_code == 0
        assert "Run manifest not found" in result.stderr

    def test_show_manifest_store_corruption_prints_forensic_error(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _CorruptRunManifestService())

        result = cli_runner.invoke(cli, ["run-manifest", "show", "manifest-corrupt"])

        assert result.exit_code == 0
        assert "Run manifest store corruption" in result.stderr
        assert "indexed manifest mismatch" in result.stderr

    def test_diff_json_outputs_changed_fields(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            [
                "run-manifest",
                "diff",
                "manifest-1",
                "manifest-2",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["left_manifest_id"] == "manifest-1"
        assert payload["right_manifest_id"] == "manifest-2"
        assert payload["replay_relationship"] == "right_is_exact_replay_of_left"
        assert (
            payload["cross_surface_replay_diff"]["verdict"]
            == "semantic_equivalent_replay"
        )
        assert payload["differences"][0]["field"] == "runtime_config"

    def test_diff_defaults_to_human_readable_text(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            ["run-manifest", "diff", "manifest-1", "manifest-2"],
        )

        assert result.exit_code == 0
        assert "Manifest Diff" in result.output
        assert "left_manifest_id: manifest-1" in result.output
        assert "right_manifest_id: manifest-2" in result.output
        assert "replay_relationship: right_is_exact_replay_of_left" in result.output
        assert "cross_surface_replay_diff:" in result.output
        assert "verdict: semantic_equivalent_replay" in result.output
        assert "checkpoint_anchors:" in result.output
        assert "compatible: true" in result.output
        assert "field: runtime_config" in result.output

    def test_diff_yaml_outputs_changed_fields(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            [
                "run-manifest",
                "diff",
                "manifest-1",
                "manifest-2",
                "--format",
                "yaml",
            ],
        )

        assert result.exit_code == 0
        assert "left_manifest_id: manifest-1" in result.output
        assert "right_manifest_id: manifest-2" in result.output
        assert "replay_relationship: right_is_exact_replay_of_left" in result.output
        assert "differences:" in result.output
        assert "field: runtime_config" in result.output

    def test_verify_json_outputs_cross_store_replay_evidence(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            [
                "run-manifest",
                "verify",
                "manifest-1",
                "manifest-2",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["verdict"] == "cross_store_replay_verified"
        assert payload["verified"] is True
        assert payload["effective_config"]["semantic_equivalent"] is True
        assert payload["effective_config"]["anchor_matches"] == {
            "left_artifact_id": True,
            "right_artifact_id": True,
            "left_effective_config_hash": True,
            "right_effective_config_hash": True,
        }

    def test_verify_defaults_to_human_readable_text(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            ["run-manifest", "verify", "manifest-1", "manifest-2"],
        )

        assert result.exit_code == 0
        assert "Run Manifest Verification" in result.output
        assert "verdict: cross_store_replay_verified" in result.output
        assert "verified: true" in result.output
        assert "effective_config:" in result.output

    def test_verify_missing_manifest_prints_error(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_run_manifest_service(monkeypatch, _FakeRunManifestService())

        result = cli_runner.invoke(
            cli,
            ["run-manifest", "verify", "manifest-1", "missing"],
        )

        assert result.exit_code == 0
        assert "Run manifest verification failed" in result.stderr

    def test_forensic_diff_json_outputs_cross_artifact_report(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_forensic_diff_service(monkeypatch, _FakeForensicRunDiffService())

        result = cli_runner.invoke(
            cli,
            [
                "run-manifest",
                "forensic-diff",
                "manifest-1",
                "manifest-2",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["classification"] == "semantic_drift"
        assert payload["checkpoint_compatibility"]["compatible"] is False
        assert payload["artifact_byte_equivalence"]["equivalent"] is False
        assert payload["artifact_completeness"]["right"]["complete"] is False
        assert payload["missing_evidence"]["right"] == [
            "run_ledger_entries_missing",
            "published_artifacts_missing",
        ]

    def test_forensic_diff_defaults_to_human_readable_text(
        self,
        cli_runner: CliRunner,
        monkeypatch: Any,
    ) -> None:
        _patch_forensic_diff_service(monkeypatch, _FakeForensicRunDiffService())

        result = cli_runner.invoke(
            cli,
            ["run-manifest", "forensic-diff", "manifest-1", "manifest-2"],
        )

        assert result.exit_code == 0
        assert "Forensic Run Diff" in result.output
        assert "classification: semantic_drift" in result.output
        assert "checkpoint_compatibility:" in result.output
        assert "artifact_byte_equivalence:" in result.output
        assert "artifact_completeness:" in result.output
        assert "missing_evidence:" in result.output
