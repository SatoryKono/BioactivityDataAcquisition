"""Regression control metrics for architecture quality.

Each test function enforces a specific quality metric with a ratchet budget.
When the codebase improves, lower the budget to prevent regression.

Implements §5 of the quality scorecard plan.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

DEBT_SCORECARD_YAML = Path("configs/quality/debt_scorecard.yaml")
EXEMPTIONS_YAML = Path("configs/quality/architecture_metric_exemptions.yaml")


def _load_debt_scorecard() -> dict[str, Any]:
    """Load debt scorecard config as mapping for coarse-budget synchronization."""
    if not DEBT_SCORECARD_YAML.exists():
        pytest.skip("Debt scorecard YAML not found")

    with open(DEBT_SCORECARD_YAML, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        pytest.fail("Debt scorecard YAML must be a mapping")
    return raw


def _enforceable_baseline(scorecard: dict[str, Any]) -> dict[str, Any]:
    """Resolve the live enforceable baseline section from scorecard governance."""
    governance = scorecard.get("governance", {})
    section_name = "baseline"
    if isinstance(governance, dict):
        baseline_policy = governance.get("baseline_policy", {})
        if isinstance(baseline_policy, dict):
            configured = baseline_policy.get("enforceable_section")
            if isinstance(configured, str) and configured.strip():
                section_name = configured.strip()

    baseline = scorecard.get(section_name, {})
    if not isinstance(baseline, dict):
        pytest.fail(f"scorecard.{section_name} must be a mapping")
    return baseline


def _resolve_coarse_budget(metric_name: str) -> int:
    """Resolve explicit coarse budget from debt scorecard governance."""
    scorecard = _load_debt_scorecard()
    governance = scorecard.get("governance", {})
    if not isinstance(governance, dict):
        pytest.fail("scorecard.governance must be a mapping")

    coarse = governance.get("coarse_budgets", {})
    if not isinstance(coarse, dict):
        pytest.fail("scorecard.governance.coarse_budgets must be a mapping")

    metric = coarse.get(metric_name)
    if not isinstance(metric, dict):
        pytest.fail(f"scorecard.governance.coarse_budgets.{metric_name} missing")

    max_count = metric.get("max_count")
    if not isinstance(max_count, int):
        pytest.fail(
            "scorecard.governance.coarse_budgets."
            f"{metric_name}.max_count must be an int"
        )
    return max_count


def _resolve_registry_budget(registry_name: str) -> int:
    """Resolve enforceable registry budget from debt scorecard baseline."""
    scorecard = _load_debt_scorecard()
    baseline = _enforceable_baseline(scorecard)
    by_registry = baseline.get("by_registry", {})
    if not isinstance(by_registry, dict):
        pytest.fail("scorecard baseline.by_registry must be a mapping")

    value = by_registry.get(registry_name)
    if not isinstance(value, int):
        pytest.fail(f"scorecard baseline.by_registry.{registry_name} must be an int")
    return value


def _resolve_total_exemptions_budget() -> int:
    """Resolve enforceable total exemption budget from debt scorecard baseline."""
    scorecard = _load_debt_scorecard()
    baseline = _enforceable_baseline(scorecard)
    total = baseline.get("total_exemptions")
    if not isinstance(total, int):
        pytest.fail("scorecard baseline.total_exemptions must be an int")
    return total


# ---------------------------------------------------------------------------
# Metric 1: workflow_yaml_invalid_count (target: 0)
# ---------------------------------------------------------------------------

WORKFLOWS_DIR = Path(".github/workflows")


def test_workflow_yaml_validity() -> None:
    """All GitHub Actions workflow YAML files must be valid YAML."""
    if not WORKFLOWS_DIR.exists():
        pytest.skip("No .github/workflows directory")

    violations: list[str] = []
    for yml_file in sorted(WORKFLOWS_DIR.glob("*.yml")):
        try:
            with open(yml_file, encoding="utf-8") as f:
                yaml.safe_load(f)
        except yaml.YAMLError as exc:
            violations.append(f"{yml_file.name}: {exc}")

    assert not violations, (
        f"workflow_yaml_invalid_count={len(violations)} (target: 0)\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


# ---------------------------------------------------------------------------
# Metric 2: ruff_error_count (target: 0) + mypy_error_count (target: 0)
# ---------------------------------------------------------------------------


def _resolve_quality_tool_command(module_name: str) -> list[str] | None:
    """Resolve a deterministic command for running a Python quality tool.

    Prefer the current interpreter when the tool is installed in the active
    environment so the ratchet does not silently skip on hosts without ``uv``.
    Fall back to ``uv run`` only when the module is not importable directly.
    """
    if importlib.util.find_spec(module_name) is not None:
        return [sys.executable, "-m", module_name]
    if shutil.which("uv") is not None:
        return ["uv", "run", module_name]
    return None


def _resolve_mypy_command() -> list[str] | None:
    """Resolve the canonical mypy runner for the current host OS.

    The repository ships shell/PowerShell wrappers that choose the correct
    virtualenv for mixed Windows/WSL checkouts and pin cache directories away
    from host-level read-only locations. Falling back to ad-hoc ``uv run`` can
    fail before mypy starts, which would otherwise appear as a false-green
    ``0``-error run in the ratchet.
    """
    repo_root = Path(__file__).resolve().parents[2]
    dev_root = repo_root / "scripts" / "engineering" / "dev"

    if os.name == "nt":
        powershell_wrapper = dev_root / "run_mypy.ps1"
        if powershell_wrapper.exists():
            return [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(powershell_wrapper),
            ]

    shell_wrapper = dev_root / "run_mypy.sh"
    if shell_wrapper.exists():
        return ["bash", str(shell_wrapper)]

    return _resolve_quality_tool_command("mypy")


def _tool_error_preview(errors: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"  - {e.get('filename', '?')}:{e.get('location', {}).get('row', '?')}: "
        f"{e.get('code', '?')} {e.get('message', '')}"
        for e in errors[:20]
    )


def _mypy_error_lines(stdout: str) -> list[str]:
    return [line for line in stdout.splitlines() if ": error:" in line]


def test_ruff_error_count(
    cached_subprocess_run: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    """Ruff linter error count must not exceed the ratchet budget."""
    max_ruff_errors = _resolve_coarse_budget("ruff_error_count")
    tool_cmd = _resolve_quality_tool_command("ruff")
    if tool_cmd is None:
        pytest.skip("ruff executable/runtime not found")

    result = cached_subprocess_run(
        [*tool_cmd, "check", "src/bioetl/", "--output-format=json"],
        timeout=120,
    )

    if result.returncode == 0:
        return  # no errors

    try:
        errors = json.loads(result.stdout)
    except json.JSONDecodeError:
        errors = []

    error_count = len(errors)
    assert error_count <= max_ruff_errors, (
        f"ruff_error_count={error_count} exceeds budget {max_ruff_errors}\n"
        + _tool_error_preview(errors)
    )


@pytest.mark.slow
@pytest.mark.timeout(300)
def test_mypy_error_count(
    cached_subprocess_run: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    """mypy --strict error count must not exceed the ratchet budget.

    Marked as 'slow' because mypy subprocess takes ~160s.
    Run explicitly with: pytest -m slow
    No-ops by default outside the dedicated type-checking workflow.
    """
    if os.getenv("BIOETL_ENFORCE_GLOBAL_MYPY_RATCHET") != "1":
        return

    max_mypy_errors = _resolve_coarse_budget("mypy_error_count")
    tool_cmd = _resolve_mypy_command()
    if tool_cmd is None:
        pytest.fail("mypy executable/runtime not found")

    result = cached_subprocess_run(
        [
            *tool_cmd,
            "--config-file",
            "pyproject.toml",
            "--strict",
            "--no-incremental",
            "src/bioetl/",
            "--no-error-summary",
        ],
        timeout=300,
    )

    error_lines = _mypy_error_lines(result.stdout)
    if result.returncode != 0 and not error_lines:
        preview = "\n".join(
            part for part in (result.stdout.strip(), result.stderr.strip()) if part
        )
        pytest.fail(
            "mypy invocation failed before reporting type-check results.\n"
            f"command={' '.join(tool_cmd)}\n"
            f"output:\n{preview or '<no output>'}"
        )
    error_count = len(error_lines)
    assert error_count <= max_mypy_errors, (
        f"mypy_error_count={error_count} exceeds budget {max_mypy_errors}\n"
        + "\n".join(f"  - {line}" for line in error_lines[:20])
    )


# ---------------------------------------------------------------------------
# Metric 3: architecture_skip_count (ratchet)
# ---------------------------------------------------------------------------


def _count_skip_markers(items: list[pytest.Item]) -> int:
    """Count collect-time skip/skipif markers for already collected items."""
    skipped = 0
    for item in items:
        for marker in item.iter_markers():
            if marker.name in ("skip", "skipif"):
                skipped += 1
                break
    return skipped


def _architecture_skip_cache_key(project_root: Path) -> str:
    """Build a stable cache key for static architecture skip inventory."""
    digest = hashlib.blake2b(digest_size=16)
    digest.update(sys.version.encode("utf-8"))
    digest.update(sys.platform.encode("utf-8"))

    tracked_paths: list[Path] = [
        project_root / "tests" / "conftest.py",
        project_root / "tests" / "architecture" / "conftest.py",
        project_root / "pyproject.toml",
    ]
    tracked_paths.extend(
        sorted((project_root / "tests" / "architecture").glob("test_*.py"))
    )

    for path in tracked_paths:
        if not path.exists():
            continue
        stat = path.stat()
        digest.update(path.relative_to(project_root).as_posix().encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))

    return f"bioetl/architecture_skip_count/{digest.hexdigest()}"


def _architecture_session_items(request: pytest.FixtureRequest) -> list[pytest.Item]:
    return [
        item
        for item in request.session.items
        if item.nodeid.replace("\\", "/").startswith("tests/architecture/")
    ]


def _cached_architecture_skip_count(
    request: pytest.FixtureRequest,
    cache_key: str,
) -> int | None:
    cached_skipped = request.config.cache.get(cache_key, None)
    return cached_skipped if isinstance(cached_skipped, int) else None


def _has_skip_marker(decorators: list[ast.expr]) -> bool:
    """Return whether a decorator list contains pytest skip/skipif markers."""
    for decorator in decorators:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if not isinstance(target, ast.Attribute):
            continue
        if target.attr not in {"skip", "skipif"}:
            continue
        value = target.value
        if isinstance(value, ast.Attribute) and value.attr == "mark":
            return True
    return False


def _count_skip_markers_in_tree(tree: ast.Module) -> int:
    """Count architecture test items carrying explicit skip/skipif markers."""
    skipped = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_") and _has_skip_marker(node.decorator_list):
                skipped += 1
            continue

        if not isinstance(node, ast.ClassDef):
            continue

        class_has_skip = _has_skip_marker(node.decorator_list)
        for child in node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not child.name.startswith("test_"):
                continue
            if class_has_skip or _has_skip_marker(child.decorator_list):
                skipped += 1

    return skipped


def _collect_architecture_skip_count(project_root: Path) -> int:
    """Count explicit architecture skip markers from source without nested pytest."""
    skipped = 0
    for path in sorted((project_root / "tests" / "architecture").glob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            pytest.fail(
                "Failed to parse architecture test while counting skip markers: "
                f"{path.relative_to(project_root)}:{exc.lineno}"
            )
        skipped += _count_skip_markers_in_tree(tree)
    return skipped


def _architecture_skip_count() -> int:
    return _collect_architecture_skip_count(Path.cwd())


@pytest.mark.timeout(240)
def test_architecture_skip_count() -> None:
    """Architecture test skip count must not exceed the ratchet budget.

    Uses a static AST inventory so the ratchet stays deterministic across
    narrow vs broad invocations and across host-specific marker injection.
    """
    max_architecture_skips = _resolve_coarse_budget("architecture_skip_count")
    skipped = _architecture_skip_count()

    assert skipped <= max_architecture_skips, (
        f"architecture_skip_count={skipped} exceeds budget {max_architecture_skips}"
    )


# ---------------------------------------------------------------------------
# Metric 4: inline_adapter_construction_count (target: 0)
# ---------------------------------------------------------------------------

# Adapter classes that must only be instantiated in composition/
FORBIDDEN_ADAPTER_CLASSES = frozenset(
    {
        "ChemblAdapter",
        "PubChemAdapter",
        "UniProtAdapter",
        "PubMedAdapter",
        "CrossRefAdapter",
        "OpenAlexAdapter",
        "SemanticScholarAdapter",
        "UniProtIDMappingClient",
    }
)

# Layers where direct adapter instantiation is forbidden
# infrastructure excluded: adapters contain @classmethod factories for self-construction
_FORBIDDEN_LAYERS = ("domain", "application", "interfaces")


def _file_in_forbidden_layer(src_dir: Path, py_file: Path) -> bool:
    bioetl = src_dir / "bioetl"
    return any((bioetl / layer) in py_file.parents for layer in _FORBIDDEN_LAYERS)


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _adapter_instantiations_in_tree(
    src_dir: Path,
    py_file: Path,
    tree: ast.AST,
) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in FORBIDDEN_ADAPTER_CLASSES:
            rel = py_file.relative_to(src_dir)
            violations.append(f"{rel}:{node.lineno}: {name}()")
    return violations


def _cached_adapter_instantiations(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
) -> list[str]:
    """Collect adapter instantiations from a prebuilt AST cache."""
    violations: list[str] = []
    for py_file, tree in source_ast_cache.items():
        if py_file.name.startswith("__") or not _file_in_forbidden_layer(
            src_dir, py_file
        ):
            continue
        violations.extend(_adapter_instantiations_in_tree(src_dir, py_file, tree))
    return violations


def _parsed_tree(path: Path) -> ast.AST | None:
    """Parse a Python file into AST, tolerating syntax errors."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def _filesystem_adapter_instantiations(src_dir: Path) -> list[str]:
    """Collect adapter instantiations by parsing forbidden layers on disk."""
    violations: list[str] = []
    for layer in _FORBIDDEN_LAYERS:
        layer_path = src_dir / "bioetl" / layer
        if not layer_path.exists():
            continue
        for py_file in sorted(layer_path.rglob("*.py")):
            if py_file.name.startswith("__"):
                continue
            tree = _parsed_tree(py_file)
            if tree is None:
                continue
            violations.extend(_adapter_instantiations_in_tree(src_dir, py_file, tree))
    return violations


