"""Synthetic-only fault injection for the opt-in Bronze group journal."""

from __future__ import annotations

import errno
import json
import hashlib
import os
import platform
import select
import subprocess
import sys
from pathlib import Path

import pytest

from bioetl.infrastructure.storage.bronze import cleanup_group_journal as journal
from bioetl.infrastructure.storage.bronze import cleanup_group_records as records


pytestmark = pytest.mark.integration

DATE = "2024-01-01"
CUTOFF = "2024-01-02"
BATCH = "11111111-1111-4111-8111-111111111111"
POSIX_ONLY = pytest.mark.skipif(
    not journal.destructive_cleanup_supported(),
    reason="POSIX pinned directory and flock capability unavailable",
)


@pytest.fixture(scope="module", autouse=True)
def journal_execution_environment(tmp_path_factory, record_testsuite_property) -> None:
    """Record the actual checkout and temp mount; never infer POSIX from a job label."""
    repo = Path(__file__).resolve().parents[4]
    module = Path(journal.__file__).resolve()
    assert module.is_relative_to(repo / "src"), "journal imported from another checkout"
    temp = tmp_path_factory.mktemp("fs001-journal-environment").resolve()
    environment = {
        "os": platform.platform(),
        "python": sys.version,
        "module": str(module),
        "journal_sha256": hashlib.sha256(module.read_bytes()).hexdigest(),
        "journal_components_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(module.parent.glob("cleanup_group_*.py"))
        },
        "uid": os.geteuid() if hasattr(os, "geteuid") else None,
        "temp_device": temp.stat().st_dev,
        "destructive_supported": journal.destructive_cleanup_supported(),
        "mount": None,
        "capabilities": None,
        "directory_xattr_fd": None,
    }
    if sys.platform.startswith("linux"):
        probe_fd = os.open(temp, journal._DIR_FLAGS)
        try:
            probe_tag = "user.bioetl.fs001-probe"
            os.setxattr(probe_fd, probe_tag, b"probe", flags=os.XATTR_CREATE)
            os.fsync(probe_fd)
            environment["directory_xattr_fd"] = (
                os.getxattr(probe_fd, probe_tag) == b"probe"
            )
            os.removexattr(probe_fd, probe_tag)
            os.fsync(probe_fd)
        except OSError as exc:
            environment["directory_xattr_fd"] = {"supported": False, "errno": exc.errno}
        finally:
            os.close(probe_fd)
        mounts = []
        for line in Path("/proc/self/mountinfo").read_text().splitlines():
            fields = line.split()
            mountpoint = fields[4]
            for escaped, decoded in (
                (r"\040", " "),
                (r"\011", "\t"),
                (r"\012", "\n"),
                (r"\134", "\\"),
            ):
                mountpoint = mountpoint.replace(escaped, decoded)
            if temp.is_relative_to(Path(mountpoint)):
                separator = fields.index("-")
                mounts.append(
                    (
                        len(mountpoint),
                        {
                            "target": mountpoint,
                            "options": fields[5],
                            "filesystem": fields[separator + 1],
                            "super_options": fields[separator + 3],
                        },
                    )
                )
        environment["mount"] = max(mounts, key=lambda item: item[0])[1]
        environment["capabilities"] = [
            line
            for line in Path("/proc/self/status").read_text().splitlines()
            if line.startswith(("CapEff:", "CapBnd:"))
        ]
    record_testsuite_property(
        "FS001_ENVIRONMENT", json.dumps(environment, sort_keys=True)
    )


def _fixture(
    tmp_path: Path, *, copy: bool = False
) -> tuple[Path, journal.GroupSpec, Path]:
    root = tmp_path / "bronze"
    date_dir = root / "chembl" / "activity" / DATE
    date_dir.mkdir(parents=True)
    spec = journal.GroupSpec("chembl", "activity", DATE, BATCH, CUTOFF)
    names = spec.names()
    (date_dir / names["payload"]).write_bytes(b"payload\n")
    (date_dir / names["sidecar"]).write_text(
        json.dumps(
            {
                "provider": "chembl",
                "entity": "activity",
                "batch_id": BATCH,
                "cleanup_association": {
                    "schema": 1,
                    "payload_sha256": hashlib.sha256(b"payload\n").hexdigest(),
                    "copy_sha256": hashlib.sha256(b"copy\n").hexdigest()
                    if copy
                    else None,
                },
            }
        ),
        encoding="utf-8",
    )
    if copy:
        (date_dir / names["copy"]).write_bytes(b"copy\n")
    return root, spec, date_dir


def _body() -> dict[str, object]:
    spec = journal.GroupSpec("chembl", "activity", DATE, BATCH, CUTOFF)
    identity = {"dev": 1, "ino": 2, "size": 3, "sha256": "a" * 64}
    return {
        "schema": 4,
        "operation_id": "1" * 32,
        "state": "prepared",
        "scope": {
            "provider": spec.provider,
            "entity": spec.entity,
            "date": spec.date,
            "batch_id": spec.batch_id,
            "cutoff": spec.cutoff,
            "flat_structure": False,
        },
        "relative_date": spec.relative_date().as_posix(),
        "root": [1, 2],
        "chain": [[1, 2], [1, 3], [1, 4], [1, 5]],
        "names": spec.names(),
        "members": {"payload": identity, "sidecar": identity},
        "staged": [],
        "removed": [],
        "stage": {"dev": 1, "ino": 6, "token": "1" * 32},
    }


def _public_writer(root: Path):
    from bioetl.domain.ports.noop import NoOpMetrics
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

    return BronzeWriter(base_path=root, logger=NoOpLogger(), metrics=NoOpMetrics())


