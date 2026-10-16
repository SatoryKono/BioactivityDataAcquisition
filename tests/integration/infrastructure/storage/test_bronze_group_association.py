"""Writer-produced content association on synthetic temporary Bronze roots."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze import cleanup_group_journal as journal
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

pytestmark = pytest.mark.integration

BATCH = "11111111-1111-4111-8111-111111111111"


@pytest.mark.asyncio
@pytest.mark.parametrize("save_json", [False, True])
@pytest.mark.parametrize("flat_structure", [False, True])
async def test_writer_attests_exact_payload_and_optional_copy(
    tmp_path: Path, save_json: bool, flat_structure: bool
) -> None:
    writer = BronzeWriter(
        base_path=tmp_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        json_export=(save_json, None),
        flat_structure=flat_structure,
    )
    arguments = {
        "provider": "chembl",
        "entity": "activity",
        "date": datetime(2024, 1, 1, tzinfo=UTC),
        "batch_id": BatchID(UUID(BATCH)),
        "run_id": RunID(UUID("22222222-2222-4222-8222-222222222222")),
        "run_type": RunType.INCREMENTAL,
        "ingestion_ts": datetime(2024, 1, 1, tzinfo=UTC),
    }
    result = await writer.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
    payload = tmp_path / result.relative_path
    sidecar = Path(f"{payload}.meta.json")
    metadata = json.loads(sidecar.read_bytes())
    association = metadata["cleanup_association"]
    assert (
        association["payload_sha256"]
        == hashlib.sha256(payload.read_bytes()).hexdigest()
    )
    copy = payload.with_suffix("")
    assert association["copy_sha256"] == (
        hashlib.sha256(copy.read_bytes()).hexdigest() if save_json else None
    )
    original = sidecar.read_bytes()
    await writer.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
    assert sidecar.read_bytes() == original
    toggled = BronzeWriter(
        base_path=tmp_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        json_export=(not save_json, None),
        flat_structure=flat_structure,
    )
    await toggled.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
    assert sidecar.read_bytes() == original
    assert copy.exists() is save_json
    spec = journal.GroupSpec(
        "chembl", "activity", "2024-01-01", BATCH, "2024-01-02", flat_structure
    )
    members = {"payload": {"sha256": hashlib.sha256(payload.read_bytes()).hexdigest()}}
    if save_json:
        members["copy"] = {"sha256": hashlib.sha256(copy.read_bytes()).hexdigest()}
    journal._validate_association(metadata, spec, members)
    # Legacy retries remain valid; they do not acquire cleanup ownership.
    del metadata["cleanup_association"]
    legacy = json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()
    sidecar.write_bytes(legacy)
    await writer.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
    assert sidecar.read_bytes() == legacy


@pytest.mark.parametrize(
    "mutation", ["legacy", "payload", "copy", "scope", "schema", "digest"]
)
def test_association_rejects_unattested_or_foreign_content(mutation: str) -> None:
    spec = journal.GroupSpec("chembl", "activity", "2024-01-01", BATCH, "2024-01-02")
    metadata = {
        "provider": "chembl",
        "entity": "activity",
        "batch_id": BATCH,
        "cleanup_association": {
            "schema": 1,
            "payload_sha256": "a" * 64,
            "copy_sha256": "b" * 64,
        },
    }
    members = {"payload": {"sha256": "a" * 64}, "copy": {"sha256": "b" * 64}}
    journal._validate_association(metadata, spec, members)
    if mutation == "legacy":
        del metadata["cleanup_association"]
    elif mutation == "scope":
        metadata["provider"] = "foreign"
    elif mutation == "schema":
        metadata["cleanup_association"]["schema"] = True
    elif mutation == "digest":
        del members["copy"]
        metadata["cleanup_association"]["copy_sha256"] = "invalid"
    else:
        members[mutation]["sha256"] = "c" * 64
    with pytest.raises(journal.GroupJournalConflict, match="unassociated"):
        journal._validate_association(metadata, spec, members)


@pytest.mark.asyncio
@pytest.mark.parametrize("existing_lock", [False, True])
async def test_cleanup_preview_with_cold_cache_never_mutates_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing_lock: bool
) -> None:
    import os

    from bioetl.infrastructure.storage.bronze import cleanup_core

    if not cleanup_core._platform_cleanup_supported():
        pytest.skip("POSIX pinned directory/flock capability unavailable")
    writer = BronzeWriter(
        base_path=tmp_path, logger=NoOpLogger(), metrics=NoOpMetrics()
    )
    lock = tmp_path / ".bronze-cleanup.lock"
    if existing_lock:
        lock.touch()
    before = sorted(path.name for path in tmp_path.iterdir())
    monkeypatch.setattr(cleanup_core, "_DIR_XATTR_BY_DEV", {})

    def forbidden(*args, **kwargs):
        pytest.fail("dry-run attempted a filesystem mutation")

    with monkeypatch.context() as preview:
        for name in ("mkdir", "rmdir", "unlink", "remove", "setxattr", "removexattr"):
            preview.setattr(os, name, forbidden)
        original_open = os.open

        def readonly_open(path, flags, *args, **kwargs):
            assert not flags & (os.O_CREAT | os.O_TRUNC)
            return original_open(path, flags, *args, **kwargs)

        preview.setattr(os, "open", readonly_open)
        await writer.cleanup_old_files(datetime(2025, 1, 1, tzinfo=UTC), dry_run=True)
    assert sorted(path.name for path in tmp_path.iterdir()) == before
    assert cleanup_core._DIR_XATTR_BY_DEV == {}
    probes = []
    original_probe = cleanup_core._run_directory_xattr_probe

    def record_probe(parent, device):
        probes.append((parent, device))
        return original_probe(parent, device)

    monkeypatch.setattr(cleanup_core, "_run_directory_xattr_probe", record_probe)
    try:
        await writer.cleanup_old_files(datetime(2025, 1, 1, tzinfo=UTC), dry_run=False)
    except NotImplementedError:
        assert cleanup_core._DIR_XATTR_BY_DEV[tmp_path.stat().st_dev] is False
        assert sorted(path.name for path in tmp_path.iterdir()) == before
    else:
        assert cleanup_core._DIR_XATTR_BY_DEV[tmp_path.stat().st_dev] is True
        assert lock.exists()
    assert probes == [(str(tmp_path), tmp_path.stat().st_dev)]
    assert not list(tmp_path.glob("bioetl-xattr-probe-*"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", ["copy_write", "digest", "foreign_copy", "sidecar_write"]
)
async def test_retry_preserves_attestation_and_foreign_bytes_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from bioetl.infrastructure.storage.bronze import write_execution

    writer = BronzeWriter(
        base_path=tmp_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        json_export=(True, None),
    )
    arguments = {
        "provider": "chembl",
        "entity": "activity",
        "date": datetime(2024, 1, 1, tzinfo=UTC),
        "batch_id": BatchID(UUID(BATCH)),
        "run_id": RunID(UUID("22222222-2222-4222-8222-222222222222")),
        "run_type": RunType.INCREMENTAL,
        "ingestion_ts": datetime(2024, 1, 1, tzinfo=UTC),
    }
    if failure in {"copy_write", "sidecar_write"}:

        def fail(*args, **kwargs):
            raise OSError("injected partial write")

        async def fail_copy(*args, **kwargs):
            fail()

        with monkeypatch.context() as fault:
            if failure == "copy_write":
                fault.setattr(BronzeWriter, "_write_json_copy", fail_copy)
            else:
                fault.setattr(write_execution, "write_bytes_if_absent_or_same", fail)
            with pytest.raises(OSError, match="injected partial write"):
                await writer.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
        assert len(list(tmp_path.rglob("*.jsonl.zst"))) == 1
        assert not list(tmp_path.rglob("*.jsonl"))
    result = await writer.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
    payload = tmp_path / result.relative_path
    sidecar = Path(f"{payload}.meta.json")
    copy = payload.with_suffix("")
    if failure == "digest":
        metadata = json.loads(sidecar.read_bytes())
        metadata["cleanup_association"]["copy_sha256"] = "a" * 64
        sidecar.write_text(json.dumps(metadata, sort_keys=True, separators=(",", ":")))
    elif failure == "foreign_copy":
        copy.write_bytes(b"foreign data must survive")
    before = {path: path.read_bytes() for path in (payload, sidecar, copy)}
    if failure in {"digest", "foreign_copy"}:
        with pytest.raises((OSError, ValueError)):
            await writer.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
    else:
        await writer.write_bronze(records=iter([b'{"id":1}\n']), **arguments)
        journal._validate_association(
            json.loads(sidecar.read_bytes()),
            journal.GroupSpec("chembl", "activity", "2024-01-01", BATCH, "2024-01-02"),
            {
                "payload": {"sha256": hashlib.sha256(payload.read_bytes()).hexdigest()},
                "copy": {"sha256": hashlib.sha256(copy.read_bytes()).hexdigest()},
            },
        )
    assert {path: path.read_bytes() for path in before} == before


def test_readonly_journal_cannot_begin_or_recover_without_volume_capability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bioetl.infrastructure.storage.bronze import cleanup_core

    if not cleanup_core._platform_cleanup_supported():
        pytest.skip("POSIX pinned directory/flock capability unavailable")
    monkeypatch.setattr(cleanup_core, "_DIR_XATTR_BY_DEV", {})
    with cleanup_core.bronze_tree_lock(
        tmp_path, exclusive=False, create_lock=False
    ) as lease:
        group = journal.GroupJournal(lease)
        assert cleanup_core._DIR_XATTR_BY_DEV == {}
        roots = []

        def unsupported(root):
            roots.append(root)
            return False

        monkeypatch.setattr(journal, "destructive_cleanup_supported", unsupported)
        with pytest.raises(NotImplementedError, match="target-volume"):
            group.begin(
                journal.GroupSpec(
                    "chembl", "activity", "2024-01-01", BATCH, "2024-01-02"
                )
            )
        with pytest.raises(NotImplementedError, match="target-volume"):
            group.recover_with_result("1" * 32)
        assert roots == [tmp_path, tmp_path]
    assert list(tmp_path.iterdir()) == []