def _find_adapter_instantiations(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module] | None = None,
) -> list[str]:
    """Find direct adapter class instantiations outside composition/."""
    if source_ast_cache is not None:
        return _cached_adapter_instantiations(src_dir, source_ast_cache)
    return _filesystem_adapter_instantiations(src_dir)


def test_inline_adapter_construction_budget(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Adapter classes must only be instantiated in composition layer."""
    violations = _find_adapter_instantiations(src_dir, source_ast_cache)
    assert not violations, (
        f"inline_adapter_construction_count={len(violations)} (target: 0)\n"
        "Adapter instantiation outside composition/ detected:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


# ---------------------------------------------------------------------------
# Metric 5: exemptions_total (baseline from debt scorecard, ratchet)
# ---------------------------------------------------------------------------


def test_exemptions_total_budget() -> None:
    """Total exemption count must not exceed the ratchet budget."""
    max_exemptions_total = _resolve_total_exemptions_budget()
    if not EXEMPTIONS_YAML.exists():
        pytest.skip("Exemptions YAML not found")

    with open(EXEMPTIONS_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    registries = data.get("registries", {})
    per_registry: dict[str, int] = {}
    total = 0
    for reg_name, entries in registries.items():
        count = len(entries) if isinstance(entries, dict) else 0
        per_registry[reg_name] = count
        total += count

    breakdown = ", ".join(f"{k}={v}" for k, v in sorted(per_registry.items()))
    assert total <= max_exemptions_total, (
        f"exemptions_total={total} exceeds budget {max_exemptions_total}\n"
        f"Breakdown: {breakdown}"
    )


# ---------------------------------------------------------------------------
# Metric 6: files_over_loc_threshold + class_size_exemption_count
# ---------------------------------------------------------------------------


def _count_registry_entries(registry_name: str) -> int:
    """Count entries in a specific exemption registry."""
    if not EXEMPTIONS_YAML.exists():
        return 0
    with open(EXEMPTIONS_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    entries = data.get("registries", {}).get(registry_name, {})
    return len(entries) if isinstance(entries, dict) else 0


def test_file_size_exemption_count() -> None:
    """File size exemption count must not exceed ratchet budget."""
    max_file_size_exemptions = _resolve_registry_budget("file_size_limits")
    count = _count_registry_entries("file_size_limits")
    assert count <= max_file_size_exemptions, (
        f"files_over_loc_threshold={count} exceeds budget {max_file_size_exemptions}"
    )


def test_class_size_exemption_count() -> None:
    """Class size exemption count must not exceed ratchet budget."""
    max_class_size_exemptions = _resolve_registry_budget("class_size")
    count = _count_registry_entries("class_size")
    assert count <= max_class_size_exemptions, (
        f"class_size_exemption_count={count} exceeds budget {max_class_size_exemptions}"
    )


# ---------------------------------------------------------------------------
# Metric 7: e2e_skip_rate + recurrent_flaky_count (structural checks)
# ---------------------------------------------------------------------------


def test_e2e_scripts_exist() -> None:
    """E2E health-check scripts must exist."""
    skip_rate = Path("scripts/engineering/ci/check_e2e_matrix_skip_rate.py")
    rerun = Path("scripts/engineering/ci/check_e2e_rerun_stability.py")

    missing = []
    if not skip_rate.exists():
        missing.append(str(skip_rate))
    if not rerun.exists():
        missing.append(str(rerun))

    assert not missing, f"Missing E2E scripts: {', '.join(missing)}"


def test_e2e_workflow_slo_configured() -> None:
    """E2E matrix health workflow must enforce skip-rate and stability SLOs."""
    workflow = Path(".github/workflows/e2e-matrix-health.yml")
    if not workflow.exists():
        pytest.skip("E2E workflow not found")

    content = workflow.read_text(encoding="utf-8")

    assert "--max-skip-rate" in content, "Workflow must enforce max-skip-rate SLO"
    assert "--max-recurrent-code-regression 0" in content, (
        "Workflow must enforce zero recurrent code regressions"
    )
    assert "check_e2e_matrix_skip_rate.py" in content
    assert "check_e2e_rerun_stability.py" in content


# ---------------------------------------------------------------------------
# Metric 8: probe_mode_fallback_rate (structural check)
# ---------------------------------------------------------------------------


def test_probe_mode_fallback_counter_exists() -> None:
    """PROBE_MODE_FALLBACK_TOTAL counter must be defined and observer-owned."""
    metrics_defs = Path(
        "src/bioetl/infrastructure/observability/metrics_definitions.py"
    )
    observer = Path("src/bioetl/application/observability/observer.py")

    assert metrics_defs.exists(), "metrics_definitions.py not found"
    assert observer.exists(), "observer.py not found"

    defs_content = metrics_defs.read_text(encoding="utf-8")
    assert "PROBE_MODE_FALLBACK_TOTAL" in defs_content, (
        "PROBE_MODE_FALLBACK_TOTAL counter not defined in metrics_definitions.py"
    )

    observer_content = observer.read_text(encoding="utf-8")
    assert "bioetl_probe_mode_fallback_total" in observer_content, (
        "bioetl_probe_mode_fallback_total not instrumented in observer-owned path"
    )


# ---------------------------------------------------------------------------
# Metric 9: dependency_map_violations (target: 0)
# ---------------------------------------------------------------------------

GROUP_EDGE_LIMIT = 60
GROUP_EDGE_TOTAL_BUDGET = 343  # current generated dependency-map baseline

_dep_map_module = None
_dep_map_snapshot = None


def _load_dep_map_module() -> Any | None:
    """Load dependency map generator script as a module (cached)."""
    global _dep_map_module
    if _dep_map_module is not None:
        return _dep_map_module

    import sys

    script_path = Path("scripts/engineering/qa/generate_architecture_dependency_map.py")
    if not script_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        "dep_map_gen", str(script_path.resolve())
    )
    if spec is None or spec.loader is None:
        return None

    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules so @dataclass can resolve the module
    sys.modules["dep_map_gen"] = mod
    spec.loader.exec_module(mod)
    _dep_map_module = mod
    return mod


def _load_dep_map_snapshot() -> Any:
    """Load dependency snapshot once per test session."""
    global _dep_map_snapshot
    if _dep_map_snapshot is not None:
        return _dep_map_snapshot

    mod = _load_dep_map_module()
    if mod is None:
        pytest.skip("Dependency map script not found")

    src_root = Path("src/bioetl")
    if not src_root.exists():
        pytest.skip("src/bioetl not found")

    _dep_map_snapshot = mod.collect_dependency_snapshot(src_root)
    return _dep_map_snapshot


def test_dependency_map_violations_zero() -> None:
    """Dependency map must have zero import-matrix violations."""
    snapshot = _load_dep_map_snapshot()

    assert len(snapshot.violations) == 0, (
        f"dependency_map_violations={len(snapshot.violations)} (target: 0)\n"
        + "\n".join(
            f"  - {v.source} -> {v.target} ({v.imports} imports)"
            for v in snapshot.violations
        )
    )


def test_cross_layer_group_edges_budget() -> None:
    """Cross-layer group edges must not exceed the budget."""
    snapshot = _load_dep_map_snapshot()
    edge_count = len(snapshot.cross_layer_group_edges)

    assert edge_count <= GROUP_EDGE_LIMIT, (
        f"cross_layer_group_edges={edge_count} exceeds budget {GROUP_EDGE_LIMIT}"
    )


def test_cross_layer_group_edges_total_budget() -> None:
    """Total cross-layer group edges (full graph) must not exceed the budget."""
    snapshot = _load_dep_map_snapshot()
    total = snapshot.cross_layer_group_edges_total

    assert total <= GROUP_EDGE_TOTAL_BUDGET, (
        f"cross_layer_group_edges_total={total} exceeds budget "
        f"{GROUP_EDGE_TOTAL_BUDGET}"
    )


# ---------------------------------------------------------------------------
# Metric 10: p95_silver_merge_duration + atomic_retry_exhausted_rate
# ---------------------------------------------------------------------------


def test_silver_merge_resilience_instrumented() -> None:
    """Silver merge resilience must have retry policy and observability hooks."""
    resilience = Path("src/bioetl/infrastructure/storage/delta/resilience.py")
    delta_mixin = Path("src/bioetl/infrastructure/storage/silver/delta_mixin.py")
    delta_helpers = Path("src/bioetl/infrastructure/storage/silver/delta_helpers.py")
    merge_resilience_helpers = Path(
        "src/bioetl/infrastructure/storage/silver/merge_resilience_helpers.py"
    )

    assert resilience.exists(), "delta/resilience.py not found"
    assert delta_mixin.exists(), "silver/delta_mixin.py not found"
    assert delta_helpers.exists(), "silver/delta_helpers.py not found"
    assert merge_resilience_helpers.exists(), (
        "silver/merge_resilience_helpers.py not found"
    )

    res_content = resilience.read_text(encoding="utf-8")
    assert "SilverMergeResiliencePolicy" in res_content, (
        "SilverMergeResiliencePolicy not defined in delta/resilience.py"
    )
    assert "max_retries" in res_content, (
        "Retry configuration missing in SilverMergeResiliencePolicy"
    )

    delta_content = (
        delta_mixin.read_text(encoding="utf-8")
        + "\n"
        + delta_helpers.read_text(encoding="utf-8")
        + "\n"
        + merge_resilience_helpers.read_text(encoding="utf-8")
    )
    assert "silver_merge_retry" in delta_content, (
        "silver_merge_retry observability event missing in delta write path"
    )
    assert "silver_merge_timeout" in delta_content, (
        "silver_merge_timeout observability event missing in delta write path"
    )


def test_retry_exhausted_counter_exists() -> None:
    """data_source_retry_exhausted_total counter must be defined."""
    metrics_defs = Path(
        "src/bioetl/infrastructure/observability/metrics_definitions.py"
    )
    assert metrics_defs.exists(), "metrics_definitions.py not found"

    content = metrics_defs.read_text(encoding="utf-8")
    assert "retry_exhausted" in content, (
        "retry_exhausted counter not defined in metrics_definitions.py"
    )


# ---------------------------------------------------------------------------
# Metric 11: architecture_test_p95_duration (structural check)
# ---------------------------------------------------------------------------

ARCH_TEST_P95_BUDGET_SECONDS = 30.0  # ratchet: p95 per-test duration


def _read_required_file(path: Path, *, missing_message: str) -> str:
    assert path.exists(), missing_message
    return path.read_text(encoding="utf-8")


def _assert_architecture_workflow_shape(content: str) -> None:
    assert "architecture-fast-baseline" in content, (
        "Workflow must have architecture-fast-baseline job for fast profile"
    )
    assert "architecture-heavy-nightly" in content, (
        "Workflow must have architecture-heavy-nightly job for full profile"
    )
    assert "workflow_dispatch" in content, (
        "Architecture workflow must allow manual fast profile execution"
    )
    assert "schedule:" in content, (
        "Architecture workflow must keep scheduled heavy profile execution"
    )
    assert "pull_request:" not in content and "push:" not in content, (
        "Fast architecture pytest on PR/push should live only in tests.yml to avoid duplication"
    )
    assert "make qa-arch-fast" in content, (
        "Fast baseline must delegate to the canonical qa-arch-fast target"
    )


def _assert_makefile_architecture_target(content: str) -> None:
    assert "qa-arch-fast:" in content, (
        "Makefile must keep the qa-arch-fast target for architecture CI"
    )
    assert (
        'tests/architecture/ -m "not slow and not serial and not memory"' in content
    ), (
        "qa-arch-fast must exclude @pytest.mark.slow, @pytest.mark.serial, and memory tests"
    )


def test_architecture_test_p95_duration_tracked() -> None:
    """Architecture workflow must keep manual fast + scheduled heavy split."""
    workflow = Path(".github/workflows/architecture.yml")
    if not workflow.exists():
        pytest.skip("Architecture workflow not found")

    workflow_content = workflow.read_text(encoding="utf-8")
    makefile_content = _read_required_file(
        Path("Makefile"),
        missing_message="Makefile must define the canonical qa-arch-fast target",
    )
    _assert_architecture_workflow_shape(workflow_content)
    _assert_makefile_architecture_target(makefile_content)


# ---------------------------------------------------------------------------
# Metric 12: scorecard_registry_sync (governance debt automation)
# ---------------------------------------------------------------------------


def _load_exemptions_registries() -> dict[str, Any]:
    if not EXEMPTIONS_YAML.exists():
        pytest.skip("Exemptions YAML not found")
    with open(EXEMPTIONS_YAML, encoding="utf-8") as f:
        exemptions = yaml.safe_load(f) or {}
    registries = exemptions.get("registries", {})
    if not isinstance(registries, dict):
        pytest.fail("exemptions.registries must be a mapping")
    return registries


def _scorecard_baseline_section(
    scorecard: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    governance = scorecard.get("governance", {})
    section_name = "baseline"
    if isinstance(governance, dict):
        baseline_policy = governance.get("baseline_policy", {})
        if isinstance(baseline_policy, dict):
            sync_source = baseline_policy.get("registry_sync_source")
            assert sync_source == "baseline", (
                "Registry sync must be anchored to the enforceable baseline "
                "section, not to historical_baseline"
            )
            if isinstance(sync_source, str) and sync_source.strip():
                section_name = sync_source

    baseline = scorecard.get(section_name, {})
    if not isinstance(baseline, dict):
        pytest.fail(f"scorecard.{section_name} must be a mapping")
    return section_name, baseline


def _registry_counts(registries: dict[str, Any]) -> tuple[dict[str, int], int]:
    actual_by_registry: dict[str, int] = {}
    actual_total = 0
    for reg_name, entries in registries.items():
        count = len(entries) if isinstance(entries, dict) else 0
        actual_by_registry[reg_name] = count
        actual_total += count
    return actual_by_registry, actual_total


def _scorecard_registry_mismatches(
    actual_by_registry: dict[str, int],
    actual_total: int,
    expected_by_registry: dict[str, Any],
    expected_total: int,
) -> list[str]:
    mismatches: list[str] = []
    if actual_total != expected_total:
        mismatches.append(
            f"total_exemptions: scorecard={expected_total}, actual={actual_total}"
        )
    for reg_name, actual_count in sorted(actual_by_registry.items()):
        expected_count = expected_by_registry.get(reg_name, 0)
        if actual_count != expected_count:
            mismatches.append(
                f"{reg_name}: scorecard={expected_count}, actual={actual_count}"
            )
    return mismatches


def test_scorecard_baseline_matches_registry() -> None:
    """Scorecard baseline must match actual exemption registry counts."""
    scorecard = _load_debt_scorecard()
    registries = _load_exemptions_registries()
    actual_by_registry, actual_total = _registry_counts(registries)
    baseline_section_name, baseline = _scorecard_baseline_section(scorecard)
    expected_total = baseline.get("total_exemptions", 0)
    expected_by_registry = baseline.get("by_registry", {})
    mismatches = _scorecard_registry_mismatches(
        actual_by_registry=actual_by_registry,
        actual_total=actual_total,
        expected_by_registry=expected_by_registry,
        expected_total=expected_total,
    )

    assert not mismatches, (
        "Scorecard baseline drifted from actual exemption registry:\n"
        + "\n".join(f"  - {m}" for m in mismatches)
        + f"\nUpdate configs/quality/debt_scorecard.yaml {baseline_section_name} section."
    )


def test_scorecard_hotspot_budgets_cover_priority_registries() -> None:
    """Hotspot budgets must cover the registries declared in burn-down priorities."""
    scorecard = _load_debt_scorecard()
    governance = scorecard.get("governance", {})
    assert isinstance(governance, dict)
    burn_down = governance.get("burn_down_priorities", {})
    assert isinstance(burn_down, dict)
    priority_registries = burn_down.get("registries", [])
    assert isinstance(priority_registries, list)

    hotspot_budgets = scorecard.get("hotspot_budgets", [])
    assert isinstance(hotspot_budgets, list) and hotspot_budgets, (
        "Debt scorecard must declare non-empty hotspot_budgets"
    )

    covered_registries = {
        registry_name
        for entry in hotspot_budgets
        if isinstance(entry, dict)
        for registry_name in entry.get("registry_budgets", {})
        if isinstance(registry_name, str)
    }
    missing = sorted(
        registry_name
        for registry_name in priority_registries
        if isinstance(registry_name, str) and registry_name not in covered_registries
    )
    assert not missing, (
        "hotspot_budgets must cover burn_down_priorities registries: "
        + ", ".join(missing)
    )
