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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for apply_entity_naming_rename_plan repository path handling."""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

pytestmark = pytest.mark.repo_backed


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[4]
    module_path = (
        repo_root
        / "scripts"
        / "engineering"
        / "repo"
        / "apply_entity_naming_rename_plan.py"
    )
    spec = importlib.util.spec_from_file_location(
        "apply_entity_naming_rename_plan_module",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_load_rows_normalizes_repo_absolute_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    target = tmp_path / "src" / "bioetl" / "sample.py"
    target.parent.mkdir(parents=True)
    target.write_text("LegacyEntity\n", encoding="utf-8")

    matrix_path = tmp_path / "matrix.csv"
    with matrix_path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(
            file_obj,
            fieldnames=[
                "wave",
                "phase_order",
                "action",
                "symbol_kind",
                "old_name",
                "new_name",
                "file_path",
                "file_kind",
                "auto_safe",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "wave": "W1",
                "phase_order": "1",
                "action": "replace_symbol",
                "symbol_kind": "class",
                "old_name": "LegacyEntity",
                "new_name": "CanonicalEntity",
                "file_path": str(target),
                "file_kind": "python",
                "auto_safe": "true",
                "notes": "",
            }
        )

    rows = module.load_rows(matrix_path)

    assert rows[0].file_path == Path("src/bioetl/sample.py")


def test_repo_relative_path_rejects_parent_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    with pytest.raises(ValueError, match="parent traversal"):
        module._repo_relative_path(Path("../escape.py"))


def test_apply_rows_writes_only_with_repo_relative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)

    target = tmp_path / "src" / "bioetl" / "sample.py"
    target.parent.mkdir(parents=True)
    target.write_text("LegacyEntity\n", encoding="utf-8")

    row = module.RenameRow(
        wave="W1",
        phase_order=1,
        action="replace_symbol",
        symbol_kind="class",
        old_name="LegacyEntity",
        new_name="CanonicalEntity",
        file_path=Path("src/bioetl/sample.py"),
        validated_file_path=module.ValidatedRepoPath(target),
        file_kind="python",
        auto_safe=True,
        notes="",
    )

    exit_code = module.apply_rows([row], apply=True)

    assert exit_code == 0
    assert target.read_text(encoding="utf-8") == "CanonicalEntity\n"
