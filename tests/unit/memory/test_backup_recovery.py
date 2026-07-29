"""Tests for deterministic memory backup and verified recovery."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from memory.backup import (
    BackupVerificationError,
    create_backup,
    recover_backup,
    verify_backup,
)


def _source(tmp_path: Path) -> Path:
    source = tmp_path / "memory"
    (source / "nested").mkdir(parents=True)
    (source / "a.json").write_text('{"a": 1}\n', encoding="utf-8")
    (source / "nested" / "b.md").write_text("# B\n", encoding="utf-8")
    return source


def test_backup_is_deterministic_and_idempotent(tmp_path: Path) -> None:
    source = _source(tmp_path)
    backup_root = tmp_path / "backups"

    first = create_backup(source, backup_root)
    second = create_backup(source, backup_root)

    assert first.bundle_path == second.bundle_path
    assert first.root_digest == second.root_digest
    assert first.created is True
    assert second.created is False
    assert first.file_count == 2
    assert verify_backup(first.bundle_path)["root_digest"] == first.root_digest


def test_backup_manifest_has_stable_sorted_paths(tmp_path: Path) -> None:
    result = create_backup(_source(tmp_path), tmp_path / "backups")

    manifest = json.loads(
        (result.bundle_path / "manifest.json").read_text(encoding="utf-8")
    )

    assert [entry["path"] for entry in manifest["files"]] == [
        "a.json",
        "nested/b.md",
    ]


def test_recovery_dry_run_does_not_write(tmp_path: Path) -> None:
    result = create_backup(_source(tmp_path), tmp_path / "backups")
    target = tmp_path / "recovered"

    recovered = recover_backup(result.bundle_path, target)

    assert recovered == (Path("a.json"), Path("nested/b.md"))
    assert not target.exists()


def test_verified_recovery_replaces_target(tmp_path: Path) -> None:
    result = create_backup(_source(tmp_path), tmp_path / "backups")
    target = tmp_path / "recovered"
    target.mkdir()
    (target / "stale.txt").write_text("stale", encoding="utf-8")

    recover_backup(result.bundle_path, target, apply=True)

    assert not (target / "stale.txt").exists()
    assert (target / "a.json").read_text(encoding="utf-8") == '{"a": 1}\n'
    assert (target / "nested" / "b.md").read_text(encoding="utf-8") == "# B\n"


def test_tampered_backup_is_rejected_before_recovery(tmp_path: Path) -> None:
    result = create_backup(_source(tmp_path), tmp_path / "backups")
    (result.bundle_path / "payload" / "a.json").write_text(
        '{"tampered": true}\n',
        encoding="utf-8",
    )
    target = tmp_path / "target"

    with pytest.raises(BackupVerificationError, match="digest mismatch"):
        recover_backup(result.bundle_path, target, apply=True)

    assert not target.exists()


def test_failed_recovery_restores_original_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = create_backup(_source(tmp_path), tmp_path / "backups")
    target = tmp_path / "target"
    target.mkdir()
    original = target / "original.txt"
    original.write_text("preserve me", encoding="utf-8")
    real_replace = os.replace
    calls = 0

    def fail_publish(source: Path, destination: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic publish failure")
        real_replace(source, destination)

    monkeypatch.setattr("memory.backup.os.replace", fail_publish)

    with pytest.raises(OSError, match="synthetic publish failure"):
        recover_backup(result.bundle_path, target, apply=True)

    assert original.read_text(encoding="utf-8") == "preserve me"
