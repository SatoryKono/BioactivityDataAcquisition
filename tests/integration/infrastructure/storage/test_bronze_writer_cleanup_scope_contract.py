# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Scope, ownership, and read-only cleanup guards for BronzeWriter (#12102)."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import pytest
from bioetl.infrastructure.storage.bronze import (
    cleanup_core,
    cleanup_preview_mixin,
    cleanup_support,
)
from bioetl.infrastructure.storage.bronze.cleanup_support import (
    bronze_tree_lock,
    destructive_cleanup_supported,
    is_owned_artifact,
    iter_safe_child_dirs,
    safe_unlink,
    validate_scope_filter,
)

from tests.integration.infrastructure.storage.test_bronze_writer_cleanup_safety import (
    ARTIFACT,
    JSON_COPY,
    OLD_DATE,
    SIDECAR,
    _date_dir,
    _make_writer,
)

pytestmark = pytest.mark.integration


def test_preview_stops_scandir_within_one_oversized_partition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    for index in range(20):
        (date_dir / f"manual_{index}.txt").write_bytes(b"retain")
    original_scandir = cleanup_preview_mixin.os.scandir
    seen = 0

    @contextmanager
    def observed_scandir(path: Path | int | str):
        nonlocal seen
        # Capability probes may pass a directory fd; leave those untouched.
        if isinstance(path, int):
            with original_scandir(path) as entries:
                yield entries
            return
        with original_scandir(path) as entries:
            if Path(path) != date_dir:
                yield entries
                return

            def bounded_entries():
                nonlocal seen
                for entry in entries:
                    seen += 1
                    if seen > 4:
                        raise AssertionError("preview consumed beyond its entry budget")
                    yield entry

            yield bounded_entries()

    monkeypatch.setattr(cleanup_preview_mixin, "_PREVIEW_MAX_ENTRIES", 6)
    monkeypatch.setattr(cleanup_preview_mixin.os, "scandir", observed_scandir)
    with pytest.raises(ValueError, match="filesystem entries"):
        _make_writer(tmp_path).preview_cleanup()
    assert seen == 4
    monkeypatch.setattr(cleanup_preview_mixin.os, "scandir", original_scandir)
    assert len(list(date_dir.iterdir())) == 20


def test_validate_scope_filter_accepts_canonical_names() -> None:
    """Canonical provider/entity names pass validation."""
    validate_scope_filter("chembl", "provider")
    validate_scope_filter("pubchem_compound2", "entity")
    validate_scope_filter(None, "provider")


def test_is_owned_artifact_contract() -> None:
    """Ownership allowlist matches only Bronze writer artifacts."""
    assert is_owned_artifact(ARTIFACT)
    assert is_owned_artifact(SIDECAR)
    assert is_owned_artifact(JSON_COPY)
    assert not is_owned_artifact("batch_2024-01-01_x.jsonl.zst")
    assert not is_owned_artifact("batch_manual_backup.jsonl.zst")
    assert not is_owned_artifact("batch_.jsonl.zst")
    assert not is_owned_artifact("batch.jsonl.zst")
    assert not is_owned_artifact("README.txt")
    assert not is_owned_artifact("batch_2024-01-01_x.parquet")


def test_owned_artifact_requires_valid_date_scope_and_payload_association() -> None:
    """A plausible name or sidecar alone does not establish writer ownership."""
    invalid_day = ARTIFACT.replace(OLD_DATE, "2024-02-30")
    assert not is_owned_artifact(invalid_day)
    assert not is_owned_artifact(ARTIFACT, date_name="2023-01-01")
    assert not is_owned_artifact(SIDECAR, date_name=OLD_DATE, payload_names=set())
    assert is_owned_artifact(SIDECAR, date_name=OLD_DATE, payload_names={ARTIFACT})


def test_absent_handle_capability_refuses_exclusive_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unsupported platform cannot silently enter destructive cleanup."""
    monkeypatch.setattr(cleanup_core, "_ANCHORED_OPS", False)
    assert not destructive_cleanup_supported()
    with pytest.raises(NotImplementedError, match="dir_fd/no-follow"):
        with bronze_tree_lock(tmp_path, exclusive=True):
            pytest.fail("unsupported exclusive lock entered")
    with bronze_tree_lock(tmp_path, exclusive=False):
        pass


def test_discovery_permission_error_is_reported_before_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unreadable scope enumeration remains visible to a read-only plan."""
    original_scandir = cleanup_support.os.scandir

    def deny_scope(path: object) -> os.ScandirIterator[str]:
        if path == tmp_path:
            raise PermissionError("denied scope")
        return original_scandir(path)

    monkeypatch.setattr(cleanup_support.os, "scandir", deny_scope)
    skipped: list[tuple[str, str]] = []
    assert cleanup_support.scan_dir_entries(tmp_path) is None
    assert (
        iter_safe_child_dirs(
            tmp_path, on_skip=lambda path, reason: skipped.append((path, reason))
        )
        == []
    )
    assert skipped == [(str(tmp_path), "scan_error")]


def test_named_scope_stat_failure_is_reported_without_following(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A denied provider lookup cannot become a missing or traversed scope."""
    provider = tmp_path / "chembl"
    provider.mkdir()
    original_lstat = Path.lstat

    def deny_provider(path: Path) -> os.stat_result:
        if path == provider:
            raise PermissionError("denied provider")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", deny_provider)
    skipped: list[tuple[str, str]] = []
    assert (
        cleanup_support.safe_named_child_dir(
            tmp_path,
            "chembl",
            tmp_path,
            on_skip=lambda path, reason: skipped.append((path, reason)),
        )
        is None
    )
    assert skipped == [(str(provider), "stat_error")]
    assert provider.is_dir()


def test_safe_unlink_refuses_outside_root(tmp_path: Path) -> None:
    """safe_unlink never deletes paths resolved outside the trusted root."""
    outside = tmp_path.parent / f"{tmp_path.name}_victim2"
    outside.write_bytes(b"x")

    if destructive_cleanup_supported():
        assert safe_unlink(outside, tmp_path, tmp_path.resolve()) is False
    else:
        with pytest.raises(NotImplementedError):
            safe_unlink(outside, tmp_path, tmp_path.resolve())
    assert outside.exists()
