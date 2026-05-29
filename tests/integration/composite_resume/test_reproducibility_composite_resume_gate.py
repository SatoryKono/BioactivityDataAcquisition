"""Composite resume replay gate for control-plane checkpoints."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.composite_control_plane_builder import (
    build_composite_control_plane_bundle,
)
from bioetl.composition.bootstrap.runtime.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.infrastructure.config import Settings
from tests.integration.ci.reproducibility_contract_support import (
    build_replay_matrix_composite_config as _build_replay_matrix_composite_config,
    load_manifest_payload as _load_manifest_payload,
    write_composite_snapshot_envelope as _write_composite_snapshot_envelope,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.no_api,
]


def _load_snapshot_ids(manifest_payload: dict) -> list[str]:
    snapshot_ids: list[str] = []
    source_refs = manifest_payload.get("source_refs")
    assert isinstance(source_refs, list) and source_refs
    for source_ref in source_refs:
        assert isinstance(source_ref, dict)
        input_snapshots = source_ref.get("input_snapshots")
        assert isinstance(input_snapshots, list) and input_snapshots
        for snapshot in input_snapshots:
            assert isinstance(snapshot, dict)
            snapshot_id = snapshot.get("snapshot_id")
            assert isinstance(snapshot_id, str)
            snapshot_ids.append(snapshot_id)
    return snapshot_ids


def test_reproducibility_composite_full_snapshot_envelope_exact_replay_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Composite resume matrix should keep replay envelope invariant across repeated builds."""
    data_dir = tmp_path / "runtime"
    bronze_root = tmp_path / "cached-bronze"
    _write_composite_snapshot_envelope(bronze_root)
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.composite_control_plane_builder.get_code_revision_provenance",
        lambda: SimpleNamespace(
            git_commit="test-clean-composite-replay",
            source_revision_state="clean",
            dependency_lock_hash="sha256:test-lock-composite-replay",
        ),
    )
    config = _build_replay_matrix_composite_config()
    runtime = CompositeRuntimeConfig(
        resume=True,
        use_cached_bronze=True,
        cached_bronze_path=str(bronze_root),
        cached_bronze_date="2026-01-01",
    )

    manifests: list[dict] = []
    for index in range(2):
        settings = Settings(
            data_dir=data_dir,
            pipeline={
                "control_plane": {
                    "run_manifest_enabled": True,
                    "run_ledger_enabled": True,
                    "required_persistence_profile": "replay_ready",
                    "checkpoint_compatibility_policy": "hard_fail",
                }
            },
        )
        infra_context = CompositeInfrastructureContext(
            run_id=str(UUID(f"00000000-0000-0000-0000-00000000052{index}")),
            settings=settings,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracer=MagicMock(),
            storage=MagicMock(),
            lock=MagicMock(),
        )
        bundle = build_composite_control_plane_bundle(
            config=config,
            runtime=runtime,
            infra_context=infra_context,
        )
        manifest = _load_manifest_payload(data_dir, bundle.manifest_id)
        assert manifest["replay_capability"] == "exact_replay_supported"
        manifests.append(manifest)

    first, second = manifests
    assert first["run_id"] != second["run_id"]
    assert first["manifest_id"] != second["manifest_id"]
    assert first["provider"] == "composite"
    assert first["entity"] == "publication"
    assert first["code_provenance"]["pipeline_version"] == "1.0.0"
    assert first["execution_fingerprint"] == second["execution_fingerprint"]
    assert (
        first["code_provenance"]["effective_config_artifact_id"]
        == second["code_provenance"]["effective_config_artifact_id"]
    )

    snapshot_ids_first = _load_snapshot_ids(first)
    snapshot_ids_second = _load_snapshot_ids(second)
    assert snapshot_ids_first == snapshot_ids_second
    assert len(snapshot_ids_first) == 3

    evidence_dir = tmp_path / "reports" / "reproducibility"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = evidence_dir / "composite_publication_exact_replay_matrix.json"
    evidence_path.write_text(
        json.dumps(
            {
                "pipeline_name": config.name,
                "case": "composite_full_snapshot_envelope_exact_replay",
                "replay_capability": first["replay_capability"],
                "semantic_identity": {
                    "execution_fingerprint": first["execution_fingerprint"],
                    "effective_config_artifact_id": first["code_provenance"][
                        "effective_config_artifact_id"
                    ],
                    "snapshot_ids": snapshot_ids_first,
                },
                "occurrences": [
                    {
                        "run_id": first["run_id"],
                        "manifest_id": first["manifest_id"],
                    },
                    {
                        "run_id": second["run_id"],
                        "manifest_id": second["manifest_id"],
                    },
                ],
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert evidence["case"] == "composite_full_snapshot_envelope_exact_replay"
    assert len(evidence["occurrences"]) == 2
