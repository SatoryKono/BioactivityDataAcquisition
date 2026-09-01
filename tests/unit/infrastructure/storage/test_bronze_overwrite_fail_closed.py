# pyright: reportArgumentType=false
"""Unit tests for Bronze same-batch overwrite fail-closed behavior (#9632)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.storage.bronze.io_mixin import (
    BronzeWriterIOMixin,
    _publish_new_file_exclusive,
    write_bytes_if_absent_or_same,
)


class _Mixin(BronzeWriterIOMixin):
    COMPRESSION_LEVEL = 3
    COMPRESSION_THREADS = 1
    COMPRESSION_CHUNK_SIZE = 65536

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self._flat_structure = True
        self.logger = MagicMock()
        self._logger = self.logger
        self._metrics = MagicMock()
        self._resolve_bronze_path = lambda provider, entity, date_str, filename: (
            filename
        )


@pytest.mark.unit
def test_bronze_same_payload_is_idempotent(tmp_path: Path) -> None:
    mixin = _Mixin(tmp_path)
    target = tmp_path / "batch.jsonl.zst"
    records = [b'{"id": 1}\n', b'{"id": 2}\n']
    mixin._write_atomic_stream(iter(records), target)
    first = target.read_bytes()
    mixin._write_atomic_stream(iter(records), target)
    assert target.read_bytes() == first


@pytest.mark.unit
def test_bronze_different_payload_raises_file_exists(tmp_path: Path) -> None:
    mixin = _Mixin(tmp_path)
    target = tmp_path / "batch.jsonl.zst"
    mixin._write_atomic_stream(iter([b'{"id": 1}\n']), target)
    with pytest.raises(FileExistsError, match="already exists with different payload"):
        mixin._write_atomic_stream(iter([b'{"id": 2}\n']), target)


@pytest.mark.unit
def test_concurrent_identical_bronze_payload_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A concurrent identical publish is accepted without replacing its payload."""
    mixin = _Mixin(tmp_path)
    target = tmp_path / "batch.jsonl.zst"

    def publish_other_writer(source: Path, final_target: Path) -> None:
        """
        Simulate another writer publishing a file before reporting a conflict.
        
        Parameters:
            source (Path): Path containing the bytes to publish.
            final_target (Path): Destination path for the published bytes.
        
        Raises:
            FileExistsError: Always raised after the bytes are written to the destination.
        """
        final_target.write_bytes(source.read_bytes())
        raise FileExistsError(final_target)

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.bronze.io_mixin._publish_new_file_exclusive",
        publish_other_writer,
    )

    record_count, uncompressed_size = mixin._write_atomic_stream(
        iter([b'{"id": 1}\n']), target
    )

    assert (record_count, uncompressed_size) == (1, 10)
    assert target.exists()


@pytest.mark.unit
def test_sidecar_same_bytes_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "batch.meta.json"
    payload = b'{"k": 1}'
    write_bytes_if_absent_or_same(path, payload, mismatch_message="mismatch")
    write_bytes_if_absent_or_same(path, payload, mismatch_message="mismatch")
    assert path.read_bytes() == payload


@pytest.mark.unit
def test_sidecar_different_bytes_raises(tmp_path: Path) -> None:
    path = tmp_path / "batch.meta.json"
    write_bytes_if_absent_or_same(
        path, b'{"k": 1}', mismatch_message="sidecar mismatch"
    )
    with pytest.raises(FileExistsError, match="sidecar mismatch"):
        write_bytes_if_absent_or_same(
            path, b'{"k": 2}', mismatch_message="sidecar mismatch"
        )


@pytest.mark.unit
def test_payload_publish_failure_leaves_no_partial_final_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / ".batch.tmp"
    target = tmp_path / "batch.jsonl.zst"
    source.write_bytes(b"complete-payload")

    def fail_link(source_path: str, target_path: str) -> None:
        del source_path, target_path
        raise OSError("simulated publish failure")

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.bronze.io_mixin.os.link",
        fail_link,
    )

    with pytest.raises(OSError, match="simulated publish failure"):
        _publish_new_file_exclusive(source, target)

    assert not target.exists()
    assert source.read_bytes() == b"complete-payload"


@pytest.mark.unit
def test_sidecar_publish_failure_leaves_no_partial_final_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "batch.meta.json"

    def fail_publish(source: Path, final_target: Path) -> None:
        """
        Simulate a failure while publishing a temporary file.
        
        Raises:
            OSError: Always, to represent a publish failure.
        """
        del source, final_target
        raise OSError("simulated publish failure")

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.bronze.io_mixin._publish_new_file_exclusive",
        fail_publish,
    )

    with pytest.raises(OSError, match="simulated publish failure"):
        write_bytes_if_absent_or_same(
            target,
            b"complete-metadata",
            mismatch_message="sidecar mismatch",
        )

    assert not target.exists()
    assert list(tmp_path.glob(".*_*.tmp")) == []


@pytest.mark.unit
def test_concurrent_different_sidecar_is_not_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "batch.meta.json"

    def publish_other_writer(source: Path, final_target: Path) -> None:
        """
        Publish competing content at the target path and then signal that it already exists.
        
        Parameters:
        	final_target (Path): Path to the target file to populate before raising the error.
        """
        del source
        final_target.write_bytes(b"other-writer")
        raise FileExistsError(final_target)

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.bronze.io_mixin._publish_new_file_exclusive",
        publish_other_writer,
    )

    with pytest.raises(FileExistsError, match="sidecar mismatch"):
        write_bytes_if_absent_or_same(
            target,
            b"candidate",
            mismatch_message="sidecar mismatch",
        )

    assert target.read_bytes() == b"other-writer"
