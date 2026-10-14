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

import asyncio
import os
import subprocess
import threading
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from unittest.mock import MagicMock, Mock
from uuid import UUID

import pytest

from tests.helpers.bronze_cleanup import sidecar_bytes

from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.storage import bronze_writer as bronze_writer_module
from bioetl.infrastructure.storage.bronze import (
    cleanup_core,
    cleanup_planner,
    cleanup_posix,
    cleanup_preview_mixin,
    cleanup_support,
    read_cleanup_mixin,
)
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
    not destructive_cleanup_supported(),
    reason="POSIX anchored destructive capability required (Windows NOT_VERIFIED)",
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


def _sidecar(data: bytes, artifact: str = ARTIFACT, copy: bytes | None = None) -> bytes:
    return sidecar_bytes(data, artifact, copy)


def _write_pair(
    date_dir: Path,
    data: bytes = b"x",
    *,
    artifact: str | None = None,
    copy: bytes | None = None,
) -> None:
    artifact = artifact or ARTIFACT.replace(OLD_DATE, date_dir.name)
    (date_dir / artifact).write_bytes(data)
    (date_dir / f"{artifact}.meta.json").write_bytes(_sidecar(data, artifact, copy))
    if copy is not None:
        (date_dir / artifact.removesuffix(".zst")).write_bytes(copy)


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


async def test_writer_lock_failure_records_attempt_and_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refused shared lock is still one observable public write attempt."""
    metrics = Mock()
    tracing = Mock()
    span = Mock()
    span_context = MagicMock()
    span_context.__enter__.return_value = span
    tracing.get_tracer.return_value.start_as_current_span.return_value = span_context
    writer = BronzeWriter(
        base_path=tmp_path / "bronze",
        logger=NoOpLogger(),
        metrics=metrics,
        tracing=tracing,
    )

    @contextmanager
    def denied_lock(_base_path: Path, *, exclusive: bool, **options):
        assert not exclusive
        raise PermissionError("lock denied")
        yield  # pragma: no cover - retain contextmanager protocol

    monkeypatch.setattr(bronze_writer_module, "bronze_tree_lock", denied_lock)
    with pytest.raises(PermissionError, match="lock denied"):
        await writer.write_bronze(
            records=iter([b"{}\n"]),
            provider="chembl",
            entity="activity",
            date=CUTOFF,
            batch_id=BatchID(UUID(int=1)),
            run_id=RunID(UUID(int=2)),
            run_type=RunType.INCREMENTAL,
            ingestion_ts=CUTOFF,
        )
    metrics.increment_counter.assert_called_once_with(
        "bioetl_bronze_write_attempts_total",
        1,
        {"provider": "chembl", "entity": "activity"},
    )
    tracing.get_tracer.return_value.start_as_current_span.assert_called_once_with(
        "write_bronze"
    )
    assert span_context.__exit__.call_count == 1


@_APPLY_POSIX
async def test_cleanup_skips_noncanonical_date_dirs(tmp_path: Path) -> None:
    """Only strict YYYY-MM-DD names are cleanup candidates."""
    writer = _make_writer(tmp_path)
    entity = tmp_path / "chembl" / "activity"
    invalid_dates = (
        "0000000000",
        "9999999999",
        "2026-1-1",
        "not-a-date",
        "2026-13-45",
        "2026-02-29",
        "2024-13-99",
        "20240101",
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
async def test_calendar_cutoff_keeps_boundary_and_fresh_dates(tmp_path: Path) -> None:
    """A valid leap day is old; cutoff day and later dates are retained."""
    writer = _make_writer(tmp_path)
    entity_dir = tmp_path / "chembl" / "activity"
    partitions: dict[str, Path] = {}
    for date_name in ("2024-02-29", "2024-06-01", "2024-06-02"):
        date_dir = _date_dir(entity_dir, date=date_name)
        artifact = ARTIFACT.replace(OLD_DATE, date_name)
        _write_pair(date_dir, date_name.encode(), artifact=artifact)
        partitions[date_name] = date_dir

    result = await writer.cleanup_old_files(datetime(2024, 6, 1, tzinfo=UTC))

    assert result["files_removed"] == 2
    assert not partitions["2024-02-29"].exists()
    assert partitions["2024-06-01"].is_dir()
    assert partitions["2024-06-02"].is_dir()


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
    unknown_dir = date_dir / "manual"
    unknown_dir.mkdir()
    (unknown_dir / "keep.txt").write_bytes(b"nested sentinel")
    retained_bytes = (
        sum(path.stat().st_size for path in date_dir.iterdir() if path.is_file())
        - (date_dir / ARTIFACT).stat().st_size
        - (date_dir / SIDECAR).stat().st_size
    )

    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 2  # payload + sidecar
    assert result["files_skipped"] == 5
    assert result["bytes_skipped"] == retained_bytes
    assert result["directories_removed"] == 0
    assert result["directories_skipped"] == 2  # manual child and date parent
    assert (date_dir / "batch.jsonl.zst").exists()
    assert (date_dir / "README.txt").exists()
    assert (date_dir / "batch_manual_backup.jsonl.zst").read_bytes() == b"backup"
    assert (unknown_dir / "keep.txt").read_bytes() == b"nested sentinel"
    assert not (date_dir / ARTIFACT).exists()


async def test_noncanonical_scope_directories_are_never_owned(tmp_path: Path) -> None:
    """Unfiltered cleanup and preview reject names the writer cannot create."""
    writer = _make_writer(tmp_path)
    foreign = [
        _date_dir(tmp_path, "manual-backup", "activity"),
        _date_dir(tmp_path, "chembl", "activity-copy"),
    ]
    for date_dir in foreign:
        _write_pair(date_dir, b"foreign")
    before = {
        str(path): path.read_bytes()
        for date_dir in foreign
        for path in (date_dir / ARTIFACT, date_dir / SIDECAR)
    }

    dry = await writer.cleanup_old_files(CUTOFF, dry_run=True)
    preview = writer.preview_cleanup()
    assert dry["files_planned"] == 0
    assert preview["file_count"] == 0
    if destructive_cleanup_supported():
        applied = await writer.cleanup_old_files(CUTOFF)
        assert applied["files_removed"] == 0
        assert applied["directories_skipped"] >= 2
    else:
        with pytest.raises(NotImplementedError):
            await writer.cleanup_old_files(CUTOFF)
    assert {path: Path(path).read_bytes() for path in before} == before


@_APPLY_POSIX
async def test_cleanup_removes_json_copy_artifact(tmp_path: Path) -> None:
    """Optional uncompressed copies are owned artifacts too."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir, copy=b"{}")

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
    """An unattested symlink copy prevents removal of its entire group."""
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

    assert result["files_removed"] == 0
    assert result["files_conflicted"] == 2
    assert result["files_skipped"] == 1
    assert owned.read_bytes() == b"x"
    assert (date_dir / SIDECAR).read_bytes() == _sidecar(b"x")
    assert (date_dir / JSON_COPY).is_symlink()
    assert outside_file.read_bytes() == b"victim"


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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str | None,
    entity: str | None,
) -> None:
    """Scope filters with traversal/glob semantics are rejected."""
    writer = _make_writer(tmp_path)
    discovery = Mock(side_effect=AssertionError("filesystem traversal started"))
    preview_resolution = Mock(side_effect=AssertionError("preview traversal started"))
    monkeypatch.setattr(writer, "_find_old_date_dirs", discovery)
    monkeypatch.setattr(writer, "_resolve_bronze_preview_root", preview_resolution)
    with pytest.raises(ValueError, match=r"Invalid .* filter"):
        await writer.cleanup_old_files(CUTOFF, provider=provider, entity=entity)

    with pytest.raises(ValueError, match=r"Invalid .* filter"):
        writer.preview_cleanup(provider=provider, entity=entity)
    discovery.assert_not_called()
    preview_resolution.assert_not_called()


