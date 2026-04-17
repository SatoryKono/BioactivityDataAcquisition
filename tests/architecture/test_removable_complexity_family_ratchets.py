"""Architecture guardrails for removable-complexity hotspot families."""

from __future__ import annotations

import ast
from pathlib import Path

import yaml

from scripts.engineering.qa.hotspot_family_metrics import (
    count_files_ge_loc,
    count_internal_fan_in,
    iter_family_python_files,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCORECARD_PATH = PROJECT_ROOT / "configs/quality/debt_scorecard.yaml"


def _load_scorecard() -> dict[str, object]:
    payload = yaml.safe_load(SCORECARD_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _imported_modules(relative_path: str) -> set[str]:
    tree = ast.parse((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


def _top_level_symbols(relative_path: str) -> set[str]:
    tree = ast.parse((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        )
    }


def test_removable_complexity_family_budgets_hold_reviewed_baseline() -> None:
    """Top removable-complexity families must stay within their reviewed budgets."""
    scorecard = _load_scorecard()
    policy = scorecard.get("removable_complexity_family_ratchets", {})
    assert isinstance(policy, dict)
    assert policy.get("snapshot_date") == "2026-04-13"
    assert isinstance(policy.get("update_policy"), str) and policy["update_policy"]

    families = policy.get("families", [])
    assert isinstance(families, list) and families

    for family in families:
        assert isinstance(family, dict)
        path_prefixes = family.get("path_prefixes", [])
        assert isinstance(path_prefixes, list) and path_prefixes
        files = iter_family_python_files(
            path_prefixes=[
                prefix for prefix in path_prefixes if isinstance(prefix, str)
            ]
        )
        actual_files_ge_250 = count_files_ge_loc(files=files, min_lines=250)
        actual_fan_in, actual_module = count_internal_fan_in(files=files)

        budgets = family.get("family_budgets", {})
        assert isinstance(budgets, dict)
        max_files_ge_250 = budgets.get("files_ge_250_loc")
        max_fan_in = budgets.get("max_internal_fan_in")
        assert isinstance(max_files_ge_250, int)
        assert isinstance(max_fan_in, int)

        assert actual_files_ge_250 <= max_files_ge_250, (
            f"{family.get('name')} regressed to {actual_files_ge_250} files >= 250 LOC "
            f"(budget {max_files_ge_250}). Rebaseline intentionally or keep the cleanup wave moving."
        )
        assert actual_fan_in <= max_fan_in, (
            f"{family.get('name')} regressed to max_internal_fan_in={actual_fan_in} "
            f"at {actual_module} (budget {max_fan_in}). Rebaseline intentionally or reduce coupling."
        )


def test_removable_complexity_tracked_seams_stay_extracted() -> None:
    """Tracked complexity seams should stay narrow and helper-backed."""
    scorecard = _load_scorecard()
    policy = scorecard.get("removable_complexity_family_ratchets", {})
    assert isinstance(policy, dict)
    families = policy.get("families", [])
    assert isinstance(families, list) and families

    tracked_seams = [
        seam
        for family in families
        if isinstance(family, dict)
        for seam in family.get("tracked_seams", [])
        if isinstance(seam, dict)
    ]
    assert tracked_seams, "Expected at least one tracked removable-complexity seam"

    for seam in tracked_seams:
        path = seam.get("path")
        max_lines = seam.get("max_lines")
        assert isinstance(path, str) and path
        assert isinstance(max_lines, int) and max_lines > 0

        source = (PROJECT_ROOT / path).read_text(encoding="utf-8")
        line_count = len(source.splitlines())
        assert line_count <= max_lines, (
            f"{path} regrew to {line_count} lines (max {max_lines}). Keep the seam thin "
            "or rebaseline the removable-complexity ratchet intentionally."
        )

        required_modules = seam.get("required_modules", [])
        if isinstance(required_modules, list) and required_modules:
            imported_modules = _imported_modules(path)
            missing_modules = {
                module for module in required_modules if module not in imported_modules
            }
            assert not missing_modules, (
                f"{path} no longer imports required extracted helpers:\n"
                + "\n".join(sorted(missing_modules))
            )

        required_symbols = seam.get("required_symbols", [])
        if isinstance(required_symbols, list) and required_symbols:
            symbols = _top_level_symbols(path)
            missing_symbols = {
                symbol for symbol in required_symbols if symbol not in symbols
            }
            assert not missing_symbols, (
                f"{path} no longer defines required extracted symbols:\n"
                + "\n".join(sorted(missing_symbols))
            )
