"""Regression control metrics for architecture quality.

Each test function enforces a specific quality metric with a ratchet budget.
When the codebase improves, lower the budget to prevent regression.

Implements §5 of the quality scorecard plan.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest
import yaml

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


MAX_RUFF_ERRORS = 8  # ratchet: reduce to 0


def test_ruff_error_count() -> None:
    """Ruff linter error count must not exceed the ratchet budget."""
    try:
        result = subprocess.run(
            ["uv", "run", "ruff", "check", "src/bioetl/", "--output-format=json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        pytest.skip("uv or ruff not found")

    if result.returncode == 0:
        return  # no errors

    try:
        errors = json.loads(result.stdout)
    except json.JSONDecodeError:
        errors = []

    error_count = len(errors)
    assert error_count <= MAX_RUFF_ERRORS, (
        f"ruff_error_count={error_count} exceeds budget {MAX_RUFF_ERRORS}\n"
        + "\n".join(
            f"  - {e.get('filename', '?')}:{e.get('location', {}).get('row', '?')}: "
            f"{e.get('code', '?')} {e.get('message', '')}"
            for e in errors[:20]
        )
    )


MAX_MYPY_ERRORS = 152  # ratchet: reduce toward 0


@pytest.mark.slow
@pytest.mark.timeout(300)
def test_mypy_error_count() -> None:
    """mypy --strict error count must not exceed the ratchet budget.

    Marked as 'slow' because mypy subprocess takes ~160s.
    Run explicitly with: pytest -m slow
    Skipped by default in addopts (``-m 'not benchmark and not slow'``).
    """
    try:
        result = subprocess.run(
            [
                "uv",
                "run",
                "mypy",
                "--strict",
                "src/bioetl/",
                "--no-error-summary",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except FileNotFoundError:
        pytest.skip("uv or mypy not found")

    error_lines = [line for line in result.stdout.splitlines() if ": error:" in line]
    error_count = len(error_lines)
    assert error_count <= MAX_MYPY_ERRORS, (
        f"mypy_error_count={error_count} exceeds budget {MAX_MYPY_ERRORS}\n"
        + "\n".join(f"  - {line}" for line in error_lines[:20])
    )


# ---------------------------------------------------------------------------
# Metric 3: architecture_skip_count (target: ≤24, ratchet)
# ---------------------------------------------------------------------------

MAX_ARCHITECTURE_SKIPS = 24


class _SkipMarkerCounter:
    """Lightweight pytest plugin that counts skip markers during collection."""

    def __init__(self) -> None:
        self.skipped = 0
        self.total = 0

    def pytest_collection_modifyitems(self, items: list) -> None:
        """Count items with skip/skipif markers (without running tests)."""
        self.total = len(items)
        for item in items:
            for marker in item.iter_markers():
                if marker.name in ("skip", "skipif"):
                    self.skipped += 1
                    break


@pytest.mark.timeout(120)
def test_architecture_skip_count() -> None:
    """Architecture test skip count must not exceed the ratchet budget.

    Uses collect-only mode to count skip markers without re-running all
    architecture tests.  Only counts marker-based skips (@pytest.mark.skip,
    @pytest.mark.skipif), not runtime pytest.skip() calls.
    """
    counter = _SkipMarkerCounter()
    # Collect (but don't run) architecture tests to count skip markers.
    pytest.main(
        [
            "tests/architecture/",
            "--collect-only",
            "-q",
            "--ignore=tests/architecture/test_regression_metrics.py",
            "-p",
            "no:timeout",
            "-p",
            "no:xdist",
            "--no-header",
            "--override-ini=addopts=",
        ],
        plugins=[counter],
    )

    assert counter.skipped <= MAX_ARCHITECTURE_SKIPS, (
        f"architecture_skip_count={counter.skipped} exceeds budget {MAX_ARCHITECTURE_SKIPS}"
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


def _find_adapter_instantiations(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module] | None = None,
) -> list[str]:
    """Find direct adapter class instantiations outside composition/."""
    violations: list[str] = []
    bioetl = src_dir / "bioetl"

    if source_ast_cache is not None:
        for py_file, tree in source_ast_cache.items():
            if py_file.name.startswith("__"):
                continue
            # Check if file is in one of the forbidden layers
            layer_match = False
            for layer in _FORBIDDEN_LAYERS:
                if (bioetl / layer) in py_file.parents:
                    layer_match = True
                    break
            if not layer_match:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = None
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in FORBIDDEN_ADAPTER_CLASSES:
                    rel = py_file.relative_to(src_dir)
                    violations.append(f"{rel}:{node.lineno}: {name}()")
    else:
        for layer in _FORBIDDEN_LAYERS:
            layer_path = bioetl / layer
            if not layer_path.exists():
                continue
            for py_file in sorted(layer_path.rglob("*.py")):
                if py_file.name.startswith("__"):
                    continue
                source = py_file.read_text(encoding="utf-8")
                try:
                    tree = ast.parse(source)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    name = None
                    if isinstance(node.func, ast.Name):
                        name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        name = node.func.attr
                    if name in FORBIDDEN_ADAPTER_CLASSES:
                        rel = py_file.relative_to(src_dir)
                        violations.append(f"{rel}:{node.lineno}: {name}()")
    return violations


def test_inline_adapter_construction_budget(
    src_dir: Path, source_ast_cache: dict,
) -> None:
    """Adapter classes must only be instantiated in composition layer."""
    violations = _find_adapter_instantiations(src_dir, source_ast_cache)
    assert not violations, (
        f"inline_adapter_construction_count={len(violations)} (target: 0)\n"
        "Adapter instantiation outside composition/ detected:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


# ---------------------------------------------------------------------------
# Metric 5: exemptions_total (baseline: 92, ratchet)
# ---------------------------------------------------------------------------

MAX_EXEMPTIONS_TOTAL = 92
EXEMPTIONS_YAML = Path("configs/quality/architecture_metric_exemptions.yaml")


def test_exemptions_total_budget() -> None:
    """Total exemption count must not exceed the ratchet budget."""
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
    assert total <= MAX_EXEMPTIONS_TOTAL, (
        f"exemptions_total={total} exceeds budget {MAX_EXEMPTIONS_TOTAL}\n"
        f"Breakdown: {breakdown}"
    )


# ---------------------------------------------------------------------------
# Metric 6: files_over_loc_threshold + class_size_exemption_count
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_EXEMPTIONS = 26
MAX_CLASS_SIZE_EXEMPTIONS = 24


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
    count = _count_registry_entries("file_size_limits")
    assert count <= MAX_FILE_SIZE_EXEMPTIONS, (
        f"files_over_loc_threshold={count} exceeds budget {MAX_FILE_SIZE_EXEMPTIONS}"
    )


def test_class_size_exemption_count() -> None:
    """Class size exemption count must not exceed ratchet budget."""
    count = _count_registry_entries("class_size")
    assert count <= MAX_CLASS_SIZE_EXEMPTIONS, (
        f"class_size_exemption_count={count} exceeds budget {MAX_CLASS_SIZE_EXEMPTIONS}"
    )


# ---------------------------------------------------------------------------
# Metric 7: e2e_skip_rate + recurrent_flaky_count (structural checks)
# ---------------------------------------------------------------------------


def test_e2e_scripts_exist() -> None:
    """E2E health-check scripts must exist."""
    skip_rate = Path("scripts/ci/check_e2e_matrix_skip_rate.py")
    rerun = Path("scripts/ci/check_e2e_rerun_stability.py")

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
    """PROBE_MODE_FALLBACK_TOTAL counter must be defined and used."""
    metrics_defs = Path(
        "src/bioetl/infrastructure/observability/metrics_definitions.py"
    )
    aggregator = Path("src/bioetl/application/core/preflight_health_aggregator.py")

    assert metrics_defs.exists(), "metrics_definitions.py not found"
    assert aggregator.exists(), "preflight_health_aggregator.py not found"

    defs_content = metrics_defs.read_text(encoding="utf-8")
    assert "PROBE_MODE_FALLBACK_TOTAL" in defs_content, (
        "PROBE_MODE_FALLBACK_TOTAL counter not defined in metrics_definitions.py"
    )

    agg_content = aggregator.read_text(encoding="utf-8")
    assert "probe_mode_fallback_total" in agg_content, (
        "probe_mode_fallback_total not instrumented in preflight_health_aggregator.py"
    )


# ---------------------------------------------------------------------------
# Metric 9: dependency_map_violations (target: 0)
# ---------------------------------------------------------------------------

GROUP_EDGE_LIMIT = 60
GROUP_EDGE_TOTAL_BUDGET = 240  # ratchet: full graph coupling budget (baseline: 232)

_dep_map_module = None


def _load_dep_map_module():  # type: ignore[no-untyped-def]
    """Load dependency map generator script as a module (cached)."""
    global _dep_map_module
    if _dep_map_module is not None:
        return _dep_map_module

    import sys

    script_path = Path("scripts/qa/generate_architecture_dependency_map.py")
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


def test_dependency_map_violations_zero() -> None:
    """Dependency map must have zero import-matrix violations."""
    mod = _load_dep_map_module()
    if mod is None:
        pytest.skip("Dependency map script not found")

    src_root = Path("src/bioetl")
    if not src_root.exists():
        pytest.skip("src/bioetl not found")

    snapshot = mod.collect_dependency_snapshot(src_root)

    assert len(snapshot.violations) == 0, (
        f"dependency_map_violations={len(snapshot.violations)} (target: 0)\n"
        + "\n".join(
            f"  - {v.source} -> {v.target} ({v.imports} imports)"
            for v in snapshot.violations
        )
    )


def test_cross_layer_group_edges_budget() -> None:
    """Cross-layer group edges must not exceed the budget."""
    mod = _load_dep_map_module()
    if mod is None:
        pytest.skip("Dependency map script not found")

    src_root = Path("src/bioetl")
    if not src_root.exists():
        pytest.skip("src/bioetl not found")

    snapshot = mod.collect_dependency_snapshot(src_root)
    edge_count = len(snapshot.cross_layer_group_edges)

    assert edge_count <= GROUP_EDGE_LIMIT, (
        f"cross_layer_group_edges={edge_count} exceeds budget {GROUP_EDGE_LIMIT}"
    )


def test_cross_layer_group_edges_total_budget() -> None:
    """Total cross-layer group edges (full graph) must not exceed the budget."""
    mod = _load_dep_map_module()
    if mod is None:
        pytest.skip("Dependency map script not found")

    src_root = Path("src/bioetl")
    if not src_root.exists():
        pytest.skip("src/bioetl not found")

    snapshot = mod.collect_dependency_snapshot(src_root)
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
    resilience = Path("src/bioetl/infrastructure/storage/write_resilience.py")
    delta_mixin = Path("src/bioetl/infrastructure/storage/silver_writer_delta_mixin.py")

    assert resilience.exists(), "write_resilience.py not found"
    assert delta_mixin.exists(), "silver_writer_delta_mixin.py not found"

    res_content = resilience.read_text(encoding="utf-8")
    assert "SilverMergeResiliencePolicy" in res_content, (
        "SilverMergeResiliencePolicy not defined in write_resilience.py"
    )
    assert "max_retries" in res_content, (
        "Retry configuration missing in SilverMergeResiliencePolicy"
    )

    delta_content = delta_mixin.read_text(encoding="utf-8")
    assert "silver_merge_retry" in delta_content, (
        "silver_merge_retry observability event missing in delta mixin"
    )
    assert "silver_merge_timeout" in delta_content, (
        "silver_merge_timeout observability event missing in delta mixin"
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


def test_architecture_test_p95_duration_tracked() -> None:
    """CI architecture workflow must have fast/nightly split with timeout enforcement."""
    workflow = Path(".github/workflows/architecture.yml")
    if not workflow.exists():
        pytest.skip("Architecture workflow not found")

    content = workflow.read_text(encoding="utf-8")

    assert "architecture-fast-baseline" in content, (
        "Workflow must have architecture-fast-baseline job for fast profile"
    )
    assert "architecture-heavy-nightly" in content, (
        "Workflow must have architecture-heavy-nightly job for full profile"
    )
    assert "not slow" in content, "Fast baseline must exclude @pytest.mark.slow tests"


# ---------------------------------------------------------------------------
# Metric 12: scorecard_registry_sync (governance debt automation)
# ---------------------------------------------------------------------------

DEBT_SCORECARD_YAML = Path("configs/quality/debt_scorecard.yaml")


def test_scorecard_baseline_matches_registry() -> None:
    """Scorecard baseline must match actual exemption registry counts."""
    if not EXEMPTIONS_YAML.exists():
        pytest.skip("Exemptions YAML not found")
    if not DEBT_SCORECARD_YAML.exists():
        pytest.skip("Debt scorecard YAML not found")

    with open(EXEMPTIONS_YAML, encoding="utf-8") as f:
        exemptions = yaml.safe_load(f)
    with open(DEBT_SCORECARD_YAML, encoding="utf-8") as f:
        scorecard = yaml.safe_load(f)

    registries = exemptions.get("registries", {})
    actual_by_registry: dict[str, int] = {}
    actual_total = 0
    for reg_name, entries in registries.items():
        count = len(entries) if isinstance(entries, dict) else 0
        actual_by_registry[reg_name] = count
        actual_total += count

    baseline = scorecard.get("baseline", {})
    expected_total = baseline.get("total_exemptions", 0)
    expected_by_registry = baseline.get("by_registry", {})

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

    assert not mismatches, (
        "Scorecard baseline drifted from actual exemption registry:\n"
        + "\n".join(f"  - {m}" for m in mismatches)
        + "\nUpdate configs/quality/debt_scorecard.yaml baseline section."
    )