def test_preview_stops_scandir_within_one_oversized_partition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    for index in range(20):
        (date_dir / f"manual_{index}.txt").write_bytes(b"retain")
    original_scandir = cleanup_preview_mixin.os.scandir
    seen = 0

    @contextmanager
    def observed_scandir(path: Path):
        nonlocal seen
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
async def test_cleanup_refuses_links_at_or_above_trusted_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    anchored: bool,
    flat: bool,
    root_link: bool,
) -> None:
    """Root or ancestor aliases cannot establish destructive ownership."""
    if anchored and not cleanup_core._ANCHORED_OPS:
        pytest.skip("anchored operations unavailable")
    monkeypatch.setattr(cleanup_core, "_ANCHORED_OPS", anchored)
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

    dry = await writer.cleanup_old_files(CUTOFF, dry_run=True)
    preview = writer.preview_cleanup()
    assert dry["files_planned"] == 0
    assert preview["file_count"] == 0
    with pytest.raises(OSError):
        await writer.cleanup_old_files(CUTOFF)
    assert (date_dir / ARTIFACT).read_bytes() == b"payload"
    assert (date_dir / SIDECAR).read_bytes() == _sidecar(b"payload")


@pytest.mark.parametrize("anchored", [True])
@pytest.mark.parametrize("inside", [False, True])
def test_cleanup_reverification_refuses_links_below_trusted_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    anchored: bool,
    inside: bool,
) -> None:
    """Even an internal link below a trusted root alias must be rejected."""
    if anchored and not cleanup_core._ANCHORED_OPS:
        pytest.skip("anchored operations unavailable")
    monkeypatch.setattr(cleanup_core, "_ANCHORED_OPS", anchored)
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


@pytest.mark.parametrize("linked_ancestor", [False, True])
async def test_public_cleanup_rejects_linked_root_or_ancestor(
    tmp_path: Path, linked_ancestor: bool
) -> None:
    outside_parent = tmp_path / "outside-parent"
    outside_root = outside_parent / "bronze"
    date_dir = _date_dir(outside_root, "chembl", "activity")
    _write_pair(date_dir, b"outside sentinel")
    empty_outside = date_dir / "empty"
    empty_outside.mkdir()
    if linked_ancestor:
        root = _symlink_or_skip(tmp_path / "linked-parent", outside_parent) / "bronze"
    else:
        root = _symlink_or_skip(tmp_path / "bronze", outside_root)
    writer = _make_writer(root)

    dry = await writer.cleanup_old_files(CUTOFF, dry_run=True)
    preview = writer.preview_cleanup()
    assert dry["files_planned"] == 0
    assert dry["directories_planned"] == 0
    assert preview["file_count"] == 0
    assert not preview["exists"]
    with pytest.raises((OSError, NotImplementedError)):
        await writer.cleanup_old_files(CUTOFF)
    if destructive_cleanup_supported():
        assert not safe_unlink(
            root / "chembl" / "activity" / OLD_DATE / ARTIFACT,
            root,
            outside_root,
            (date_dir / ARTIFACT).lstat(),
        )
        assert not safe_rmdir(
            root / "chembl" / "activity" / OLD_DATE / "empty",
            root,
            outside_root,
            empty_outside.lstat(),
        )
    assert (date_dir / ARTIFACT).read_bytes() == b"outside sentinel"
    assert (date_dir / SIDECAR).read_bytes() == _sidecar(b"outside sentinel")
    assert empty_outside.is_dir()
    assert not (outside_root / ".bronze-cleanup.lock").exists()


