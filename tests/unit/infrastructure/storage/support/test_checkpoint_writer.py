# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Focused unit tests for filesystem checkpoint writer branches."""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from bioetl.infrastructure.storage.support.checkpoint_writer import (
    CheckpointPathError,
    FileCompositeCheckpointWriter,
)


pytestmark = pytest.mark.unit


def _symlink_or_skip(
    link: Path,
    target: Path,
    *,
    target_is_directory: bool,
) -> None:
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except OSError as exc:
        permission_errors = {errno.EACCES, errno.EPERM}
        if exc.errno in permission_errors or getattr(exc, "winerror", None) == 1314:
            pytest.skip(f"symlink privilege is unavailable: {exc}")
        raise


def _assert_file_operations_reject_escape(
    writer: FileCompositeCheckpointWriter,
    path: str,
) -> None:
    with pytest.raises(CheckpointPathError):
        writer.read(path)
    with pytest.raises(CheckpointPathError):
        writer.write_atomic(path, "{}")
    with pytest.raises(CheckpointPathError):
        writer.delete(path)
    with pytest.raises(CheckpointPathError):
        writer.exists(path)


def test_checkpoint_writer_read_delete_exists_and_missing_paths(tmp_path: Path) -> None:
    writer = FileCompositeCheckpointWriter(tmp_path)

    assert writer.read("missing.json") is None
    assert not writer.exists("missing.json")
    assert writer.delete("missing.json") is False

    writer.write_atomic("state.json", '{"status": "ok"}')

    assert writer.read("state.json") == '{"status": "ok"}'
    assert writer.exists("state.json")
    assert writer.delete("state.json") is True
    assert writer.read("state.json") is None


def test_checkpoint_writer_list_glob_returns_lexical_descending(tmp_path: Path) -> None:
    writer = FileCompositeCheckpointWriter(tmp_path)

    assert writer.list_glob("*.json") == []

    # Ordering is lexical descending by filename (not mtime).
    first = tmp_path / "run_001.json"
    second = tmp_path / "run_002.json"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")
    os.utime(first, (2, 2))
    os.utime(second, (1, 1))

    assert writer.list_glob("*.json") == ["run_002.json", "run_001.json"]


def test_checkpoint_writer_write_atomic_removes_temp_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer = FileCompositeCheckpointWriter(tmp_path)
    path_cls = type(tmp_path)

    def _raise_replace(self: Path, target: Path) -> Path:
        del self, target
        raise OSError("replace failed")

    monkeypatch.setattr(path_cls, "replace", _raise_replace)

    with pytest.raises(OSError, match="replace failed"):
        writer.write_atomic("state.json", "{}")

    leftover_temps = list(tmp_path.glob(".state_*.tmp")) + list(
        tmp_path.glob("state.tmp")
    )
    assert leftover_temps == []
    assert not (tmp_path / "state.json").exists()


def test_checkpoint_writer_rejects_path_escape(tmp_path: Path) -> None:
    writer = FileCompositeCheckpointWriter(tmp_path)
    with pytest.raises(CheckpointPathError):
        writer.read("../escape.json")


@pytest.mark.parametrize(
    "path",
    [
        "../escape.json",
        "nested/../../escape.json",
        "/absolute/escape.json",
        r"C:\absolute\escape.json",
        r"C:drive-relative\escape.json",
        r"\\server\share\escape.json",
    ],
)
def test_checkpoint_writer_rejects_cross_platform_lexical_escapes(
    tmp_path: Path,
    path: str,
) -> None:
    writer = FileCompositeCheckpointWriter(tmp_path)

    _assert_file_operations_reject_escape(writer, path)


@pytest.mark.parametrize(
    "pattern",
    [
        "../*.json",
        "/absolute/*.json",
        r"C:\absolute\*.json",
        r"\\server\share\*.json",
    ],
)
def test_checkpoint_writer_rejects_cross_platform_glob_escapes(
    tmp_path: Path,
    pattern: str,
) -> None:
    writer = FileCompositeCheckpointWriter(tmp_path)

    with pytest.raises(CheckpointPathError):
        writer.list_glob(pattern)


def test_checkpoint_writer_rejects_directory_symlink_escape_for_all_operations(
    tmp_path: Path,
) -> None:
    root = tmp_path / "checkpoints"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    external = outside / "escape.json"
    external.write_text("external", encoding="utf-8")
    _symlink_or_skip(root / "link", outside, target_is_directory=True)
    writer = FileCompositeCheckpointWriter(root)

    _assert_file_operations_reject_escape(writer, "link/escape.json")

    assert external.read_text(encoding="utf-8") == "external"


def test_checkpoint_writer_rejects_nested_symlinked_parent_escape(
    tmp_path: Path,
) -> None:
    root = tmp_path / "checkpoints"
    nested = root / "nested"
    outside = tmp_path / "outside"
    nested.mkdir(parents=True)
    outside.mkdir()
    _symlink_or_skip(nested / "link", outside, target_is_directory=True)
    writer = FileCompositeCheckpointWriter(root)

    _assert_file_operations_reject_escape(writer, "nested/link/escape.json")

    assert not (outside / "escape.json").exists()


def test_checkpoint_writer_rejects_resolved_glob_escape(tmp_path: Path) -> None:
    root = tmp_path / "checkpoints"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    external = outside / "escape.json"
    external.write_text("external", encoding="utf-8")
    _symlink_or_skip(root / "escaped.json", external, target_is_directory=False)
    writer = FileCompositeCheckpointWriter(root)

    with pytest.raises(CheckpointPathError):
        writer.list_glob("*.json")

    assert external.read_text(encoding="utf-8") == "external"


def test_checkpoint_writer_accepts_symlinked_checkpoint_root(tmp_path: Path) -> None:
    actual_root = tmp_path / "actual"
    actual_root.mkdir()
    root_link = tmp_path / "checkpoint-link"
    _symlink_or_skip(root_link, actual_root, target_is_directory=True)
    writer = FileCompositeCheckpointWriter(root_link)

    writer.write_atomic("state.json", "{}")

    assert writer.read("state.json") == "{}"
    assert (actual_root / "state.json").read_text(encoding="utf-8") == "{}"


def test_checkpoint_writer_rejects_oversized_payload(tmp_path: Path) -> None:
    from bioetl.infrastructure.storage.support.checkpoint_writer import (
        CheckpointSizeError,
    )

    writer = FileCompositeCheckpointWriter(tmp_path, max_checkpoint_bytes=8)
    with pytest.raises(CheckpointSizeError):
        writer.write_atomic("state.json", "x" * 16)