@POSIX_ONLY
@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["legacy", "payload", "copy"])
async def test_public_cleanup_preserves_unattested_group(tmp_path: Path, mutation: str):
    from datetime import datetime

    root, spec, date = _fixture(tmp_path, copy=True)
    names = spec.names()
    if mutation == "legacy":
        (date / names["sidecar"]).write_text("{}")
    else:
        (date / names[mutation]).write_bytes(b"foreign")
    original = {p.name: p.read_bytes() for p in date.iterdir()}
    result = await _public_writer(root).cleanup_old_files(
        datetime.fromisoformat(CUTOFF)
    )
    assert result["files_removed"] == 0
    assert result["files_conflicted"] == 3
    assert {p.name: p.read_bytes() for p in date.iterdir()} == original


@POSIX_ONLY
@pytest.mark.asyncio
async def test_public_cleanup_retries_late_failure_without_widening_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from datetime import datetime

    root, spec, date = _fixture(tmp_path)
    original_unlink = os.unlink
    injected = False

    def fail_once(name, *args, **kwargs):
        nonlocal injected
        if name == "sidecar" and not injected:
            injected = True
            raise OSError("transient sidecar unlink")
        return original_unlink(name, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", fail_once)
    writer = _public_writer(root)
    cutoff = datetime.fromisoformat(CUTOFF)
    first = await writer.cleanup_old_files(cutoff)
    assert first["files_removed"] == 1
    assert first["bytes_freed"] == len(b"payload\n")
    assert first["files_failed"] == 1
    assert date.exists()
    refused = await writer.cleanup_old_files(cutoff, provider="openalex")
    assert refused["files_removed"] == 0
    assert refused["directories_skipped"] == 1
    second = await writer.cleanup_old_files(
        cutoff, provider=spec.provider, entity=spec.entity
    )
    assert second["files_planned"] == second["files_removed"] == 1
    assert second["files_failed"] == 0
    assert not date.exists()


@POSIX_ONLY
def test_begin_rejects_new_attested_inode_after_plan(tmp_path: Path):
    root, spec, date = _fixture(tmp_path)
    expected = {p.name: p.stat() for p in date.iterdir()}
    date_identity = date.stat()
    payload = date / spec.names()["payload"]
    payload.unlink()
    payload.write_bytes(b"payload\n")
    with journal.open_group_journal(root) as operation:
        with pytest.raises(
            journal.GroupJournalConflict, match="planned group member changed"
        ):
            operation.begin(
                spec, expected_members=expected, expected_date=date_identity
            )
    assert payload.exists()


@POSIX_ONLY
@pytest.mark.parametrize("barrier", ["root_fsync", "stage_fsync", "setxattr"])
def test_stage_setup_failure_is_retryable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, barrier: str
) -> None:
    root, spec, date = _fixture(tmp_path)
    original_fsync, original_setxattr = os.fsync, os.setxattr
    with journal.open_group_journal(root) as group:
        operation = group.begin(spec)
        stage = root / f".bronze-group-stage-{operation}"
        failed = False

        def fsync(fd: int) -> None:
            nonlocal failed
            if (
                stage.exists()
                and not failed
                and (
                    (barrier == "root_fsync" and fd == group._root_fd)
                    or (barrier == "stage_fsync" and fd != group._root_fd)
                )
            ):
                failed = True
                raise OSError("transient stage setup")
            original_fsync(fd)

        def setxattr(*args, **kwargs) -> None:
            nonlocal failed
            if barrier == "setxattr" and not failed:
                failed = True
                raise OSError("transient xattr")
            original_setxattr(*args, **kwargs)

        monkeypatch.setattr(os, "fsync", fsync)
        monkeypatch.setattr(os, "setxattr", setxattr)
        with pytest.raises(journal.GroupJournalFailure):
            group.recover(operation)
        assert failed and not stage.exists()
        assert (date / spec.names()["payload"]).read_bytes() == b"payload\n"
        assert group.recover(operation) == 2


@POSIX_ONLY
def test_stage_setup_failure_preserves_substituted_directory(tmp_path: Path) -> None:
    root, spec, _date = _fixture(tmp_path)
    with journal.open_group_journal(root) as group:
        operation = group.begin(spec)
        stage = root / f".bronze-group-stage-{operation}"

        def substitute(phase: str) -> None:
            if phase == "after_stage_create":
                stage.rename(tmp_path / "held-original-stage")
                stage.mkdir(mode=0o700)
                (stage / "foreign").write_bytes(b"preserve")
                raise OSError("setup interrupted")

        with pytest.raises(journal.GroupJournalConflict, match="substituted"):
            group.recover(operation, substitute)
        assert (stage / "foreign").read_bytes() == b"preserve"


@pytest.mark.parametrize(
    "date,batch,cutoff",
    [
        ("2026-1-1", BATCH, CUTOFF),
        ("2026-02-29", BATCH, "2026-03-01"),
        ("2024-01-02", BATCH, CUTOFF),
        (DATE, "not-a-batch", CUTOFF),
    ],
)
def test_spec_rejects_invalid_or_ineligible_group(
    date: str, batch: str, cutoff: str
) -> None:
    with pytest.raises(ValueError):
        journal.GroupSpec("chembl", "activity", date, batch, cutoff).names()


@POSIX_ONLY
@pytest.mark.parametrize("mutation", ["legacy", "payload", "copy"])
def test_begin_does_not_adopt_unattested_group(tmp_path: Path, mutation: str) -> None:
    root, spec, date_dir = _fixture(tmp_path, copy=True)
    if mutation == "legacy":
        sidecar = date_dir / spec.names()["sidecar"]
        metadata = json.loads(sidecar.read_bytes())
        del metadata["cleanup_association"]
        sidecar.write_text(json.dumps(metadata), encoding="utf-8")
    else:
        (date_dir / spec.names()[mutation]).write_bytes(b"foreign replacement")
    original = {name: (date_dir / name).read_bytes() for name in spec.names().values()}
    with journal.open_group_journal(root) as group:
        with pytest.raises(journal.GroupJournalConflict, match="unassociated"):
            group.begin(spec)
    assert {name: (date_dir / name).read_bytes() for name in original} == original
    assert not (root / ".bronze-group-journals").exists()


