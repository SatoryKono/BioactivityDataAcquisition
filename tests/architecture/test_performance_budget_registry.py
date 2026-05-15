"""Architecture guardrail for the hotspot performance budget registry."""

from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HOTSPOT_BUDGETS_PATH = ROOT / "tests" / "performance" / "hotspot_budgets.json"
HOTSPOT_TEST_PATH = ROOT / "tests" / "performance" / "test_hotspot_budgets.py"


def _load_registry_keys() -> set[str]:
    payload = json.loads(HOTSPOT_BUDGETS_PATH.read_text(encoding="utf-8"))
    return set(payload.get("benchmarks", {}))


def _load_implemented_benchmark_keys() -> set[str]:
    tree = ast.parse(HOTSPOT_TEST_PATH.read_text(encoding="utf-8"))

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "_IMPLEMENTED_BENCHMARK_KEYS"
            for target in node.targets
        ):
            continue
        if (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "frozenset"
            and len(node.value.args) == 1
        ):
            return set(ast.literal_eval(node.value.args[0]))

    raise AssertionError(
        "Could not extract _IMPLEMENTED_BENCHMARK_KEYS from "
        f"{HOTSPOT_TEST_PATH.relative_to(ROOT)}"
    )


def test_hotspot_budget_registry_matches_implemented_benchmarks() -> None:
    """Budget registry JSON must stay in bijection with implemented benchmarks."""
    assert _load_registry_keys() == _load_implemented_benchmark_keys()
