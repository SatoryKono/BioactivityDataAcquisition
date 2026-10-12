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
"""FS-001 safety tests for BronzeWriter cleanup (#12102).

Covers: strict date validation, artifact ownership, symlink/reparse
rejection, root containment, filter validation, flat layout.
"""

from __future__ import annotations

import os
import subprocess
import threading
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.bronze import cleanup_support, read_cleanup_mixin
from bioetl.infrastructure.storage.bronze.cleanup_support import (
    bronze_tree_lock,
    destructive_cleanup_supported,
    is_owned_artifact,
    iter_safe_child_dirs,
    safe_rmdir,
    safe_unlink,
    validate_scope_filter,
)
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

pytestmark = pytest.mark.integration
_APPLY_POSIX = pytest.mark.skipif(
    os.name == "nt", reason="Windows destructive cleanup is fail-closed (NOT_VERIFIED)"
)

ARTIFACT = "batch_2024-01-01_12345678-1234-5678-1234-567812345678.jsonl.zst"
SIDECAR = f"{ARTIFACT}.meta.json"
JSON_COPY = ARTIFACT.removesuffix(".zst")
OLD_DATE = "2024-01-01"
CUTOFF = datetime(2024, 6, 1, tzinfo=UTC)


def _make_writer(base_path: Path, *, flat: bool = False) -> BronzeWriter:
    return BronzeWriter(
        base_path=base_path,
        logger=NoOpLogger(),
        metrics=NoOpMetrics(),
        flat_structure=flat,
    )


def _date_dir(root: Path, *parents: str, date: str = OLD_DATE) -> Path:
    date_dir = root.joinpath(*parents, date)
    date_dir.mkdir(parents=True)
    return date_dir


def _write_pair(date_dir: Path, data: bytes = b"x") -> None:
    (date_dir / ARTIFACT).write_bytes(data)
    (date_dir / SIDECAR).write_bytes(b"{}")


def _symlink_or_skip(link: Path, target: Path) -> Path:
    """Create a symlink; fall back to junction on Windows; else skip."""
    try:
        os.symlink(target, link, target_is_directory=True)
        return link
    except (OSError, NotImplementedError):
        pass
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
        )
        if result.returncode == 0:
            return link
    pytest.skip("symlink/junction creation not permitted on this host")


@_APPLY_POSIX
async def test_cleanup_skips_noncanonical_date_dirs(tmp_path: Path) -> None:
    """Only strict YYYY-MM-DD names are cleanup candidates."""
    writer = _make_writer(tmp_path)
    entity = tmp_path / "chembl" / "activity"
    invalid_dates = (
        "0000000000", "9999999999", "2026-1-1", "not-a-date",
        "2026-13-45", "2026-02-29", "2024-13-99", "20240101",
    )
    for name in invalid_dates:
        bad = _date_dir(entity, date=name)
        _write_pair(bad)
    good = _date_dir(entity, date=OLD_DATE)
    _write_pair(good)

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 2
    assert result["directories_removed"] == 1
    for name in invalid_dates:
        assert (entity / name).exists()


@_APPLY_POSIX
async def test_cleanup_preserves_unknown_artifacts(tmp_path: Path) -> None:
    """Unknown files stop deletion and keep the date directory alive."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir)
    (date_dir / "batch.jsonl.zst").write_bytes(b"legacy-name")
    (date_dir / "README.txt").write_bytes(b"keep me")
    (date_dir / "batch_manual_backup.jsonl.zst").write_bytes(b"backup")
    orphan = ARTIFACT.replace("12345678", "87654321", 1)
    (date_dir / orphan).write_bytes(b"orphan")
    sidecar_orphan = ARTIFACT.replace("12345678", "11223344", 1)
    (date_dir / f"{sidecar_orphan}.meta.json").write_bytes(b"orphan sidecar")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 2  # payload + sidecar
    assert result["files_skipped"] == 5
    assert result["directories_removed"] == 0
    assert result["directories_skipped"] == 1
    assert (date_dir / "batch.jsonl.zst").exists()
    assert (date_dir / "README.txt").exists()
    assert (date_dir / "batch_manual_backup.jsonl.zst").read_bytes() == b"backup"
    assert not (date_dir / ARTIFACT).exists()


@_APPLY_POSIX
async def test_cleanup_removes_json_copy_artifact(tmp_path: Path) -> None:
    """Optional uncompressed copies are owned artifacts too."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir)
    (date_dir / JSON_COPY).write_bytes(b"{}")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 3
    assert result["directories_removed"] == 1
    assert not date_dir.exists()


