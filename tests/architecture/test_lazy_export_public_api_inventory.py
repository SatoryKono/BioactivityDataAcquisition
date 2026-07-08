"""Owner inventory for module-level lazy export public API surfaces."""

from __future__ import annotations

import ast
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "bioetl"

EXPECTED_LAZY_EXPORT_FACADES = {
    "src/bioetl/application/core/wiring/__init__.py": "public_package_facade",
    "src/bioetl/application/pipelines/common/blocks.py": "dynamic_entrypoint",
    "src/bioetl/application/pipelines/crossref/__init__.py": ("public_package_facade"),
    "src/bioetl/application/services/control_plane/replay/__init__.py": (
        "public_package_facade"
    ),
    "src/bioetl/composition/bootstrap/__init__.py": "public_package_facade",
    "src/bioetl/composition/bootstrap/cli/__init__.py": "public_package_facade",
    "src/bioetl/composition/bootstrap/runtime/__init__.py": ("public_package_facade"),
    "src/bioetl/composition/bootstrap/runtime/composite.py": "compatibility_facade",
    "src/bioetl/composition/entrypoints.py": "public_facade",
    "src/bioetl/composition/execution_api.py": "public_facade",
    "src/bioetl/composition/factories/__init__.py": "public_package_facade",
    "src/bioetl/composition/factories/dq/__init__.py": "public_package_facade",
    "src/bioetl/composition/factories/pipeline/__init__.py": ("public_package_facade"),
    "src/bioetl/composition/factories/pipeline/registry.py": "public_facade",
    "src/bioetl/composition/factories/services/__init__.py": ("public_package_facade"),
    "src/bioetl/composition/factories/services/factory.py": "compatibility_facade",
    "src/bioetl/composition/providers/__init__.py": "public_package_facade",
    "src/bioetl/composition/registry_api.py": "public_facade",
    "src/bioetl/composition/runtime_builders/__init__.py": "public_package_facade",
    "src/bioetl/composition/runtime_builders/_run_manifest_data_roots.py": (
        "compatibility_facade"
    ),
    "src/bioetl/composition/runtime_builders/_run_manifest_refs.py": (
        "compatibility_facade"
    ),
    "src/bioetl/composition/runtime_builders/inputs_resolver.py": "public_facade",
    "src/bioetl/domain/__init__.py": "public_package_facade",
    "src/bioetl/domain/behavior/__init__.py": "public_package_facade",
    "src/bioetl/domain/config/__init__.py": "public_package_facade",
    "src/bioetl/domain/entities/__init__.py": "public_package_facade",
    "src/bioetl/domain/exceptions/__init__.py": "public_package_facade",
    "src/bioetl/domain/filtering/__init__.py": "public_package_facade",
    "src/bioetl/domain/normalization/profiles/__init__.py": ("public_package_facade"),
    "src/bioetl/domain/ports/__init__.py": "public_package_facade",
    "src/bioetl/domain/types/__init__.py": "public_package_facade",
    "src/bioetl/domain/value_objects/__init__.py": "public_package_facade",
    "src/bioetl/infrastructure/adapters/http/health_monitor.py": (
        "compatibility_facade"
    ),
    "src/bioetl/infrastructure/config/__init__.py": "public_package_facade",
    "src/bioetl/infrastructure/control_plane/__init__.py": "public_package_facade",
    "src/bioetl/infrastructure/export/__init__.py": "public_package_facade",
    "src/bioetl/infrastructure/observability/__init__.py": "public_package_facade",
    "src/bioetl/infrastructure/storage/support/atomic_ops.py": "compatibility_facade",
    "src/bioetl/interfaces/cli/commands/__init__.py": "public_package_facade",
    "src/bioetl/interfaces/cli/commands/domains/composite/__init__.py": (
        "public_package_facade"
    ),
    "src/bioetl/interfaces/cli/commands/domains/diagnostics/__init__.py": (
        "public_package_facade"
    ),
    "src/bioetl/interfaces/cli/commands/domains/health/__init__.py": (
        "public_package_facade"
    ),
    "src/bioetl/interfaces/cli/commands/domains/maintenance/__init__.py": (
        "public_package_facade"
    ),
    "src/bioetl/interfaces/cli/commands/domains/quarantine/__init__.py": (
        "public_package_facade"
    ),
    "src/bioetl/interfaces/cli/commands/domains/run_all/__init__.py": (
        "public_package_facade"
    ),
}

ALLOWED_CLASSIFICATIONS = frozenset(
    {
        "compatibility_facade",
        "dynamic_entrypoint",
        "public_facade",
        "public_package_facade",
    }
)


def _has_module_level_getattr(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(
        (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "__getattr__"
        )
        or (
            isinstance(node, ast.Assign)
            and any(_assigns_module_getattr(target) for target in node.targets)
        )
        or _calls_install_lazy_exports(node)
        for node in tree.body
    )


def _assigns_module_getattr(target: ast.expr) -> bool:
    if isinstance(target, ast.Name):
        return target.id == "__getattr__"
    if isinstance(target, ast.Tuple):
        return any(_assigns_module_getattr(element) for element in target.elts)
    return False


def _calls_install_lazy_exports(node: ast.stmt) -> bool:
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    func = node.value.func
    return isinstance(func, ast.Name) and func.id == "install_lazy_exports"


def _module_level_lazy_export_paths() -> set[str]:
    rg_path = shutil.which("rg")
    if rg_path:
        result = subprocess.run(
            [
                rg_path,
                "--files-with-matches",
                "(__getattr__|install_lazy_exports|install_cached_public_exports)",
                "src/bioetl",
                "--glob",
                "*.py",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode in {0, 1}, result.stderr
        candidate_paths = (
            ROOT / line.strip() for line in result.stdout.splitlines() if line.strip()
        )
    else:
        candidate_paths = SRC_ROOT.rglob("*.py")
    return {
        path.relative_to(ROOT).as_posix()
        for path in candidate_paths
        if _has_module_level_getattr(path)
    }


@pytest.mark.architecture
def test_module_level_lazy_export_public_api_surfaces_are_owner_classified() -> None:
    """New lazy export public API surfaces require an explicit owner classification."""
    actual_paths = _module_level_lazy_export_paths()
    expected_paths = set(EXPECTED_LAZY_EXPORT_FACADES)

    assert actual_paths == expected_paths, (
        "Module-level lazy export facade inventory drifted. Classify each new "
        "__getattr__ surface as public API, dynamic entrypoint, compatibility "
        "facade, or remove it.\n"
        f"unclassified={sorted(actual_paths - expected_paths)}\n"
        f"stale={sorted(expected_paths - actual_paths)}"
    )
    assert set(EXPECTED_LAZY_EXPORT_FACADES.values()) <= ALLOWED_CLASSIFICATIONS


@pytest.mark.architecture
def test_lazy_export_public_api_inventory_has_owner_test_coverage() -> None:
    """Compatibility-sensitive lazy export groups must have dedicated owner tests."""
    required_owner_tests = {
        "tests/architecture/test_public_surface_importer_census_governance.py",
        "tests/architecture/test_removed_surface_freeze_guards.py",
        "tests/architecture/test_application_services_lazy_facade_governance.py",
        "tests/architecture/test_domain_public_api.py",
    }
    for test_path in required_owner_tests:
        assert (ROOT / test_path).exists(), test_path
