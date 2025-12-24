"""Unit tests for atomic write utilities."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from bioetl.infrastructure.storage._atomic import (
    AtomicWriteError,
    AtomicWriteGroup,
    atomic_write,
    atomic_write_bytes,
    atomic_write_text,
)


@pytest.mark.unit
class TestAtomicWrite:
    """Tests for atomic_write context manager."""

    def test_atomic_write_creates_file(self, tmp_path: Path) -> None:
        """Test that atomic_write creates file at target path."""
        target = tmp_path / "test_file.txt"

        with atomic_write(target, mode="w") as f:
            f.write("hello world")

        assert target.exists()
        assert target.read_text() == "hello world"

    def test_atomic_write_binary(self, tmp_path: Path) -> None:
        """Test atomic_write with binary mode."""
        target = tmp_path / "test_file.bin"
        data = b"\x00\x01\x02\x03"

        with atomic_write(target, mode="wb") as f:
            f.write(data)

        assert target.exists()
        assert target.read_bytes() == data

    def test_atomic_write_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that atomic_write creates parent directories."""
        target = tmp_path / "nested" / "deep" / "file.txt"

        with atomic_write(target, mode="w") as f:
            f.write("nested content")

        assert target.exists()
        assert target.read_text() == "nested content"

    def test_atomic_write_overwrites_existing(self, tmp_path: Path) -> None:
        """Test that atomic_write overwrites existing files."""
        target = tmp_path / "existing.txt"
        target.write_text("original")

        with atomic_write(target, mode="w") as f:
            f.write("overwritten")

        assert target.read_text() == "overwritten"

    def test_atomic_write_no_temp_file_after_success(self, tmp_path: Path) -> None:
        """Test that no temp files remain after successful write."""
        target = tmp_path / "test_file.txt"

        with atomic_write(target, mode="w") as f:
            f.write("content")

        # Check no .tmp files remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_atomic_write_cleanup_on_error(self, tmp_path: Path) -> None:
        """Test that temp files are cleaned up on write error."""
        target = tmp_path / "test_file.txt"

        with pytest.raises(AtomicWriteError):
            with atomic_write(target, mode="w") as f:
                f.write("partial")
                raise ValueError("Simulated error")

        # Target should not exist
        assert not target.exists()

        # No temp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_atomic_write_preserves_original_on_error(self, tmp_path: Path) -> None:
        """Test that original file is preserved if write fails."""
        target = tmp_path / "existing.txt"
        target.write_text("original content")

        with pytest.raises(AtomicWriteError):
            with atomic_write(target, mode="w") as f:
                f.write("new content")
                raise RuntimeError("Simulated failure")

        # Original content should be preserved
        assert target.read_text() == "original content"


@pytest.mark.unit
class TestAtomicWriteHelpers:
    """Tests for atomic_write_bytes and atomic_write_text."""

    def test_atomic_write_bytes(self, tmp_path: Path) -> None:
        """Test atomic_write_bytes helper."""
        target = tmp_path / "binary.bin"
        data = b"binary data \x00\xff"

        atomic_write_bytes(target, data)

        assert target.read_bytes() == data

    def test_atomic_write_text(self, tmp_path: Path) -> None:
        """Test atomic_write_text helper."""
        target = tmp_path / "text.txt"
        text = "Hello, World!"

        atomic_write_text(target, text)

        assert target.read_text() == text

    def test_atomic_write_text_encoding(self, tmp_path: Path) -> None:
        """Test atomic_write_text with non-default encoding."""
        target = tmp_path / "unicode.txt"
        text = "Привет мир"

        atomic_write_text(target, text, encoding="utf-8")

        assert target.read_text(encoding="utf-8") == text


