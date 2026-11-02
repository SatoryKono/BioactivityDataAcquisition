"""QM-07 source cold-import, root-seam, and installed-wheel isolation checks."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architecture, pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
QUALITY_ROOT = REPO_ROOT / "scripts/engineering/quality"

QUALITY_MODULES = [
    "scripts.engineering.quality",
    "scripts.engineering.quality._baseline_validation",
    "scripts.engineering.quality._decomposition_burndown_policy",
    "scripts.engineering.quality._decomposition_owner_policy",
    "scripts.engineering.quality._decomposition_program_policy",
    "scripts.engineering.quality._decomposition_validation",
    "scripts.engineering.quality._governance_validation",
    "scripts.engineering.quality._grace_windows_validation",
    "scripts.engineering.quality._primitives",
    "scripts.engineering.quality._quarterly_targets_validation",
    "scripts.engineering.quality.architecture_debt_artifact_tasks",
    "scripts.engineering.quality.architecture_debt_reduction",
    "scripts.engineering.quality.architecture_debt_task_generation",
    "scripts.engineering.quality.architecture_debt_task_policy",
    "scripts.engineering.quality.architecture_debt_task_support",
    "scripts.engineering.quality.architecture_quality_scorecard",
    "scripts.engineering.quality.architecture_quality_scoring",
    "scripts.engineering.quality.budget_evaluator",
    "scripts.engineering.quality.debt_scorecard",
    "scripts.engineering.quality.debt_scorecard_validation",
    "scripts.engineering.quality.exemptions_registry",
    "scripts.engineering.quality.exemptions_registry_access",
    "scripts.engineering.quality.exemptions_registry_paths",
    "scripts.engineering.quality.exemptions_registry_policy",
    "scripts.engineering.quality.exemptions_registry_targets",
    "scripts.engineering.quality.exemptions_registry_validation",
    "scripts.engineering.quality.inventory",
    "scripts.engineering.quality.registry_sync_service",
    "scripts.engineering.quality.report_formatter",
    "scripts.engineering.quality.scoring",
]


def _expected_module_path(module_name: str) -> Path:
    if module_name.endswith(".quality"):
        return QUALITY_ROOT / "__init__.py"
    return QUALITY_ROOT / f"{module_name.rsplit('.', 1)[1]}.py"


def _run_isolated(code: str, *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run ``code`` with ``-I`` and explicit src/checkout on ``sys.path``."""
    prelude = (
        "import sys; "
        f"sys.path[:0] = {list(map(str, (REPO_ROOT / 'src', REPO_ROOT)))!r}; "
    )
    return subprocess.run(
        [sys.executable, "-I", "-c", prelude + code],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _run_wheel(
    python: Path,
    code: str,
    *,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    """Run ``code`` in an installed-wheel interpreter without checkout paths."""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    return subprocess.run(
        [str(python), "-I", "-c", code],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


@pytest.fixture(scope="session")
def wheel_venv_python(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    """Build the checkout wheel and install it into a temporary venv."""
    root = tmp_path_factory.mktemp("qm07-wheel")
    dist_dir = root / "dist"
    venv_dir = root / "wheel_venv"
    dist_dir.mkdir(parents=True, exist_ok=True)

    build = subprocess.run(
        ["uv", "build", "--wheel", "-o", str(dist_dir)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, f"uv build failed: {build.stderr}"
    wheels = sorted(dist_dir.glob("bioetl-*.whl"))
    assert len(wheels) == 1, f"expected one bioetl wheel, found {wheels}"

    create = subprocess.run(
        ["uv", "venv", str(venv_dir), "--python", sys.executable],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert create.returncode == 0, f"uv venv failed: {create.stderr}"
    python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    assert python.is_file(), python

    install = subprocess.run(
        ["uv", "pip", "install", "--python", str(python), str(wheels[0])],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert install.returncode == 0, f"wheel install failed: {install.stderr}"
    yield python


@pytest.mark.parametrize("module_name", QUALITY_MODULES)
def test_source_cold_import_from_outside_cwd(tmp_path: Path, module_name: str) -> None:
    code = (
        "import importlib, json; "
        f"module = importlib.import_module({module_name!r}); "
        "print(json.dumps(module.__file__))"
    )
    result = _run_isolated(code, cwd=tmp_path)
    assert result.returncode == 0, f"Import failed for {module_name}: {result.stderr}"
    origin = Path(json.loads(result.stdout)).resolve()
    assert origin == _expected_module_path(module_name).resolve(), (
        f"Unexpected origin for {module_name}: {origin}"
    )


def test_wheel_runtime_smoke_without_scripts(
    tmp_path: Path, wheel_venv_python: Path
) -> None:
    script = """
import sys

class ScriptImportBlocker:
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith("scripts"):
            raise ImportError(f"Attempted to import {fullname} in runtime!")
        return None

sys.meta_path.insert(0, ScriptImportBlocker())
import bioetl
from bioetl.application.core.runner import PipelineRunner
print(bioetl.__file__)
print(PipelineRunner.__name__)
"""
    result = _run_wheel(wheel_venv_python, script, cwd=tmp_path)
    assert result.returncode == 0, f"Wheel smoke failed: {result.stderr}"
    origin = Path(result.stdout.splitlines()[0].strip()).resolve()
    assert "site-packages" in origin.as_posix()
    assert origin.name == "__init__.py"
    assert "PipelineRunner" in result.stdout


def test_wheel_harness_catches_script_imports(
    tmp_path: Path, wheel_venv_python: Path
) -> None:
    script = """
import sys

class ScriptImportBlocker:
    def find_spec(self, fullname, path, target=None):
        if fullname.startswith("scripts"):
            raise ImportError(f"Attempted to import {fullname} in runtime!")
        return None

sys.meta_path.insert(0, ScriptImportBlocker())
import scripts.engineering
"""
    result = _run_wheel(wheel_venv_python, script, cwd=tmp_path)
    assert result.returncode != 0
    assert "Attempted to import scripts" in result.stderr


def test_root_seams_from_outside_cwd(tmp_path: Path) -> None:
    code = """
import json
from pathlib import Path
from scripts.engineering.quality.architecture_debt_reduction import (
    PLAN_SCHEMA_VERSION,
    _project_root as debt_reduction_root,
)
from scripts.engineering.quality.architecture_debt_task_generation import (
    _project_root as task_generation_root,
    generate_architecture_debt_tasks_payload,
)
from scripts.engineering.quality.architecture_quality_scorecard import (
    PROJECT_ROOT as SCORECARD_ROOT,
    build_architecture_quality_scorecard,
)
from scripts.engineering.quality.debt_scorecard import load_debt_scorecard
from scripts.engineering.quality.exemptions_registry_paths import project_root

roots = {
    "debt_reduction": str(debt_reduction_root().resolve()),
    "task_generation": str(task_generation_root().resolve()),
    "scorecard_const": str(Path(SCORECARD_ROOT).resolve()),
    "exemptions": str(project_root().resolve()),
}
assert len(set(roots.values())) == 1, roots
root = Path(next(iter(roots.values())))
assert (root / "pyproject.toml").is_file()
assert (root / "scripts").is_dir()
assert isinstance(PLAN_SCHEMA_VERSION, str) and PLAN_SCHEMA_VERSION
assert callable(build_architecture_quality_scorecard)
assert callable(load_debt_scorecard)
assert callable(generate_architecture_debt_tasks_payload)
print(json.dumps({"root": str(root), "plan_schema_version": PLAN_SCHEMA_VERSION}))
"""
    result = _run_isolated(code, cwd=tmp_path)
    assert result.returncode == 0, f"Root seams check failed: {result.stderr}"
    payload = json.loads(result.stdout)
    assert Path(payload["root"]).resolve() == REPO_ROOT.resolve()
    assert payload["plan_schema_version"]


def test_debt_governance_gate_evaluators_from_outside_cwd(tmp_path: Path) -> None:
    code = """
import json
from scripts.engineering.qa.debt_governance_gate_evaluators import (
    build_architecture_quality_scorecard,
    evaluate_debt_scorecard,
    load_debt_scorecard,
)

bindings = {
    "build_architecture_quality_scorecard": build_architecture_quality_scorecard,
    "evaluate_debt_scorecard": evaluate_debt_scorecard,
    "load_debt_scorecard": load_debt_scorecard,
}
none_bindings = [name for name, value in bindings.items() if value is None]
assert not none_bindings, f"None bindings: {none_bindings}"
for name, value in bindings.items():
    assert callable(value), name
print(json.dumps(sorted(bindings)))
"""
    result = _run_isolated(code, cwd=tmp_path)
    assert result.returncode == 0, f"Imports failed: {result.stderr}"
    assert json.loads(result.stdout) == [
        "build_architecture_quality_scorecard",
        "evaluate_debt_scorecard",
        "load_debt_scorecard",
    ]


def test_debt_scorecard_functional_bounded(tmp_path: Path) -> None:
    code = """
import json
from scripts.engineering.qa.debt_governance_gate_evaluators import (
    evaluate_debt_scorecard,
    load_debt_scorecard,
)

scorecard = load_debt_scorecard()
assert isinstance(scorecard, dict) and scorecard
violations, summary = evaluate_debt_scorecard()
assert isinstance(violations, list)
print(json.dumps({
    "keys": sorted(scorecard)[:8],
    "violation_count": len(violations),
    "summary_is_none": summary is None,
}))
"""
    result = _run_isolated(code, cwd=tmp_path)
    assert result.returncode == 0, f"Debt scorecard load failed: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["keys"]
    assert isinstance(payload["violation_count"], int)


def test_report_architecture_quality_scorecard_functional(tmp_path: Path) -> None:
    """Build scorecard in-process; do not call main() (it writes reports/)."""
    code = """
import json
from scripts.engineering.quality.architecture_quality_scorecard import (
    build_architecture_quality_scorecard,
)

payload = build_architecture_quality_scorecard()
assert isinstance(payload, dict)
required = {
    "categories",
    "generated_by",
    "integral_score",
    "metrics",
    "schema_version",
    "source_artifacts",
}
missing = sorted(required - set(payload))
assert not missing, missing
print(json.dumps({
    "schema_version": payload["schema_version"],
    "source_module_count": payload["metrics"]["source_module_count"],
    "generated_by": payload["generated_by"],
}))
"""
    result = _run_isolated(code, cwd=tmp_path)
    assert result.returncode == 0, f"Scorecard build failed: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["schema_version"]
    assert isinstance(payload["source_module_count"], int)
    assert payload["source_module_count"] > 0
    assert "architecture_quality_scorecard" in payload["generated_by"]


def test_root_seams_custom_roots_and_errors(tmp_path: Path) -> None:
    code = """
import json
from pathlib import Path
from scripts.engineering.quality.exemptions_registry_paths import (
    build_module_path_key,
    project_root,
    resolve_registry_path,
)

root = project_root().resolve()
assert (root / "pyproject.toml").is_file()
assert root != Path("/tmp/invalid_root").resolve()
registry = resolve_registry_path()
assert registry.is_absolute()
assert registry.name == "architecture_metric_exemptions.yaml"
key = build_module_path_key("src/bioetl/__init__.py")
assert key == "src/bioetl/__init__.py"
try:
    build_module_path_key("/tmp/not-in-repo.py")
except ValueError as exc:
    print(json.dumps({"root": str(root), "error": str(exc)}))
else:
    raise AssertionError("expected ValueError for escaped module path")
"""
    result = _run_isolated(code, cwd=tmp_path)
    assert result.returncode == 0, f"Root seam contracts failed: {result.stderr}"
    payload = json.loads(result.stdout)
    assert Path(payload["root"]).resolve() == REPO_ROOT.resolve()
    assert "module_path must resolve" in payload["error"]