@_APPLY_POSIX
async def test_cleanup_does_not_escape_via_symlinked_entity(tmp_path: Path) -> None:
    """A symlinked entity dir must not lead deletion outside the root."""
    outside = tmp_path.parent / f"{tmp_path.name}_outside"
    outside_date = _date_dir(outside, "escape")
    victim = outside_date / ARTIFACT
    victim.write_bytes(b"victim")

    writer = _make_writer(tmp_path)
    provider_dir = tmp_path / "chembl"
    provider_dir.mkdir()
    _symlink_or_skip(provider_dir / "activity", outside / "escape")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 0
    assert victim.exists()
    assert result["files_skipped"] == 0


@_APPLY_POSIX
async def test_cleanup_skips_symlinked_date_dir(tmp_path: Path) -> None:
    """A symlinked date dir is skipped even when it points inside the root."""
    writer = _make_writer(tmp_path)
    target = tmp_path / "link_target"
    target.mkdir()
    victim = target / ARTIFACT
    victim.write_bytes(b"x")
    entity_dir = tmp_path / "chembl" / "activity"
    entity_dir.mkdir(parents=True)
    _symlink_or_skip(entity_dir / OLD_DATE, target)

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 0
    assert victim.exists()


@_APPLY_POSIX
async def test_cleanup_refuses_link_inside_date_dir(tmp_path: Path) -> None:
    """A symlinked file inside a date dir is not unlinked."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    owned = date_dir / ARTIFACT
    _write_pair(date_dir)
    outside_file = tmp_path.parent / f"{tmp_path.name}_victim.zst"
    outside_file.write_bytes(b"victim")
    try:
        os.symlink(outside_file, date_dir / JSON_COPY)
    except (OSError, NotImplementedError):
        pytest.skip("file symlink not permitted on this host")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 2
    assert result["files_skipped"] == 1
    assert outside_file.exists()


@pytest.mark.parametrize(
    ("provider", "entity"),
    [
        ("..", None),
        ("a/b", None),
        ("a\\b", None),
        ("*", None),
        ("prov?ider", None),
        ("prov.ider", None),
        ("", None),
        ("provider", "e*"),
        ("provider", "x/y"),
    ],
)
async def test_cleanup_rejects_invalid_scope_filters(
    tmp_path: Path, provider: str | None, entity: str | None
) -> None:
    """Scope filters with traversal/glob semantics are rejected."""
    writer = _make_writer(tmp_path)
    with pytest.raises(ValueError, match=r"Invalid .* filter"):
        await writer.cleanup_old_files(CUTOFF, provider=provider, entity=entity)

    with pytest.raises(ValueError, match=r"Invalid .* filter"):
        writer.preview_cleanup(provider=provider, entity=entity)


@_APPLY_POSIX
async def test_cleanup_flat_layout(tmp_path: Path) -> None:
    """Flat layout cleans level-1 date dirs through the same contract."""
    writer = _make_writer(tmp_path, flat=True)
    old_dir = _date_dir(tmp_path)
    _write_pair(old_dir)
    recent = _date_dir(tmp_path, date="2099-01-01")
    (recent / ARTIFACT).write_bytes(b"x")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 2
    assert result["directories_removed"] == 1
    assert not old_dir.exists()
    assert recent.exists()


@_APPLY_POSIX
async def test_cleanup_flat_layout_scope_filter_is_noop(tmp_path: Path) -> None:
    """Provider/entity filters on flat storage cannot scope → refuse to broaden."""
    writer = _make_writer(tmp_path, flat=True)
    old_dir = _date_dir(tmp_path)
    (old_dir / ARTIFACT).write_bytes(b"x")

    result = await writer.cleanup_old_files(CUTOFF, provider="chembl")

    assert result["files_removed"] == 0
    assert old_dir.exists()


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


def test_iter_safe_child_dirs_skips_links(tmp_path: Path) -> None:
    """Traversal yields real dirs and refuses link entries."""
    (tmp_path / "real").mkdir()
    outside = tmp_path.parent / f"{tmp_path.name}_outside2"
    outside.mkdir(exist_ok=True)
    skipped: list[tuple[str, str]] = []
    _symlink_or_skip(tmp_path / "linked", outside)

    result = iter_safe_child_dirs(tmp_path, on_skip=lambda p, r: skipped.append((p, r)))

    assert result == [tmp_path / "real"]
    assert skipped and skipped[0][1] == "link_or_reparse"


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


@_APPLY_POSIX
@pytest.mark.parametrize("anchored", [True])
@pytest.mark.parametrize("flat", [False, True])
@pytest.mark.parametrize("root_link", [False, True])
async def test_cleanup_accepts_links_at_or_above_trusted_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    anchored: bool,
    flat: bool,
    root_link: bool,
) -> None:
    """A trusted root alias must permit both file and directory removal."""
    if anchored and not cleanup_support._ANCHORED_OPS:
        pytest.skip("anchored operations unavailable")
    monkeypatch.setattr(cleanup_support, "_ANCHORED_OPS", anchored)
    target = tmp_path / "target"
    target.mkdir()
    alias = _symlink_or_skip(tmp_path / "alias", target)
    root = alias if root_link else alias / "bronze"
    root.mkdir(exist_ok=True)
    monkeypatch.chdir(tmp_path)
    root = root.relative_to(tmp_path)
    writer = _make_writer(root, flat=flat)
    date_dir = _date_dir(root, *(() if flat else ("chembl", "activity")))
    _write_pair(date_dir, b"payload")

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 2
    assert result["bytes_freed"] == 9
    assert result["directories_removed"] == 1
    assert not date_dir.exists()


@pytest.mark.parametrize("anchored", [True])
@pytest.mark.parametrize("inside", [False, True])
def test_cleanup_reverification_refuses_links_below_trusted_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    anchored: bool,
    inside: bool,
) -> None:
    """Even an internal link below a trusted root alias must be rejected."""
    if anchored and not cleanup_support._ANCHORED_OPS:
        pytest.skip("anchored operations unavailable")
    monkeypatch.setattr(cleanup_support, "_ANCHORED_OPS", anchored)
    target = tmp_path / "target"
    target.mkdir()
    root = _symlink_or_skip(tmp_path / "alias", target)
    destination = (target if inside else tmp_path) / "destination"
    date_dir = _date_dir(destination)
    victim = date_dir / ARTIFACT
    victim.write_bytes(b"keep")
    link = _symlink_or_skip(root / "linked", destination)

    assert not safe_unlink(link / OLD_DATE / ARTIFACT, root, target)
    assert victim.read_bytes() == b"keep"
    victim.unlink()
    assert not safe_rmdir(link / OLD_DATE, root, target)
    assert date_dir.is_dir()


@_APPLY_POSIX
@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("error", [FileNotFoundError, PermissionError])
async def test_cleanup_continues_after_entry_stat_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dry_run: bool,
    error: type[OSError],
) -> None:
    """A failed stat preserves partial counts and does not stop later files."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    other_artifact = ARTIFACT.replace("12345678", "87654321", 1)
    other_sidecar = f"{other_artifact}.meta.json"
    for name in (ARTIFACT, SIDECAR, other_artifact, other_sidecar):
        (date_dir / name).write_bytes(b"data")
    with os.scandir(date_dir) as entries:
        by_name = {entry.name: entry for entry in entries}
    failed = Mock(wraps=by_name[other_sidecar])
    failed.name = other_sidecar
    failed.path = str(date_dir / other_sidecar)
    failed.stat.side_effect = error("entry inaccessible")
    monkeypatch.setattr(
        read_cleanup_mixin,
        "scan_dir_entries",
        lambda _: [by_name[ARTIFACT], by_name[SIDECAR], by_name[other_artifact], failed],
    )
    log_skip = Mock()
    monkeypatch.setattr(writer, "_log_cleanup_skip", log_skip)

    result = await writer.cleanup_old_files(CUTOFF, dry_run=dry_run)

    assert result["files_planned"] == 2
    assert result["files_removed"] == (0 if dry_run else 2)
    assert result["bytes_freed"] == (0 if dry_run else 8)
    assert result["directories_removed"] == 0
    assert result["files_failed"] == 1
    assert result["files_skipped"] == 1  # orphan payload of the failed pair
    failed.stat.assert_called_once_with(follow_symlinks=False)
    log_skip.assert_any_call(str(date_dir / other_sidecar), "stat_error")
    assert (date_dir / other_sidecar).exists()
    assert (date_dir / ARTIFACT).exists() is dry_run
    assert (date_dir / SIDECAR).exists() is dry_run
    assert (date_dir / other_artifact).exists()