@_APPLY_POSIX
async def test_root_replaced_by_link_at_handle_open_preserves_external_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "bronze"
    _write_pair(_date_dir(root, "chembl", "activity"))
    moved = tmp_path / "moved"
    outside = tmp_path / "outside"
    outside_date = _date_dir(outside, "chembl", "activity")
    _write_pair(outside_date, b"outside sentinel")
    empty_outside = outside_date / "empty"
    empty_outside.mkdir()
    original_open = cleanup_core.os.open
    switched = False

    def replace_before_open(
        path: object, flags: int, *args: object, **kwargs: object
    ) -> int:
        nonlocal switched
        if path == root.name and kwargs.get("dir_fd") is not None and not switched:
            switched = True
            root.rename(moved)
            os.symlink(outside, root, target_is_directory=True)
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(cleanup_core.os, "open", replace_before_open)
    with pytest.raises(OSError):
        await _make_writer(root).cleanup_old_files(CUTOFF)
    assert switched
    assert (outside_date / ARTIFACT).read_bytes() == b"outside sentinel"
    assert (outside_date / SIDECAR).read_bytes() == _sidecar(b"outside sentinel")
    assert empty_outside.is_dir()
    assert (moved / "chembl" / "activity" / OLD_DATE / ARTIFACT).is_file()


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
    _write_pair(date_dir, b"data")
    _write_pair(date_dir, b"data", artifact=other_artifact)
    with os.scandir(date_dir) as entries:
        by_name = {entry.name: entry for entry in entries}
    failed = Mock(wraps=by_name[other_sidecar])
    failed.name = other_sidecar
    failed.path = str(date_dir / other_sidecar)
    failed.stat.side_effect = error("entry inaccessible")
    monkeypatch.setattr(
        cleanup_planner,
        "scan_dir_entries",
        lambda _: [
            by_name[ARTIFACT],
            by_name[SIDECAR],
            by_name[other_artifact],
            failed,
        ],
    )
    log_skip = Mock()
    monkeypatch.setattr(writer, "_log_cleanup_skip", log_skip)

    result = await writer.cleanup_old_files(CUTOFF, dry_run=dry_run)

    assert result["files_planned"] == 2
    assert result["files_removed"] == (0 if dry_run else 2)
    assert result["bytes_freed"] == (0 if dry_run else 4 + len(_sidecar(b"data")))
    assert result["directories_removed"] == 0
    assert result["files_failed"] == 1
    assert result["bytes_failed"] == 0  # stat did not yield a reliable size
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
    """A later group error retains exact counts and converges on retry."""
    writer = _make_writer(tmp_path)
    metrics = Mock()
    writer._metrics = metrics
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    second = ARTIFACT.replace("12345678", "87654321", 1)
    _write_pair(date_dir, b"data")
    _write_pair(date_dir, b"data", artifact=second)
    original_unlink = os.unlink
    failed = False

    def fail_late(name, *args, **kwargs):
        nonlocal failed
        if name == "sidecar" and not failed:
            failed = True
            raise PermissionError("locked by another process")
        return original_unlink(name, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", fail_late)
    result = await writer.cleanup_old_files(CUTOFF)
    assert result["files_planned"] == 4
    assert result["files_removed"] == 3
    assert result["bytes_freed"] == 8 + len(_sidecar(b"data", second))
    assert result["files_failed"] == 1
    assert result["bytes_failed"] == len(_sidecar(b"data"))
    assert result["directories_skipped"] == 1
    assert result["directories_removed"] == 0
    assert date_dir.exists() and not list(date_dir.iterdir())
    staged = list(tmp_path.glob(".bronze-group-stage-*/sidecar"))
    assert len(staged) == 1 and staged[0].read_bytes() == _sidecar(b"data")
    metrics.increment_counter.assert_any_call(
        "bioetl_bronze_cleanup_files_failed_total", 1, {"operation": "cleanup"}
    )
    metrics.increment_counter.assert_any_call(
        "bioetl_bronze_cleanup_bytes_failed_total",
        len(_sidecar(b"data")),
        {"operation": "cleanup"},
    )
    monkeypatch.setattr(os, "unlink", original_unlink)
    retry = await writer.cleanup_old_files(CUTOFF)
    assert retry["files_removed"] == 1
    assert retry["bytes_freed"] == len(_sidecar(b"data"))
    assert retry["directories_removed"] == 1
    assert not date_dir.exists()
    assert not list(tmp_path.glob(".bronze-group-stage-*"))


@_APPLY_POSIX
async def test_failed_copy_keeps_its_payload_and_sidecar_retryable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir, b"payload", copy=b"copy")
    original_unlink = os.unlink

    def fail_copy(name, *args, **kwargs):
        if name == "copy":
            raise PermissionError("injected copy failure")
        return original_unlink(name, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", fail_copy)
    first = await writer.cleanup_old_files(CUTOFF)
    assert first["files_planned"] == 3
    assert first["files_removed"] == 0
    assert first["files_failed"] == 3
    assert (date_dir / ARTIFACT).read_bytes() == b"payload"
    assert (date_dir / SIDECAR).read_bytes() == _sidecar(b"payload", copy=b"copy")
    staged = list(tmp_path.glob(".bronze-group-stage-*/copy"))
    assert len(staged) == 1 and staged[0].read_bytes() == b"copy"
    monkeypatch.setattr(os, "unlink", original_unlink)
    second = await writer.cleanup_old_files(CUTOFF)
    assert second["files_removed"] == 3
    assert second["directories_removed"] == 1


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
        if str(name).startswith(".bronze-group-stage-") and not failed:
            failed = True
            raise PermissionError("stage directory locked")
        original_rmdir(name, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "rmdir", fail_first_stage)
    result = await writer.cleanup_old_files(CUTOFF)

    assert failed
    assert result["files_removed"] == 2
    assert result["bytes_freed"] == 1 + len(_sidecar(b"x"))
    assert result["directories_removed"] == 0
    assert result["directories_failed"] == 1
    assert result["directories_skipped"] == 1
    assert date_dir.is_dir() and not list(date_dir.iterdir())
    assert any(
        path.name.startswith(".bronze-group-stage-") for path in tmp_path.iterdir()
    )
    assert list((tmp_path / ".bronze-group-journals").glob("*.json"))
    monkeypatch.setattr(cleanup_support.os, "rmdir", original_rmdir)
    retry = await writer.cleanup_old_files(CUTOFF)
    assert retry["files_removed"] == 0
    assert retry["directories_removed"] == 1
    assert not date_dir.exists()
    assert not list(tmp_path.glob(".bronze-group-stage-*"))
    assert not list((tmp_path / ".bronze-group-journals").glob("*.json"))


@_APPLY_POSIX
def test_final_stage_sync_failure_keeps_removed_count_and_closes_fd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A post-unlink fsync error is a stage failure, not an undone deletion."""
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    target = date_dir / ARTIFACT
    target.write_bytes(b"owned")
    original_unlink = cleanup_posix.os.unlink
    original_fsync = cleanup_posix.os.fsync
    removed = False
    failed_fd: int | None = None
    stage_errors: list[OSError] = []

    def track_unlink(path: object, **kwargs: object) -> None:
        nonlocal removed
        original_unlink(path, **kwargs)
        if path == ARTIFACT:
            removed = True

    def fail_final_sync(fd: int) -> None:
        nonlocal failed_fd
        if removed and failed_fd is None:
            failed_fd = fd
            raise OSError("injected final stage sync")
        original_fsync(fd)

    monkeypatch.setattr(cleanup_posix.os, "unlink", track_unlink)
    monkeypatch.setattr(cleanup_posix.os, "fsync", fail_final_sync)
    assert safe_unlink(
        target,
        tmp_path,
        tmp_path,
        target.stat(),
        on_stage_error=lambda _name, error: stage_errors.append(error),
    )
    assert removed and not target.exists()
    assert len(stage_errors) == 1
    assert "final stage sync" in str(stage_errors[0])
    assert failed_fd is not None
    with pytest.raises(OSError):
        os.fstat(failed_fd)


@_APPLY_POSIX
async def test_date_rmdir_failure_preserves_partial_file_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed directory removal follows successful files in the result."""
    writer = _make_writer(tmp_path)
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir)
    original_rmdir = cleanup_support.os.rmdir

    def deny_date_rmdir(name: object, **kwargs: object) -> None:
        if name == OLD_DATE:
            raise PermissionError("directory locked")
        original_rmdir(name, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "rmdir", deny_date_rmdir)
    result = await writer.cleanup_old_files(CUTOFF)

    assert result["files_removed"] == 2
    assert result["bytes_freed"] == 1 + len(_sidecar(b"x"))
    assert result["directories_failed"] == 1
    assert result["directories_removed"] == 0
    assert date_dir.is_dir() and not list(date_dir.iterdir())


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
        barrier = root.name if component == "root" else component
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
        source.with_name(f"{source.name}_backup") / target.relative_to(source)
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


