"""Golden fixtures for reproducibility control-plane surfaces."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.run_manifest_diagnostics import (
    build_diagnostics_summary,
)
from bioetl.application.services.lineage import MetadataCoordinator
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunArtifactRef,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.models.metadata import EnvironmentMetadata, InputSnapshotRef, SourceMetadata
from bioetl.domain.ports import BronzeMetadataInput
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext

FIXTURE_DIR = Path("tests/fixtures/golden/reproducibility")
UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"


def _save_fixture(name: str, payload: dict[str, object]) -> None:
    fixture_path = FIXTURE_DIR / f"{name}.json"
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_fixture(name: str) -> dict[str, object]:
    fixture_path = FIXTURE_DIR / f"{name}.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _assert_matches_fixture(name: str, payload: dict[str, object]) -> None:
    if UPDATE_SNAPSHOTS:
        _save_fixture(name, payload)
        pytest.skip(f"Updated reproducibility golden fixture {name}")

    fixture_path = FIXTURE_DIR / f"{name}.json"
    if not fixture_path.exists():
        pytest.fail(
            f"Missing reproducibility golden fixture {fixture_path}. "
            "Run with UPDATE_SNAPSHOTS=1 to create it."
        )

    assert payload == _load_fixture(name)


def _make_manifest() -> RunManifest:
    return RunManifest(
        manifest_id="manifest-golden-001",
        execution_fingerprint="fp-golden-001",
        schema_version="1.0",
        created_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000901")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={
            "limit": 25,
            "exact_replay": True,
            "execution_context": "ordinary",
            "required_persistence_profile": "replay_ready",
        },
        runtime_config={"run_type": "incremental", "limit": 25, "exact_replay": True},
        resolved_config={"provider": "chembl", "entity": "activity", "limit": 25},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            source_revision_state="clean",
            config_hash="a" * 64,
            resolved_config_hash="b" * 64,
            effective_config_hash="c" * 64,
            contract_ref="chembl.activity",
            contract_version="1.2.0",
            contract_schema_hash="d" * 64,
            dq_policy_ref="chembl_activity.gold",
            rule_bundle_version="2026.03",
            dq_contract_compatibility_hash="e" * 64,
            effective_config_artifact_id="eca-golden-001",
        ),
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query="assay_type=B",
                input_snapshots=(
                    RunInputSnapshotRef(
                        snapshot_id="snapshot-golden-001",
                        content_hash="f" * 64,
                        immutable_uri="s3://bioetl-bronze/chembl/activity/batch-001.jsonl.zst",
                        query_fingerprint="g" * 64,
                        storage_provider="s3",
                        object_bucket="bioetl-bronze",
                        object_key="chembl/activity/batch-001.jsonl.zst",
                        object_version_id="version-001",
                        etag="etag-001",
                        last_modified="2025-01-01T11:55:00Z",
                        captured_at=datetime(2025, 1, 1, 11, 55, tzinfo=UTC),
                    ),
                ),
            ),
        ),
        planned_artifacts=(
            RunArtifactRef(layer="silver", path="silver/chembl/activity"),
        ),
    )


def _make_bronze_sidecar_payload() -> dict[str, object]:
    MetadataCoordinator.reset_environment_cache()
    MetadataCoordinator._cached_environment = EnvironmentMetadata(
        hostname="golden-host",
        python_version="3.12.0",
        bioetl_version="0.0-test",
    )
    context = RunContext.create(
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000902")),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
        provider="chembl",
        entity="activity",
        pipeline_version="1.0.0",
        git_commit="abc1234",
        config_hash="a" * 64,
        resolved_config_hash="b" * 64,
        effective_config_hash="c" * 64,
        manifest_id="manifest-golden-001",
        contract_ref="chembl.activity",
        contract_version="1.2.0",
        contract_schema_hash="d" * 64,
        dq_policy_ref="chembl_activity.gold",
        rule_bundle_version="2026.03",
        dq_contract_compatibility_hash="e" * 64,
        effective_config_artifact_id="eca-golden-001",
        execution_fingerprint="fp-golden-001",
    )
    coordinator = MetadataCoordinator(context)
    source_metadata = SourceMetadata(
        type="api",
        url="https://www.ebi.ac.uk/chembl/api/data/activity",
        query_string="assay_type=B",
        input_snapshots=[
            InputSnapshotRef(
                snapshot_id="snapshot-golden-001",
                content_hash="f" * 64,
                immutable_uri="s3://bioetl-bronze/chembl/activity/batch-001.jsonl.zst",
                query_fingerprint="g" * 64,
                storage_provider="s3",
                object_bucket="bioetl-bronze",
                object_key="chembl/activity/batch-001.jsonl.zst",
                object_version_id="version-001",
                etag="etag-001",
                last_modified="2025-01-01T11:55:00Z",
                captured_at=datetime(2025, 1, 1, 11, 55, tzinfo=UTC),
            )
        ],
    )
    metadata = coordinator.create_bronze_metadata(
        BronzeMetadataInput(
            batch_id=BatchID(UUID("00000000-0000-0000-0000-000000000903")),
            record_count=100,
            compressed_size=5000,
            output_path="v1/chembl/activity/2025-01-01/batch-001.jsonl.zst",
            started_at=datetime(2025, 1, 1, 12, 0, tzinfo=UTC),
            completed_at=datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC),
            source_metadata=source_metadata,
        )
    )
    return metadata.model_dump(mode="json")


def test_run_manifest_golden_fixture() -> None:
    _assert_matches_fixture("run_manifest_v1", _make_manifest().to_dict())


def test_bronze_sidecar_golden_fixture() -> None:
    _assert_matches_fixture("bronze_sidecar_v1", _make_bronze_sidecar_payload())


def test_diagnostics_summary_golden_fixture() -> None:
    _assert_matches_fixture(
        "diagnostics_summary_v1",
        build_diagnostics_summary(_make_manifest(), ()),
    )
