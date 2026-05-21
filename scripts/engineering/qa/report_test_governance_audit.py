"""Static test-governance inventory for BioETL test-surface remediation."""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from functools import cache
from pathlib import Path
from typing import Any, cast

import yaml

from scripts.engineering.qa.file_discovery import discover_files

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = Path("configs/quality/test_governance_audit.yaml")
TEST_FUNCTION_PREFIX = "test_"
COMPATIBILITY_FILE_RE = re.compile(
    r"(compat|compatibility|legacy|deprecated|facade|shim|sunset)",
    re.IGNORECASE,
)
ASSERT_METHOD_NAMES = {
    "assert_any_call",
    "assert_called",
    "assert_called_once",
    "assert_called_once_with",
    "assert_called_with",
    "assert_has_calls",
    "assert_not_called",
}
ASSERTLESS_CATEGORY_RULES = {
    "architecture_helper_guard": (
        "architecture policy tests whose assertions are delegated to shared guard "
        "helpers or pytest.fail paths"
    ),
    "benchmark_or_performance": "performance/benchmark tests where measurement is the assertion surface",
    "intentional_no_exception_contract": "explicit no-op/smoke/does-not-raise contract tests",
    "helper_asserted": "tests that delegate verification to check/validate/verify helper calls",
    "weak_no_value": "candidate tests that need later assertion strengthening or removal review",
}
PYTEST_ASSERTION_HELPERS = {
    "pytest.fail",
    "pytest.raises",
    "pytest.warns",
}
BUDGET_TO_METRIC = {
    "refined_assertless_max": "refined_assertless_tests",
    "duplicate_test_names_max": "duplicate_test_names",
    "duplicate_test_name_occurrences_max": "duplicate_test_name_occurrences",
    "compatibility_test_file_max": "compatibility_test_files",
    "markerless_test_functions_max": "markerless_test_functions",
    "uuid4_call_sites_max": "uuid4_call_sites",
    "date_today_call_sites_max": "date_today_call_sites",
}


def _iter_test_files(root: Path) -> list[Path]:
    tests_root = root / "tests"
    return [
        tests_root / relative_path
        for relative_path in discover_files(
            str(tests_root.resolve()),
            ".py",
            TEST_FUNCTION_PREFIX,
        )
    ]


def _qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _qualified_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _has_pytest_mark(decorators: list[ast.expr]) -> bool:
    for decorator in decorators:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        qualified = _qualified_name(target)
        if qualified.startswith("pytest.mark"):
            return True
    return False


