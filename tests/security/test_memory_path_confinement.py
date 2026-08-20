"""Path-traversal regression tests for memory filesystem sinks (#9062)."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.fs_confine import canonicalize_memory_path
from memory.migrations import migrate_json_file
from memory.proof import file_digest
from memory.storage import atomic_write_bytes

pytestmark = pytest.mark.security


def test_canonicalize_rejects_parent_segment(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="path traversal"):
        canonicalize_memory_path(Path(tmp_path, "ok", "..", "escape"))


def test_canonicalize_confines_under_root(tmp_path: Path) -> None:
    root = tmp_path / "store"
    root.mkdir()
    inside = canonicalize_memory_path(root / "record.json", root=root)
    assert inside == (root / "record.json").resolve()
    with pytest.raises(ValueError, match="outside"):
        canonicalize_memory_path(tmp_path / "other.json", root=root)


def test_migrate_json_file_rejects_traversal(tmp_path: Path) -> None:
    victim = tmp_path / "victim.json"
    victim.write_text("{\"id\":\"x\"}\n", encoding="utf-8")
    sneaky = Path(tmp_path, "nested", "..", "victim.json")
    sneaky.parent.mkdir(exist_ok=True)
    with pytest.raises(ValueError, match="path traversal"):
        migrate_json_file(sneaky, target_version=1)


def test_atomic_write_bytes_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="path traversal"):
        atomic_write_bytes(Path(tmp_path, "a", "..", "b.json"), b"{}")


def test_file_digest_rejects_traversal(tmp_path: Path) -> None:
    target = tmp_path / "blob.bin"
    target.write_bytes(b"abc")
    with pytest.raises(ValueError, match="path traversal"):
        file_digest(Path(tmp_path, "x", "..", "blob.bin"))
