"""Synthetic-only fault injection for the opt-in Bronze group journal."""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from bioetl.infrastructure.storage.bronze import cleanup_group_journal as journal


DATE = "2024-01-01"
CUTOFF = "2024-01-02"
BATCH = "11111111-1111-4111-8111-111111111111"
POSIX_ONLY = pytest.mark.skipif(
    not journal.destructive_cleanup_supported(),
    reason="POSIX pinned directory and flock capability unavailable",
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
        json.dumps({"provider": "chembl", "entity": "activity", "batch_id": BATCH}),
        encoding="utf-8",
    )
    if copy:
        (date_dir / names["copy"]).write_bytes(b"copy\n")
    return root, spec, date_dir


def _body() -> dict[str, object]:
    spec = journal.GroupSpec("chembl", "activity", DATE, BATCH, CUTOFF)
    identity = {"dev": 1, "ino": 2, "size": 3, "sha256": "a" * 64}
    return {
        "schema": 1,
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
    }


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


@pytest.mark.parametrize("raw", [b"", b"{", b"[]", b'{"body":1,"body":2}'])
def test_record_rejects_truncated_or_ambiguous_bytes(raw: bytes) -> None:
    with pytest.raises(journal.GroupJournalConflict):
        journal._decode_record(raw, "1" * 32)


def test_record_rejects_forged_checksum_and_unstaged_absence() -> None:
    body = _body()
    raw = journal._record_bytes(body)
    assert journal._decode_record(raw, "1" * 32) == body
    envelope = json.loads(raw)
    envelope["body"]["schema"] = 2
    with pytest.raises(journal.GroupJournalConflict):
        journal._decode_record(json.dumps(envelope).encode(), "1" * 32)
    body["schema"] = 2
    with pytest.raises(journal.GroupJournalConflict):
        journal._decode_record(journal._record_bytes(body), "1" * 32)
    body["schema"] = 1
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
        assert group.recover(uuid4().hex) == 0
        with pytest.raises(FileNotFoundError):
            group.begin(spec)
    assert (date_dir / spec.names()["sidecar"]).exists()


@POSIX_ONLY
def test_stage_without_intent_is_a_conflict(tmp_path: Path) -> None:
    root, spec, date_dir = _fixture(tmp_path)
    operation_id = uuid4().hex
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
        assert (date_dir / spec.names()["sidecar"]).exists() is False
    with journal.open_group_journal(root) as group:
        assert group.recover(operation_id) == 1
        assert group.recover(operation_id) == 0
    assert outsider.read_bytes() == b"retain"
    assert all(not (date_dir / name).exists() for name in spec.names().values())


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
        ):
            group.recover(operation_id, replace_stage)
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
                body["operation_id"] = uuid4().hex
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
    root, spec, _date_dir = _fixture(tmp_path)
    original_write = journal._write_all
    monkeypatch.setattr(
        journal, "_write_all", lambda *_: (_ for _ in ()).throw(OSError("write denied"))
    )
    with (
        journal.open_group_journal(root) as group,
        pytest.raises(OSError, match="write denied"),
    ):
        group.begin(spec)
    monkeypatch.setattr(journal, "_write_all", original_write)
    # A torn intent is never replayed. Use another isolated root for barrier faults.
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
        assert group.recover(operation_id) == 1
    assert all(
        not (date_dir / name).exists()
        for name in (spec.names()["payload"], spec.names()["sidecar"])
    )
