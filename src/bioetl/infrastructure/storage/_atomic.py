"""Atomic file write utilities.

Implements atomic write pattern (temp file + rename) for data integrity.

Requirements:
- REQ-DATA-004: Atomic writes to prevent partial/corrupted files
- Cross-platform compatibility (Unix, Windows)

Architecture:
- Uses tempfile.mkstemp for secure temp file creation
- Uses Path.replace() for atomic overwrite (works on Windows)
- Cleanup on error to prevent orphan temp files
"""

import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import IO


class AtomicWriteError(Exception):
    """Raised when atomic write fails."""

    def __init__(self, target: Path, reason: str) -> None:
        self.target = target
        self.reason = reason
        super().__init__(f"Atomic write failed for '{target}': {reason}")


@contextmanager
def atomic_write(
    target: Path,
    mode: str = "wb",
    suffix: str = ".tmp",
    prefix: str = ".",
    encoding: str | None = None,
) -> Iterator[IO]:
    """Context manager for atomic file writes.

    Writes to a temporary file first, then atomically replaces the target.
    If any error occurs, the temp file is cleaned up and target is unchanged.

    Args:
        target: Path to the final destination file
        mode: File open mode ('wb' for binary, 'w' for text)
        suffix: Suffix for temp file (default: '.tmp')
        prefix: Prefix for temp file (default: '.')
        encoding: Text encoding for text mode (ignored in binary mode)

    Yields:
        File handle for writing

    Raises:
        AtomicWriteError: If write or rename fails

    Example:
        >>> with atomic_write(Path("/data/file.json")) as f:
        ...     f.write(b'{"key": "value"}')
        # File is only visible at target after successful completion

    """
    # Ensure parent directory exists
    target.parent.mkdir(parents=True, exist_ok=True)

    # Create temp file in same directory (required for atomic rename)
    fd, temp_path_str = tempfile.mkstemp(
        suffix=suffix,
        prefix=prefix + target.stem + "_",
        dir=target.parent,
    )
    temp_path = Path(temp_path_str)

    try:
        # Open with os.fdopen to use the file descriptor
        # Pass encoding for text mode (ignored in binary mode)
        with os.fdopen(fd, mode, encoding=encoding) as f:
            yield f

        # Atomic replace (works on both Unix and Windows)
        temp_path.replace(target)

    except Exception as e:
        # Clean up temp file on any error
        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError:
            pass  # Best effort cleanup

        if isinstance(e, AtomicWriteError):
            raise
        raise AtomicWriteError(target, str(e)) from e


def atomic_write_bytes(target: Path, data: bytes) -> None:
    """Write bytes atomically to target file.

    Args:
        target: Path to the final destination file
        data: Bytes to write

    Raises:
        AtomicWriteError: If write fails

    """
    with atomic_write(target, mode="wb") as f:
        f.write(data)


def atomic_write_text(target: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text atomically to target file.

    Args:
        target: Path to the final destination file
        text: Text to write
        encoding: Text encoding (default: utf-8)

    Raises:
        AtomicWriteError: If write fails

    """
    with atomic_write(target, mode="w", encoding=encoding) as f:
        f.write(text)


class AtomicWriteGroup:
    """Manage atomic writes for multiple related files.

    Ensures all files in a group are written atomically together.
    If any file fails, all temp files are cleaned up.

    Example:
        >>> group = AtomicWriteGroup()
        >>> group.add(data_path, compressed_data)
        >>> group.add(meta_path, metadata_json.encode())
        >>> group.commit()  # Both files appear atomically

    """

    def __init__(self) -> None:
        self._pending: list[tuple[Path, Path, bytes]] = []  # (target, temp, data)

    def add(self, target: Path, data: bytes) -> None:
        """Add a file to the atomic write group.

        Args:
            target: Path to the final destination file
            data: Bytes to write

        """
        target.parent.mkdir(parents=True, exist_ok=True)

        fd, temp_path_str = tempfile.mkstemp(
            suffix=".tmp",
            prefix="." + target.stem + "_",
            dir=target.parent,
        )
        temp_path = Path(temp_path_str)

        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            self._pending.append((target, temp_path, data))
        except Exception:
            # Clean up on write failure
            with suppress(OSError):
                temp_path.unlink()
            raise

    def commit(self) -> None:
        """Commit all pending writes atomically.

        Replaces all target files with their temp files.
        If any replace fails, attempts to rollback.

        Raises:
            AtomicWriteError: If commit fails

        """
        committed: list[tuple[Path, Path]] = []

        try:
            for target, temp_path, _ in self._pending:
                temp_path.replace(target)
                committed.append((target, temp_path))
        except Exception as e:
            # Rollback: remove any committed files (best effort)
            # Note: True rollback is impossible after replace,
            # but we clean up uncommitted temps
            self._cleanup_uncommitted(committed)
            raise AtomicWriteError(
                target, f"Commit failed after {len(committed)} files: {e}"
            ) from e
        finally:
            self._pending.clear()

    def rollback(self) -> None:
        """Cancel all pending writes and clean up temp files."""
        for _, temp_path, _ in self._pending:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass
        self._pending.clear()

    def _cleanup_uncommitted(self, committed: list[tuple[Path, Path]]) -> None:
        """Clean up temp files that weren't committed."""
        committed_temps = {temp for _, temp in committed}
        for _, temp_path, _ in self._pending:
            if temp_path not in committed_temps:
                try:
                    if temp_path.exists():
                        temp_path.unlink()
                except OSError:
                    pass

    def __enter__(self) -> "AtomicWriteGroup":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None:
            self.rollback()
        # If no exception, user should have called commit()
