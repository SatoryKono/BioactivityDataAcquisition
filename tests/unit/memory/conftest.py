from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


def _local_temp_root() -> Path:
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            local_temp = Path(local_app_data) / "Temp"
            if local_temp.is_dir():
                return local_temp
        return Path(tempfile.gettempdir())
    local_tmp = Path("/tmp")
    if local_tmp.exists():
        return local_tmp
    return Path(tempfile.gettempdir())


@pytest.fixture
def memory_local_tmp_path() -> Generator[Path, None, None]:
    sandbox_dir = Path(
        tempfile.mkdtemp(prefix="bioetl-memory-tests-", dir=str(_local_temp_root()))
    )
    try:
        yield sandbox_dir
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)
