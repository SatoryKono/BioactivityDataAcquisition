"""Explicit Bronze cache paths must survive persisted-manifest verification."""

from hashlib import sha256
from types import SimpleNamespace

import pytest

from bioetl.composition.runtime_builders._run_manifest_refs import build_run_source_refs
from bioetl.domain.context import CachedBronzeContext
from bioetl.infrastructure.control_plane.replay_object_verifier import (
    ReplayObjectVerifier,
)

pytestmark = pytest.mark.unit


def test_exact_replay_custom_cache_persists_resolvable_snapshot_uri(tmp_path):
    cache = tmp_path / "staged input"
    cache.mkdir()
    batch = cache / "batch_000000.jsonl.zst"
    batch.write_bytes(b"captured batch")
    settings = SimpleNamespace(bronze_path=tmp_path / "default-bronze")
    refs = build_run_source_refs(
        ctx=SimpleNamespace(exact_replay=True, pipeline_name="chembl_activity"),
        cached_bronze=CachedBronzeContext.from_options(path=str(cache)),
        settings=settings,
        provider="chembl",
        entity="activity",
    )
    snapshot = refs[0].input_snapshots[0]
    assert snapshot.immutable_uri == batch.as_uri()
    assert snapshot.content_hash == sha256(batch.read_bytes()).hexdigest()
    verifier = ReplayObjectVerifier(tmp_path, tmp_path, settings.bronze_path)
    manifest = SimpleNamespace(source_refs=refs)
    assert verifier._snapshots(manifest) is True
    batch.write_bytes(b"changed input")
    assert verifier._snapshots(manifest) is False
