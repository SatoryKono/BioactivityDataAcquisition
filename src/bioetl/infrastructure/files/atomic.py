"""
Atomic file operation utilities.
"""

import os
from pathlib import Path
import platform
import time
from typing import Callable

from bioetl.infrastructure.settings.files import DEFAULT_FILE_SETTINGS


class AtomicFileOperation:
    """Utility for atomic file operations."""

    def write_atomic(self, path: Path, write_fn: Callable[[Path], None]) -> None:
        """Perform atomic write via temporary file.

        Args:
            path: Target path.
            write_fn: Write function accepting temporary path.
        """
        tmp_path = path.with_suffix(".tmp")

        try:
            # 1. Write to temporary file
            write_fn(tmp_path)

            # 2. Atomic move with retry
            self._replace_with_retry(tmp_path, path)

        except Exception:
            # Cleanup on error (if file was created)
            if tmp_path.exists():
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise

    def _replace_with_retry(self, src: Path, dst: Path) -> None:
        """Atomic file replacement with retries (for Windows).

        Uses os.replace for atomic replacement on all platforms.
        """
        last_error: OSError | None = None
        is_windows = platform.system() == "Windows"
        # On Windows use longer delay due to antivirus/indexers
        delay = DEFAULT_FILE_SETTINGS.retry_delay_sec * (2.0 if is_windows else 1.0)
        # Increase retries on Windows for locked files
        max_retries = DEFAULT_FILE_SETTINGS.max_retries * (2 if is_windows else 1)

        for attempt in range(max_retries):
            try:
                if self._try_replace(src, dst, is_windows):
                    return
                # If attempt did not raise exception but failed, record the error.
                last_error = last_error or OSError(
                    "Move failed without explicit error."
                )
            except OSError as exc:
                last_error = exc

            if attempt == max_retries - 1:
                # Provide helpful error message for Windows file lock issues
                if (
                    is_windows
                    and last_error
                    and isinstance(last_error, PermissionError)
                ):
                    msg = (
                        f"Cannot replace file '{dst}': file is locked by another "
                        f"process. Please close any programs that have this file "
                        f"open (e.g., Excel, Notepad, or file explorer) and try "
                        f"again. Original error: {last_error}"
                    )
                    raise PermissionError(msg) from last_error
                raise last_error or OSError("Move failed without explicit error.")
            time.sleep(delay)

    def _try_replace(self, src: Path, dst: Path, is_windows: bool) -> bool:
        """Attempt to replace file atomically.

        Returns:
            True if replacement successful, False otherwise.
        """
        try:
            os.replace(src, dst)
            return True
        except PermissionError as exc:
            # On Windows PermissionError often means file is locked
            if self._try_windows_unlock_replace(src, dst, is_windows):
                return True
            # Re-raise as PermissionError to preserve type for better error messages
            raise exc
        except OSError as exc:
            # On Windows, Access Denied (errno 5) may come as OSError
            if is_windows and hasattr(exc, "winerror") and exc.winerror == 5:
                # Convert to PermissionError for consistent handling
                raise PermissionError(f"Cannot replace file '{dst}': {exc}") from exc
            raise

    def _try_windows_unlock_replace(
        self,
        src: Path,
        dst: Path,
        is_windows: bool,
    ) -> bool:
        """Attempt to unlock and replace file on Windows.

        Returns:
            True if replacement successful, False otherwise.
        """
        if not is_windows or not dst.exists():
            return False

        try:
            dst.unlink()
            os.replace(src, dst)
            return True
        except OSError:
            return False