@_APPLY_POSIX
@pytest.mark.parametrize("component", ["root", "provider"])
def test_root_or_provider_replaced_at_unlink_keeps_outside_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, component: str
) -> None:
    """After isolation, an ancestor swap cannot redirect the staged unlink."""
    root = tmp_path / "bronze"
    date_dir = _date_dir(root, "chembl", "activity")
    target = date_dir / ARTIFACT
    target.write_bytes(b"planned")
    planned = target.stat()
    outside = tmp_path / "outside"
    outside_date = _date_dir(outside, "chembl", "activity")
    outside_target = outside_date / ARTIFACT
    outside_target.write_bytes(b"outside")
    original_unlink = cleanup_support.os.unlink
    source = root if component == "root" else root / "chembl"
    destination = outside if component == "root" else outside / "chembl"
    moved = source.with_name(f"{source.name}_moved")
    replaced = False

    def replace_at_unlink(name: object, **kwargs: object) -> None:
        nonlocal replaced
        if name == ARTIFACT and not replaced:
            replaced = True
            source.rename(moved)
            os.symlink(destination, source, target_is_directory=True)
        original_unlink(name, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "unlink", replace_at_unlink)
    assert safe_unlink(target, root, root, planned)
    assert replaced
    assert outside_target.read_bytes() == b"outside"
    remainder = (
        Path("chembl") / "activity" / OLD_DATE
        if component == "root"
        else Path("activity") / OLD_DATE
    )
    moved_date = moved / remainder
    assert moved_date.is_dir() and not (moved_date / ARTIFACT).exists()


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


