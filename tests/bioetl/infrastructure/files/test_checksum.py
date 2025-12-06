import hashlib

from bioetl.infrastructure.files.checksum import (
    compute_file_sha256,
    compute_files_sha256,
)


def test_compute_sha256(tmp_path):
    test_file = tmp_path / "test_checksum.txt"
    content = b"test content for checksum"
    test_file.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()
    actual_hash = compute_file_sha256(test_file)

    assert actual_hash == expected_hash


def test_compute_sha256_large_file(tmp_path):
    test_file = tmp_path / "large_test_checksum.txt"
    # Create content slightly larger than chunk size
    content = b"a" * 10000
    test_file.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()
    actual_hash = compute_file_sha256(test_file)

    assert actual_hash == expected_hash


def test_compute_files_sha256(tmp_path):
    file_one = tmp_path / "one.txt"
    file_two = tmp_path / "two.txt"
    missing_file = tmp_path / "missing.txt"

    file_one.write_text("first", encoding="utf-8")
    file_two.write_text("second", encoding="utf-8")

    checksums = compute_files_sha256([file_one, file_two, missing_file])

    assert checksums == {
        file_one.name: hashlib.sha256(b"first").hexdigest(),
        file_two.name: hashlib.sha256(b"second").hexdigest(),
    }


def test_compute_files_sha256_empty_list(tmp_path):
    checksums = compute_files_sha256([])

    assert checksums == {}
