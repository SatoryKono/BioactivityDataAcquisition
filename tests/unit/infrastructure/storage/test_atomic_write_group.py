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
"""Unit tests for atomic multi-file write groups."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.storage.support.atomic_group import AtomicWriteGroup
from bioetl.infrastructure.storage.support.atomic_ops import AtomicWriteError


pytestmark = pytest.mark.unit


def _temp_files(parent: Path) -> list[Path]:
    return sorted(parent.glob(".*_*.tmp"))


def test_atomic_write_group_commit_replaces_all_targets(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "nested" / "second.txt"

    group = AtomicWriteGroup()
    group.add(first, b"alpha")
    group.add(second, b"beta")

    assert _temp_files(tmp_path)
    assert _temp_files(second.parent)

    group.commit()

    assert first.read_bytes() == b"alpha"
    assert second.read_bytes() == b"beta"
    assert _temp_files(tmp_path) == []
    assert _temp_files(second.parent) == []


def test_atomic_write_group_rollback_removes_pending_temp_files(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    group = AtomicWriteGroup()
    group.add(target, b"payload")

    assert _temp_files(tmp_path)

    group.rollback()

    assert not target.exists()
    assert _temp_files(tmp_path) == []


def test_atomic_write_group_context_rolls_back_on_exception(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"

    with pytest.raises(RuntimeError, match="abort"):
        with AtomicWriteGroup() as group:
            group.add(target, b"payload")
            raise RuntimeError("abort")

    assert not target.exists()
    assert _temp_files(tmp_path) == []


def test_atomic_write_group_cleans_uncommitted_temp_files_on_commit_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"

    def fail_second_replace(
        temp_path: Path,
        target: Path,
        *,
        retry_policy: object,
    ) -> None:
        del retry_policy
        if target == first:
            temp_path.replace(target)
            return
        raise OSError("replace failed")

    monkeypatch.setattr(
        "bioetl.infrastructure.storage.support.atomic_group._replace_with_retry",
        fail_second_replace,
    )

    group = AtomicWriteGroup()
    group.add(first, b"alpha")
    group.add(second, b"beta")

    with pytest.raises(AtomicWriteError, match="Commit failed after 1 files"):
        group.commit()

    assert first.read_bytes() == b"alpha"
    assert not second.exists()
    assert _temp_files(tmp_path) == []