@_APPLY_POSIX
def test_root_replaced_at_rmdir_keeps_outside_empty_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late root swap cannot redirect rmdir to an unrelated directory."""
    root = tmp_path / "bronze"
    date_dir = _date_dir(root, "chembl", "activity")
    planned = date_dir.stat()
    outside = tmp_path / "outside"
    outside_date = _date_dir(outside, "chembl", "activity")
    original_rmdir = cleanup_support.os.rmdir
    moved_root = tmp_path / "bronze_moved"
    replaced = False

    def replace_at_rmdir(name: object, **kwargs: object) -> None:
        nonlocal replaced
        if name == OLD_DATE and not replaced:
            replaced = True
            root.rename(moved_root)
            os.symlink(outside, root, target_is_directory=True)
        original_rmdir(name, **kwargs)

    monkeypatch.setattr(cleanup_support.os, "rmdir", replace_at_rmdir)
    assert safe_rmdir(date_dir, root, root, planned)
    assert replaced
    assert outside_date.is_dir() and not list(outside_date.iterdir())
    assert not (moved_root / "chembl" / "activity" / OLD_DATE).exists()


async def test_shielded_io_wait_propagates_repeated_cancellation_after_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repeated cancellation must not end the wait before in-flight I/O."""
    release = asyncio.Event()
    entered = asyncio.Event()
    retry_once = asyncio.Event()
    retry_twice = asyncio.Event()

    async def blocked_io() -> None:
        await release.wait()

    io_task = asyncio.create_task(blocked_io())
    original_shield = asyncio.shield
    shield_calls = 0

    def observed_shield(task: asyncio.Task[None]) -> asyncio.Future[None]:
        nonlocal shield_calls
        if task is io_task:
            shield_calls += 1
            if shield_calls == 1:
                entered.set()
            elif shield_calls == 2:
                retry_once.set()
            elif shield_calls == 3:
                retry_twice.set()
        return original_shield(task)

    monkeypatch.setattr(bronze_writer_module.asyncio, "shield", observed_shield)
    waiter = asyncio.create_task(
        bronze_writer_module._wait_for_task_completion(io_task)
    )
    try:
        await asyncio.wait_for(entered.wait(), 3)
        waiter.cancel()
        await asyncio.wait_for(retry_once.wait(), 3)
        waiter.cancel()
        await asyncio.wait_for(retry_twice.wait(), 3)
        assert not io_task.done()
        assert not waiter.done()
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(waiter, 3)
    assert io_task.done()


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


@_APPLY_POSIX
async def test_cancelled_writer_keeps_lock_until_io_finishes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancellation cannot release the shared lock ahead of in-flight I/O."""
    import fcntl

    writer = _make_writer(tmp_path)
    batch_id = BatchID(UUID(int=1))
    run_id = RunID(UUID(int=2))
    run_type = RunType.INCREMENTAL
    writing = asyncio.Event()
    release_write = asyncio.Event()
    waiting_after_cancel = asyncio.Event()
    original_wait = bronze_writer_module._wait_for_task_completion

    async def watched_wait(task: asyncio.Task[object]) -> None:
        waiting_after_cancel.set()
        await original_wait(task)

    async def blocked_write(_request: object, _locked_root: Path) -> object:
        writing.set()
        await release_write.wait()
        return Mock()

    monkeypatch.setattr(bronze_writer_module, "_wait_for_task_completion", watched_wait)
    monkeypatch.setattr(writer, "_write_bronze_with_tracing", blocked_write)
    write_task = asyncio.create_task(
        writer.write_bronze(
            records=iter([b"{}"]),
            provider="chembl",
            entity="activity",
            date=CUTOFF,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=CUTOFF,
        )
    )
    await asyncio.wait_for(writing.wait(), 3)
    write_task.cancel()
    await asyncio.wait_for(waiting_after_cancel.wait(), 3)
    write_task.cancel()
    probe = os.open(tmp_path / ".bronze-cleanup.lock", os.O_RDONLY)
    try:
        with pytest.raises(BlockingIOError):
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(probe)
    release_write.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(write_task, 3)
    with bronze_tree_lock(tmp_path, exclusive=True):
        pass


@_APPLY_POSIX
async def test_cancelled_writer_waiting_for_lock_does_not_leak_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An acquire already running in a thread is released after cancellation."""
    import fcntl

    tmp_path.mkdir(exist_ok=True)
    writer = _make_writer(tmp_path)
    batch_id = BatchID(UUID(int=1))
    run_id = RunID(UUID(int=2))
    run_type = RunType.INCREMENTAL
    attempted = threading.Event()
    acquired = threading.Event()
    original_lock = bronze_tree_lock

    async def real_to_thread(
        func: Callable[..., object], /, *args: object, **kwargs: object
    ) -> object:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    # Repository test setup inlines asyncio.to_thread by default. This case
    # explicitly needs a blocked worker and event-loop progress at the same time.
    monkeypatch.setattr(asyncio, "to_thread", real_to_thread)

    @contextmanager
    def observed_lock(base_path: Path, *, exclusive: bool, **options):
        attempted.set()
        with original_lock(base_path, exclusive=exclusive):
            acquired.set()
            yield

    monkeypatch.setattr(bronze_writer_module, "bronze_tree_lock", observed_lock)
    with bronze_tree_lock(tmp_path, exclusive=True):
        write_task = asyncio.create_task(
            writer.write_bronze(
                records=iter([b"{}"]),
                provider="chembl",
                entity="activity",
                date=CUTOFF,
                batch_id=batch_id,
                run_id=run_id,
                run_type=run_type,
                ingestion_ts=CUTOFF,
            )
        )
        assert await asyncio.wait_for(asyncio.to_thread(attempted.wait), 3)
        write_task.cancel()
    assert await asyncio.wait_for(asyncio.to_thread(acquired.wait), 3)
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(write_task, 3)
    probe = os.open(tmp_path / ".bronze-cleanup.lock", os.O_RDONLY)
    try:
        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(probe)


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


