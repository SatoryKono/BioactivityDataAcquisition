from pathlib import Path
import platform
from unittest.mock import patch

import pytest

from bioetl.infrastructure.files.atomic import AtomicFileOperation
from bioetl.infrastructure.settings.files import MAX_FILE_RETRIES


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


def test_replace_with_retry_success(atomic_op, tmp_path):
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("content")

    atomic_op._replace_with_retry(src, dst)

    assert dst.read_text() == "content"
    assert not src.exists()


@patch("time.sleep")
def test_replace_with_retry_retries(mock_sleep, atomic_op, tmp_path):
    src = tmp_path / "src_retry.txt"
    dst = tmp_path / "dst_retry.txt"
    src.write_text("content")

    # Fail twice, then succeed
    # Note: Since we mock os.replace, the file won't actually move.
    # We only verify the retry logic here.
    with patch(
        "os.replace", side_effect=[OSError("Busy"), OSError("Busy"), None]
    ) as mock_replace:
        atomic_op._replace_with_retry(src, dst)

    assert mock_replace.call_count == 3
    assert mock_sleep.call_count == 2


@patch("time.sleep")
def test_replace_with_retry_max_retries_exceeded(mock_sleep, atomic_op, tmp_path):
    src = tmp_path / "src_max.txt"
    dst = tmp_path / "dst_max.txt"
    src.write_text("content")

    is_windows = platform.system() == "Windows"
    expected_retries = MAX_FILE_RETRIES * (2 if is_windows else 1)

    with patch("os.replace", side_effect=OSError("Locked")):
        with pytest.raises(OSError, match="Locked"):
            atomic_op._replace_with_retry(src, dst)

    assert mock_sleep.call_count == expected_retries - 1


@patch("time.sleep")
def test_replace_with_retry_windows_permission_error_message(
    mock_sleep, atomic_op, tmp_path
):
    """Test that Windows PermissionError provides helpful error message."""
    src = tmp_path / "src_perm.txt"
    dst = tmp_path / "dst_perm.txt"
    src.write_text("content")
    dst.write_text("locked")

    is_windows = platform.system() == "Windows"
    if not is_windows:
        pytest.skip("Windows-specific test")

    expected_retries = MAX_FILE_RETRIES * 2

    # Simulate PermissionError (file locked)
    with patch(
        "os.replace", side_effect=PermissionError("[WinError 5] Access is denied")
    ):
        with pytest.raises(
            PermissionError,
            match="file is locked by another process",
        ) as exc_info:
            atomic_op._replace_with_retry(src, dst)

        # Verify helpful error message
        assert "Please close any programs" in str(exc_info.value)
        assert str(dst) in str(exc_info.value)

    assert mock_sleep.call_count == expected_retries - 1


@patch("time.sleep")
def test_try_replace_converts_windows_access_denied(mock_sleep, atomic_op, tmp_path):
    """Test that OSError with winerror=5 is converted to PermissionError."""
    src = tmp_path / "src_win.txt"
    dst = tmp_path / "dst_win.txt"
    src.write_text("content")
    dst.write_text("locked")

    is_windows = platform.system() == "Windows"
    if not is_windows:
        pytest.skip("Windows-specific test")

    # Create OSError with winerror attribute (simulating Windows Access Denied)
    class WindowsOSError(OSError):
        def __init__(self):
            super().__init__("[WinError 5] Access is denied")
            self.winerror = 5

    expected_retries = MAX_FILE_RETRIES * 2

    with patch("os.replace", side_effect=WindowsOSError()):
        with pytest.raises(PermissionError) as exc_info:
            atomic_op._replace_with_retry(src, dst)

        # Verify error message mentions the file
        assert str(dst) in str(exc_info.value)

    assert mock_sleep.call_count == expected_retries - 1


def test_move_overwrites_existing(atomic_op, tmp_path):
    src = tmp_path / "src_overwrite.txt"
    dst = tmp_path / "dst_overwrite.txt"
    src.write_text("new")
    dst.write_text("old")

    atomic_op._replace_with_retry(src, dst)

    assert dst.read_text() == "new"
    assert not src.exists()
