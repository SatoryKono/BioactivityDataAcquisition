"""Tests for ChecksumCalculator component."""

import pytest

from bioetl.infrastructure.output.components.checksum_calculator import (
    ChecksumCalculator,
)


@pytest.fixture
def calculator():
    """Create ChecksumCalculator instance."""
    return ChecksumCalculator()


def test_compute_checksum_for_file(calculator, tmp_path):
    """Test computing checksum for a single file."""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    # Compute checksum
    checksum = calculator.compute_checksum(test_file)

    # SHA256 of "Hello, World!" is known
    assert (
        checksum == "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    )


def test_compute_checksum_deterministic(calculator, tmp_path):
    """Test that checksum is deterministic."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Same content")

    checksum1 = calculator.compute_checksum(test_file)
    checksum2 = calculator.compute_checksum(test_file)

    assert checksum1 == checksum2


def test_compute_checksum_different_content(calculator, tmp_path):
    """Test that different content produces different checksums."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("Content A")
    file2.write_text("Content B")

    checksum1 = calculator.compute_checksum(file1)
    checksum2 = calculator.compute_checksum(file2)

    assert checksum1 != checksum2


def test_compute_checksums_multiple_files(calculator, tmp_path):
    """Test computing checksums for multiple files."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("Content 1")
    file2.write_text("Content 2")

    checksums = calculator.compute_checksums([file1, file2])

    assert "file1.txt" in checksums
    assert "file2.txt" in checksums
    assert len(checksums) == 2


def test_compute_checksums_skips_missing_files(calculator, tmp_path):
    """Test that missing files are skipped."""
    existing = tmp_path / "exists.txt"
    existing.write_text("I exist")
    missing = tmp_path / "missing.txt"

    checksums = calculator.compute_checksums([existing, missing])

    assert "exists.txt" in checksums
    assert "missing.txt" not in checksums


def test_compute_checksums_empty_list(calculator):
    """Test computing checksums for empty list."""
    checksums = calculator.compute_checksums([])
    assert checksums == {}


def test_custom_chunk_size():
    """Test calculator with custom chunk size."""
    calculator = ChecksumCalculator(chunk_size=1024)
    assert calculator._chunk_size == 1024
