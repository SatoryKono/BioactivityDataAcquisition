import os
import sys
import pathlib
import pytest

_ORIGINAL_OS_NAME = os.name
_ORIGINAL_SYS_PLATFORM = sys.platform
_ORIGINAL_PATH = pathlib.Path

@pytest.fixture(autouse=True)
def _guard_global_pathlib_state():
    """Автоматически восстанавливает глобальное состояние после грязных тестов."""
    yield
    if os.name != _ORIGINAL_OS_NAME:
        os.name = _ORIGINAL_OS_NAME
    if sys.platform != _ORIGINAL_SYS_PLATFORM:
        sys.platform = _ORIGINAL_SYS_PLATFORM
    if pathlib.Path is not _ORIGINAL_PATH:
        pathlib.Path = _ORIGINAL_PATH