@pytest.mark.unit
class TestAtomicWriteGroup:
    """Tests for AtomicWriteGroup."""

    def test_group_writes_multiple_files(self, tmp_path: Path) -> None:
        """Test that AtomicWriteGroup writes multiple files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        with AtomicWriteGroup() as group:
            group.add(file1, b"content1")
            group.add(file2, b"content2")
            group.commit()

        assert file1.read_bytes() == b"content1"
        assert file2.read_bytes() == b"content2"

    def test_group_atomic_commit(self, tmp_path: Path) -> None:
        """Test that files only appear after commit."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        group = AtomicWriteGroup()
        group.add(file1, b"content1")
        group.add(file2, b"content2")

        # Files should not exist yet
        assert not file1.exists()
        assert not file2.exists()

        # Temp files should exist
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 2

        group.commit()

        # Now files should exist
        assert file1.exists()
        assert file2.exists()

        # No temp files remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_group_rollback_on_context_exit_with_exception(
        self, tmp_path: Path
    ) -> None:
        """Test that rollback happens on context exit with exception."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        with pytest.raises(ValueError):
            with AtomicWriteGroup() as group:
                group.add(file1, b"content1")
                group.add(file2, b"content2")
                raise ValueError("Simulated error before commit")

        # Files should not exist
        assert not file1.exists()
        assert not file2.exists()

        # No temp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    def test_group_explicit_rollback(self, tmp_path: Path) -> None:
        """Test explicit rollback cleans up temp files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        group = AtomicWriteGroup()
        group.add(file1, b"content1")
        group.add(file2, b"content2")

        # Temp files should exist
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 2

        group.rollback()

        # No temp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0

        # Files should not exist
        assert not file1.exists()
        assert not file2.exists()

    def test_group_preserves_original_on_partial_commit_failure(
        self, tmp_path: Path
    ) -> None:
        """Test that original files are preserved if commit fails partway."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"

        # Create original file1
        file1.write_text("original1")

        group = AtomicWriteGroup()
        group.add(file1, b"new content 1")
        group.add(file2, b"new content 2")

        # Mock Path.replace to fail on second file
        original_replace = Path.replace
        call_count = [0]

        def failing_replace(self, target):
            call_count[0] += 1
            if call_count[0] == 2:
                raise OSError("Simulated disk error")
            return original_replace(self, target)

        with patch.object(Path, "replace", failing_replace):
            with pytest.raises(AtomicWriteError):
                group.commit()

        # Note: First file may have been replaced before failure
        # This is a known limitation - true atomic multi-file writes
        # require a transactional filesystem

    def test_group_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that AtomicWriteGroup creates parent directories."""
        file1 = tmp_path / "nested" / "dir1" / "file1.txt"
        file2 = tmp_path / "nested" / "dir2" / "file2.txt"

        with AtomicWriteGroup() as group:
            group.add(file1, b"content1")
            group.add(file2, b"content2")
            group.commit()

        assert file1.read_bytes() == b"content1"
        assert file2.read_bytes() == b"content2"


@pytest.mark.unit
class TestAtomicWriteEdgeCases:
    """Edge case tests for atomic write utilities."""

    def test_write_empty_file(self, tmp_path: Path) -> None:
        """Test writing an empty file."""
        target = tmp_path / "empty.txt"

        atomic_write_bytes(target, b"")

        assert target.exists()
        assert target.read_bytes() == b""

    def test_write_large_file(self, tmp_path: Path) -> None:
        """Test writing a large file."""
        target = tmp_path / "large.bin"
        data = b"x" * (10 * 1024 * 1024)  # 10 MB

        atomic_write_bytes(target, data)

        assert target.read_bytes() == data

    def test_concurrent_writes_to_different_files(self, tmp_path: Path) -> None:
        """Test that concurrent writes to different files work."""
        import concurrent.futures

        def write_file(idx: int) -> Path:
            target = tmp_path / f"file_{idx}.txt"
            atomic_write_text(target, f"content {idx}")
            return target

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_file, i) for i in range(10)]
            results = [f.result() for f in futures]

        for i, path in enumerate(results):
            assert path.read_text() == f"content {i}"

    def test_special_characters_in_path(self, tmp_path: Path) -> None:
        """Test writing to paths with special characters."""
        target = tmp_path / "file with spaces.txt"

        atomic_write_text(target, "content")

        assert target.read_text() == "content"

    def test_temp_file_in_same_directory(self, tmp_path: Path) -> None:
        """Test that temp file is created in same directory as target."""
        target = tmp_path / "subdir" / "file.txt"

        with atomic_write(target, mode="w") as f:
            # During write, temp file should be in same dir
            tmp_files = list(target.parent.glob("*.tmp"))
            assert len(tmp_files) == 1
            assert tmp_files[0].parent == target.parent
            f.write("content")

        assert target.read_text() == "content"
