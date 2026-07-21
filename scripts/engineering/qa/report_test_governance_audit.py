"""Static test-governance inventory for BioETL test-surface remediation."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from functools import cache
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.engineering.qa.file_discovery import discover_files  # noqa: E402

DEFAULT_CONFIG = Path("configs/quality/test_governance_audit.yaml")
DEFAULT_JSON_ARTIFACT = Path("reports/quality/test-governance-current.json")
DEFAULT_FIXTURE_DUPLICATION_ARTIFACT = Path(
    "reports/quality/test-fixture-asset-duplication.json"
)
GOVERNANCE_SOURCE_FILES = (
    Path("pyproject.toml"),
    DEFAULT_CONFIG,
    Path("configs/quality/test_matrix.yaml"),
    Path("scripts/engineering/qa/file_discovery.py"),
    Path("scripts/engineering/qa/report_test_governance_audit.py"),
)
TEST_FUNCTION_PREFIX = "test_"
TESTS_ROOT = Path("tests")
REPO_BACKED_UNIT_ROOT = Path("tests/unit/repo_backed")
FIXTURE_DUPLICATION_SCAN_ROOT = Path("tests/fixtures")
FIXTURE_DUPLICATION_EXTENSIONS = frozenset({".json", ".yaml", ".yml"})
COMPATIBILITY_FILE_RE = re.compile(
    r"(compat|compatibility|legacy|deprecated|shim|sunset)",
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
NO_EXCEPTION_CONTRACT_NAME_TOKENS = (
    "accepts",
    "accepted",
    "allows",
    "allowed",
    "all_stages",
    "case__",
    "callable",
    "can_be",
    "can_log",
    "clear",
    "close",
    "consume",
    "creation",
    "defaults",
    "delegated",
    "detect",
    "does_not_raise",
    "does_nothing",
    "do_nothing",
    "edge_cases",
    "empty",
    "handles",
    "ignored",
    "ignores",
    "idempotent",
    "increments",
    "imports",
    "no_error",
    "no_records",
    "no_op",
    "none_skips",
    "noop",
    "null_allowed",
    "optional",
    "preserves",
    "returns",
    "single_value",
    "skip",
    "skips",
    "valid",
    "with_stage",
    "without",
    "works",
)
BUDGET_TO_METRIC = {
    "refined_assertless_max": "refined_assertless_tests",
    "duplicate_test_names_max": "duplicate_test_names",
    "duplicate_test_name_occurrences_max": "duplicate_test_name_occurrences",
    "compatibility_test_file_max": "compatibility_test_files",
    "markerless_test_functions_max": "markerless_test_functions",
    "uuid4_call_sites_max": "uuid4_call_sites",
    "date_today_call_sites_max": "date_today_call_sites",
}
CRITICAL_BEHAVIOR_ENVELOPES = {
    "control_plane_replay": (
        "tests/unit/application/services/test_run_manifest_service.py",
        "tests/unit/application/services/test_checkpoint_execution_identity_alignment.py",
        "tests/architecture/test_determinism_identity_policy.py",
        "tests/architecture/test_replay_time_seam_inventory.py",
    ),
    "gold_strict_contracts": (
        "tests/contract/test_gold_entity_coverage_complete.py",
        "tests/contract/test_gold_pk_consistency.py",
        "tests/contract/test_gold_schema_strict_violations.py",
        "tests/contract/test_gold_dq_golden_snapshots.py",
    ),
    "medallion_storage": (
        "tests/unit/infrastructure/storage/test_medallion_regression_envelope.py",
        "tests/unit/infrastructure/storage/test_silver_writer_merged_mixin.py",
    ),
    "quarantine_replay": (
        "tests/unit/domain/aggregates/test_quarantine_entry.py",
        "tests/unit/domain/aggregates/test_quarantine_entry_invariant_properties.py",
    ),
    "test_governance": ("tests/architecture/test_test_governance_audit.py",),
}


def _iter_fixture_asset_files(root: Path) -> list[Path]:
    fixtures_root = root / FIXTURE_DUPLICATION_SCAN_ROOT
    if not fixtures_root.exists():
        return []
    return [
        path
        for path in sorted(fixtures_root.rglob("*"))
        if path.is_file() and path.suffix.lower() in FIXTURE_DUPLICATION_EXTENSIONS
    ]


def _iter_all_test_python_files(root: Path) -> list[Path]:
    tests_root = root / TESTS_ROOT
    if not tests_root.exists():
        return []
    return [
        path
        for path in sorted(tests_root.rglob("*.py"))
        if path.is_file() and "__pycache__" not in path.parts
    ]


def _read_text_file(path: Path) -> str:
    """Read a text file as UTF-8, recovering UTF-16 BOM/encoding mistakes.

    Some Windows editors rewrite Python files as UTF-16 LE (BOM ``\\xff\\xfe``).
    Governance scanning must not crash on those files; when recovery succeeds the
    file is rewritten as UTF-8 so subsequent tooling stays stable.
    """
    raw = path.read_bytes()
    if not raw:
        return ""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
        path.write_bytes(text.encode("utf-8"))
        return text
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # Last-resort recovery for UTF-16 without a reliable BOM prefix.
        text = raw.decode("utf-16")
        path.write_bytes(text.encode("utf-8"))
        return text


@cache
def _compute_test_governance_source_tree_sha256(root_str: str) -> str:
    """Hash the report inputs so committed artifacts can be reused when fresh."""
    root = Path(root_str).resolve()
    digest = hashlib.sha256()
    governance_files = [
        root / relative_path
        for relative_path in GOVERNANCE_SOURCE_FILES
        if (root / relative_path).exists()
    ]
    files = sorted(
        [
            *governance_files,
            *_iter_all_test_python_files(root),
            *_iter_fixture_asset_files(root),
        ],
        key=lambda path: path.relative_to(root).as_posix().lower(),
    )
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def _load_current_artifact_if_fresh(root: Path) -> dict[str, Any] | None:
    artifact_path = root / DEFAULT_JSON_ARTIFACT
    if not artifact_path.exists():
        return None
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    expected_hash = str(payload.get("source_tree_sha256") or "")
    if not expected_hash:
        return None
    current_hash = _compute_test_governance_source_tree_sha256(str(root))
    if current_hash != expected_hash:
        return None
    return cast(dict[str, Any], payload)


def _lane_from_test_path(relative_path: str) -> str:
    parts = relative_path.split("/")
    if len(parts) >= 2 and parts[0] == "tests":
        return parts[1]
    return "unknown"


def _duplicate_location_classification(locations: list[str]) -> str:
    files = [location.rsplit(":", maxsplit=1)[0] for location in locations]
    unique_files = set(files)
    if len(unique_files) == 1:
        return "same_file"
    if len(unique_files) == len(files):
        return "cross_file"
    return "mixed"


def _build_duplicate_name_inventory(
    duplicate_names: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    inventory: list[dict[str, Any]] = []
    classification_counts: Counter[str] = Counter()

    for name, locations in sorted(
        duplicate_names.items(),
        key=lambda item: (-len(item[1]), item[0]),
    ):
        classification = _duplicate_location_classification(locations)
        classification_counts[classification] += 1
        lane_counts = Counter(
            _lane_from_test_path(location.rsplit(":", maxsplit=1)[0])
            for location in locations
        )
        inventory.append(
            {
                "name": name,
                "count": len(locations),
                "classification": classification,
                "lane_counts": dict(sorted(lane_counts.items())),
                "locations": locations,
                "suggested_pattern": "test_<subject>__<condition>__<expected_behavior>",
            }
        )

    summary = {
        "total_duplicate_names": len(duplicate_names),
        "duplicate_occurrences": sum(
            len(locations) for locations in duplicate_names.values()
        ),
        "same_file_groups": classification_counts["same_file"],
        "cross_file_groups": classification_counts["cross_file"],
        "mixed_groups": classification_counts["mixed"],
    }
    return inventory, summary


def _fixture_duplication_scope(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    if normalized.startswith("tests/fixtures/vcr/"):
        return "vcr"
    if normalized.startswith("tests/fixtures/golden/"):
        return "golden"
    return "fixture"


def _sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> tuple[str, int]:
    """Return the SHA-256 digest and byte size for a file path."""
    digest = hashlib.sha256()
    total_bytes = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
            total_bytes += len(chunk)
    return digest.hexdigest(), total_bytes


def _collect_fixture_asset_duplication(root: Path) -> dict[str, Any]:
    fixtures_root = root / FIXTURE_DUPLICATION_SCAN_ROOT
    scope_file_counts: Counter[str] = Counter()
    paths_by_size: dict[int, list[tuple[Path, str]]] = defaultdict(list)
    groups_by_hash: dict[str, list[str]] = defaultdict(list)
    total_bytes_by_hash: dict[str, int] = defaultdict(int)

    if fixtures_root.exists():
        for path in _iter_fixture_asset_files(root):
            relative = path.relative_to(root).as_posix()
            scope_file_counts[_fixture_duplication_scope(relative)] += 1
            try:
                file_size = path.stat().st_size
            except OSError:
                continue
            paths_by_size[file_size].append((path, relative))

    for file_size, rows in sorted(paths_by_size.items()):
        if len(rows) < 2:
            continue
        for path, relative in rows:
            digest, total_bytes = _sha256_file(path)
            groups_by_hash[digest].append(relative)
            total_bytes_by_hash[digest] += total_bytes

    duplicate_groups: list[dict[str, Any]] = []
    duplicate_file_count = 0
    for digest, paths in sorted(
        groups_by_hash.items(),
        key=lambda item: (-len(item[1]), item[0]),
    ):
        if len(paths) < 2:
            continue
        duplicate_file_count += len(paths)
        group_scope_counts = Counter(_fixture_duplication_scope(path) for path in paths)
        duplicate_groups.append(
            {
                "sha256": digest,
                "file_count": len(paths),
                "total_bytes": total_bytes_by_hash[digest],
                "scope_counts": dict(sorted(group_scope_counts.items())),
                "paths": sorted(paths, key=str.lower),
            }
        )

    return {
        "scan_root": FIXTURE_DUPLICATION_SCAN_ROOT.as_posix(),
        "tracked_extensions": sorted(FIXTURE_DUPLICATION_EXTENSIONS),
        "total_files": sum(scope_file_counts.values()),
        "scope_file_counts": dict(sorted(scope_file_counts.items())),
        "duplicate_groups": len(duplicate_groups),
        "duplicate_files": duplicate_file_count,
        "max_group_size": max(
            (int(group["file_count"]) for group in duplicate_groups),
            default=0,
        ),
        "groups": duplicate_groups,
    }


def _collect_test_file_inventory(root: Path, test_files: list[Path]) -> dict[str, Any]:
    tests_root = root / TESTS_ROOT
    all_top_level_dirs = [
        path.relative_to(root).as_posix() + "/"
        for path in sorted(tests_root.iterdir(), key=lambda item: item.name.lower())
        if path.is_dir()
    ]
    top_level_dirs = [
        path for path in all_top_level_dirs if not path.endswith("__pycache__/")
    ]

    return {
        "test_file_count_definition": (
            "tests/**/test_*.py matching pyproject tool.pytest.ini_options.python_files"
        ),
        "pytest_python_files": [f"{TEST_FUNCTION_PREFIX}*.py"],
        "test_glob_file_count": len(test_files),
        "test_python_file_count": len(_iter_all_test_python_files(root)),
        "top_level_directory_count": len(top_level_dirs),
        "top_level_directory_count_including_pycache": len(all_top_level_dirs),
        "top_level_directories": top_level_dirs,
        "top_level_directories_including_pycache": all_top_level_dirs,
    }


def _collect_repo_backed_unit_inventory(root: Path) -> dict[str, Any]:
    subtree = root / REPO_BACKED_UNIT_ROOT
    test_files = (
        sorted(subtree.rglob("test_*.py"), key=lambda path: path.as_posix().lower())
        if subtree.exists()
        else []
    )
    unmarked_paths: list[str] = []
    marked_count = 0
    for path in test_files:
        relative = path.relative_to(root).as_posix()
        try:
            text = _read_text_file(path)
        except (OSError, UnicodeDecodeError):
            unmarked_paths.append(relative)
            continue
        if "pytest.mark.repo_backed" in text:
            marked_count += 1
        else:
            unmarked_paths.append(relative)

    return {
        "decision": "dedicated_repo_backed_unit_lane_not_zero_inventory",
        "subtree": REPO_BACKED_UNIT_ROOT.as_posix() + "/",
        "lane": "repo-backed-unit",
        "marker": "pytest.mark.repo_backed",
        "test_files": len(test_files),
        "marked_test_files": marked_count,
        "unmarked_test_files": unmarked_paths,
    }


def _critical_envelope_template() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "paths": list(paths),
            "test_count": 0,
            "assertion_backed_tests": 0,
            "intentional_no_exception_tests": 0,
            "assertless_tests": [],
            "assertion_examples": [],
        }
        for name, paths in CRITICAL_BEHAVIOR_ENVELOPES.items()
    }


def _normalize_repo_relative_path(relative_path: str) -> str:
    """Normalize repo-relative paths for cross-platform governance scans."""
    return relative_path.replace("\\", "/")


def _matching_critical_envelopes(relative_path: str) -> tuple[str, ...]:
    normalized_path = _normalize_repo_relative_path(relative_path)
    return tuple(
        name
        for name, paths in CRITICAL_BEHAVIOR_ENVELOPES.items()
        if normalized_path in paths
    )


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


def _has_pytest_fixture(decorators: list[ast.expr]) -> bool:
    for decorator in decorators:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        qualified = _qualified_name(target)
        if qualified in {"pytest.fixture", "fixture"}:
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
        if leaf in ASSERT_METHOD_NAMES or leaf.startswith(("assert_", "_assert_")):
            self.has_assertion_signal = True
        if leaf.startswith(("check_", "validate_", "verify_", "expect_")):
            self.has_assertion_signal = True
            self.helper_assertion_calls.append(qualified)

        if qualified:
            self.called_names.append(qualified)

        if qualified in {"uuid.uuid4", "uuid4"}:
            self.uuid4_call_sites += 1
        if qualified in {"date.today", "datetime.date.today"}:
            self.date_today_call_sites += 1

        self.generic_visit(node)


class _TestFunctionCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.functions: list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, bool]] = []
        self._class_mark_stack: list[bool] = [False]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        inherited_mark = self._class_mark_stack[-1]
        class_has_mark = _has_pytest_mark(node.decorator_list)
        self._class_mark_stack.append(inherited_mark or class_has_mark)
        self.generic_visit(node)
        self._class_mark_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._collect_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._collect_function(node)

    def _collect_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        if node.name.startswith(TEST_FUNCTION_PREFIX) and not _has_pytest_fixture(
            node.decorator_list
        ):
            self.functions.append((node, self._class_mark_stack[-1]))


def _test_functions(
    tree: ast.Module,
) -> list[tuple[ast.FunctionDef | ast.AsyncFunctionDef, bool]]:
    collector = _TestFunctionCollector()
    collector.visit(tree)
    return collector.functions


def _classify_assertless_candidate(
    *,
    relative_path: str,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    visitor: _TestBodyVisitor,
) -> str:
    name = function.name
    lower_name = name.lower()
    normalized_path = _normalize_repo_relative_path(relative_path)
    if normalized_path.startswith("tests/architecture/"):
        return "architecture_helper_guard"
    if normalized_path.startswith("tests/performance/") or "benchmark" in {
        arg.arg for arg in function.args.args
    }:
        return "benchmark_or_performance"
    if any(token in lower_name for token in NO_EXCEPTION_CONTRACT_NAME_TOKENS):
        return "intentional_no_exception_contract"
    if visitor.helper_assertion_calls:
        return "helper_asserted"
    return "weak_no_value"


@cache
def _collect_test_governance_report_cached(root_str: str) -> dict[str, Any]:
    """Collect deterministic static counts used as remediation budgets."""
    root = Path(root_str).resolve()
    fresh_artifact = _load_current_artifact_if_fresh(root)
    if fresh_artifact is not None:
        return fresh_artifact
    test_files = _iter_test_files(root)
    test_name_locations: dict[str, list[str]] = defaultdict(list)
    assertless_examples: list[str] = []
    assertless_candidates: list[dict[str, str]] = []
    assertless_category_counts: Counter[str] = Counter()
    compatibility_files: list[str] = []
    parse_errors: list[dict[str, str]] = []
    critical_behavior_envelopes = _critical_envelope_template()

    total_functions = 0
    assertless_total_candidates = 0
    refined_assertless_tests = 0
    markerless_test_functions = 0
    markerless_examples: list[str] = []
    uuid4_call_sites = 0
    date_today_call_sites = 0

    for path in test_files:
        relative = _normalize_repo_relative_path(path.relative_to(root).as_posix())
        if COMPATIBILITY_FILE_RE.search(relative):
            compatibility_files.append(relative)

        try:
            source = _read_text_file(path)
        except OSError:
            continue
        except UnicodeDecodeError as exc:
            parse_errors.append(
                {
                    "path": relative,
                    "error": f"utf-8 decode failed: {exc}",
                }
            )
            continue

        try:
            tree = ast.parse(source, filename=relative)
        except SyntaxError as exc:
            parse_errors.append({"path": relative, "error": str(exc)})
            continue

        module_has_mark = _has_module_pytestmark(tree)
        for function, class_has_mark in _test_functions(tree):
            total_functions += 1
            location = f"{relative}:{function.lineno}"
            test_name_locations[function.name].append(location)

            visitor = _TestBodyVisitor()
            visitor.visit(function)
            uuid4_call_sites += visitor.uuid4_call_sites
            date_today_call_sites += visitor.date_today_call_sites
            matched_envelopes = _matching_critical_envelopes(relative)
            assertless_category: str | None = None

            if not visitor.has_assertion_signal:
                assertless_total_candidates += 1
                assertless_category = _classify_assertless_candidate(
                    relative_path=relative,
                    function=function,
                    visitor=visitor,
                )
                assertless_category_counts[assertless_category] += 1
                if assertless_category == "weak_no_value":
                    refined_assertless_tests += 1
                assertless_candidates.append(
                    {
                        "path": relative,
                        "line": str(function.lineno),
                        "test_name": function.name,
                        "category": assertless_category,
                        "rationale": ASSERTLESS_CATEGORY_RULES[assertless_category],
                    }
                )
                if len(assertless_examples) < 25:
                    assertless_examples.append(location)

            for envelope_name in matched_envelopes:
                envelope = critical_behavior_envelopes[envelope_name]
                envelope["test_count"] += 1
                if visitor.has_assertion_signal:
                    envelope["assertion_backed_tests"] += 1
                    if len(envelope["assertion_examples"]) < 10:
                        envelope["assertion_examples"].append(location)
                else:
                    if assertless_category == "intentional_no_exception_contract":
                        envelope["intentional_no_exception_tests"] += 1
                    envelope["assertless_tests"].append(
                        {
                            "path": relative,
                            "line": str(function.lineno),
                            "test_name": function.name,
                            "category": assertless_category or "unknown",
                        }
                    )

            if (
                not module_has_mark
                and not class_has_mark
                and not _has_pytest_mark(function.decorator_list)
            ):
                markerless_test_functions += 1
                markerless_examples.append(f"{relative}:{function.lineno}")

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
    duplicate_inventory, duplicate_inventory_summary = _build_duplicate_name_inventory(
        duplicate_names
    )
    assertion_gap_count = sum(
        1
        for envelope in critical_behavior_envelopes.values()
        if int(envelope["test_count"]) <= 0
        or int(envelope["assertion_backed_tests"]) <= 0
    )

    # Build assertless_families for file-level aggregation
    assertless_families: dict[str, dict[str, Any]] = {}
    for candidate in assertless_candidates:
        path = candidate["path"]
        if path not in assertless_families:
            assertless_families[path] = {
                "assertless_tests": 0,
                "categories": {},
            }
        assertless_families[path]["assertless_tests"] += 1
        category = candidate["category"]
        assertless_families[path]["categories"][category] = (
            assertless_families[path]["categories"].get(category, 0) + 1
        )

    # Build summary metrics
    intentional_no_exception_contract = assertless_category_counts.get(
        "intentional_no_exception_contract", 0
    )

    summary = {
        "assertless_total_candidates": assertless_total_candidates,
        "compatibility_test_files": len(compatibility_files),
        "date_today_call_sites": date_today_call_sites,
        "duplicate_test_name_occurrences": sum(
            len(locations) for locations in duplicate_names.values()
        ),
        "duplicate_test_names": len(duplicate_names),
        "intentional_no_exception_contract": intentional_no_exception_contract,
        "markerless_test_functions": markerless_test_functions,
        "markerless_examples": markerless_examples,
        "refined_assertless_tests": refined_assertless_tests,
        "uuid4_call_sites": uuid4_call_sites,
    }

    report = {
        "root": ".",
        "total_test_files": len(test_files),
        "total_test_functions": total_functions,
        "test_file_inventory": _collect_test_file_inventory(root, test_files),
        "repo_backed_unit_inventory": _collect_repo_backed_unit_inventory(root),
        "assertless_total_candidates": assertless_total_candidates,
        "refined_assertless_tests": refined_assertless_tests,
        "assertless_category_counts": {
            category: assertless_category_counts.get(category, 0)
            for category in sorted(ASSERTLESS_CATEGORY_RULES)
        },
        "assertless_candidates": assertless_candidates,
        "assertless_examples": assertless_examples,
        "markerless_test_functions": markerless_test_functions,
        "markerless_examples": markerless_examples,
        "duplicate_test_names": len(duplicate_names),
        "duplicate_test_name_occurrences": sum(
            len(locations) for locations in duplicate_names.values()
        ),
        "top_duplicate_test_names": top_duplicate_names,
        "duplicate_test_name_inventory": duplicate_inventory,
        "duplicate_test_name_inventory_summary": duplicate_inventory_summary,
        "compatibility_test_files": len(compatibility_files),
        "compatibility_files": compatibility_files,
        "compatibility_examples": compatibility_files[:25],
        "markerless_test_functions": markerless_test_functions,
        "uuid4_call_sites": uuid4_call_sites,
        "date_today_call_sites": date_today_call_sites,
        "critical_behavior_envelope_count": len(critical_behavior_envelopes),
        "critical_behavior_envelope_assertion_gap_count": assertion_gap_count,
        "critical_behavior_envelopes": critical_behavior_envelopes,
        "fixture_asset_duplication": _collect_fixture_asset_duplication(root),
        "parse_errors": parse_errors,
    }

    return {
        **report,
        "source_tree_sha256": _compute_test_governance_source_tree_sha256(root_str),
        **summary,
        "assertless_families": assertless_families,
        "budget_violations": [],
        "report": report,
        "summary": summary,
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


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _check_json_artifact(path: Path, payload: dict[str, Any]) -> bool:
    expected = _canonical_json(payload)
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    actual = path.read_text(encoding="utf-8")
    if actual == expected:
        return True
    print(f"[drift] mismatch: {path}")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report static BioETL test-governance debt budgets.",
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=ROOT / DEFAULT_CONFIG)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--fixture-duplication-out",
        type=Path,
        help=(
            "Write the tracked exact-byte duplication inventory for "
            "tests/fixtures/**/*.{json,yaml,yml}."
        ),
    )
    parser.add_argument(
        "--duplicate-name-inventory-out",
        type=Path,
        help=(
            "Optionally write the duplicate test-name inventory. CI keeps this "
            "inventory embedded in test-governance-current.json and does not "
            "commit a separate duplicate-name artifact."
        ),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    payload = collect_test_governance_report(args.root)
    json_out = args.json_out
    fixture_duplication_out = args.fixture_duplication_out
    duplicate_name_inventory_out = args.duplicate_name_inventory_out
    if args.check and json_out is None:
        candidate = args.root / DEFAULT_JSON_ARTIFACT
        if candidate.exists():
            json_out = candidate
    if args.check and fixture_duplication_out is None:
        candidate = args.root / DEFAULT_FIXTURE_DUPLICATION_ARTIFACT
        if candidate.exists():
            fixture_duplication_out = candidate
    if args.check and duplicate_name_inventory_out is not None:
        duplicate_name_inventory_out = args.root / duplicate_name_inventory_out
    exit_code = 0

    if args.config.exists():
        config = load_config(args.config)
        violations = evaluate_budgets(payload["report"], config)
        payload["budget_violations"] = violations
        if args.check and violations:
            exit_code = 1

    fixture_duplication_payload = payload["report"]["fixture_asset_duplication"]
    duplicate_name_inventory_payload = {
        "summary": payload["report"]["duplicate_test_name_inventory_summary"],
        "inventory": payload["report"]["duplicate_test_name_inventory"],
    }
    output = _canonical_json(payload)
    if args.check:
        if json_out is not None and not _check_json_artifact(json_out, payload):
            exit_code = 1
        if fixture_duplication_out is not None and not _check_json_artifact(
            fixture_duplication_out,
            fixture_duplication_payload,
        ):
            exit_code = 1
        if duplicate_name_inventory_out is not None and not _check_json_artifact(
            duplicate_name_inventory_out,
            duplicate_name_inventory_payload,
        ):
            exit_code = 1
    elif json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(output, encoding="utf-8")
    else:
        print(output)
    if fixture_duplication_out and not args.check:
        fixture_duplication_out.parent.mkdir(parents=True, exist_ok=True)
        fixture_duplication_out.write_text(
            _canonical_json(fixture_duplication_payload),
            encoding="utf-8",
        )
    if duplicate_name_inventory_out and not args.check:
        duplicate_name_inventory_out.parent.mkdir(parents=True, exist_ok=True)
        duplicate_name_inventory_out.write_text(
            _canonical_json(duplicate_name_inventory_payload),
            encoding="utf-8",
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
