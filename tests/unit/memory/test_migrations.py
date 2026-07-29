"""Tests for explicit, dry-run-first memory schema migrations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory.migrations import (
    MigrationError,
    MigrationStep,
    migrate_json_file,
    migrate_payload,
)


def test_migration_dry_run_does_not_write(tmp_path: Path) -> None:
    path = tmp_path / "record.json"
    original = b'{"id":"legacy"}\n'
    path.write_bytes(original)

    result = migrate_json_file(path, target_version=1)

    assert result.changed is True
    assert result.applied is False
    assert result.preserved_original is None
    assert path.read_bytes() == original


def test_apply_preserves_original_and_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "record.json"
    original = b'{"id":"legacy"}\n'
    path.write_bytes(original)

    first = migrate_json_file(path, target_version=1, apply=True)
    second = migrate_json_file(path, target_version=1, apply=True)

    assert first.applied is True
    assert first.preserved_original is not None
    assert first.preserved_original.read_bytes() == original
    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == 1
    assert second.changed is False
    assert second.applied is False


def test_migrate_payload_does_not_mutate_input() -> None:
    payload = {"id": "legacy", "nested": {"value": 1}}

    migrated = migrate_payload(payload, target_version=1)

    assert "schema_version" not in payload
    assert migrated["schema_version"] == 1


def test_missing_explicit_step_is_rejected() -> None:
    with pytest.raises(MigrationError, match="no migration step"):
        migrate_payload({"schema_version": 1}, target_version=2, migrations={})


def test_invalid_step_contract_is_rejected() -> None:
    with pytest.raises(ValueError, match="exactly one version"):
        MigrationStep(0, 2, lambda payload: payload)


def test_failed_write_restores_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "record.json"
    original = b'{"id":"legacy"}\n'
    path.write_bytes(original)

    def fail_write(*args: object, **kwargs: object) -> str:
        path.write_text("partial", encoding="utf-8")
        raise OSError("synthetic failure")

    monkeypatch.setattr("memory.migrations.atomic_write_json", fail_write)

    with pytest.raises(OSError, match="synthetic failure"):
        migrate_json_file(path, target_version=1, apply=True)

    assert path.read_bytes() == original