@pytest.mark.skipif(os.name != "nt", reason="Windows junction-specific case")
async def test_windows_junction_preview_skips_and_apply_refuses(tmp_path: Path) -> None:
    """A junction is distinct from a symlink and never enables apply."""
    root = tmp_path / "bronze"
    provider_dir = root / "chembl"
    provider_dir.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside_date = _date_dir(outside, date=OLD_DATE)
    _write_pair(outside_date)
    junction = provider_dir / "activity"
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(outside)],
        capture_output=True,
        check=False,
    )
    if created.returncode != 0:
        pytest.skip("Windows junction capability unavailable (NOT_VERIFIED)")
    writer = _make_writer(root)

    dry = await writer.cleanup_old_files(CUTOFF, dry_run=True)
    preview = writer.preview_cleanup(provider="chembl", entity="activity")
    with pytest.raises(NotImplementedError, match="unsupported"):
        await writer.cleanup_old_files(CUTOFF)

    assert dry["files_planned"] == 0
    assert preview["file_count"] == 0
    assert preview["exists"] is False
    assert (outside_date / ARTIFACT).read_bytes() == b"x"


@_APPLY_POSIX
async def test_cleanup_missing_root_never_traverses_later_backfill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An absent root is a completed no-op, even if a writer creates it next."""
    root = tmp_path / "bronze"
    writer = _make_writer(root)

    def unexpected_discovery(*_args: object, **_kwargs: object) -> list[Path]:
        _write_pair(_date_dir(root, "chembl", "activity"))
        raise AssertionError("absent-root cleanup must not discover")

    monkeypatch.setattr(writer, "_find_old_date_dirs", unexpected_discovery)
    result = await writer.cleanup_old_files(CUTOFF)
    assert result["files_removed"] == 0
    assert not root.exists()


@_APPLY_POSIX
async def test_cleanup_refuses_switched_alias_after_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A switched alias cannot redirect cleanup to another unlocked root."""
    old_root, new_root = tmp_path / "old", tmp_path / "new"
    alias = tmp_path / "alias"
    old_date = _date_dir(alias, "chembl", "activity")
    new_date = _date_dir(new_root, "chembl", "activity")
    _write_pair(old_date)
    _write_pair(new_date, b"outside")
    writer = _make_writer(alias)
    original_lock = bronze_tree_lock

    @contextmanager
    def switch_after_lock(base_path: Path, *, exclusive: bool, **options):
        with original_lock(base_path, exclusive=exclusive, **options) as locked_root:
            alias.rename(old_root)
            alias.symlink_to(new_root, target_is_directory=True)
            yield locked_root

    monkeypatch.setattr(read_cleanup_mixin, "bronze_tree_lock", switch_after_lock)
    result = await writer.cleanup_old_files(CUTOFF)
    assert result["files_removed"] == 0
    assert (old_root / old_date.relative_to(alias) / ARTIFACT).is_file()
    assert (new_date / ARTIFACT).read_bytes() == b"outside"


@_APPLY_POSIX
@pytest.mark.parametrize("replacement_barrier", ["after_lock", "before_unlink"])
async def test_replaced_root_cannot_redirect_locked_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement_barrier: str,
) -> None:
    """The locked root FD rejects a different inode at either barrier."""
    root = tmp_path / "bronze"
    original_date = _date_dir(root, "chembl", "activity")
    _write_pair(original_date)
    replacement = tmp_path / "replacement"
    replacement_date = _date_dir(replacement, "chembl", "activity")
    _write_pair(replacement_date, b"outside")
    moved = tmp_path / "moved_root"
    outside_empty = tmp_path / "outside_empty"
    outside_empty.mkdir()
    writer = _make_writer(root)
    switched = False

    def switch() -> None:
        nonlocal switched
        if switched:
            return
        root.rename(moved)
        replacement.rename(root)
        switched = True

    if replacement_barrier == "after_lock":
        original_lock = bronze_tree_lock

        @contextmanager
        def switch_after_lock(base_path: Path, *, exclusive: bool, **options):
            with original_lock(base_path, exclusive=exclusive, **options) as lease:
                switch()
                yield lease

        monkeypatch.setattr(read_cleanup_mixin, "bronze_tree_lock", switch_after_lock)
    else:
        from bioetl.infrastructure.storage.bronze.cleanup_group_journal import (
            GroupJournal,
        )

        original_recover = GroupJournal.recover_with_result

        def switch_before_unlink(journal, *args, **kwargs):
            switch()
            return original_recover(journal, *args, **kwargs)

        monkeypatch.setattr(GroupJournal, "recover_with_result", switch_before_unlink)

    result = await writer.cleanup_old_files(CUTOFF)
    assert switched and result["files_removed"] == 0
    assert result["files_conflicted"] + result["directories_conflicted"] >= 1
    assert (moved / "chembl" / "activity" / OLD_DATE / ARTIFACT).read_bytes() == b"x"
    assert (
        root / "chembl" / "activity" / OLD_DATE / ARTIFACT
    ).read_bytes() == b"outside"
    assert outside_empty.is_dir() and not list(outside_empty.iterdir())


async def test_cancelled_completed_cleanup_emits_exact_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = _make_writer(tmp_path)
    writer._logger = Mock()
    writer._metrics = Mock()
    started, finish = threading.Event(), threading.Event()
    result = writer._empty_cleanup_stats()
    result.update(files_removed=2, bytes_freed=17, files_failed=1, bytes_failed=3)

    def controlled_worker(*_args: object) -> dict[str, int]:
        started.set()
        assert finish.wait(5)
        return result

    monkeypatch.setattr(writer, "_cleanup_old_files_sync", controlled_worker)
    task = asyncio.create_task(writer.cleanup_old_files(CUTOFF))
    try:
        for _ in range(300):
            if started.is_set():
                break
            await asyncio.sleep(0.01)
        assert started.is_set()
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
    finally:
        finish.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    writer._logger.info.assert_called_once_with(
        "bronze_cleanup_complete", cutoff="2024-06-01", dry_run=False, **result
    )
    writer._metrics.increment_counter.assert_any_call(
        "bioetl_bronze_files_removed_total", 2, {"operation": "cleanup"}
    )
    writer._metrics.increment_counter.assert_any_call(
        "bioetl_bronze_bytes_freed_total", 17, {"operation": "cleanup"}
    )


