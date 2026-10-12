# pyright: reportArgumentType=false

from __future__ import annotations

import pytest

from bioetl.infrastructure.config.repository_source_environment import read_repository_env_text

pytestmark = pytest.mark.unit


def test_read_repository_env_text_missing(tmp_path):
    assert read_repository_env_text(tmp_path / ".env") is None

def test_read_repository_env_text_directory(tmp_path):
    dir_path = tmp_path / "env_dir"
    dir_path.mkdir()
    assert read_repository_env_text(dir_path) is None

def test_read_repository_env_text_file(tmp_path):
    file_path = tmp_path / ".env"
    file_path.write_text("TEST=1", encoding="utf-8")
    assert read_repository_env_text(file_path) == "TEST=1"
