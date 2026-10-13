"""POSIX handle-relative Bronze deletion and crash-stage recovery."""

from __future__ import annotations

import errno
import json
import os
import secrets
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

from .cleanup_core import (
    _O_DIRECTORY,
    _O_NOFOLLOW,
    _O_NONBLOCK,
    _STAGE_JOURNAL,
    _STAGE_PREFIX,
    _CleanupConflict,
    destructive_cleanup_supported,
    stat_is_link_or_reparse,
)


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


@contextmanager
def _anchored_parent(
    path: Path, root_abs: Path, root_real: Path, root_fd: int | None = None
) -> Iterator[tuple[int, int, str, list[tuple[int, int, str]]]]:
    """Open every relative parent component without following a link."""
    if not destructive_cleanup_supported():
        raise NotImplementedError("Bronze destructive cleanup has no safe handle API")
    try:
        parts = Path(os.path.abspath(path)).relative_to(root_abs).parts  # noqa: PTH100
    except ValueError as exc:
        raise _CleanupConflict from exc
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise _CleanupConflict
    fds: list[int] = []
    chain: list[tuple[int, int, str]] = []
    try:
        opened_root_fd = (
            os.dup(root_fd)
            if root_fd is not None
            else os.open(root_real, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW)
        )
        fds.append(opened_root_fd)
        parent_fd = opened_root_fd
        for name in parts[:-1]:
            child_fd = os.open(
                name, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW, dir_fd=parent_fd
            )
            fds.append(child_fd)
            chain.append((parent_fd, child_fd, name))
            parent_fd = child_fd
        if not _chain_is_stable(opened_root_fd, root_abs, chain):
            raise _CleanupConflict
        yield opened_root_fd, parent_fd, parts[-1], chain
    finally:
        for fd in reversed(fds):
            os.close(fd)


def _chain_is_stable(
    root_fd: int, root_abs: Path, chain: list[tuple[int, int, str]]
) -> bool:
    try:
        if not _same_identity(os.fstat(root_fd), root_abs.stat()):
            return False
        for parent_fd, child_fd, name in chain:
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if stat_is_link_or_reparse(named) or not _same_identity(
                named, os.fstat(child_fd)
            ):
                return False
    except OSError:
        return False
    return True


@dataclass(frozen=True, slots=True)
class _StageOrigin:
    parts: tuple[str, ...]
    dev: int
    ino: int


def _parse_stage_origin(raw: bytes, stage_name: str) -> _StageOrigin:
    try:
        record = json.loads(raw)
        relative = record["relative"]
        dev, ino = record["dev"], record["ino"]
        parts = tuple(relative.split("/")) if isinstance(relative, str) else ()
        if (
            not parts
            or any(part in ("", ".", "..") for part in parts)
            or not isinstance(dev, int)
            or not isinstance(ino, int)
        ):
            raise ValueError("invalid stage origin")
    except (KeyError, TypeError, ValueError) as exc:
        raise OSError(f"Bronze stage {stage_name} has invalid origin") from exc
    return _StageOrigin(parts, dev, ino)


def _load_stage_origin(stage_fd: int, stage_name: str) -> _StageOrigin:
    """Read a bounded origin record; never claim an unjournaled stage."""
    try:
        journal_fd = os.open(
            _STAGE_JOURNAL, os.O_RDONLY | _O_NONBLOCK | _O_NOFOLLOW, dir_fd=stage_fd
        )
    except FileNotFoundError:
        raise OSError(f"Bronze stage {stage_name} has no origin journal") from None
    try:
        if not stat.S_ISREG(os.fstat(journal_fd).st_mode):
            raise OSError(f"Bronze stage {stage_name} has a non-file journal")
        raw = os.read(journal_fd, 4097)
    finally:
        os.close(journal_fd)
    if len(raw) > 4096:
        raise OSError(f"Bronze stage {stage_name} has an oversized journal")
    return _parse_stage_origin(raw, stage_name)


