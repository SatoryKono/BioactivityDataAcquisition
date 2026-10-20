"""Successor semantics for Bronze snapshot attach (#12006 / #12014).

Attach must not rewrite a persisted manifest in place: it creates a
successor manifest (new ``manifest_id``, ``predecessor_manifest_id``
pointing at the previous one) and recomputes ``execution_fingerprint``
after the source-ref merge, so a replay-equivalent pair keeps equal
fingerprints instead of degrading to ``semantic_drift``.
"""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from uuid import UUID

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.services.control_plane.ledger._input_snapshot_manifest import (
    persist_input_snapshots_on_manifest,
)
from bioetl.domain.config.runtime import (
    CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE,
)
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunInputSnapshotRef,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.control_plane.execution_identity import (
    build_execution_identity_payload_from_code_provenance,
)
from bioetl.domain.normalization import (
    compute_execution_identity_fingerprint,
    compute_input_snapshot_identity_fingerprint,
)
from bioetl.domain.types import RunID, RunType

_RUN_ID = RunID(UUID(int=12006))
_SNAPSHOT = RunInputSnapshotRef(
    snapshot_id="snap-1",
    content_hash="sha256:snap-1",
    immutable_uri="file:///bronze/chembl/activity/batch_1.jsonl.zst",
    storage_provider="s3",
    object_bucket="bioetl-bronze",
    object_key="chembl/activity/batch_1.jsonl.zst",
    object_version_id="snapshot-version-1",
)
_SECOND_SNAPSHOT = RunInputSnapshotRef(
    snapshot_id="snap-2",
    content_hash="sha256:snap-2",
    immutable_uri="file:///bronze/chembl/activity/batch_2.jsonl.zst",
    storage_provider="s3",
    object_bucket="bioetl-bronze",
    object_key="chembl/activity/batch_2.jsonl.zst",
    object_version_id="snapshot-version-2",
)


def _creation_fingerprint(
    manifest: RunManifest,
    snapshots: tuple[RunInputSnapshotRef, ...],
) -> str:
    """Mirror the manifest-service creation fingerprint for one manifest."""
    payload = build_execution_identity_payload_from_code_provenance(
        pipeline_name=manifest.pipeline_name,
        run_type=manifest.run_type.value,
        code_provenance=manifest.code_provenance,
        exact_replay=bool(manifest.launch_context.get("exact_replay")),
        input_snapshot_fingerprint=compute_input_snapshot_identity_fingerprint(
            snapshots
        ),
        silver_filter_compatibility_mode=str(
            manifest.runtime_config.get(
                "silver_filter_compatibility_mode",
                CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE,
            )
        ),
    )
    return compute_execution_identity_fingerprint(payload)


def _original_manifest(
    *,
    runtime_config: dict[str, object] | None = None,
) -> RunManifest:
    """Build the pre-attach manifest the way manifest creation persists it."""
    manifest = RunManifest(
        manifest_id="m1",
        run_id=_RUN_ID,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        runtime_config=runtime_config or {},
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
            ),
        ),
        replay_capability=ReplayCapability.REBUILD_ONLY,
    )
    return replace(
        manifest,
        execution_fingerprint=_creation_fingerprint(manifest, ()),
    )


class _MemoryManifestPort:
    """Port double that enforces the successor index rule without infrastructure."""

    def __init__(self) -> None:
        self._items: dict[str, RunManifest] = {}
        self._by_run: dict[RunID, str] = {}

    def get(self, manifest_id: str) -> RunManifest | None:
        return self._items.get(manifest_id)

    def save(self, manifest: RunManifest) -> None:
        current_id = self._by_run.get(manifest.run_id)
        if (
            current_id is not None
            and current_id != manifest.manifest_id
            and manifest.predecessor_manifest_id != current_id
        ):
            raise ValueError(
                f"run_id is already mapped to a different manifest_id: {current_id}"
            )
        self._items[manifest.manifest_id] = manifest
        self._by_run[manifest.run_id] = manifest.manifest_id

    def get_by_run_id(self, run_id: RunID) -> RunManifest | None:
        manifest_id = self._by_run.get(run_id)
        if manifest_id is None:
            return None
        return self._items.get(manifest_id)

    def list_all(self) -> tuple[RunManifest, ...]:
        return tuple(self._items.values())

    def restore_predecessor_publication(
        self,
        predecessor: RunManifest,
        successor_manifest_id: str,
    ) -> None:
        self._items.pop(successor_manifest_id, None)
        if self._by_run.get(predecessor.run_id) == successor_manifest_id:
            self._by_run[predecessor.run_id] = predecessor.manifest_id