@_APPLY_POSIX
async def test_cancelled_cleanup_waiter_finishes_without_late_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cancellation while flock blocks prevents deletion after lock release."""
    root = tmp_path / "bronze"
    date_dir = _date_dir(root, "chembl", "activity")
    _write_pair(date_dir)
    writer = _make_writer(root)
    attempted = threading.Event()
    original_lock = bronze_tree_lock

    async def real_to_thread(
        func: Callable[..., object], /, *args: object, **kwargs: object
    ) -> object:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    @contextmanager
    def observed_lock(base_path: Path, *, exclusive: bool, **options):
        attempted.set()
        with original_lock(base_path, exclusive=exclusive, **options) as locked_root:
            yield locked_root

    monkeypatch.setattr(asyncio, "to_thread", real_to_thread)
    monkeypatch.setattr(read_cleanup_mixin, "bronze_tree_lock", observed_lock)
    with original_lock(root, exclusive=False):
        task = asyncio.create_task(writer.cleanup_old_files(CUTOFF))
        assert await asyncio.wait_for(asyncio.to_thread(attempted.wait), 3)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        assert (date_dir / ARTIFACT).read_bytes() == b"x"
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, 3)
    assert (date_dir / ARTIFACT).read_bytes() == b"x"


@_APPLY_POSIX
def test_staged_unlink_error_restores_canonical_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir)
    target = date_dir / ARTIFACT
    original_unlink = cleanup_support.os.unlink

    def fail_unlink(path: str, *, dir_fd: int | None = None) -> None:
        if path == ARTIFACT and dir_fd is not None:
            raise PermissionError("injected unlink failure")
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(cleanup_support.os, "unlink", fail_unlink)
    with pytest.raises(PermissionError, match="injected"):
        safe_unlink(target, tmp_path, tmp_path, target.lstat())
    assert target.read_bytes() == b"x"
    assert len(list(tmp_path.glob(".bronze-cleanup-stage-*"))) == 1
    monkeypatch.setattr(cleanup_support.os, "unlink", original_unlink)
    with bronze_tree_lock(tmp_path, exclusive=True):
        pass
    assert not list(tmp_path.glob(".bronze-cleanup-stage-*"))


@_APPLY_POSIX
def test_restored_staged_entry_syncs_parent_before_journal_discard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The destination directory is made durable after restoration."""
    stage, parent = tmp_path / "stage", tmp_path / "parent"
    stage.mkdir()
    parent.mkdir()
    (stage / "owned").write_bytes(b"retained")
    stage_fd = os.open(stage, os.O_RDONLY | os.O_DIRECTORY)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
    original_fsync = cleanup_posix.os.fsync
    synced: list[int] = []

    def track_sync(fd: int) -> None:
        synced.append(fd)
        original_fsync(fd)

    monkeypatch.setattr(cleanup_posix.os, "fsync", track_sync)
    try:
        cleanup_posix._restore_staged("owned", stage_fd, parent_fd)
    finally:
        os.close(parent_fd)
        os.close(stage_fd)
    assert parent_fd in synced
    assert (parent / "owned").read_bytes() == b"retained"


@_APPLY_POSIX
def test_interrupted_stage_is_restored_before_next_cleanup_plan(tmp_path: Path) -> None:
    """A durable origin journal makes a staged inode recoverable on restart."""
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir)
    target = date_dir / ARTIFACT
    root_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    parent_fd = os.open(date_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with cleanup_support._private_stage(
            root_fd,
            target.relative_to(tmp_path),
            target.lstat(),
            on_stage_error=lambda _name, _error: None,
        ) as stage_fd:
            os.rename(ARTIFACT, ARTIFACT, src_dir_fd=parent_fd, dst_dir_fd=stage_fd)
            os.fsync(parent_fd)
            os.fsync(stage_fd)
    finally:
        os.close(parent_fd)
        os.close(root_fd)
    assert not target.exists()
    assert len(list(tmp_path.glob(".bronze-cleanup-stage-*"))) == 1

    with bronze_tree_lock(tmp_path, exclusive=True):
        assert target.read_bytes() == b"x"
    assert not list(tmp_path.glob(".bronze-cleanup-stage-*"))


@_APPLY_POSIX
async def test_writer_refuses_pending_stage_before_reusing_batch_name(
    tmp_path: Path,
) -> None:
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir, b"original")
    target = date_dir / ARTIFACT
    root_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    parent_fd = os.open(date_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with cleanup_posix._private_stage(
            root_fd,
            target.relative_to(tmp_path),
            target.lstat(),
            on_stage_error=lambda _name, _error: None,
        ) as stage_fd:
            os.rename(ARTIFACT, ARTIFACT, src_dir_fd=parent_fd, dst_dir_fd=stage_fd)
            os.fsync(parent_fd)
            os.fsync(stage_fd)
    finally:
        os.close(parent_fd)
        os.close(root_fd)
    assert not target.exists()

    writer = _make_writer(tmp_path)
    with pytest.raises(OSError, match="recovery is pending"):
        await writer.write_bronze(
            records=iter([b"new\n"]),
            provider="chembl",
            entity="activity",
            date=datetime(2024, 1, 1, tzinfo=UTC),
            batch_id=BatchID(UUID("12345678-1234-5678-1234-567812345678")),
            run_id=RunID(UUID(int=2)),
            run_type=RunType.INCREMENTAL,
            ingestion_ts=CUTOFF,
        )
    assert not target.exists()
    with bronze_tree_lock(tmp_path, exclusive=True):
        assert target.read_bytes() == b"original"


@_APPLY_POSIX
def test_unjournaled_nonempty_stage_refuses_destructive_cleanup(tmp_path: Path) -> None:
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir)
    stage = tmp_path / ".bronze-cleanup-stage-old-version"
    stage.mkdir()
    (stage / "unknown").write_bytes(b"retain")
    with pytest.raises(OSError, match="no origin journal"):
        with bronze_tree_lock(tmp_path, exclusive=True):
            pytest.fail("lock must refuse before caller can delete")
    assert (date_dir / ARTIFACT).read_bytes() == b"x"
    assert (stage / "unknown").read_bytes() == b"retain"


