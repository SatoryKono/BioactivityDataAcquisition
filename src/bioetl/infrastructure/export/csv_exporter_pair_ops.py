"""CSV published/raw pair clear and fail-closed write helpers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.ports import LoggerPort


def raw_csv_path(csv_path: Path) -> Path:
    return csv_path.with_name(f"{csv_path.name}.raw")


def require_primary_csv_update(updated: bool, *, path: Path, mode: str) -> None:
    """Fail closed when only a locked-target backup was written."""
    if updated:
        return
    raise RuntimeError(
        f"CSV {mode} did not update primary target {path}; "
        "backup-only publish is not a successful export"
    )


def _confined_existing_path(path: Path, root: Path) -> Path | None:
    if path.exists() and path.resolve(strict=False).is_relative_to(root):
        return path
    return None


def list_named_clear_pair(
    *,
    csv_path: Path,
    raw_path: Path,
    root: Path,
) -> tuple[Path | None, Path | None]:
    return (
        _confined_existing_path(csv_path, root),
        _confined_existing_path(raw_path, root),
    )


def list_all_clear_pairs(
    *,
    base_path: Path,
    root: Path,
) -> list[tuple[Path | None, Path | None]]:
    pairs: list[tuple[Path | None, Path | None]] = []
    paired_raw: set[Path] = set()
    for csv_path in base_path.glob("*.csv"):
        if not csv_path.resolve(strict=False).is_relative_to(root):
            continue
        raw_path = _confined_existing_path(raw_csv_path(csv_path), root)
        if raw_path is not None:
            paired_raw.add(raw_path.resolve(strict=False))
        pairs.append((csv_path, raw_path))
    for raw_path in base_path.glob("*.csv.raw"):
        resolved = raw_path.resolve(strict=False)
        if not resolved.is_relative_to(root) or resolved in paired_raw:
            continue
        pairs.append((None, raw_path))
    return pairs


def _try_unlink_clear_target(target: Path, logger: LoggerPort) -> bool:
    try:
        target.unlink()
    except PermissionError:
        logger.warning(
            "Cannot delete locked CSV export artifact",
            path=str(target),
            reason="file may be open in another program",
        )
        return False
    return True


def unlink_clear_pair(
    *,
    csv_path: Path | None,
    raw_path: Path | None,
    logger: LoggerPort,
) -> list[Path]:
    """Delete published CSV then raw; keep raw if CSV unlink fails."""
    deleted: list[Path] = []
    if csv_path is not None:
        if not _try_unlink_clear_target(csv_path, logger):
            return deleted
        deleted.append(csv_path)
    if raw_path is None:
        return deleted
    if not _try_unlink_clear_target(raw_path, logger):
        return deleted
    deleted.append(raw_path)
    return deleted


def unlink_clear_pairs(
    pairs: list[tuple[Path | None, Path | None]],
    logger: LoggerPort,
) -> list[Path]:
    deleted: list[Path] = []
    for csv_path, raw_path in pairs:
        deleted.extend(
            unlink_clear_pair(csv_path=csv_path, raw_path=raw_path, logger=logger)
        )
    return deleted


def snapshot_raw_sidecar(raw_path: Path, *, mode: str) -> bytes | int | None:
    if not raw_path.exists():
        return None
    return raw_path.stat().st_size if mode == "append" else raw_path.read_bytes()


def restore_raw_sidecar(raw_path: Path, snapshot: bytes | int | None) -> None:
    """Best-effort restore of raw after a failed published write."""
    if snapshot is None:
        if raw_path.exists():
            raw_path.unlink(missing_ok=True)
        return
    if isinstance(snapshot, int):
        if raw_path.stat().st_size != snapshot:
            with raw_path.open("r+b") as stream:
                stream.truncate(snapshot)
    elif raw_path.read_bytes() != snapshot:
        with raw_path.open("wb") as stream:
            stream.write(snapshot)


def write_raw_and_published_pair(
    *,
    write_raw: Callable[[], bool],
    write_published: Callable[[], bool],
    raw_path: Path,
    csv_path: Path,
    mode: str,
) -> None:
    """Update raw then published; roll back raw if published primary write fails."""
    raw_snapshot = snapshot_raw_sidecar(raw_path, mode=mode)
    try:
        require_primary_csv_update(write_raw(), path=raw_path, mode=mode)
        require_primary_csv_update(write_published(), path=csv_path, mode=mode)
    except Exception:
        restore_raw_sidecar(raw_path, raw_snapshot)
        raise
