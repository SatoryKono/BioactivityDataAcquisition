"""Unit tests for checkpoint metadata composition helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from bioetl.composition.factories.pipeline.checkpoint_metadata_helpers import (
    build_current_checkpoint_metadata,
)
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.types import RunType
from bioetl.domain.value_objects.run_context import RunContext


def test_build_current_checkpoint_metadata_includes_resume_anchors(tmp_path) -> None:
    """Current checkpoint metadata should include manifest, contract, and snapshots."""
    bronze_root = tmp_path / "bronze-cache"
    bronze_root.mkdir()
    (bronze_root / "batch_0001.jsonl.zst").write_bytes(b'{"id":1}\n')
    (bronze_root / "batch_0002.jsonl.zst").write_bytes(b'{"id":2}\n')

    run_context = RunContext.create(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        started_at=datetime.now(UTC),
        provider="chembl",
        entity="activity",
        pipeline_version="1.2.3",
        config_hash="a" * 64,
        manifest_id="manifest-1",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        dq_contract_compatibility_hash="dq-hash",
        effective_config_artifact_id="artifact-1",
    )
    pipeline = SimpleNamespace(
        config=SimpleNamespace(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
        ),
        runtime=SimpleNamespace(
            run_type=RunType.INCREMENTAL,
            exact_replay=True,
            cached_bronze=CachedBronzeContext.from_options(path=str(bronze_root)),
        ),
        services=SimpleNamespace(
            metadata_coordinator=SimpleNamespace(run_context=run_context)
        ),
    )

    metadata = build_current_checkpoint_metadata(pipeline)

    assert metadata.manifest_id == "manifest-1"
    assert metadata.contract_ref == "chembl.activity"
    assert metadata.contract_version == "1.0.0"
    assert metadata.exact_replay is True
    assert len(metadata.input_snapshot_ids) == 2
    assert metadata.input_snapshot_ids == tuple(sorted(metadata.input_snapshot_ids))
    assert metadata.execution_fingerprint is not None
