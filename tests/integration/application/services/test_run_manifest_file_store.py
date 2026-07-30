"""Integration coverage for RunManifestService and its file-store adapter."""

from __future__ import annotations

from pathlib import Path

import pytest

import bioetl.infrastructure.control_plane.file_run_manifest_store as store_module
from bioetl.application.services.control_plane.manifest.service import (
    RunManifestService,
)
from bioetl.domain.exceptions import StorageError
from bioetl.infrastructure.control_plane import FileRunManifestStore
from tests.unit.application.services.test_run_manifest_service import _make_request


pytestmark = pytest.mark.integration


def test_create_manifest_aborts_when_atomic_persistence_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    service = RunManifestService(
        manifest_port=store,
        _manifest_id_factory=lambda: "manifest-storage-failure",
    )
    original_atomic_write_text = store_module.atomic_write_text
    call_count = 0

    def _fail_on_index_write(
        path: Path,
        text: str,
        encoding: str = "utf-8",
    ) -> None:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            original_atomic_write_text(path, text, encoding=encoding)
            return
        raise OSError("run index write failed")

    monkeypatch.setattr(store_module, "atomic_write_text", _fail_on_index_write)

    with pytest.raises(StorageError, match="Run manifest save failed"):
        service.create_manifest(_make_request())

    assert store.get("manifest-storage-failure") is None
