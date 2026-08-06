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

import os
from pathlib import Path

import pytest

from bioetl.infrastructure.storage.support.checkpoint_writer import (
    FileCompositeCheckpointWriter,
)


pytestmark = pytest.mark.unit


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

    assert not (tmp_path / "state.tmp").exists()
    assert not (tmp_path / "state.json").exists()
