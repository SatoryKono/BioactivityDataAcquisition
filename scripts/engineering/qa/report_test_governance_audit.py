"""Static test-governance inventory for BioETL test-surface remediation."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.engineering.qa.file_discovery import discover_files

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
    "unreviewed_assertion_bypass_max": "unreviewed_assertion_bypass_count",
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
    "pipeline_run_fsm": (
        "tests/unit/domain/aggregates/test_batch_fsm_exhaustive.py",
        "tests/unit/domain/aggregates/test_pipeline_run.py",
        "tests/unit/domain/aggregates/test_batch_invariant_properties.py",
        "tests/unit/application/core/test_batch_transformer.py",
    ),
    "test_governance": ("tests/architecture/test_test_governance_audit.py",),
}
ASSERTION_REACHABILITY_PATHS = frozenset(
    path for paths in CRITICAL_BEHAVIOR_ENVELOPES.values() for path in paths
) | {
    "tests/integration/test_grafana_config.py",
    "tests/integration/test_grafana_dashboard_links.py",
    "tests/integration/test_grafana_layout_and_metadata.py",
    "tests/integration/test_dashboard_required_panel_links.py",
    "tests/integration/test_grafana_navigation_matrix.py",
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
    # Prefer the shared discover helper so pruned dirs (__pycache__, .venv, …)
    # and fixture/snapshot subtrees stay out of the hash/scan inventory.
    return [
        tests_root / relative for relative in discover_files(str(tests_root), ".py")
    ]


def _read_text_file(path: Path) -> str:
    """Read a text file as UTF-8, recovering UTF-16 BOM/encoding mistakes.

    Some Windows editors rewrite Python files as UTF-16 LE (BOM ``\\xff\\xfe``).
    Governance scanning must not crash on those files; when recovery succeeds the
    file is rewritten as UTF-8 so subsequent tooling stays stable.
    """
    from scripts.engineering.common.repo_paths import REPO_ROOT, ensure_repo_path

    safe_root = REPO_ROOT.resolve(strict=False)
    confined_path = ensure_repo_path(path)
    relative_path = confined_path.relative_to(safe_root)
    safe_path = safe_root.joinpath(*relative_path.parts)
    raw = safe_path.read_bytes()
    if not raw:
        return ""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        text = raw.decode("utf-16")
        safe_path.write_bytes(text.encode("utf-8"))
        return text
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        # Last-resort recovery for UTF-16 without a reliable BOM prefix.
        text = raw.decode("utf-16")
        safe_path.write_bytes(text.encode("utf-8"))
        return text


def _source_tree_hash_workers(total_files: int) -> int:
    """Bound parallelism for content hashing on cloud-synced worktrees."""
    if total_files < 64:
        return 1
    configured = os.getenv("BIOETL_TEST_GOVERNANCE_HASH_WORKERS", "").strip()
    if configured:
        try:
            return max(1, min(int(configured), 16, total_files))
        except ValueError:
            pass
    if os.name == "nt":
        return min(4, total_files)
    return min(8, total_files)


def _read_source_tree_bytes(path: Path) -> bytes:
    """Read one source-tree file for the freshness hash."""
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe_path = resolve_output_path(path, root=REPO_ROOT)
    with safe_path.open(
        "rb"
    ) as handle:  # NOSONAR - path confined by resolve_output_path
        return handle.read()


@cache
def _compute_test_governance_source_tree_sha256(root_str: str) -> str:
    """Hash the report inputs so committed artifacts can be reused when fresh.

    Digest bytes and file order match the historical sequential algorithm so
    committed ``source_tree_sha256`` values stay comparable. Only the file
    reads are parallelized (latency-bound on cloud-synced Windows trees).
    """
    root = Path(root_str).resolve()
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

    def _read_one(path: Path) -> tuple[str, bytes]:
        relative = path.relative_to(root).as_posix()
        try:
            return relative, _read_source_tree_bytes(path)
        except OSError:
            return relative, b""

    workers = _source_tree_hash_workers(len(files))
    if workers == 1:
        payloads = [_read_one(path) for path in files]
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            payloads = list(executor.map(_read_one, files, chunksize=16))

    digest = hashlib.sha256()
    for relative, content in payloads:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def _load_current_artifact_if_fresh(root: Path) -> dict[str, Any] | None:
    from scripts.engineering.common.repo_paths import resolve_output_path

    artifact_path = resolve_output_path(root / DEFAULT_JSON_ARTIFACT, root=root)
    if not artifact_path.exists():
        return None
    try:
        artifact_text = (
            artifact_path.read_text(  # NOSONAR - path confined by resolve_output_path
                encoding="utf-8"
            )
        )
        payload = json.loads(artifact_text)
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
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe_path = resolve_output_path(path, root=REPO_ROOT)
    digest = hashlib.sha256()
    total_bytes = 0
    with safe_path.open(
        "rb"
    ) as handle:  # NOSONAR - path confined by resolve_output_path
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


def _call_is_assertion_signal(call: ast.Call) -> bool:
    qualified = _qualified_name(call.func)
    leaf = qualified.rsplit(".", 1)[-1]
    return (
        qualified in PYTEST_ASSERTION_HELPERS
        or leaf in ASSERT_METHOD_NAMES
        or leaf.startswith(
            ("assert_", "_assert_", "check_", "validate_", "verify_", "expect_")
        )
    )


def _direct_assertion_signal(statement: ast.stmt) -> bool:
    """Return whether this statement asserts without relying on a nested branch."""
    if isinstance(statement, ast.Assert):
        return True
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
        return _call_is_assertion_signal(statement.value)
    if isinstance(statement, (ast.Assign, ast.AnnAssign)):
        value = statement.value
        return isinstance(value, ast.Call) and _call_is_assertion_signal(value)
    if isinstance(statement, (ast.With, ast.AsyncWith)):
        return any(
            isinstance(item.context_expr, ast.Call)
            and _call_is_assertion_signal(item.context_expr)
            for item in statement.items
        )
    return False


def _empty_parametrization_lines(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[int]:
    lines: list[int] = []
    for decorator in function.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        if _qualified_name(decorator.func) != "pytest.mark.parametrize":
            continue
        if len(decorator.args) < 2:
            continue
        values = decorator.args[1]
        if isinstance(values, (ast.List, ast.Tuple, ast.Set)) and not values.elts:
            lines.append(decorator.lineno)
    return lines


class _AssertionReachabilityAnalyzer:
    """Small conservative CFG for assertion-bypassing test paths."""

    def __init__(self) -> None:
        self.findings: list[tuple[int, str]] = []
        self.continue_before_assertion_lines: set[int] = set()

    def analyze(
        self,
        function: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> list[tuple[int, str]]:
        visitor = _TestBodyVisitor()
        visitor.visit(function)
        if not visitor.has_assertion_signal:
            return []
        for line in _empty_parametrization_lines(function):
            self.findings.append((line, "empty_parametrization"))
        final_states = self._block(function.body, {False}, in_loop=False)
        if False in final_states:
            self.findings.extend(
                (line, "continue_before_assertion")
                for line in self.continue_before_assertion_lines
            )
        return sorted(set(self.findings))

    def _block(
        self,
        statements: list[ast.stmt],
        states: set[bool],
        *,
        in_loop: bool,
    ) -> set[bool]:
        active = set(states)
        for statement in statements:
            if not active:
                break
            active = self._statement(statement, active, in_loop=in_loop)
        return active

    def _exit_statement_states(
        self,
        statement: ast.stmt,
        states: set[bool],
    ) -> set[bool] | None:
        """Handle terminal control-flow statements; None means not terminal."""
        if isinstance(statement, ast.Return):
            if False in states:
                self.findings.append(
                    (statement.lineno, "early_return_before_assertion")
                )
            return set()
        if isinstance(statement, ast.Continue):
            if False in states:
                self.continue_before_assertion_lines.add(statement.lineno)
            return set()
        if isinstance(statement, (ast.Raise, ast.Break)):
            return set()
        return None

    def _compound_statement_states(
        self,
        statement: ast.stmt,
        states: set[bool],
        *,
        in_loop: bool,
    ) -> set[bool] | None:
        """Handle compound statements; None means not a compound form."""
        if isinstance(statement, ast.If):
            return self._block(statement.body, states, in_loop=in_loop) | self._block(
                statement.orelse, states, in_loop=in_loop
            )
        if isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
            # Zero iterations is always a conservative path; body paths model the
            # last successful iteration before loop exit.
            body_states = self._block(statement.body, states, in_loop=True)
            loop_exit = states | body_states
            return self._block(statement.orelse, loop_exit, in_loop=in_loop)
        if isinstance(statement, (ast.With, ast.AsyncWith)):
            return self._block(statement.body, states, in_loop=in_loop)
        if isinstance(statement, ast.Try):
            return self._try_statement_states(statement, states, in_loop=in_loop)
        if isinstance(statement, ast.Match):
            paths = set(states)
            for case in statement.cases:
                paths |= self._block(case.body, states, in_loop=in_loop)
            return paths
        return None

    def _try_statement_states(
        self,
        statement: ast.Try,
        states: set[bool],
        *,
        in_loop: bool,
    ) -> set[bool]:
        paths = self._block(statement.body, states, in_loop=in_loop)
        for handler in statement.handlers:
            paths |= self._block(handler.body, states, in_loop=in_loop)
        paths = self._block(statement.orelse, paths, in_loop=in_loop)
        return self._block(statement.finalbody, paths, in_loop=in_loop)

    def _statement(
        self,
        statement: ast.stmt,
        states: set[bool],
        *,
        in_loop: bool,
    ) -> set[bool]:
        if _direct_assertion_signal(statement):
            states = {True for _state in states}

        exit_states = self._exit_statement_states(statement, states)
        if exit_states is not None:
            return exit_states
        compound_states = self._compound_statement_states(
            statement, states, in_loop=in_loop
        )
        if compound_states is not None:
            return compound_states
        return states


def _assertion_reachability_findings(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[tuple[int, str]]:
    return _AssertionReachabilityAnalyzer().analyze(function)


def _load_assertion_bypass_allowlist(root: Path) -> list[dict[str, str]]:
    from scripts.engineering.common.repo_paths import resolve_output_path

    config_path = resolve_output_path(root / DEFAULT_CONFIG, root=root)
    if not config_path.exists():
        return []
    config_text = (
        config_path.read_text(  # NOSONAR - path confined by resolve_output_path
            encoding="utf-8"
        )
    )
    payload = yaml.safe_load(config_text) or {}
    entries = payload.get("assertion_bypass_allowlist", [])
    return [dict(entry) for entry in entries if isinstance(entry, dict)]


def _review_assertion_bypass(
    finding: dict[str, str],
    allowlist: list[dict[str, str]],
) -> dict[str, str]:
    for entry in allowlist:
        if all(
            entry.get(key) == finding[key] for key in ("path", "test_name", "reason")
        ):
            return {
                **finding,
                "owner": entry.get("owner", "test-governance"),
                "disposition": entry.get("disposition", "reviewed-retained"),
                "reviewed": "true",
            }
    return {
        **finding,
        "owner": "unassigned",
        "disposition": "fail-unreviewed",
        "reviewed": "false",
    }


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
def _parse_test_module_source(
    path: Path,
    *,
    relative: str,
) -> tuple[ast.Module | None, dict[str, str] | None]:
    """Read and parse a test module; return (tree, parse_error)."""
    try:
        source = _read_text_file(path)
    except OSError:
        return None, None
    except UnicodeDecodeError as exc:
        return None, {
            "path": relative,
            "error": f"utf-8 decode failed: {exc}",
        }
    try:
        return ast.parse(source, filename=relative), None
    except SyntaxError as exc:
        return None, {"path": relative, "error": str(exc)}


def _record_assertion_reachability_findings(
    *,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    relative: str,
    assertion_bypass_allowlist: list[dict[str, str]],
    assertion_bypass_findings: list[dict[str, str]],
) -> None:
    """Append reviewed assertion-bypass findings for one scanned test."""
    for finding_line, reason in _assertion_reachability_findings(function):
        assertion_bypass_findings.append(
            _review_assertion_bypass(
                {
                    "path": relative,
                    "line": str(finding_line),
                    "test_name": function.name,
                    "reason": reason,
                },
                assertion_bypass_allowlist,
            )
        )


def _record_assertless_candidate(
    *,
    relative: str,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    visitor: _TestBodyVisitor,
    location: str,
    assertless_category_counts: Counter[str],
    assertless_candidates: list[dict[str, str]],
    assertless_examples: list[str],
) -> tuple[str, int, int]:
    """Record one assertless candidate; return (category, total_delta, refined_delta)."""
    assertless_category = _classify_assertless_candidate(
        relative_path=relative,
        function=function,
        visitor=visitor,
    )
    assertless_category_counts[assertless_category] += 1
    refined_delta = 1 if assertless_category == "weak_no_value" else 0
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
    return assertless_category, 1, refined_delta


def _update_critical_envelopes(
    *,
    matched_envelopes: tuple[str, ...],
    critical_behavior_envelopes: dict[str, dict[str, Any]],
    visitor: _TestBodyVisitor,
    location: str,
    relative: str,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    assertless_category: str | None,
) -> None:
    """Update critical-behavior envelope counters for one test function."""
    for envelope_name in matched_envelopes:
        envelope = critical_behavior_envelopes[envelope_name]
        envelope["test_count"] += 1
        if visitor.has_assertion_signal:
            envelope["assertion_backed_tests"] += 1
            if len(envelope["assertion_examples"]) < 10:
                envelope["assertion_examples"].append(location)
            continue
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


def _scan_one_test_function(
    *,
    function: ast.FunctionDef | ast.AsyncFunctionDef,
    class_has_mark: bool,
    module_has_mark: bool,
    relative: str,
    assertion_bypass_allowlist: list[dict[str, str]],
    critical_behavior_envelopes: dict[str, dict[str, Any]],
    test_name_locations: dict[str, list[str]],
    assertless_examples: list[str],
    assertless_candidates: list[dict[str, str]],
    assertless_category_counts: Counter[str],
    assertion_bypass_findings: list[dict[str, str]],
    markerless_examples: list[str],
) -> tuple[int, int, int, int, int, int, int]:
    """Scan one test function; return metric deltas.

    Returns
    -------
    total_functions, assertless_total, refined_assertless, markerless,
    uuid4_sites, date_today_sites, reachability_scanned
    """
    location = f"{relative}:{function.lineno}"
    test_name_locations[function.name].append(location)
    visitor = _TestBodyVisitor()
    visitor.visit(function)
    assertless_category: str | None = None
    assertless_total = 0
    refined_assertless = 0
    reachability_scanned = 0
    markerless = 0

    if relative in ASSERTION_REACHABILITY_PATHS:
        reachability_scanned = 1
        _record_assertion_reachability_findings(
            function=function,
            relative=relative,
            assertion_bypass_allowlist=assertion_bypass_allowlist,
            assertion_bypass_findings=assertion_bypass_findings,
        )

    if not visitor.has_assertion_signal:
        assertless_category, assertless_total, refined_assertless = (
            _record_assertless_candidate(
                relative=relative,
                function=function,
                visitor=visitor,
                location=location,
                assertless_category_counts=assertless_category_counts,
                assertless_candidates=assertless_candidates,
                assertless_examples=assertless_examples,
            )
        )

    _update_critical_envelopes(
        matched_envelopes=_matching_critical_envelopes(relative),
        critical_behavior_envelopes=critical_behavior_envelopes,
        visitor=visitor,
        location=location,
        relative=relative,
        function=function,
        assertless_category=assertless_category,
    )

    if (
        not module_has_mark
        and not class_has_mark
        and not _has_pytest_mark(function.decorator_list)
    ):
        markerless = 1
        markerless_examples.append(f"{relative}:{function.lineno}")

    return (
        1,
        assertless_total,
        refined_assertless,
        markerless,
        visitor.uuid4_call_sites,
        visitor.date_today_call_sites,
        reachability_scanned,
    )


def _build_assertless_families(
    assertless_candidates: list[dict[str, str]],
) -> dict[str, dict[str, Any]]:
    """Aggregate assertless candidates by file path."""
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
    return assertless_families


def _top_duplicate_test_names(
    duplicate_names: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Top 25 duplicate test names by occurrence count."""
    return [
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


def _branch_reachability_percent(
    *,
    assertion_reachability_scanned_tests: int,
    assertion_bypass_findings: list[dict[str, str]],
) -> tuple[int, float]:
    """Return (unreviewed_bypass_count, branch_reachability_percent)."""
    unreviewed_assertion_bypass_count = sum(
        finding["reviewed"] == "false" for finding in assertion_bypass_findings
    )
    functions_with_bypass = len(
        {
            (finding["path"], finding["test_name"])
            for finding in assertion_bypass_findings
        }
    )
    branch_reachability_percent = round(
        100.0
        * (assertion_reachability_scanned_tests - functions_with_bypass)
        / max(assertion_reachability_scanned_tests, 1),
        3,
    )
    return unreviewed_assertion_bypass_count, branch_reachability_percent


def _assemble_test_governance_payload(
    *,
    root: Path,
    root_str: str,
    test_files: list[Path],
    total_functions: int,
    assertless_total_candidates: int,
    refined_assertless_tests: int,
    assertless_category_counts: Counter[str],
    assertless_candidates: list[dict[str, str]],
    assertless_examples: list[str],
    markerless_test_functions: int,
    markerless_examples: list[str],
    test_name_locations: dict[str, list[str]],
    compatibility_files: list[str],
    uuid4_call_sites: int,
    date_today_call_sites: int,
    critical_behavior_envelopes: dict[str, dict[str, Any]],
    assertion_bypass_findings: list[dict[str, str]],
    assertion_reachability_scanned_tests: int,
    parse_errors: list[dict[str, str]],
) -> dict[str, Any]:
    """Assemble the final test-governance report payload from scan accumulators."""
    duplicate_names = {
        name: locations
        for name, locations in test_name_locations.items()
        if len(locations) > 1
    }
    top_duplicate_names = _top_duplicate_test_names(duplicate_names)
    duplicate_inventory, duplicate_inventory_summary = _build_duplicate_name_inventory(
        duplicate_names
    )
    assertion_gap_count = sum(
        1
        for envelope in critical_behavior_envelopes.values()
        if int(envelope["test_count"]) <= 0
        or int(envelope["assertion_backed_tests"]) <= 0
    )
    assertless_families = _build_assertless_families(assertless_candidates)
    unreviewed_assertion_bypass_count, branch_reachability_percent = (
        _branch_reachability_percent(
            assertion_reachability_scanned_tests=assertion_reachability_scanned_tests,
            assertion_bypass_findings=assertion_bypass_findings,
        )
    )
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
        "unreviewed_assertion_bypass_count": unreviewed_assertion_bypass_count,
        "assertion_branch_reachability_percent": branch_reachability_percent,
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
        "uuid4_call_sites": uuid4_call_sites,
        "date_today_call_sites": date_today_call_sites,
        "critical_behavior_envelope_count": len(critical_behavior_envelopes),
        "critical_behavior_envelope_assertion_gap_count": assertion_gap_count,
        "critical_behavior_envelopes": critical_behavior_envelopes,
        "assertion_branch_reachability": {
            "metric_percent": branch_reachability_percent,
            "scanned_test_count": assertion_reachability_scanned_tests,
            "scan_paths": sorted(ASSERTION_REACHABILITY_PATHS),
            "finding_count": len(assertion_bypass_findings),
            "unreviewed_count": unreviewed_assertion_bypass_count,
            "findings": assertion_bypass_findings,
        },
        "unreviewed_assertion_bypass_count": unreviewed_assertion_bypass_count,
        "assertion_branch_reachability_percent": branch_reachability_percent,
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
    assertion_bypass_allowlist = _load_assertion_bypass_allowlist(root)
    assertion_bypass_findings: list[dict[str, str]] = []
    assertion_reachability_scanned_tests = 0

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
        tree, parse_error = _parse_test_module_source(path, relative=relative)
        if parse_error is not None:
            parse_errors.append(parse_error)
            continue
        if tree is None:
            continue
        module_has_mark = _has_module_pytestmark(tree)
        for function, class_has_mark in _test_functions(tree):
            (
                fn_delta,
                assertless_delta,
                refined_delta,
                markerless_delta,
                uuid4_delta,
                date_today_delta,
                reachability_delta,
            ) = _scan_one_test_function(
                function=function,
                class_has_mark=class_has_mark,
                module_has_mark=module_has_mark,
                relative=relative,
                assertion_bypass_allowlist=assertion_bypass_allowlist,
                critical_behavior_envelopes=critical_behavior_envelopes,
                test_name_locations=test_name_locations,
                assertless_examples=assertless_examples,
                assertless_candidates=assertless_candidates,
                assertless_category_counts=assertless_category_counts,
                assertion_bypass_findings=assertion_bypass_findings,
                markerless_examples=markerless_examples,
            )
            total_functions += fn_delta
            assertless_total_candidates += assertless_delta
            refined_assertless_tests += refined_delta
            markerless_test_functions += markerless_delta
            uuid4_call_sites += uuid4_delta
            date_today_call_sites += date_today_delta
            assertion_reachability_scanned_tests += reachability_delta

    return _assemble_test_governance_payload(
        root=root,
        root_str=root_str,
        test_files=test_files,
        total_functions=total_functions,
        assertless_total_candidates=assertless_total_candidates,
        refined_assertless_tests=refined_assertless_tests,
        assertless_category_counts=assertless_category_counts,
        assertless_candidates=assertless_candidates,
        assertless_examples=assertless_examples,
        markerless_test_functions=markerless_test_functions,
        markerless_examples=markerless_examples,
        test_name_locations=test_name_locations,
        compatibility_files=compatibility_files,
        uuid4_call_sites=uuid4_call_sites,
        date_today_call_sites=date_today_call_sites,
        critical_behavior_envelopes=critical_behavior_envelopes,
        assertion_bypass_findings=assertion_bypass_findings,
        assertion_reachability_scanned_tests=assertion_reachability_scanned_tests,
        parse_errors=parse_errors,
    )


def collect_test_governance_report(root: Path = ROOT) -> dict[str, Any]:
    """Collect deterministic static counts used as remediation budgets."""
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe_root = resolve_output_path(root, root=REPO_ROOT)
    return _collect_test_governance_report_cached(str(safe_root))


def load_config(path: Path) -> dict[str, Any]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe_path = resolve_output_path(path, root=REPO_ROOT)
    with safe_path.open(
        encoding="utf-8"
    ) as handle:  # NOSONAR - path confined by resolve_output_path
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
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe_path = resolve_output_path(path, root=REPO_ROOT)
    expected = _canonical_json(payload)
    if not safe_path.exists():
        print(f"[drift] missing: {safe_path}")
        return False
    actual = safe_path.read_text(encoding="utf-8")  # NOSONAR - path confined
    if actual == expected:
        return True
    print(f"[drift] mismatch: {safe_path}")
    return False


def _resolve_check_default_paths(
    *,
    check: bool,
    safe_root: Path,
    json_out: Path | None,
    fixture_duplication_out: Path | None,
    duplicate_name_inventory_out: Path | None,
) -> tuple[Path | None, Path | None, Path | None]:
    from scripts.engineering.common.repo_paths import resolve_output_path

    if check and json_out is None:
        candidate = safe_root / DEFAULT_JSON_ARTIFACT
        if candidate.exists():
            json_out = candidate
    if check and fixture_duplication_out is None:
        candidate = safe_root / DEFAULT_FIXTURE_DUPLICATION_ARTIFACT
        if candidate.exists():
            fixture_duplication_out = candidate
    if check and duplicate_name_inventory_out is not None:
        duplicate_name_inventory_out = resolve_output_path(
            duplicate_name_inventory_out
            if duplicate_name_inventory_out.is_absolute()
            else safe_root / duplicate_name_inventory_out,
            root=safe_root,
        )
    return json_out, fixture_duplication_out, duplicate_name_inventory_out


def _write_json_payload(path: Path, payload: dict[str, Any] | str) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe_path = resolve_output_path(path, root=REPO_ROOT)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    text = payload if isinstance(payload, str) else _canonical_json(payload)
    safe_path.write_text(  # NOSONAR - path confined by resolve_output_path
        text, encoding="utf-8"
    )


def _run_check_mode(
    *,
    json_out: Path | None,
    fixture_duplication_out: Path | None,
    duplicate_name_inventory_out: Path | None,
    payload: dict[str, Any],
    fixture_duplication_payload: dict[str, Any],
    duplicate_name_inventory_payload: dict[str, Any],
) -> int:
    exit_code = 0
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
    return exit_code


def _run_write_mode(
    *,
    json_out: Path | None,
    fixture_duplication_out: Path | None,
    duplicate_name_inventory_out: Path | None,
    output: str,
    fixture_duplication_payload: dict[str, Any],
    duplicate_name_inventory_payload: dict[str, Any],
) -> None:
    if json_out:
        _write_json_payload(json_out, output)
    else:
        print(output)
    if fixture_duplication_out:
        _write_json_payload(fixture_duplication_out, fixture_duplication_payload)
    if duplicate_name_inventory_out:
        _write_json_payload(
            duplicate_name_inventory_out, duplicate_name_inventory_payload
        )


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

    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    safe_root = resolve_output_path(args.root, root=REPO_ROOT)
    safe_config = resolve_output_path(args.config, root=REPO_ROOT)
    payload = collect_test_governance_report(safe_root)
    json_out, fixture_duplication_out, duplicate_name_inventory_out = (
        _resolve_check_default_paths(
            check=args.check,
            safe_root=safe_root,
            json_out=args.json_out,
            fixture_duplication_out=args.fixture_duplication_out,
            duplicate_name_inventory_out=args.duplicate_name_inventory_out,
        )
    )
    exit_code = 0

    if safe_config.exists():
        config = load_config(safe_config)
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
        check_code = _run_check_mode(
            json_out=json_out,
            fixture_duplication_out=fixture_duplication_out,
            duplicate_name_inventory_out=duplicate_name_inventory_out,
            payload=payload,
            fixture_duplication_payload=fixture_duplication_payload,
            duplicate_name_inventory_payload=duplicate_name_inventory_payload,
        )
        return max(exit_code, check_code)

    _run_write_mode(
        json_out=json_out,
        fixture_duplication_out=fixture_duplication_out,
        duplicate_name_inventory_out=duplicate_name_inventory_out,
        output=output,
        fixture_duplication_payload=fixture_duplication_payload,
        duplicate_name_inventory_payload=duplicate_name_inventory_payload,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