@pytest.mark.parametrize("raw", [b"", b"{", b"[]", b'{"body":1,"body":2}'])
def test_record_rejects_truncated_or_ambiguous_bytes(raw: bytes) -> None:
    with pytest.raises(journal.GroupJournalConflict):
        journal._decode_record(raw, "1" * 32)


def test_record_rejects_forged_checksum_and_unstaged_absence() -> None:
    body = _body()
    raw = journal._record_bytes(body)
    assert journal._decode_record(raw, "1" * 32) == body
    envelope = json.loads(raw)
    envelope["body"]["schema"] = 99
    with pytest.raises(journal.GroupJournalConflict):
        journal._decode_record(json.dumps(envelope).encode(), "1" * 32)
    for version in (1, 2, 3.0):
        body["schema"] = version
        with pytest.raises(journal.GroupJournalConflict):
            journal._decode_record(journal._record_bytes(body), "1" * 32)
    body["schema"] = 4
    body["staged"] = ["sidecar", "payload"]
    with pytest.raises(journal.GroupJournalConflict):
        journal._decode_record(journal._record_bytes(body), "1" * 32)


def test_record_rejects_unknown_member_and_foreign_operation() -> None:
    body = _body()
    body["members"]["manual"] = body["members"]["payload"]  # type: ignore[index]
    with pytest.raises(journal.GroupJournalConflict):
        journal._decode_record(journal._record_bytes(body), "1" * 32)
    with pytest.raises(journal.GroupJournalConflict):
        journal._decode_record(journal._record_bytes(_body()), "2" * 32)


def test_completed_record_requires_durable_member_transitions() -> None:
    body = _body()
    body["state"] = "completed"
    with pytest.raises(journal.GroupJournalConflict):
        journal._decode_record(journal._record_bytes(body), "1" * 32)


def test_anchored_conflict_uses_public_journal_error(tmp_path, monkeypatch) -> None:
    """The platform primitive's refusal cannot escape the group-result contract."""
    monkeypatch.setattr(
        records, "destructive_cleanup_supported", lambda *_a, **_k: True
    )
    group = journal.GroupJournal(records.BronzeRootLease(tmp_path, -1))
    conflict = records._CleanupConflict()

    def refuse(*args, **kwargs):
        raise conflict

    monkeypatch.setattr(records, "_anchored_parent", refuse)
    with pytest.raises(journal.GroupJournalConflict) as failure:
        with group._date("chembl/activity/2024-01-01"):
            pytest.fail("refused traversal entered")
    assert failure.value.__cause__ is conflict
    assert failure.value.removed == 0
    assert failure.value.possibly_unlinked == 0


@POSIX_ONLY
@pytest.mark.parametrize("stop", ["before_completion", "after_completion_fsync"])
def test_restart_rejects_replaced_empty_stage(tmp_path: Path, stop: str) -> None:
    root, spec, date_dir = _fixture(tmp_path, copy=True)

    def interrupt(phase: str) -> None:
        if phase == stop:
            raise OSError("stop before stage retirement")

    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        with pytest.raises(journal.GroupJournalFailure) as failure:
            group.recover(operation_id, interrupt)
        assert failure.value.removed == 3
    stage = root / f".bronze-group-stage-{operation_id}"
    stage.rename(tmp_path / "original-stage")
    stage.mkdir(mode=0o700)
    replacement = stage.stat()
    record = root / ".bronze-group-journals" / f"{operation_id}.json"
    original = record.read_bytes()
    with journal.open_group_journal(root) as group:
        with pytest.raises(journal.GroupJournalConflict) as failure:
            group.recover(operation_id)
        assert failure.value.removed == 0
        assert failure.value.possibly_unlinked == 0
    assert stage.stat().st_ino == replacement.st_ino
    assert record.read_bytes() == original
    assert (tmp_path / "original-stage").exists()
    assert not any((date_dir / name).exists() for name in spec.names().values())


@POSIX_ONLY
def test_process_crash_before_stage_association_preserves_orphan(
    tmp_path: Path,
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
    code = (
        "import os,sys\nfrom pathlib import Path\n"
        "from bioetl.infrastructure.storage.bronze.cleanup_group_journal import open_group_journal\n"
        "with open_group_journal(Path(sys.argv[1])) as group:\n"
        " group.recover(sys.argv[2],lambda p: os._exit(78) if p=='after_stage_create' else None)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(root), operation_id],
        capture_output=True,
        check=False,
        timeout=20,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[4] / "src")},
    )
    assert result.returncode == 78, result.stderr.decode(errors="replace")
    stage = root / f".bronze-group-stage-{operation_id}"
    identity = stage.stat()
    with journal.open_group_journal(root) as group:
        with pytest.raises(journal.GroupJournalConflict, match="unassociated stage"):
            group.recover(operation_id)
    assert stage.stat().st_ino == identity.st_ino
    assert (date_dir / spec.names()["payload"]).read_bytes() == b"payload\n"
    assert (date_dir / spec.names()["sidecar"]).exists()


@POSIX_ONLY
@pytest.mark.parametrize("replacement", [b"{", b"unrelated evidence", b"valid-copy"])
def test_restart_preserves_unassociated_next(
    tmp_path: Path, replacement: bytes
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
    record = root / ".bronze-group-journals" / f"{operation_id}.json"
    original = record.read_bytes()
    raw = original if replacement == b"valid-copy" else replacement
    temp = record.with_suffix(".next")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, raw)
    finally:
        os.close(fd)
    with journal.open_group_journal(root) as group:
        with pytest.raises(journal.GroupJournalConflict, match="replacement retained"):
            group.recover(operation_id)
    assert temp.read_bytes() == raw
    assert record.read_bytes() == original
    assert (date_dir / spec.names()["payload"]).read_bytes() == b"payload\n"
    assert (date_dir / spec.names()["sidecar"]).exists()


