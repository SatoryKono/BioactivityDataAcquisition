"""
Atomic file operation utilities.
"""

import os
import platform
import time
from pathlib import Path
from typing import Callable

from bioetl.infrastructure.constants import MAX_FILE_RETRIES, RETRY_DELAY_SEC


class AtomicFileOperation:
    """
    Утилита для атомарных операций с файлами.
    """

    def write_atomic(self, path: Path, write_fn: Callable[[Path], None]) -> None:
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
        Использует os.replace для атомарной замены на всех платформах.
        """
        last_error: OSError | None = None
        is_windows = platform.system() == "Windows"
        # На Windows используем более длительную задержку из-за антивирусов/индексаторов
        delay = RETRY_DELAY_SEC * (2.0 if is_windows else 1.0)
        
        for attempt in range(MAX_FILE_RETRIES):
            try:
                # os.replace атомарно заменяет файл на всех платформах
                # На Windows использует MoveFileEx с MOVEFILE_REPLACE_EXISTING
                os.replace(src, dst)
                return
            except PermissionError as exc:
                last_error = exc
                if self._try_windows_unlock_replace(src, dst, is_windows):
                    return
            except OSError as exc:
                last_error = exc
                
            if attempt == MAX_FILE_RETRIES - 1:
                raise last_error or OSError("Move failed without explicit error.")
            time.sleep(delay)

    def _try_windows_unlock_replace(self, src: Path, dst: Path, is_windows: bool) -> bool:
        """
        Попытка разблокировать и заменить файл на Windows.
        
        Returns:
            True если замена успешна, False иначе.
        """
        if not is_windows or not dst.exists():
            return False
        
        try:
            dst.unlink()
            os.replace(src, dst)
            return True
        except OSError:
            return False
