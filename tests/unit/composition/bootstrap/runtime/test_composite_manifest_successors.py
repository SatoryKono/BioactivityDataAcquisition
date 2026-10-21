"""Successor publication across composite runtime and checkpoint boundaries."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.application.composite.checkpoint.service import (
    CompositeCheckpointService,
)
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.application.services.control_plane.ledger._input_snapshot_manifest import (
    persist_input_snapshots_on_manifest,
)
from bioetl.composition.bootstrap.runtime import (
    _composite_control_plane_support as subject,
)
from bioetl.composition.bootstrap.runtime.composite_control_plane_bundle import (
    CompositeControlPlaneBundle,
)
from bioetl.composition.bootstrap.runtime.composite_runtime_management_builder import (
    _create_checkpoint_manager,
)
from bioetl.domain.control_plane import RunInputSnapshotRef, RunManifest, RunSourceRef
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from bioetl.domain.types import RunID, RunType
from tests.helpers.clock import FixedClock

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_composite_successors_rebind_checkpoint_save_and_replay(
    tmp_path, monkeypatch
):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    run_id = RunID(UUID(int=12014))
    occurrence_names = []

    def occurrence_id(name):
        occurrence_names.append(name)
        return f"{name}-{len(occurrence_names)}"

    monkeypatch.setattr(subject, "create_runtime_occurrence_id", occurrence_id)
    service = subject.build_run_ledger_service(
        manifest_id="original",
        ledger_enabled=True,
        infra_context=SimpleNamespace(
            settings=SimpleNamespace(data_dir=str(tmp_path)),
            metrics=None,
            run_id=str(run_id),
            clock=FixedClock(now),
        ),
        pipeline_name="composite_publication",
        resolved_config_hash="",
        effective_config_hash="",
        dq_contract_compatibility_hash="",
        effective_config_artifact_id="",
        contract_ref="publication",
        contract_version="1",
    )
    assert service is not None
    assert service.manifest_port is not None
    original = RunManifest(
        manifest_id="original",
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="composite_publication",
        provider="composite",
        entity="publication",
        source_refs=(
            RunSourceRef(
                provider="pubmed",
                entity="publication",
                pipeline_name="pubmed_publication",
            ),
        ),
    )
    service.manifest_port.save(original)
    original_entry = service.record_manifest_created(original)
    storage = MagicMock()
    checkpoint = _create_checkpoint_manager(
        config=SimpleNamespace(name=original.pipeline_name, version="1"),
        runtime=CompositeRuntimeConfig(),
        run_id=str(run_id),
        logger=MagicMock(),
        checkpoint_storage=storage,
        checkpoint_manager_cls=CompositeCheckpointService,
        metrics=None,
        checkpoint_clock=FixedClock(now),
        control_plane_bundle=CompositeControlPlaneBundle(
            manifest_id=original.manifest_id,
            run_ledger_service=service,
            effective_config_hash="a" * 64,
        ),
    )
    storage.list_glob.return_value = []
    state = replace(await checkpoint.load(), last_event_id=original_entry.entry_id)
    snapshot = RunInputSnapshotRef(
        snapshot_id="snapshot",
        content_hash="sha256:input",
        immutable_uri="file:///bronze/input",
    )
    for index in range(2):
        successor = persist_input_snapshots_on_manifest(
            service,
            snapshots=(replace(snapshot, snapshot_id=f"snapshot-{index}"),),
            provider="pubmed",
            entity="publication",
            pipeline_name="pubmed_publication",
        )
        assert successor is not None
    assert occurrence_names.count("composite_run_manifest") == 2
    assert service.manifest_port.get("original") == original
    assert (
        service.manifest_id == checkpoint.expected_manifest_id == successor.manifest_id
    )
    assert len(successor.source_refs[0].input_snapshots) == 2
    successor_entry = service.record_run_started()
    assert service.ledger_port.list_entries(successor.manifest_id)[0].occurred_at == now

    await checkpoint.save(state)
    saved = json.loads(storage.write_atomic.call_args.args[1])
    assert saved["manifest_id"] == successor.manifest_id
    assert saved["execution_fingerprint"] == successor.execution_fingerprint
    assert saved[
        "input_snapshot_fingerprint"
    ] == compute_input_snapshot_identity_fingerprint(
        successor.source_refs[0].input_snapshots
    )
    assert state.manifest_id == "original"
    # Replay a state created before either publication using the successor ledger.
    replayed = checkpoint._load_service._replay_checkpoint_suffix(state)
    assert replayed.manifest_id == successor.manifest_id
    assert replayed.last_event_id == successor_entry.entry_id
