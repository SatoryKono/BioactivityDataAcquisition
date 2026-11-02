# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture tests for diagram quality budget output-path hardening."""

from __future__ import annotations

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path
from types import ModuleType

import pytest


pytestmark = pytest.mark.architecture


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = (
        repo_root
        / "scripts"
        / "diagrams"
        / "lint"
        / "enforce_diagram_quality_budget.py"
    )
    spec = importlib.util.spec_from_file_location(
        "diagram_quality_budget_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_write_output_rejects_parent_traversal() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="outside"):
        module._write_output(Path("../outside/budget.json"), "{}\n")


def test_nightly_budget_requires_a_broad_report() -> None:
    module = _load_module()

    with pytest.raises(ValueError, match="--broad-report is required"):
        module._broad_checks(
            Namespace(mode="nightly", broad_report=None, max_broad_failures=0)
        )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "schema_version": 1,
            "status": "error",
            "checked_count": 20,
            "changed_count": 0,
            "errors": ["missing SVG"],
        },
        {
            "schema_version": 1,
            "status": "passed",
            "checked_count": 20,
            "changed_count": True,
            "errors": [],
        },
    ],
)
def test_nightly_budget_rejects_invalid_broad_reports(
    tmp_path: Path, payload: dict[str, object]
) -> None:
    module = _load_module()
    report = tmp_path / "broad.json"
    report.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="broad"):
        module._broad_checks(
            Namespace(mode="nightly", broad_report=report, max_broad_failures=0)
        )


def test_nightly_budget_uses_validated_broad_change_count(tmp_path: Path) -> None:
    module = _load_module()
    report = tmp_path / "broad.json"
    report.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "passed",
                "checked_count": 20,
                "changed_count": 1,
                "errors": [],
            }
        ),
        encoding="utf-8",
    )

    [check] = module._broad_checks(
        Namespace(mode="nightly", broad_report=report, max_broad_failures=0)
    )
    assert check.value == 1
    assert check.passed is False

