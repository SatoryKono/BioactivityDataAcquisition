from __future__ import annotations

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


def _local_temp_root() -> Path:
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