@pytest.mark.parametrize("failed_level", ["root", "provider", "entity"])
async def test_discovery_scan_failure_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_level: str
) -> None:
    """A failed ancestor enumeration cannot silently produce a clean result."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir)
    blocked = {
        "root": tmp_path,
        "provider": tmp_path / "chembl",
        "entity": tmp_path / "chembl" / "activity",
    }[failed_level]
    original_scan = cleanup_support.scan_dir_entries
    monkeypatch.setattr(
        cleanup_support,
        "scan_dir_entries",
        lambda path: None if path == blocked else original_scan(path),
    )

    result = await writer.cleanup_old_files(CUTOFF, dry_run=True)

    assert result["directories_failed"] == 1
    assert result["files_planned"] == 0
    assert (date_dir / ARTIFACT).read_bytes() == b"x"


@_APPLY_POSIX
async def test_late_unlink_failure_retains_partial_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later I/O error cannot erase successful removals or retained files."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    second = ARTIFACT.replace("12345678", "87654321", 1)
    for name in (ARTIFACT, SIDECAR, second, f"{second}.meta.json"):
        (date_dir / name).write_bytes(b"data")
    original_unlink = read_cleanup_mixin.safe_unlink
    calls = 0

    def fail_late(*args: object, **kwargs: object) -> bool:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise PermissionError("locked by another process")
        return original_unlink(*args, **kwargs)

    monkeypatch.setattr(read_cleanup_mixin, "safe_unlink", fail_late)
    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_planned"] == 4
    assert result["files_removed"] == 3
    assert result["bytes_freed"] == 12
    assert result["files_failed"] == 1
    assert result["directories_skipped"] == 1
    assert result["directories_removed"] == 0
    assert sum(path.is_file() for path in date_dir.iterdir()) == 1


@_APPLY_POSIX
async def test_stage_cleanup_failure_is_reported_after_file_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A post-unlink staging error does not erase the completed deletion."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir)
    original_rmdir = cleanup_support.os.rmdir
    failed = False

    def fail_first_stage(name: object, **kwargs: object) -> None:
        nonlocal failed
        if str(name).startswith(".bronze-cleanup-stage-") and not failed:
            failed = True
            raise PermissionError("stage directory locked")
        original_rmdir(name, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "rmdir", fail_first_stage)
    result = await writer.cleanup_old_files(CUTOFF)

    assert failed
    assert result["files_removed"] == 2
    assert result["bytes_freed"] == 3
    assert result["directories_removed"] == 1
    assert result["directories_failed"] == 1
    assert not date_dir.exists()
    assert any(path.name.startswith(".bronze-cleanup-stage-") for path in tmp_path.iterdir())


@pytest.mark.skipif(
    not destructive_cleanup_supported(), reason="POSIX handle capability required"
)
def test_same_name_replacement_before_unlink_keeps_foreign_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deterministic rename barrier catches a new inode at the planned name."""
    root = tmp_path / "bronze"
    date_dir = _date_dir(root, "chembl", "activity")
    target = date_dir / ARTIFACT
    target.write_bytes(b"original")
    planned = target.stat()
    backup = date_dir / "original.backup"
    outside = tmp_path / "outside-sentinel"
    outside.write_bytes(b"outside")
    original_rename = cleanup_support.os.rename
    swapped = False

    def replace_at_rename(src: object, dst: object, **kwargs: object) -> None:
        nonlocal swapped
        if src == ARTIFACT and not swapped:
            swapped = True
            target.rename(backup)
            target.write_bytes(b"foreign")
        original_rename(src, dst, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "rename", replace_at_rename)
    assert not safe_unlink(target, root, root, planned)
    assert swapped
    assert target.read_bytes() == b"foreign"
    assert backup.read_bytes() == b"original"
    assert outside.read_bytes() == b"outside"