@POSIX_ONLY
def test_stage_token_replacement_refuses_before_member_removal(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)

    def interrupt(phase: str) -> None:
        if phase == "after_stage_association_fsync":
            raise OSError("stop after durable association")

    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        with pytest.raises(journal.GroupJournalFailure):
            group.recover(operation_id, interrupt)
    stage = root / f".bronze-group-stage-{operation_id}"
    os.setxattr(stage, journal._STAGE_TAG, b"foreign")
    with journal.open_group_journal(root) as group:
        with pytest.raises(journal.GroupJournalConflict):
            group.recover(operation_id)
    assert os.getxattr(stage, journal._STAGE_TAG) == b"foreign"
    assert (date_dir / spec.names()["payload"]).read_bytes() == b"payload\n"


@POSIX_ONLY
def test_late_journal_replacement_retains_partial_result(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        record = root / ".bronze-group-journals" / f"{operation_id}.json"

        def replace(phase: str) -> None:
            if phase == "before_journal_unlink":
                record.write_bytes(b"external evidence")

        with pytest.raises(journal.GroupJournalConflict) as failure:
            group.recover(operation_id, replace)
        assert failure.value.removed == 2
        assert failure.value.removed_bytes > 0
    assert record.read_bytes() == b"external evidence"
    assert not (date_dir / spec.names()["payload"]).exists()


@POSIX_ONLY
def test_stage_moved_outside_root_is_not_unlinked_through_old_handle(
    tmp_path: Path,
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    outside = tmp_path / "outside-stage"
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        stage = root / f".bronze-group-stage-{operation_id}"

        def move(phase: str) -> None:
            if phase == "after_payload_stage":
                stage.rename(outside)
                stage.mkdir(mode=0o700)

        with pytest.raises(journal.GroupJournalConflict) as failure:
            group.recover(operation_id, move)
        assert failure.value.removed == 0
        assert failure.value.possibly_unlinked == 0
    assert (outside / "payload").read_bytes() == b"payload\n"
    assert stage.is_dir()
    assert (date_dir / spec.names()["sidecar"]).exists()


@POSIX_ONLY
def test_unsupported_stage_tag_never_falls_back_to_unattested_removal(
    tmp_path: Path, monkeypatch
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    real_setxattr = journal.os.setxattr

    def refuse_stage_tag(path, attribute, value, *args, **kwargs):
        name = attribute.decode() if isinstance(attribute, bytes) else attribute
        if name == "user.bioetl.fs001-stage":
            raise OSError(errno.ENOTSUP, "directory xattrs unavailable")
        return real_setxattr(path, attribute, value, *args, **kwargs)

    monkeypatch.setattr(journal.os, "setxattr", refuse_stage_tag)
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        with pytest.raises(journal.GroupJournalFailure) as failure:
            group.recover(operation_id)
        assert failure.value.removed == 0
        assert failure.value.possibly_unlinked == 0
        assert failure.value.phase == "stage_association"
    assert (date_dir / spec.names()["payload"]).read_bytes() == b"payload\n"
    assert (date_dir / spec.names()["sidecar"]).exists()


@POSIX_ONLY
def test_begin_reuses_identical_pending_intent(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        record = root / ".bronze-group-journals" / f"{operation_id}.json"
        original = record.read_bytes()
        assert group.begin(spec) == operation_id
        assert record.read_bytes() == original
    assert len(list((root / ".bronze-group-journals").iterdir())) == 1
    assert (date_dir / spec.names()["payload"]).read_bytes() == b"payload\n"


@POSIX_ONLY
def test_begin_retry_confirms_published_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, spec, _ = _fixture(tmp_path)
    original_fsync = os.fsync
    with journal.open_group_journal(root) as group:

        def fail_published(fd: int) -> None:
            if list((root / ".bronze-group-journals").glob("*.json")):
                raise OSError("published intent confirmation failed")
            original_fsync(fd)

        monkeypatch.setattr(os, "fsync", fail_published)
        with pytest.raises(OSError, match="confirmation failed"):
            group.begin(spec)
        receipt = next((root / ".bronze-group-journals").glob("*.json"))
        original = receipt.read_bytes()
        with pytest.raises(OSError, match="confirmation failed"):
            group.begin(spec)
        monkeypatch.setattr(os, "fsync", original_fsync)
        assert group.begin(spec) == receipt.stem
        assert receipt.read_bytes() == original
        assert group.recover(receipt.stem) == 2


@POSIX_ONLY
def test_retired_receipt_retry_confirms_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, spec, _ = _fixture(tmp_path)
    original_fsync = os.fsync
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        receipt = root / ".bronze-group-journals" / f"{operation_id}.json"
        journal_identity = receipt.parent.stat()

        def fail_retirement(fd: int) -> None:
            identity = os.fstat(fd)
            if not receipt.exists() and (identity.st_dev, identity.st_ino) == (
                journal_identity.st_dev,
                journal_identity.st_ino,
            ):
                raise OSError("retirement confirmation failed")
            original_fsync(fd)

        monkeypatch.setattr(os, "fsync", fail_retirement)
        with pytest.raises(journal.GroupJournalFailure):
            group.recover(operation_id)
        assert not receipt.exists()
        with pytest.raises(journal.GroupJournalFailure):
            group.recover(operation_id)
        monkeypatch.setattr(os, "fsync", original_fsync)
        assert group.recover(operation_id) == 0


@POSIX_ONLY
@pytest.mark.parametrize("exclusive", [False, True])
def test_pending_group_blocks_regular_root_operations(
    tmp_path: Path, exclusive: bool
) -> None:
    root, spec, _ = _fixture(tmp_path)
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
    with pytest.raises(OSError, match="group recovery is pending"):
        with journal.bronze_tree_lock(root, exclusive=exclusive):
            pytest.fail("pending group admitted regular operation")
    with journal.open_group_journal(root) as group:
        assert group.recover(operation_id) == 2
    with journal.bronze_tree_lock(root, exclusive=exclusive):
        pass


def test_windows_apply_capability_fails_closed(tmp_path: Path) -> None:
    if journal.destructive_cleanup_supported():
        pytest.skip("capability is present on this POSIX host")
    with pytest.raises(NotImplementedError):
        with journal.open_group_journal(tmp_path):
            pytest.fail("unsupported apply entered")


@pytest.mark.skipif(os.name != "nt", reason="Windows reparse capability check")
def test_windows_symlink_root_keeps_apply_disabled(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(root, target_is_directory=True)
    except OSError:
        pytest.skip("Windows symlink privilege unavailable")
    with pytest.raises(NotImplementedError):
        with journal.open_group_journal(alias):
            pytest.fail("Windows destructive apply entered")


@POSIX_ONLY
def test_missing_intent_never_adopts_orphan(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    (date_dir / spec.names()["payload"]).unlink()
    with journal.open_group_journal(root) as group:
        assert group.recover("f" * 32) == 0
        with pytest.raises(FileNotFoundError):
            group.begin(spec)
    assert (date_dir / spec.names()["sidecar"]).exists()


@POSIX_ONLY
def test_stage_without_intent_is_a_conflict(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    operation_id = "f" * 32
    (root / f".bronze-group-stage-{operation_id}").mkdir()
    with journal.open_group_journal(root) as group:
        with pytest.raises(journal.GroupJournalConflict, match="without group journal"):
            group.recover(operation_id)
    assert (date_dir / spec.names()["payload"]).read_bytes() == b"payload\n"


@POSIX_ONLY
@pytest.mark.parametrize("copy,first_removed", [(False, 1), (True, 2)])
def test_late_sidecar_failure_recovers_exact_group(
    tmp_path: Path, copy: bool, first_removed: int
) -> None:
    root, spec, date_dir = _fixture(tmp_path, copy=copy)
    outsider = date_dir / "manual-backup.json"
    outsider.write_bytes(b"retain")
    sidecar_bytes = (date_dir / spec.names()["sidecar"]).read_bytes()
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        with pytest.raises(journal.GroupJournalFailure) as failure:
            group.recover(
                operation_id,
                lambda phase: (
                    (_ for _ in ()).throw(OSError("sidecar denied"))
                    if phase == "before_sidecar_unlink"
                    else None
                ),
            )
        assert failure.value.removed == first_removed
        assert failure.value.removed_bytes == len(b"payload\n") + (
            len(b"copy\n") if copy else 0
        )
        assert failure.value.possibly_unlinked == 0
        assert failure.value.possibly_unlinked_bytes == 0
        assert (date_dir / spec.names()["sidecar"]).exists() is False
        record_path = root / ".bronze-group-journals" / f"{operation_id}.json"
        record = journal._decode_record(record_path.read_bytes(), operation_id)
        assert record["staged"] == (["copy"] if copy else []) + ["payload", "sidecar"]
        assert (
            root / f".bronze-group-stage-{operation_id}" / "sidecar"
        ).read_bytes() == sidecar_bytes
    with journal.open_group_journal(root) as group:
        result = group.recover_with_result(operation_id)
        assert result.removed == 1
        assert result.removed_bytes == len(sidecar_bytes)
        assert group.recover(operation_id) == 0
    assert outsider.read_bytes() == b"retain"
    assert all(not (date_dir / name).exists() for name in spec.names().values())


@POSIX_ONLY
def test_late_foreign_replacement_preserves_partial_result(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    sidecar = date_dir / spec.names()["sidecar"]
    payload = date_dir / spec.names()["payload"]

    def replace_after_payload(phase: str) -> None:
        if phase == "after_payload_unlink":
            sidecar.unlink()
            sidecar.write_bytes(b"foreign")

    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        with pytest.raises(journal.GroupJournalConflict) as conflict:
            group.recover(operation_id, replace_after_payload)
        assert conflict.value.operation_id == operation_id
        assert conflict.value.removed == 1
        assert conflict.value.removed_bytes == len(b"payload\n")
        assert conflict.value.possibly_unlinked == 0
        assert conflict.value.phase == "sidecar_identity"
        assert not payload.exists()
        assert sidecar.read_bytes() == b"foreign"
        with pytest.raises(journal.GroupJournalConflict) as retry_conflict:
            group.recover(operation_id)
        assert retry_conflict.value.removed == 0
    assert sidecar.read_bytes() == b"foreign"
    assert (root / ".bronze-group-journals" / f"{operation_id}.json").exists()


@POSIX_ONLY
@pytest.mark.parametrize(
    "phase",
    [
        "after_intent_fsync",
        "after_payload_stage",
        "after_payload_staged_record",
        "before_payload_unlink",
        "after_payload_unlink",
        "before_completion",
        "after_completion_fsync",
        "before_journal_unlink",
    ],
)
def test_recovery_across_durable_barriers(tmp_path: Path, phase: str) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    with journal.open_group_journal(root) as group:
        if phase == "after_intent_fsync":
            captured: list[str] = []
            with pytest.raises(OSError, match="injected"):
                group.begin(
                    spec,
                    lambda point: (
                        (_ for _ in ()).throw(OSError("injected"))
                        if point == phase
                        else None
                    ),
                )
            captured = [
                p.stem for p in (root / ".bronze-group-journals").glob("*.json")
            ]
            assert len(captured) == 1
            operation_id = captured[0]
        else:
            operation_id = group.begin(spec)
            with pytest.raises((journal.GroupJournalFailure, OSError)):
                group.recover(
                    operation_id,
                    lambda point: (
                        (_ for _ in ()).throw(OSError("injected"))
                        if point == phase
                        else None
                    ),
                )
    with journal.open_group_journal(root) as group:
        group.recover(operation_id)
        assert group.recover(operation_id) == 0
    assert all(
        not (date_dir / name).exists()
        for name in (spec.names()["payload"], spec.names()["sidecar"])
    )


@POSIX_ONLY
def test_process_crash_after_payload_unlink_then_retry(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
    code = (
        "import os,sys\nfrom pathlib import Path\n"
        "from bioetl.infrastructure.storage.bronze.cleanup_group_journal import open_group_journal\n"
        "with open_group_journal(Path(sys.argv[1])) as group:\n"
        " group.recover(sys.argv[2],lambda p: os._exit(77) if p=='after_payload_unlink' else None)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(root), operation_id],
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[4] / "src")},
    )
    assert result.returncode == 77, result.stderr.decode(errors="replace")
    with journal.open_group_journal(root) as group:
        assert group.recover(operation_id) == 1
    assert all(
        not (date_dir / name).exists()
        for name in (spec.names()["payload"], spec.names()["sidecar"])
    )


@POSIX_ONLY
def test_process_crash_between_unlink_and_directory_fsync_recovers(
    tmp_path: Path,
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    outsider = tmp_path / "outside"
    outsider.write_bytes(b"sentinel")
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
    code = (
        "import os,sys\nfrom pathlib import Path\n"
        "import bioetl.infrastructure.storage.bronze.cleanup_group_journal as journal\n"
        "original_unlink=os.unlink\n"
        "def crash_after_unlink(name, *, dir_fd=None):\n"
        " original_unlink(name,dir_fd=dir_fd)\n"
        " if name=='payload': os._exit(77)\n"
        "journal.os.unlink=crash_after_unlink\n"
        "with journal.open_group_journal(Path(sys.argv[1])) as group:\n"
        " group.recover(sys.argv[2])\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(root), operation_id],
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[4] / "src")},
    )
    assert result.returncode == 77, result.stderr.decode(errors="replace")
    record_path = root / ".bronze-group-journals" / f"{operation_id}.json"
    record = journal._decode_record(record_path.read_bytes(), operation_id)
    assert record["staged"] == ["payload"]
    assert not (root / f".bronze-group-stage-{operation_id}" / "payload").exists()
    assert not (date_dir / spec.names()["payload"]).exists()
    assert (date_dir / spec.names()["sidecar"]).exists()
    with journal.open_group_journal(root) as group:
        assert group.recover(operation_id) == 1
        assert group.recover(operation_id) == 0
    assert outsider.read_bytes() == b"sentinel"
    assert not record_path.exists()


@POSIX_ONLY
def test_replaced_name_or_symlink_never_deleted(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    outsider = tmp_path / "outside"
    outsider.write_bytes(b"sentinel")
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        payload = date_dir / spec.names()["payload"]
        payload.unlink()
        payload.write_bytes(b"foreign")
        with pytest.raises(journal.GroupJournalConflict):
            group.recover(operation_id)
        assert payload.read_bytes() == b"foreign"
        payload.unlink()
        try:
            payload.symlink_to(outsider)
        except (OSError, NotImplementedError):
            pytest.skip("symlink creation unavailable")
        with pytest.raises((journal.GroupJournalConflict, journal.GroupJournalFailure)):
            group.recover(operation_id)
    assert outsider.read_bytes() == b"sentinel"


@POSIX_ONLY
def test_durably_staged_member_reappearing_at_source_is_not_redeleted(
    tmp_path: Path,
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    payload = date_dir / spec.names()["payload"]
    original = payload.stat()
    original_bytes = payload.read_bytes()
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        stage = root / f".bronze-group-stage-{operation_id}" / "payload"

        def restore_same_inode(phase: str) -> None:
            if phase == "after_payload_staged_record":
                stage.rename(payload)
                raise OSError("injected stop after source reappearance")

        with pytest.raises(journal.GroupJournalFailure) as stopped:
            group.recover(operation_id, restore_same_inode)
        assert stopped.value.removed == 0
        assert payload.stat().st_ino == original.st_ino
        assert payload.read_bytes() == original_bytes
        with pytest.raises(
            journal.GroupJournalConflict, match="staged payload reappeared at source"
        ) as conflict:
            group.recover(operation_id)
        assert conflict.value.removed == 0
        assert payload.stat().st_ino == original.st_ino
        assert payload.read_bytes() == original_bytes
        assert (root / ".bronze-group-journals" / f"{operation_id}.json").exists()


@POSIX_ONLY
def test_copy_appearing_after_intent_does_not_delete_partial_group(
    tmp_path: Path,
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    copy = date_dir / spec.names()["copy"]
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        copy.write_bytes(b"new copy")
        with pytest.raises(
            journal.GroupJournalConflict, match="unattested group copy appeared"
        ) as conflict:
            group.recover(operation_id)
        assert conflict.value.removed == 0
        assert copy.read_bytes() == b"new copy"
        assert all(
            (date_dir / spec.names()[key]).exists() for key in ("payload", "sidecar")
        )
        assert (root / ".bronze-group-journals" / f"{operation_id}.json").exists()


@POSIX_ONLY
def test_unattested_copy_at_completion_preserves_partial_result(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    copy = date_dir / spec.names()["copy"]
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)

        def add_copy(phase: str) -> None:
            if phase == "before_completion":
                copy.write_bytes(b"late copy")

        with pytest.raises(journal.GroupJournalConflict) as conflict:
            group.recover(operation_id, add_copy)
        assert conflict.value.removed == 2
        assert conflict.value.possibly_unlinked == 0
        assert copy.read_bytes() == b"late copy"
        assert all(
            not (date_dir / spec.names()[key]).exists()
            for key in ("payload", "sidecar")
        )
        assert (root / ".bronze-group-journals" / f"{operation_id}.json").exists()


@POSIX_ONLY
@pytest.mark.parametrize("barrier", ["before_payload_stage", "before_payload_unlink"])
def test_same_name_foreign_replacement_at_barrier_is_preserved(
    tmp_path: Path, barrier: str
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    outsider = tmp_path / "outside"
    outsider.write_bytes(b"sentinel")
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        target = (
            date_dir / spec.names()["payload"]
            if barrier == "before_payload_stage"
            else root / f".bronze-group-stage-{operation_id}" / "payload"
        )

        def replace(phase: str) -> None:
            if phase == barrier:
                target.unlink()
                target.write_bytes(b"foreign")

        with pytest.raises(journal.GroupJournalConflict):
            group.recover(operation_id, replace)
        assert target.read_bytes() == b"foreign"
    assert outsider.read_bytes() == b"sentinel"


@POSIX_ONLY
def test_empty_foreign_directory_is_not_rmdir_target(tmp_path: Path) -> None:
    root, spec, _date_dir = _fixture(tmp_path)
    foreign = tmp_path / "foreign-empty"
    foreign.mkdir(mode=0o700)
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        stage = root / f".bronze-group-stage-{operation_id}"

        def replace_stage(phase: str) -> None:
            if phase == "after_completion_fsync":
                stage.rename(tmp_path / "original-stage")
                foreign.rename(stage)

        with pytest.raises(
            journal.GroupJournalConflict, match="stage directory replaced"
        ) as conflict:
            group.recover(operation_id, replace_stage)
        assert conflict.value.removed == 2
        assert conflict.value.possibly_unlinked == 0
        assert stage.is_dir()
        assert (root / ".bronze-group-journals" / f"{operation_id}.json").exists()


@POSIX_ONLY
@pytest.mark.parametrize("replace", ["root", "date"])
def test_root_or_date_replacement_fails_before_unlink(
    tmp_path: Path, replace: str
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    outsider = tmp_path / "outside"
    outsider.mkdir()
    (outsider / "sentinel").write_bytes(b"retain")
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        if replace == "root":
            root.rename(tmp_path / "moved-root")
            root.mkdir()
        else:
            date_dir.rename(tmp_path / "moved-date")
            date_dir.mkdir()
        with pytest.raises(journal.GroupJournalConflict):
            group.recover(operation_id)
    assert (outsider / "sentinel").read_bytes() == b"retain"
    moved = tmp_path / ("moved-root" if replace == "root" else "moved-date")
    expected = moved / "chembl" / "activity" / DATE if replace == "root" else moved
    assert (expected / spec.names()["payload"]).read_bytes() == b"payload\n"


@POSIX_ONLY
def test_symlink_root_is_rejected(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(root, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable")
    with pytest.raises(OSError):
        with journal.open_group_journal(alias):
            pytest.fail("linked root entered destructive API")
    assert (date_dir / spec.names()["payload"]).read_bytes() == b"payload\n"


@POSIX_ONLY
def test_competing_recovery_waits_for_cooperative_root_lock(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    code = (
        "import sys\nfrom pathlib import Path\n"
        "from bioetl.infrastructure.storage.bronze.cleanup_group_journal import open_group_journal\n"
        "print('attempt',flush=True)\n"
        "with open_group_journal(Path(sys.argv[1])) as group:\n"
        " print('removed='+str(group.recover(sys.argv[2])),flush=True)\n"
    )
    with journal.open_group_journal(root) as first:
        operation_id = first.begin(spec)
        child = subprocess.Popen(
            [sys.executable, "-c", code, str(root), operation_id],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[4] / "src")},
        )
        assert child.stdout is not None
        assert child.stdout.readline().strip() == b"attempt"
        assert select.select([child.stdout], [], [], 0)[0] == []
        assert first.recover(operation_id) == 2
    stdout, stderr = child.communicate(timeout=20)
    assert child.returncode == 0, stderr.decode(errors="replace")
    assert stdout.strip() == b"removed=0"
    assert all(
        not (date_dir / name).exists()
        for name in (spec.names()["payload"], spec.names()["sidecar"])
    )


@POSIX_ONLY
@pytest.mark.parametrize("mutation", ["truncate", "version", "root", "foreign"])
def test_invalid_journal_does_not_delete(tmp_path: Path, mutation: str) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        path = root / ".bronze-group-journals" / f"{operation_id}.json"
        body = json.loads(path.read_bytes())["body"]
        if mutation == "truncate":
            raw = b"{"
        else:
            if mutation == "version":
                body["schema"] = 99
            elif mutation == "root":
                body["root"] = [999, 999]
            else:
                body["operation_id"] = (
                    "0" if operation_id[0] != "0" else "1"
                ) + operation_id[1:]
            raw = journal._record_bytes(body)
        path.write_bytes(raw)
        with pytest.raises(journal.GroupJournalConflict):
            group.recover(operation_id)
    assert (date_dir / spec.names()["payload"]).read_bytes() == b"payload\n"


@POSIX_ONLY
def test_missing_unstaged_member_is_ambiguous(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        (date_dir / spec.names()["sidecar"]).unlink()
        with pytest.raises(journal.GroupJournalConflict, match="unexplained absence"):
            group.recover(operation_id)
    assert (date_dir / spec.names()["payload"]).exists()


@POSIX_ONLY
def test_write_fsync_and_finalization_errors_retain_intent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    original_write = records._write_all
    monkeypatch.setattr(
        records, "_write_all", lambda *_: (_ for _ in ()).throw(OSError("write denied"))
    )
    with (
        journal.open_group_journal(root) as group,
        pytest.raises(OSError, match="write denied"),
    ):
        group.begin(spec)
    monkeypatch.setattr(records, "_write_all", original_write)
    journal_dir = root / ".bronze-group-journals"
    assert list(journal_dir.glob("*.json")) == []
    assert list(journal_dir.glob("*.next")) == []
    assert all(
        (date_dir / spec.names()[key]).exists() for key in ("payload", "sidecar")
    )
    # An unpublished temp is never replayed. Use another isolated root for faults.
    root, spec, _date_dir = _fixture(tmp_path / "fresh")
    original_fsync = journal.os.fsync
    calls = 0

    def fail_second_fsync(fd: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("fsync denied")
        original_fsync(fd)

    monkeypatch.setattr(journal.os, "fsync", fail_second_fsync)
    with (
        journal.open_group_journal(root) as group,
        pytest.raises(OSError, match="fsync denied"),
    ):
        group.begin(spec)
    monkeypatch.setattr(journal.os, "fsync", original_fsync)
    root, spec, _date_dir = _fixture(tmp_path / "final")
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        original_rmdir = journal.os.rmdir

        def fail_stage_rmdir(name: str, *, dir_fd: int) -> None:
            if name.startswith(".bronze-group-stage-"):
                raise OSError("finalization denied")
            original_rmdir(name, dir_fd=dir_fd)

        monkeypatch.setattr(journal.os, "rmdir", fail_stage_rmdir)
        with pytest.raises(journal.GroupJournalFailure) as failure:
            group.recover(operation_id)
        assert failure.value.removed == 2
        assert "finalization denied" in str(failure.value.__cause__)
        monkeypatch.setattr(journal.os, "rmdir", original_rmdir)
        assert (root / ".bronze-group-journals" / f"{operation_id}.json").exists()
        assert group.recover(operation_id) == 0


@POSIX_ONLY
def test_unlink_then_fsync_failure_reports_uncertain_partial_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    original_fsync = journal.os.fsync
    armed = False

    def fail_next_fsync(fd: int) -> None:
        nonlocal armed
        if armed:
            armed = False
            raise OSError("post-unlink fsync denied")
        original_fsync(fd)

    def arm_before_unlink(phase: str) -> None:
        nonlocal armed
        if phase == "before_payload_unlink":
            armed = True

    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        monkeypatch.setattr(journal.os, "fsync", fail_next_fsync)
        with pytest.raises(journal.GroupJournalFailure) as failure:
            group.recover(operation_id, arm_before_unlink)
        monkeypatch.setattr(journal.os, "fsync", original_fsync)
        assert failure.value.removed == 0
        assert failure.value.possibly_unlinked == 1
        assert failure.value.removed_bytes == 0
        assert failure.value.possibly_unlinked_bytes == len(b"payload\n")
        assert group.recover(operation_id) == 1
    assert all(
        not (date_dir / name).exists()
        for name in (spec.names()["payload"], spec.names()["sidecar"])
    )


@POSIX_ONLY
@pytest.mark.parametrize("phase", ["after_payload_stage", "before_completion"])
def test_record_substitution_is_not_overwritten(tmp_path: Path, phase: str) -> None:
    root, spec, _date_dir = _fixture(tmp_path)
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        receipt = root / ".bronze-group-journals" / f"{operation_id}.json"

        def replace_record(point: str) -> None:
            if point == phase:
                receipt.unlink()
                fd = os.open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    os.write(fd, b"foreign receipt")
                finally:
                    os.close(fd)

        with pytest.raises(
            journal.GroupJournalConflict, match="journal replaced"
        ) as error:
            group.recover(operation_id, replace_record)
        assert receipt.read_bytes() == b"foreign receipt"
        assert error.value.removed == (2 if phase == "before_completion" else 0)
        assert list(receipt.parent.glob("*.next")) == []


@POSIX_ONLY
def test_completed_missing_stage_is_fsynced_before_receipt_retirement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, spec, _date_dir = _fixture(tmp_path)
    original_fsync = os.fsync
    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        stage = root / f".bronze-group-stage-{operation_id}"
        receipt = root / ".bronze-group-journals" / f"{operation_id}.json"

        def fail_root_confirmation(fd: int) -> None:
            if fd == group._root_fd and not stage.exists():
                raise OSError("root confirmation failed")
            original_fsync(fd)

        monkeypatch.setattr(journal.os, "fsync", fail_root_confirmation)
        with pytest.raises(journal.GroupJournalFailure) as failure:
            group.recover(operation_id)
        assert failure.value.removed == 2
        assert not stage.exists()
        assert receipt.exists()
        with pytest.raises(journal.GroupJournalFailure) as retry:
            group.recover(operation_id)
        assert retry.value.removed == 0
        assert receipt.exists()
        monkeypatch.setattr(journal.os, "fsync", original_fsync)
        assert group.recover(operation_id) == 0
        assert not receipt.exists()


@POSIX_ONLY
def test_synchronous_write_failure_retains_substituted_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    retained = tmp_path / "owned-temp"

    def replace_temp_then_fail(_fd: int, _raw: bytes) -> None:
        temp = next((root / ".bronze-group-journals").glob("*.next"))
        temp.rename(retained)
        temp.write_bytes(b"foreign temp")
        raise OSError("write failed after substitution")

    monkeypatch.setattr(records, "_write_all", replace_temp_then_fail)
    with journal.open_group_journal(root) as group:
        with pytest.raises(OSError, match="write failed after substitution"):
            group.begin(spec)
    temp = next((root / ".bronze-group-journals").glob("*.next"))
    assert temp.read_bytes() == b"foreign temp"
    assert retained.exists()
    assert (date_dir / spec.names()["payload"]).exists()


@POSIX_ONLY
def test_retry_confirms_uncertain_absence_before_completed_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, spec, _date_dir = _fixture(tmp_path)
    original_fsync = os.fsync
    armed = False

    def fail_once(fd: int) -> None:
        nonlocal armed
        if armed:
            armed = False
            raise OSError("confirmation failed")
        original_fsync(fd)

    def arm_unlink(phase: str) -> None:
        nonlocal armed
        if phase == "before_sidecar_unlink":
            armed = True

    def arm_completion(phase: str) -> None:
        nonlocal armed
        if phase == "before_completion":
            armed = True

    with journal.open_group_journal(root) as group:
        operation_id = group.begin(spec)
        receipt = root / ".bronze-group-journals" / f"{operation_id}.json"
        monkeypatch.setattr(journal.os, "fsync", fail_once)
        with pytest.raises(journal.GroupJournalFailure) as initial:
            group.recover(operation_id, arm_unlink)
        assert initial.value.removed == 1
        assert initial.value.possibly_unlinked == 1
        with pytest.raises(journal.GroupJournalFailure) as retry:
            group.recover(operation_id, arm_completion)
        assert retry.value.removed == 0
        assert retry.value.possibly_unlinked == 0
        assert (
            journal._decode_record(receipt.read_bytes(), operation_id)["state"]
            == "prepared"
        )
        monkeypatch.setattr(journal.os, "fsync", original_fsync)
        assert group.recover(operation_id) == 0
        assert not receipt.exists()