@_APPLY_POSIX
def test_unjournaled_empty_stage_like_directory_is_preserved(tmp_path: Path) -> None:
    """A name prefix alone does not establish cleanup ownership."""
    stage = tmp_path / ".bronze-cleanup-stage-manual"
    stage.mkdir()
    with pytest.raises(OSError, match="no origin journal"):
        with bronze_tree_lock(tmp_path, exclusive=True):
            pytest.fail("unknown directory must stop destructive recovery")
    assert stage.is_dir()


@_APPLY_POSIX
def test_invalid_completion_marker_preserves_unknown_empty_stage(
    tmp_path: Path,
) -> None:
    suffix = "a" * 32
    stage = tmp_path / f".bronze-cleanup-stage-{suffix}"
    stage.mkdir()
    marker = tmp_path / f".bronze-cleanup-done-{suffix}"
    marker.write_bytes(b"not an origin record")
    with pytest.raises(OSError, match="invalid origin"):
        with bronze_tree_lock(tmp_path, exclusive=True):
            pytest.fail("invalid marker must stop destructive recovery")
    assert stage.is_dir()
    assert marker.read_bytes() == b"not an origin record"


@_APPLY_POSIX
async def test_retained_artifact_metrics_use_registered_prometheus_counters(
    tmp_path: Path,
) -> None:
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir)
    (date_dir / "README").write_bytes(b"keep")
    writer = _make_writer(tmp_path)
    writer._metrics = PrometheusMetrics()
    result = await writer.cleanup_old_files(CUTOFF)
    assert result["files_removed"] == 2
    assert result["files_skipped"] == 1
    assert (date_dir / "README").read_bytes() == b"keep"


@_APPLY_POSIX
@pytest.mark.parametrize("directory", [False, True])
def test_post_rename_fsync_failure_restores_canonical_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory: bool
) -> None:
    """The first durability failure after isolation restores the same inode."""
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    if not directory:
        _write_pair(date_dir)
    target = date_dir if directory else date_dir / ARTIFACT
    original = target.lstat()
    outside = tmp_path / "outside"
    outside.mkdir()
    original_rename = cleanup_posix.os.rename
    original_fsync = cleanup_posix.os.fsync
    isolated = False
    injected = False

    def observed_rename(src: str, dst: str, **kwargs: object) -> None:
        nonlocal isolated
        original_rename(src, dst, **kwargs)
        if src == target.name and not isolated:
            isolated = True

    def fail_first_post_rename(fd: int) -> None:
        nonlocal injected
        if isolated and not injected:
            injected = True
            raise OSError("injected post-rename fsync")
        original_fsync(fd)

    monkeypatch.setattr(cleanup_posix.os, "rename", observed_rename)
    monkeypatch.setattr(cleanup_posix.os, "fsync", fail_first_post_rename)
    with pytest.raises(OSError, match="post-rename fsync"):
        if directory:
            safe_rmdir(target, tmp_path, tmp_path, original)
        else:
            safe_unlink(target, tmp_path, tmp_path, original)
    assert isolated and injected
    assert target.lstat().st_ino == original.st_ino
    assert outside.is_dir() and not list(outside.iterdir())
    assert len(list(tmp_path.glob(".bronze-cleanup-stage-*"))) == 1
    with bronze_tree_lock(tmp_path, exclusive=True):
        pass
    assert not list(tmp_path.glob(".bronze-cleanup-stage-*"))


@_APPLY_POSIX
def test_fifo_stage_journal_fails_without_blocking_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Recovery rejects a FIFO before read and leaves all artifacts untouched."""
    date_dir = _date_dir(tmp_path, "chembl", "activity")
    _write_pair(date_dir)
    stage = tmp_path / ".bronze-cleanup-stage-untrusted"
    stage.mkdir()
    os.mkfifo(stage / "origin.json")
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    original_open = cleanup_posix.os.open
    checked = False

    def require_nonblocking_journal(
        path: object, flags: int, *args: object, **kwargs: object
    ) -> int:
        nonlocal checked
        if path == "origin.json":
            checked = True
            assert flags & os.O_NONBLOCK
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(cleanup_posix.os, "open", require_nonblocking_journal)
    with pytest.raises(OSError, match="non-file journal"):
        with bronze_tree_lock(tmp_path, exclusive=True):
            pytest.fail("untrusted stage must refuse the lock")
    assert checked
    assert (date_dir / ARTIFACT).read_bytes() == b"x"
    assert outside.read_bytes() == b"outside"
    assert (stage / "origin.json").is_fifo()