@_APPLY_POSIX
def test_same_name_replacement_at_unlink_only_removes_staged_inode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The actual unlink targets the isolated old inode, not a new name entry."""
    root = tmp_path / "bronze"
    date_dir = _date_dir(root, "chembl", "activity")
    target = date_dir / ARTIFACT
    target.write_bytes(b"planned")
    planned = target.stat()
    outside = tmp_path / "outside-sentinel"
    outside.write_bytes(b"outside")
    original_unlink = cleanup_support.os.unlink
    replaced = False

    def replace_at_unlink(name: object, **kwargs: object) -> None:
        nonlocal replaced
        if name == ARTIFACT and not replaced:
            replaced = True
            target.write_bytes(b"new writer content")
        original_unlink(name, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "unlink", replace_at_unlink)
    assert safe_unlink(target, root, root, planned)
    assert replaced
    assert target.read_bytes() == b"new writer content"
    assert target.stat().st_ino != planned.st_ino
    assert outside.read_bytes() == b"outside"


@_APPLY_POSIX
@pytest.mark.parametrize("component", ["root", "chembl", "activity", OLD_DATE])
def test_component_swap_before_open_does_not_delete_outside(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, component: str
) -> None:
    root = tmp_path / "bronze"
    date_dir = _date_dir(root, "chembl", "activity")
    target = date_dir / ARTIFACT
    target.write_bytes(b"inside")
    outside_date = _date_dir(tmp_path / "outside", "chembl", "activity")
    outside_target = outside_date / ARTIFACT
    outside_target.write_bytes(b"outside")
    source = {
        "root": root,
        "chembl": root / "chembl",
        "activity": root / "chembl" / "activity",
        OLD_DATE: date_dir,
    }[component]
    destination = {
        "root": tmp_path / "outside",
        "chembl": tmp_path / "outside" / "chembl",
        "activity": tmp_path / "outside" / "chembl" / "activity",
        OLD_DATE: outside_date,
    }[component]
    original_open = cleanup_support.os.open
    swapped = False

    def swap_at_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal swapped
        barrier = str(root) if component == "root" else component
        if str(path) == barrier and not swapped:
            swapped = True
            source.rename(source.with_name(f"{source.name}_backup"))
            os.symlink(destination, source, target_is_directory=True)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "open", swap_at_open)
    try:
        removed = safe_unlink(target, root, root, target.stat())
    except OSError:
        removed = False
    assert not removed
    assert swapped
    assert outside_target.read_bytes() == b"outside"
    assert (
        source.with_name(f"{source.name}_backup")
        / target.relative_to(source)
    ).read_bytes() == b"inside"


@pytest.mark.skipif(
    not destructive_cleanup_supported(), reason="POSIX handle capability required"
)
def test_open_date_renamed_before_unlink_retains_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "bronze"
    date_dir = _date_dir(root, "chembl", "activity")
    target = date_dir / ARTIFACT
    target.write_bytes(b"inside")
    planned = target.stat()
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"outside")
    moved = outside / "moved_date"
    original_rename = cleanup_support.os.rename
    moved_at_barrier = False

    def rename_open_date(src: object, dst: object, **kwargs: object) -> None:
        nonlocal moved_at_barrier
        if src == ARTIFACT and not moved_at_barrier:
            moved_at_barrier = True
            date_dir.rename(moved)
        original_rename(src, dst, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "rename", rename_open_date)
    assert not safe_unlink(target, root, root, planned)
    assert moved_at_barrier
    assert (moved / ARTIFACT).read_bytes() == b"inside"
    assert sentinel.read_bytes() == b"outside"


@_APPLY_POSIX
def test_open_date_renamed_at_unlink_cannot_redirect_staged_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late directory rename does not redirect unlink to its new location."""
    root = tmp_path / "bronze"
    date_dir = _date_dir(root, "chembl", "activity")
    target = date_dir / ARTIFACT
    target.write_bytes(b"planned")
    planned = target.stat()
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_bytes(b"outside")
    moved = outside / "moved_date"
    original_unlink = cleanup_support.os.unlink
    renamed = False

    def rename_at_unlink(name: object, **kwargs: object) -> None:
        nonlocal renamed
        if name == ARTIFACT and not renamed:
            renamed = True
            date_dir.rename(moved)
        original_unlink(name, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "unlink", rename_at_unlink)
    assert safe_unlink(target, root, root, planned)
    assert renamed and moved.is_dir()
    assert not (moved / ARTIFACT).exists()
    assert sentinel.read_bytes() == b"outside"