def _service(
    store: _MemoryManifestPort,
    *,
    manifest_id: str = "m1",
    next_id: str | None = "m2",
) -> SimpleNamespace:
    factory = (lambda: next_id) if next_id is not None else None
    return SimpleNamespace(
        manifest_port=store,
        manifest_id=manifest_id,
        _manifest_id_factory=factory,
    )


def _attach(
    service: SimpleNamespace,
    snapshot: RunInputSnapshotRef = _SNAPSHOT,
) -> RunManifest | None:
    return persist_input_snapshots_on_manifest(
        service,  # type: ignore[arg-type]
        snapshots=(snapshot,),
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
    )


def test_attach_creates_successor_with_predecessor_link() -> None:
    store = _MemoryManifestPort()
    original = _original_manifest()
    store.save(original)

    service = _service(store)
    successor = _attach(service)

    assert successor is not None
    assert service.manifest_id == "m2"
    assert successor.manifest_id == "m2"
    assert successor.predecessor_manifest_id == "m1"
    assert successor.source_refs[0].input_snapshots == (_SNAPSHOT,)
    assert successor.replay_capability is ReplayCapability.EXACT_REPLAY_SUPPORTED
    assert store.get("m2") == successor
    current = store.get_by_run_id(_RUN_ID)
    assert current is not None
    assert current.manifest_id == "m2"


def test_attach_leaves_original_manifest_immutable() -> None:
    store = _MemoryManifestPort()
    original = _original_manifest()
    store.save(original)

    _attach(_service(store))

    persisted_original = store.get("m1")
    assert persisted_original == original
    assert persisted_original is not None
    assert persisted_original.source_refs[0].input_snapshots == ()
    assert persisted_original.predecessor_manifest_id is None


def test_attach_recomputed_fingerprint_matches_creation_with_snapshots() -> None:
    """Equivalent pair: attach-after-create == create-with-snapshots (#12006)."""
    store = _MemoryManifestPort()
    original = _original_manifest()
    store.save(original)
    pre_merge_fingerprint = original.execution_fingerprint

    successor = _attach(_service(store))

    assert successor is not None
    expected = _creation_fingerprint(original, (_SNAPSHOT,))
    assert successor.execution_fingerprint == expected
    assert successor.execution_fingerprint != pre_merge_fingerprint


def test_attach_recomputed_fingerprint_with_explicit_compat_mode() -> None:
    store = _MemoryManifestPort()
    original = _original_manifest(
        runtime_config={
            "silver_filter_compatibility_mode": (
                CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE
            ),
        },
    )
    store.save(original)

    successor = _attach(_service(store))

    assert successor is not None
    assert successor.execution_fingerprint == _creation_fingerprint(
        original, (_SNAPSHOT,)
    )