def _has_module_pytestmark(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "pytestmark":
                    return True
    return False


class _TestBodyVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.has_assertion_signal = False
        self.uuid4_call_sites = 0
        self.date_today_call_sites = 0
        self.helper_assertion_calls: list[str] = []
        self.called_names: list[str] = []

    def visit_Assert(self, node: ast.Assert) -> None:
        self.has_assertion_signal = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        qualified = _qualified_name(node.func)
        leaf = qualified.rsplit(".", 1)[-1]

        if qualified in PYTEST_ASSERTION_HELPERS:
            self.has_assertion_signal = True
        if leaf in ASSERT_METHOD_NAMES or leaf.startswith("assert_"):
            self.has_assertion_signal = True
        if leaf.startswith(("check_", "validate_", "verify_", "expect_")):
            self.helper_assertion_calls.append(qualified)

        if qualified:
            self.called_names.append(qualified)

        if qualified in {"uuid.uuid4", "uuid4"}:
            self.uuid4_call_sites += 1
        if qualified in {"date.today", "datetime.date.today"}:
            self.date_today_call_sites += 1

        self.generic_visit(node)


def _test_functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    functions: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(
            node, ast.FunctionDef | ast.AsyncFunctionDef
        ) and node.name.startswith(TEST_FUNCTION_PREFIX):
            functions.append(node)
    return functions


def _classify_assertless_candidate(
    *,
    relative_path: str,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    visitor: _TestBodyVisitor,
) -> str:
    name = function.name
    lower_name = name.lower()
    if "tests/architecture/" in relative_path:
        return "architecture_helper_guard"
    if "tests/performance/" in relative_path or "benchmark" in {
        arg.arg for arg in function.args.args
    }:
        return "benchmark_or_performance"
    if any(
        token in lower_name
        for token in (
            "noop",
            "no_op",
            "does_not_raise",
            "no_error",
            "smoke",
            "skip",
            "skips",
            "close",
            "aclose",
        )
    ):
        return "intentional_no_exception_contract"
    if visitor.helper_assertion_calls:
        return "helper_asserted"
    return "weak_no_value"


@cache
def _collect_test_governance_report_cached(root_str: str) -> dict[str, Any]:
    """Collect deterministic static counts used as remediation budgets."""
    root = Path(root_str).resolve()
    test_files = _iter_test_files(root)
    test_name_locations: dict[str, list[str]] = defaultdict(list)
    assertless_examples: list[str] = []
    assertless_candidates: list[dict[str, str]] = []
    assertless_category_counts: Counter[str] = Counter()
    compatibility_files: list[str] = []
    parse_errors: list[dict[str, str]] = []

    total_functions = 0
    refined_assertless_tests = 0
    markerless_test_functions = 0
    uuid4_call_sites = 0
    date_today_call_sites = 0

    for path in test_files:
        relative = path.relative_to(root).as_posix()
        if COMPATIBILITY_FILE_RE.search(relative):
            compatibility_files.append(relative)

        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
        except SyntaxError as exc:
            parse_errors.append({"path": relative, "error": str(exc)})
            continue

        module_has_mark = _has_module_pytestmark(tree)
        for function in _test_functions(tree):
            total_functions += 1
            location = f"{relative}:{function.lineno}"
            test_name_locations[function.name].append(location)

            visitor = _TestBodyVisitor()
            visitor.visit(function)
            uuid4_call_sites += visitor.uuid4_call_sites
            date_today_call_sites += visitor.date_today_call_sites

            if not visitor.has_assertion_signal:
                refined_assertless_tests += 1
                category = _classify_assertless_candidate(
                    relative_path=relative,
                    function=function,
                    visitor=visitor,
                )
                assertless_category_counts[category] += 1
                assertless_candidates.append(
                    {
                        "path": relative,
                        "line": str(function.lineno),
                        "test_name": function.name,
                        "category": category,
                        "rationale": ASSERTLESS_CATEGORY_RULES[category],
                    }
                )
                if len(assertless_examples) < 25:
                    assertless_examples.append(location)

            if not module_has_mark and not _has_pytest_mark(function.decorator_list):
                markerless_test_functions += 1

    duplicate_names = {
        name: locations
        for name, locations in test_name_locations.items()
        if len(locations) > 1
    }
    top_duplicate_names = [
        {
            "name": name,
            "count": len(locations),
            "examples": locations[:10],
        }
        for name, locations in sorted(
            duplicate_names.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )[:25]
    ]

    return {
        "root": root.as_posix(),
        "total_test_files": len(test_files),
        "total_test_functions": total_functions,
        "refined_assertless_tests": refined_assertless_tests,
        "assertless_category_counts": dict(sorted(assertless_category_counts.items())),
        "assertless_candidates": assertless_candidates,
        "assertless_examples": assertless_examples,
        "duplicate_test_names": len(duplicate_names),
        "duplicate_test_name_occurrences": sum(
            len(locations) for locations in duplicate_names.values()
        ),
        "top_duplicate_test_names": top_duplicate_names,
        "compatibility_test_files": len(compatibility_files),
        "compatibility_files": compatibility_files,
        "compatibility_examples": compatibility_files[:25],
        "markerless_test_functions": markerless_test_functions,
        "uuid4_call_sites": uuid4_call_sites,
        "date_today_call_sites": date_today_call_sites,
        "parse_errors": parse_errors,
    }


def collect_test_governance_report(root: Path = ROOT) -> dict[str, Any]:
    """Collect deterministic static counts used as remediation budgets."""
    return _collect_test_governance_report_cached(str(root.resolve()))


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return cast(dict[str, Any], yaml.safe_load(handle))


def evaluate_budgets(
    report: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    budgets = cast(dict[str, int], config.get("budgets", {}))
    violations: list[dict[str, Any]] = []
    for budget_key, metric_key in BUDGET_TO_METRIC.items():
        if budget_key not in budgets:
            continue
        actual = int(report[metric_key])
        expected_max = int(budgets[budget_key])
        if actual > expected_max:
            violations.append(
                {
                    "budget": budget_key,
                    "metric": metric_key,
                    "actual": actual,
                    "expected_max": expected_max,
                }
            )
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report static BioETL test-governance debt budgets.",
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=ROOT / DEFAULT_CONFIG)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    report = collect_test_governance_report(args.root)
    payload: dict[str, Any] = {"report": report}
    exit_code = 0

    if args.config.exists():
        config = load_config(args.config)
        violations = evaluate_budgets(report, config)
        payload["budget_violations"] = violations
        if args.check and violations:
            exit_code = 1

    output = json.dumps(payload, indent=2, sort_keys=True)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