@pytest.mark.skipif(
    not destructive_cleanup_supported(), reason="POSIX handle capability required"
)
def test_same_name_empty_directory_replacement_is_not_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "bronze"
    date_dir = _date_dir(root, "chembl", "activity")
    planned = date_dir.stat()
    original = date_dir.with_name("original_date")
    outside_empty = tmp_path / "outside_empty"
    outside_empty.mkdir()
    original_rename = cleanup_support.os.rename
    swapped = False

    def replace_at_rename(src: object, dst: object, **kwargs: object) -> None:
        nonlocal swapped
        if src == OLD_DATE and not swapped:
            swapped = True
            date_dir.rename(original)
            date_dir.mkdir()
        original_rename(src, dst, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "rename", replace_at_rename)
    assert not safe_rmdir(date_dir, root, root, planned)
    assert swapped
    assert date_dir.is_dir() and original.is_dir() and outside_empty.is_dir()


@_APPLY_POSIX
def test_same_name_directory_replacement_at_rmdir_is_retained(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The actual rmdir removes the isolated directory, not its replacement."""
    root = tmp_path / "bronze"
    date_dir = _date_dir(root, "chembl", "activity")
    planned = date_dir.stat()
    outside_empty = tmp_path / "outside_empty"
    outside_empty.mkdir()
    original_rmdir = cleanup_support.os.rmdir
    replaced = False

    def replace_at_rmdir(name: object, **kwargs: object) -> None:
        nonlocal replaced
        if name == OLD_DATE and not replaced:
            replaced = True
            date_dir.mkdir()
        original_rmdir(name, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "rmdir", replace_at_rmdir)
    assert safe_rmdir(date_dir, root, root, planned)
    assert replaced
    assert date_dir.is_dir() and date_dir.stat().st_ino != planned.st_ino
    assert outside_empty.is_dir()


@pytest.mark.skipif(
    not destructive_cleanup_supported(), reason="POSIX flock capability required"
)
def test_writer_lock_waits_for_exclusive_cleaner(tmp_path: Path) -> None:
    import fcntl

    root = tmp_path / "bronze"
    root.mkdir()
    started = threading.Event()
    entered = threading.Event()

    def writer() -> None:
        started.set()
        with bronze_tree_lock(root, exclusive=False):
            entered.set()

    with bronze_tree_lock(root, exclusive=True):
        thread = threading.Thread(target=writer)
        thread.start()
        assert started.wait(2)
        probe = os.open(root / ".bronze-cleanup.lock", os.O_RDONLY)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(probe, fcntl.LOCK_SH | fcntl.LOCK_NB)
        finally:
            os.close(probe)
        assert not entered.is_set()
    thread.join(2)
    assert not thread.is_alive() and entered.is_set()


@pytest.mark.skipif(os.name != "nt", reason="Windows-specific fail-closed gate")
async def test_windows_apply_refuses_before_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir)
    outside = tmp_path.parent / f"{tmp_path.name}_outside-sentinel"
    outside.write_bytes(b"outside")
    monkeypatch.setattr(
        writer, "_find_old_date_dirs", Mock(side_effect=AssertionError("traversal"))
    )
    with pytest.raises(NotImplementedError, match="unsupported"):
        await writer.cleanup_old_files(CUTOFF)
    assert (date_dir / ARTIFACT).read_bytes() == b"x"
    assert outside.read_bytes() == b"outside"