def _restore_stage_entry(
    root_fd: int, root_real: Path, stage_fd: int, stage_name: str, origin: _StageOrigin
) -> None:
    name = origin.parts[-1]
    target = root_real.joinpath(*origin.parts)
    try:
        staged = os.stat(name, dir_fd=stage_fd, follow_symlinks=False)
    except FileNotFoundError:
        # A restored entry may still need a durable parent before its journal
        # can be discarded. An absent canonical entry means deletion completed.
        with _anchored_parent(target, root_real, root_real, root_fd) as (
            _opened_root,
            parent_fd,
            _name,
            chain,
        ):
            if not _chain_is_stable(root_fd, root_real, chain):
                raise OSError("Bronze stage parent changed") from None
            try:
                current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                return
            if (current.st_dev, current.st_ino) != (origin.dev, origin.ino):
                raise OSError(f"Bronze stage {stage_name} origin occupied") from None
            os.fsync(parent_fd)
        return
    if (staged.st_dev, staged.st_ino) != (origin.dev, origin.ino):
        raise OSError(f"Bronze stage {stage_name} identity changed")
    with _anchored_parent(target, root_real, root_real, root_fd) as (
        _opened_root,
        parent_fd,
        _name,
        chain,
    ):
        if not _chain_is_stable(root_fd, root_real, chain):
            raise OSError("Bronze stage parent changed")
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            os.rename(name, name, src_dir_fd=stage_fd, dst_dir_fd=parent_fd)
            os.fsync(parent_fd)
        else:
            raise OSError(f"Bronze stage {stage_name} origin occupied")


def _recover_stages(root_fd: int, root_real: Path) -> None:
    """Restore crash-interrupted isolates before any new destructive plan."""
    for stage_name in os.listdir(root_fd):
        if not stage_name.startswith(_STAGE_PREFIX):
            continue
        stage_fd = os.open(
            stage_name, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW, dir_fd=root_fd
        )
        try:
            origin = _load_stage_origin(stage_fd, stage_name)
            _restore_stage_entry(root_fd, root_real, stage_fd, stage_name, origin)
            os.unlink(_STAGE_JOURNAL, dir_fd=stage_fd)
            os.fsync(stage_fd)
        finally:
            os.close(stage_fd)
        os.rmdir(stage_name, dir_fd=root_fd)
        os.fsync(root_fd)


@contextmanager
def _private_stage(
    root_fd: int,
    relative: Path,
    identity: os.stat_result,
    on_stage_error: Callable[[str, OSError], None] | None = None,
) -> Iterator[int]:
    """Isolate a target name before checking its identity and deleting it."""
    name = f"{_STAGE_PREFIX}{secrets.token_hex(16)}"
    os.mkdir(name, 0o700, dir_fd=root_fd)
    try:
        stage_fd = os.open(name, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW, dir_fd=root_fd)
    except BaseException:
        os.rmdir(name, dir_fd=root_fd)
        raise
    prepared = False
    completed = False
    try:
        journal_fd = os.open(
            _STAGE_JOURNAL,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_NOFOLLOW,
            0o600,
            dir_fd=stage_fd,
        )
        try:
            payload = json.dumps(
                {
                    "relative": relative.as_posix(),
                    "dev": identity.st_dev,
                    "ino": identity.st_ino,
                }
            ).encode()
            if len(payload) > 4096:
                raise OSError("Bronze stage origin exceeds journal limit")
            written = 0
            while written < len(payload):
                count = os.write(journal_fd, payload[written:])
                if count <= 0:
                    raise OSError("Bronze stage journal write made no progress")
                written += count
            os.fsync(journal_fd)
        finally:
            os.close(journal_fd)
        os.fsync(stage_fd)
        os.fsync(root_fd)
        prepared = True
        yield stage_fd
        completed = True
    finally:
        if not prepared:
            try:
                with suppress(FileNotFoundError):
                    os.unlink(_STAGE_JOURNAL, dir_fd=stage_fd)
                os.fsync(stage_fd)
            finally:
                os.close(stage_fd)
            os.rmdir(name, dir_fd=root_fd)
            os.fsync(root_fd)
        elif not completed:
            os.close(stage_fd)
        else:
            _finish_private_stage(root_fd, stage_fd, name, relative, on_stage_error)