def test_second_attach_on_the_same_service_extends_chain() -> None:
    store = _MemoryManifestPort()
    store.save(_original_manifest())
    ids = iter(("m2", "m3"))
    service = _service(store)
    service._manifest_id_factory = lambda: next(ids)

    first = _attach(service)
    assert first is not None
    assert service.manifest_id == "m2"
    second = _attach(service, snapshot=_SECOND_SNAPSHOT)

    assert second is not None
    assert second.manifest_id == "m3"
    assert second.predecessor_manifest_id == "m2"
    persisted_first = store.get("m2")
    assert persisted_first is not None
    assert persisted_first.predecessor_manifest_id == "m1"
    assert persisted_first.source_refs[0].input_snapshots == (_SNAPSHOT,)
    snapshot_ids = {
        snap.snapshot_id for ref in second.source_refs for snap in ref.input_snapshots
    }
    assert snapshot_ids == {"snap-1", "snap-2"}
    current = store.get_by_run_id(_RUN_ID)
    assert current is not None
    assert current.manifest_id == "m3"
    assert {item.manifest_id for item in store.list_all()} == {"m1", "m2", "m3"}


def test_attach_without_factory_returns_none_and_keeps_manifest() -> None:
    store = _MemoryManifestPort()
    original = _original_manifest()
    store.save(original)

    result = _attach(_service(store, next_id=None))

    assert result is None
    current = store.get_by_run_id(_RUN_ID)
    assert current is not None
    assert current.manifest_id == "m1"
    assert store.get("m2") is None


def test_attach_rebinds_ledger_then_advances_service_manifest_id() -> None:
    store = _MemoryManifestPort()
    store.save(_original_manifest())
    calls: list[dict[str, object]] = []

    class _Ledger:
        def record_manifest_successor(self, **kwargs: object) -> None:
            calls.append(kwargs)

    service = _service(store)
    service.ledger_port = _Ledger()

    successor = _attach(service)

    assert successor is not None
    assert service.manifest_id == "m2"
    assert calls == [
        {
            "run_id": _RUN_ID,
            "predecessor_manifest_id": "m1",
            "successor_manifest_id": "m2",
        }
    ]


def test_attach_rebind_failure_restores_predecessor_and_keeps_service_id() -> None:
    store = _MemoryManifestPort()
    store.save(_original_manifest())

    class _Ledger:
        def record_manifest_successor(self, **kwargs: object) -> None:
            raise RuntimeError("injected rebind failure")

    service = _service(store)
    service.ledger_port = _Ledger()
    with pytest.raises(RuntimeError, match="injected rebind failure"):
        _attach(service)

    assert service.manifest_id == "m1"
    assert store.get("m2") is None
    current = store.get_by_run_id(_RUN_ID)
    assert current is not None
    assert current.manifest_id == "m1"


def test_attach_restore_failure_chains_the_rebind_error() -> None:
    store = _MemoryManifestPort()
    store.save(_original_manifest())

    class _Ledger:
        def record_manifest_successor(self, **kwargs: object) -> None:
            raise RuntimeError("injected rebind failure")

    def _fail_restore(predecessor: RunManifest, successor_manifest_id: str) -> None:
        raise RuntimeError("injected restore failure")

    store.restore_predecessor_publication = _fail_restore  # type: ignore[method-assign]
    service = _service(store)
    service.ledger_port = _Ledger()
    with pytest.raises(RuntimeError, match="injected restore failure") as caught:
        _attach(service)

    assert isinstance(caught.value.__cause__, RuntimeError)
    assert "injected rebind failure" in str(caught.value.__cause__)
    assert service.manifest_id == "m1"


def test_attach_failure_keeps_original_manifest_current() -> None:
    store = _MemoryManifestPort()
    original = _original_manifest()
    store.save(original)

    class _FailingSavePort:
        def get(self, manifest_id: str) -> RunManifest | None:
            return store.get(manifest_id)

        def save(self, manifest: RunManifest) -> None:
            raise RuntimeError("injected save failure")

    service = SimpleNamespace(
        manifest_port=_FailingSavePort(),
        manifest_id="m1",
        _manifest_id_factory=lambda: "m2",
    )
    with pytest.raises(RuntimeError, match="injected save failure"):
        _attach(service)

    current = store.get_by_run_id(_RUN_ID)
    assert current is not None
    assert current.manifest_id == "m1"
    assert current == original
    assert store.get("m2") is None
