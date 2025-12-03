from pathlib import Path
from unittest.mock import patch

import pytest

from bioetl.infrastructure.constants import MAX_FILE_RETRIES
from bioetl.infrastructure.files.atomic import AtomicFileOperation


@pytest.fixture
def atomic_op():
    return AtomicFileOperation()


def test_write_atomic_success(atomic_op, tmp_path):
    target_file = tmp_path / "test.txt"
    content = "test content"

    def write_fn(path: Path):
        path.write_text(content, encoding="utf-8")

    atomic_op.write_atomic(target_file, write_fn)

    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == content
    assert not target_file.with_suffix(".tmp").exists()


def test_write_atomic_failure_cleans_up(atomic_op, tmp_path):
    target_file = tmp_path / "fail.txt"
    tmp_file = target_file.with_suffix(".tmp")

    def write_fn(path: Path):
        path.write_text("partial", encoding="utf-8")
        raise RuntimeError("Write failed")

    with pytest.raises(RuntimeError, match="Write failed"):
        atomic_op.write_atomic(target_file, write_fn)

    assert not target_file.exists()
    assert not tmp_file.exists()


def test_write_atomic_cleanup_failure_ignored(atomic_op, tmp_path):
    target_file = tmp_path / "fail_cleanup.txt"

    def write_fn(path: Path):
        path.write_text("partial", encoding="utf-8")
        raise RuntimeError("Original error")

    # Simulate os.remove failing during cleanup
    with patch("os.remove", side_effect=OSError("Cleanup failed")):
        with pytest.raises(RuntimeError, match="Original error"):
            atomic_op.write_atomic(target_file, write_fn)


def test_move_with_retry_success(atomic_op, tmp_path):
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("content")

    atomic_op._move_with_retry(src, dst)

    assert dst.read_text() == "content"
    assert not src.exists()


@patch("time.sleep")
def test_move_with_retry_retries(mock_sleep, atomic_op, tmp_path):
    src = tmp_path / "src_retry.txt"
    dst = tmp_path / "dst_retry.txt"
    src.write_text("content")

    # Fail twice, then succeed
    # Note: Since we mock shutil.move, the file won't actually move.
    # We only verify the retry logic here.
    with patch("shutil.move", side_effect=[OSError("Busy"), OSError("Busy"), None]) as mock_move:
        atomic_op._move_with_retry(src, dst)

    assert mock_move.call_count == 3
    assert mock_sleep.call_count == 2


@patch("time.sleep")
def test_move_with_retry_max_retries_exceeded(mock_sleep, atomic_op, tmp_path):
    src = tmp_path / "src_max.txt"
    dst = tmp_path / "dst_max.txt"
    src.write_text("content")

    with patch("shutil.move", side_effect=OSError("Locked")):
        with pytest.raises(OSError, match="Locked"):
            atomic_op._move_with_retry(src, dst)

    assert mock_sleep.call_count == MAX_FILE_RETRIES - 1


def test_move_overwrites_existing(atomic_op, tmp_path):
    src = tmp_path / "src_overwrite.txt"
    dst = tmp_path / "dst_overwrite.txt"
    src.write_text("new")
    dst.write_text("old")

    atomic_op._move_with_retry(src, dst)

    assert dst.read_text() == "new"
    assert not src.exists()
