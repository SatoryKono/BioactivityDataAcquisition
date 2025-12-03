import hashlib

from bioetl.infrastructure.services.checksum import ChecksumService


def test_compute_sha256(tmp_path):
    service = ChecksumService()
    test_file = tmp_path / "test_checksum.txt"
    content = b"test content for checksum"
    test_file.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()
    actual_hash = service.compute_sha256(test_file)

    assert actual_hash == expected_hash


def test_compute_sha256_large_file(tmp_path):
    service = ChecksumService()
    test_file = tmp_path / "large_test_checksum.txt"
    # Create content slightly larger than chunk size
    content = b"a" * 10000
    test_file.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()
    actual_hash = service.compute_sha256(test_file)

    assert actual_hash == expected_hash
