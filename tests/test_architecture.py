import os
import re
import subprocess
import tomllib
from pathlib import Path
import pytest
import inspect
from typing import runtime_checkable, Protocol

from bioetl.domain.ports import DataSourcePort, LockPort, CheckpointPort, StoragePort, QuarantinePort

# --- REQ-ARCH-001, REQ-ARCH-003 ---
def test_domain_layer_purity(src_dir: Path):
    """Domain layer must not have I/O dependencies."""
    domain_path = src_dir / "bioetl" / "domain"
    disallowed_imports = {"httpx", "requests", "boto3", "sqlalchemy", "psycopg2", "deltalake", "polars"}

    for py_file in domain_path.rglob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            content = f.read()
            for lib in disallowed_imports:
                assert f"import {lib}" not in content, f"Disallowed import '{lib}' in {py_file}"
                assert f"from {lib}" not in content, f"Disallowed import '{lib}' in {py_file}"

# --- REQ-ARCH-001 ---
def test_ports_are_protocols(src_dir: Path):
    """Ports must be defined using typing.Protocol."""
    ports_file = src_dir / "bioetl" / "domain" / "ports.py"
    assert ports_file.exists()
    with open(ports_file, "r", encoding="utf-8") as f:
        content = f.read()
        # Find lines importing from typing
        typing_imports = re.findall(r"from typing import .*", content)
        assert any("Protocol" in line for line in typing_imports), "Protocol not imported from typing"

# --- REQ-ARCH-004 ---
def test_critical_ports_are_runtime_checkable():
    """Critical port protocols should be runtime checkable."""
    critical_ports = [DataSourcePort, LockPort, CheckpointPort, StoragePort, QuarantinePort]
    for port in critical_ports:
        assert hasattr(port, "_is_runtime_protocol"), f"{port.__name__} is not runtime checkable, add @runtime_checkable"

# --- REQ-STACK-001 ---
def test_httpx_is_http_client(pyproject_toml: Path):
    """httpx must be the declared HTTP client."""
    with open(pyproject_toml, "rb") as f:
        data = tomllib.load(f)
    dependencies = data.get("project", {}).get("dependencies", [])
    assert any("httpx" in dep for dep in dependencies)

# --- REQ-STACK-004 ---
def test_ruff_is_linter(pyproject_toml: Path):
    """Ruff must be the declared linter."""
    with open(pyproject_toml, "rb") as f:
        data = tomllib.load(f)
    dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    assert any("ruff" in dep for dep in dev_deps)

# --- REQ-SECRET-004 ---
def test_dotenv_is_gitignored(project_root: Path):
    """.env files must be in .gitignore."""
    gitignore_path = project_root / ".gitignore"
    assert gitignore_path.exists()
    with open(gitignore_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Check for exact .env or patterns like *.env or / .env
        assert re.search(r"(^|\n)\.env($|\n)", content) or \
               re.search(r"(^|\n)\*\.env($|\n)", content) or \
               re.search(r"(^|\n)\.env\*($|\n)", content)

# --- REQ-DX-004, REQ-DX-005 ---
def test_dev_experience_files_exist(project_root: Path):
    """Core DX files must exist."""
    assert (project_root / "Makefile").exists(), "Makefile is missing"
    assert (project_root / "docker-compose.yml").exists() or (project_root / "compose.yml").exists(), "Docker compose file is missing"
    assert (project_root / ".env.example").exists(), ".env.example is missing"

# --- REQ-DEP-001 ---
def test_dependencies_have_version_constraints(pyproject_toml: Path):
    """Dependencies in pyproject.toml should have version constraints."""
    with open(pyproject_toml, "rb") as f:
        data = tomllib.load(f)

    deps = data.get("project", {}).get("dependencies", [])
    dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    docs_deps = data.get("project", {}).get("optional-dependencies", {}).get("docs", [])

    all_deps = deps + dev_deps + docs_deps
    version_indicators = (">=", "==", "~=", "<", ">", "!=")
    for dep in all_deps:
        # Skip comments and empty lines
        if dep.startswith("#") or not dep.strip():
            continue
        has_version = any(ind in dep for ind in version_indicators)
        assert has_version, f"Dependency '{dep}' has no version constraint"

# --- REQ-DEP-002 ---
def test_pip_audit_in_dev_deps(pyproject_toml: Path):
    """pip-audit must be a dev dependency."""
    with open(pyproject_toml, "rb") as f:
        data = tomllib.load(f)
    dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    assert any("pip-audit" in dep for dep in dev_deps)

# --- REQ-DOC-002 ---
def test_doc_naming_convention(src_dir: Path, docs_dir: Path):
    """Provider doc folders should mirror src folders."""
    src_providers_path = src_dir / "bioetl" / "infrastructure" / "adapters"
    docs_providers_path = docs_dir / "providers" # Assuming this is the convention

    if not src_providers_path.exists() or not docs_providers_path.exists():
        pytest.skip("Provider directories not found, skipping test.")

    src_providers = {d.name for d in src_providers_path.iterdir() if d.is_dir()}
    docs_providers = {d.name for d in docs_providers_path.iterdir() if d.is_dir()}

    assert src_providers.issubset(docs_providers), f"Missing doc folders for providers: {src_providers - docs_providers}"


# --- REQ-COMPLEXITY-001 ---
def test_code_complexity_with_xenon(src_dir: Path):
    """Code complexity must meet xenon thresholds (max-absolute B, max-modules B, max-average B).

    Runs: xenon --max-absolute B --max-modules B --max-average B --exclude "tests/*,src/tools/*" src

    Grade thresholds:
    - A: CC <= 5 (simple, low risk)
    - B: 6 <= CC <= 10 (more complex, moderate risk)
    - C: 11 <= CC <= 20 (complex, high risk)
    - D: 21 <= CC <= 30 (very complex, very high risk)
    - F: CC > 30 (unmaintainable)
    """
    try:
        result = subprocess.run(
            [
                "xenon",
                "--max-absolute", "B",
                "--max-modules", "B",
                "--max-average", "B",
                "--exclude", "tests/*,src/tools/*",
                str(src_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        pytest.skip("xenon not installed, run: pip install xenon")

    assert result.returncode == 0, (
        f"Code complexity check failed.\n"
        f"xenon output:\n{result.stdout}\n{result.stderr}\n\n"
        f"Functions/modules exceed complexity threshold B (CC > 10).\n"
        f"Refactor complex code to reduce cyclomatic complexity."
    )
