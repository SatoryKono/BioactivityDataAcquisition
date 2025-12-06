"""
Atomic file operation utilities.
"""
import os
import shutil
import time
from pathlib import Path
from typing import Callable

from bioetl.infrastructure.constants import MAX_FILE_RETRIES, RETRY_DELAY_SEC


class AtomicFileOperation:
    """
    Утилита для атомарных операций с файлами.
    """

    def write_atomic(
        self, path: Path, write_fn: Callable[[Path], None]
    ) -> None:
        """
        Выполняет атомарную запись через временный файл.

        Args:
            path: Целевой путь.
            write_fn: Функция записи, принимающая временный путь.
        """
        tmp_path = path.with_suffix(".tmp")

        try:
            # 1. Запись во временный файл
            write_fn(tmp_path)

            # 2. Атомарное перемещение с retry
            self._replace_with_retry(tmp_path, path)

        except Exception:
            # Очистка в случае ошибки (если файл создан)
            if tmp_path.exists():
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise

    def _replace_with_retry(self, src: Path, dst: Path) -> None:
        """
        Атомарная замена файла с повторными попытками (для Windows).
        Использует shutil.move, чтобы позволить перезапись и поддержать мок в тестах.
        """
        move_fn = shutil.move
        last_error: OSError | None = None
        for attempt in range(MAX_FILE_RETRIES):
            try:
                move_fn(src, dst)
                return
            except OSError as exc:
                last_error = exc
            if attempt == MAX_FILE_RETRIES - 1:
                raise last_error or OSError("Move failed without explicit error.")
            time.sleep(RETRY_DELAY_SEC)