def _finish_private_stage(
    root_fd: int,
    stage_fd: int,
    name: str,
    relative: Path,
    on_stage_error: Callable[[str, OSError], None] | None,
) -> None:
    """Report post-commit durability failures without losing removal counts."""
    stage_error: OSError | None = None
    try:
        if relative.name not in os.listdir(stage_fd):
            with suppress(FileNotFoundError):
                os.unlink(_STAGE_JOURNAL, dir_fd=stage_fd)
            os.fsync(stage_fd)
    except OSError as exc:
        stage_error = exc
    finally:
        os.close(stage_fd)
    try:
        os.rmdir(name, dir_fd=root_fd)
        os.fsync(root_fd)
    except OSError as exc:
        # A conflicted artifact may remain in the stage; expose its name.
        stage_error = stage_error or exc
    if stage_error is not None:
        if on_stage_error is None:
            raise stage_error
        on_stage_error(name, stage_error)


def _restore_staged(name: str, stage_fd: int, parent_fd: int) -> None:
    """Restore a refused artifact only when its original name is still free."""
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        os.rename(name, name, src_dir_fd=stage_fd, dst_dir_fd=parent_fd)
        os.fsync(parent_fd)


def safe_unlink(
    file_path: Path,
    root_abs: Path,
    root_real: Path,
    expected: os.stat_result | None = None,
    *,
    on_stage_error: Callable[[str, OSError], None] | None = None,
    root_fd: int | None = None,
) -> bool:
    """Delete only the planned inode after atomic isolation under the root."""
    try:
        with _anchored_parent(file_path, root_abs, root_real, root_fd) as (
            root_fd,
            parent_fd,
            name,
            chain,
        ):
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (
                stat_is_link_or_reparse(current)
                or not stat.S_ISREG(current.st_mode)
                or (expected is not None and not _same_identity(expected, current))
            ):
                return False
            relative = Path(os.path.abspath(file_path)).relative_to(root_abs)  # noqa: PTH100
            with _private_stage(root_fd, relative, current, on_stage_error) as stage_fd:
                try:
                    os.rename(name, name, src_dir_fd=parent_fd, dst_dir_fd=stage_fd)
                    os.fsync(parent_fd)
                    os.fsync(stage_fd)
                    staged = os.stat(name, dir_fd=stage_fd, follow_symlinks=False)
                    if not _same_identity(current, staged) or not _chain_is_stable(
                        root_fd, root_abs, chain
                    ):
                        _restore_staged(name, stage_fd, parent_fd)
                        return False
                    os.unlink(name, dir_fd=stage_fd)
                    return True
                except BaseException:
                    _restore_staged(name, stage_fd, parent_fd)
                    raise
    except (FileNotFoundError, NotADirectoryError, _CleanupConflict):
        return False


def _rmdir_staged(name: str, stage_fd: int) -> bool:
    try:
        os.rmdir(name, dir_fd=stage_fd)
    except OSError as exc:
        if exc.errno in (errno.ENOTEMPTY, errno.EEXIST):
            return False
        raise
    return True


def safe_rmdir(
    dir_path: Path,
    root_abs: Path,
    root_real: Path,
    expected: os.stat_result | None = None,
    *,
    on_stage_error: Callable[[str, OSError], None] | None = None,
    root_fd: int | None = None,
) -> bool:
    """Remove only the planned empty directory after atomic isolation."""
    try:
        with _anchored_parent(dir_path, root_abs, root_real, root_fd) as (
            root_fd,
            parent_fd,
            name,
            chain,
        ):
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (
                stat_is_link_or_reparse(current)
                or not stat.S_ISDIR(current.st_mode)
                or (expected is not None and not _same_identity(expected, current))
            ):
                return False
            relative = Path(os.path.abspath(dir_path)).relative_to(root_abs)  # noqa: PTH100
            with _private_stage(root_fd, relative, current, on_stage_error) as stage_fd:
                try:
                    os.rename(name, name, src_dir_fd=parent_fd, dst_dir_fd=stage_fd)
                    os.fsync(parent_fd)
                    os.fsync(stage_fd)
                    staged = os.stat(name, dir_fd=stage_fd, follow_symlinks=False)
                    if not _same_identity(current, staged) or not _chain_is_stable(
                        root_fd, root_abs, chain
                    ):
                        _restore_staged(name, stage_fd, parent_fd)
                        return False
                    if not _rmdir_staged(name, stage_fd):
                        _restore_staged(name, stage_fd, parent_fd)
                        return False
                except BaseException:
                    _restore_staged(name, stage_fd, parent_fd)
                    raise
                return True
    except (FileNotFoundError, NotADirectoryError, _CleanupConflict):
        return False
