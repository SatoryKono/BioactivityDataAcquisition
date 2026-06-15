"""Architecture tests for interfaces layer dependencies.

Ensures that CLI and other interfaces do not directly import infrastructure.
In project policy, interfaces should route through application services or
composition entrypoints rather than bind themselves to infrastructure modules.
"""

from __future__ import annotations

import ast
from datetime import date
from pathlib import Path

import pytest

# Base path for source files
SRC_PATH = Path(__file__).parent.parent.parent / "src" / "bioetl"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERFACES_LAYER_DOC = (
    PROJECT_ROOT / "docs" / "02-architecture" / "04-interfaces-layer.md"
)
INTERFACES_INFRASTRUCTURE_IMPORT_ALLOWLIST: dict[str, dict[str, object]] = {}
_ALLOWLIST_REQUIRED_FIELDS = frozenset({"imports", "owner", "reason", "review_by"})


def _interfaces_python_files() -> list[Path]:
    interfaces_path = SRC_PATH / "interfaces"
    assert interfaces_path.exists(), "Interfaces layer not found"
    return sorted(interfaces_path.rglob("*.py"))


def _relative_source_path(path: Path) -> str:
    return path.relative_to(SRC_PATH.parent).as_posix()


def _direct_infrastructure_imports(path: Path) -> list[str]:
    return sorted(
        {
            imported
            for imported in get_imports_from_file(path)
            if imported == "bioetl.infrastructure"
            or imported.startswith("bioetl.infrastructure.")
        }
    )


def _allowlisted_imports_for(path: Path) -> frozenset[str]:
    entry = INTERFACES_INFRASTRUCTURE_IMPORT_ALLOWLIST.get(_relative_source_path(path))
    if entry is None:
        return frozenset()

    missing_fields = _ALLOWLIST_REQUIRED_FIELDS - set(entry)
    assert not missing_fields, (
        f"{_relative_source_path(path)} allowlist entry is missing fields: "
        f"{sorted(missing_fields)}"
    )
    assert str(entry["owner"]).strip(), f"{_relative_source_path(path)} owner required"
    assert str(entry["reason"]).strip(), (
        f"{_relative_source_path(path)} reason required"
    )
    date.fromisoformat(str(entry["review_by"]))
    imports = entry["imports"]
    assert isinstance(imports, (list, tuple, set, frozenset)), (
        f"{_relative_source_path(path)} imports allowlist must be a collection"
    )
    return frozenset(str(item) for item in imports)


def get_imports_from_file(file_path: Path) -> list[str]:
    """Extract all import statements from a Python file.

    Args:
        file_path: Path to Python file.

    Returns:
        List of imported module paths.
    """
    with open(file_path) as f:
        try:
            tree = ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return []

    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    return imports


def _parsed_import_tree(file_path: Path) -> ast.AST | None:
    with open(file_path) as f:
        try:
            return ast.parse(f.read(), filename=str(file_path))
        except SyntaxError:
            return None


def _type_checking_import_lines(tree: ast.AST) -> set[int]:
    type_checking_imports: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            for stmt in ast.walk(node):
                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    type_checking_imports.add(stmt.lineno)
    return type_checking_imports


def _runtime_import_from_node(
    node: ast.AST,
    *,
    type_checking_imports: set[int],
) -> list[str]:
    if getattr(node, "lineno", None) in type_checking_imports:
        return []
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        return [node.module]
    return []


@pytest.mark.architecture
class TestInterfacesNoDIrectInfrastructure:
    """Test that interfaces don't directly import infrastructure."""

    def test_interfaces_layer_doc_points_to_active_import_policy(self) -> None:
        """Interfaces layer doc must reference ADR-005, not the legacy matrix claim."""
        content = INTERFACES_LAYER_DOC.read_text(encoding="utf-8")

        assert "матрица импортов (interfaces может импортировать всё)" not in content, (
            "Interfaces layer doc still references the legacy import-matrix claim."
        )
        assert "(decisions/ADR-005-composition-layer-separation.md)" in content, (
            "Interfaces layer doc must link to ADR-005 as the active import matrix."
        )
        assert "не импортирует `infrastructure` напрямую" in content, (
            "Interfaces layer doc must state that direct interfaces->infrastructure imports are forbidden."
        )

    def test_ai_memory_import_matrices_forbid_direct_infrastructure(self) -> None:
        """AI memory mirrors must not preserve the legacy interfaces->infra claim."""
        memory_paths = (
            Path("docs/00-project/ai/memory/agent-memory.md"),
            Path("docs/00-project/ai/memory/memory-py-audit-bot.md"),
            Path("docs/00-project/ai/memory/memory-py-plan-bot.md"),
            Path("docs/00-project/ai/agents/guides/CLAUDE.md"),
            Path("docs/00-project/ai/agents/guides/AGENT.md"),
        )

        stale_tokens = (
            "| **interfaces**     |   OK   |     OK      |       OK",
            "interfaces` может импортировать всё",
        )
        for memory_path in memory_paths:
            content = memory_path.read_text(encoding="utf-8")
            assert not any(token in content for token in stale_tokens), (
                f"{memory_path} still preserves legacy interfaces->infrastructure guidance"
            )
            assert (
                "interfaces -> infrastructure" in content
                or "не `infrastructure` напрямую" in content
            )

    def test_all_interfaces_files_no_direct_infrastructure_imports(self):
        """All interfaces modules must route infrastructure access through composition."""
        violations: list[str] = []
        unused_allowlist_paths = set(INTERFACES_INFRASTRUCTURE_IMPORT_ALLOWLIST)

        for py_file in _interfaces_python_files():
            rel_path = _relative_source_path(py_file)
            unused_allowlist_paths.discard(rel_path)
            allowlisted_imports = _allowlisted_imports_for(py_file)
            forbidden_imports = [
                imported
                for imported in _direct_infrastructure_imports(py_file)
                if imported not in allowlisted_imports
            ]
            if forbidden_imports:
                violations.append(f"{rel_path}: {forbidden_imports}")

        assert not unused_allowlist_paths, (
            "Interfaces infrastructure import allowlist has stale paths: "
            f"{sorted(unused_allowlist_paths)}"
        )
        assert violations == [], (
            "Interfaces layer must not import infrastructure directly.\n"
            "Route access through composition APIs or add a timeboxed allowlist "
            "entry with imports, owner, reason, and review_by.\n"
            + "\n".join(f"  - {violation}" for violation in violations)
        )

    def test_cli_no_infrastructure_imports(self):
        """Test that CLI doesn't import from infrastructure directly."""
        # CLI is now in a package structure: interfaces/cli/main.py
        cli_path = SRC_PATH / "interfaces" / "cli" / "main.py"
        assert cli_path.exists(), "CLI main.py not found"

        imports = get_imports_from_file(cli_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        assert infrastructure_imports == [], (
            f"CLI should not import directly from infrastructure. "
            f"Found: {infrastructure_imports}. "
            f"Use Application services or Composition entrypoints instead."
        )

    def test_cli_no_bootstrap_internal_imports(self):
        """Test that CLI doesn't import from _bootstrap internal module.

        CLI should use composition.entrypoints, not _bootstrap directly.
        """
        # CLI is now in a package structure: interfaces/cli/main.py
        cli_path = SRC_PATH / "interfaces" / "cli" / "main.py"
        assert cli_path.exists(), "CLI main.py not found"

        imports = get_imports_from_file(cli_path)

        bootstrap_imports = [imp for imp in imports if "composition._bootstrap" in imp]

        assert bootstrap_imports == [], (
            f"CLI should not import from _bootstrap. "
            f"Found: {bootstrap_imports}. "
            f"Use composition.entrypoints instead."
        )

    def test_all_cli_commands_no_infrastructure_imports(self):
        """Test that ALL CLI command files don't import infrastructure.

        CLI commands should use Application services or Composition entrypoints
        instead of importing infrastructure modules directly.
        """
        commands_dir = SRC_PATH / "interfaces" / "cli" / "commands"
        assert commands_dir.exists(), "CLI commands directory not found"

        violations = []

        for py_file in commands_dir.glob("*.py"):
            # Skip __init__.py as it typically just re-exports
            if py_file.name == "__init__.py":
                continue

            imports = get_imports_from_file(py_file)
            infrastructure_imports = [
                imp for imp in imports if "bioetl.infrastructure" in imp
            ]

            if infrastructure_imports:
                violations.append(f"{py_file.name}: {infrastructure_imports}")

        assert violations == [], (
            "CLI commands should not import from infrastructure directly. "
            "Found violations:\n  - " + "\n  - ".join(violations) + "\n"
            "Use Application services or Composition entrypoints instead."
        )

    def test_legacy_cli_infrastructure_imports_documented(self):
        """Document and track legacy infrastructure imports in CLI commands.

        This test tracks known violations that are allowed temporarily.
        As violations are fixed, remove them from the allowlist.
        If all are fixed, this test can be removed.
        """
        commands_dir = SRC_PATH / "interfaces" / "cli" / "commands"
        assert commands_dir.exists(), "CLI commands directory not found"

        # Expected legacy violations - keep in sync with test above
        # Note: quarantine.py was fixed in IF-002 refactoring to use QuarantineService
        # Note: health.py was fixed to use composition entrypoints for DI
        expected_violations: dict[str, list[str]] = {
            # All CLI commands now properly use composition entrypoints
        }

        actual_violations = {}

        for py_file in commands_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            imports = get_imports_from_file(py_file)
            infrastructure_imports = sorted(
                {imp for imp in imports if "bioetl.infrastructure" in imp}
            )

            if infrastructure_imports:
                actual_violations[py_file.name] = infrastructure_imports

        # Check that we're tracking all known violations
        for filename, expected_imports in expected_violations.items():
            actual = actual_violations.get(filename, [])
            for expected_import in expected_imports:
                assert expected_import in actual, (
                    f"Expected violation in {filename}: {expected_import} "
                    f"was fixed! Remove from allowed_legacy_files."
                )

        # Check for new violations not in our allowlist
        for filename, imports in actual_violations.items():
            if filename not in expected_violations:
                pytest.fail(
                    f"New infrastructure import in {filename}: {imports}. "
                    f"Either fix it or add to expected_violations with justification."
                )

    def test_interfaces_module_no_infrastructure_imports(self):
        """Test that interfaces __init__ doesn't import infrastructure."""
        init_path = SRC_PATH / "interfaces" / "__init__.py"
        assert init_path.exists(), "interfaces __init__ not found"

        imports = get_imports_from_file(init_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        assert infrastructure_imports == [], (
            "interfaces/__init__ should not import infrastructure directly. "
            f"Found: {infrastructure_imports}"
        )

    def test_observability_no_infrastructure_imports(self):
        """Legacy observability facade must stay removed."""
        obs_path = SRC_PATH / "interfaces" / "observability.py"
        assert not obs_path.exists(), (
            "interfaces/observability.py should stay removed; use "
            "bioetl.composition.observability_api instead."
        )


@pytest.mark.architecture
class TestApplicationServicesExist:
    """Test that Application services exist for administrative operations."""

    def test_checkpoint_service_exists(self):
        """Test CheckpointService exists."""
        service_path = SRC_PATH / "application" / "services" / "checkpoint_service.py"
        assert service_path.exists(), "CheckpointService should exist"

    def test_quarantine_service_exists(self):
        """Test QuarantineService exists."""
        service_path = SRC_PATH / "application" / "services" / "quarantine_service.py"
        assert service_path.exists(), "QuarantineService should exist"

    def test_lock_service_exists(self):
        """Test LockService exists."""
        service_path = SRC_PATH / "application" / "services" / "lock_service.py"
        assert service_path.exists(), "LockService should exist"

    def test_bronze_cleanup_service_exists(self):
        """Test BronzeCleanupService exists."""
        service_path = (
            SRC_PATH / "application" / "services" / "bronze_cleanup_service.py"
        )
        assert service_path.exists(), "BronzeCleanupService should exist"


@pytest.mark.architecture
class TestEntrypointsLegacyServiceCompatibility:
    """Test removed service getter behavior in composition entrypoints."""

    def test_entrypoints_exports_services(self):
        """Legacy service getters must stay removed from composition entrypoints."""
        from bioetl.composition import entrypoints

        entrypoint_names = set(dir(entrypoints))
        assert "get_checkpoint_service" not in entrypoint_names, (
            "entrypoints should not expose get_checkpoint_service anymore"
        )
        assert "get_quarantine_service" not in entrypoint_names, (
            "entrypoints should not expose get_quarantine_service anymore"
        )
        assert "get_bronze_cleanup_service" not in entrypoint_names, (
            "entrypoints should not expose get_bronze_cleanup_service anymore"
        )

    def test_entrypoints_all_excludes_legacy_service_getters(self):
        """Legacy service getters must stay off entrypoints and retired umbrella APIs."""
        from bioetl.composition import entrypoints

        assert "get_checkpoint_service" not in entrypoints.__all__
        assert "get_quarantine_service" not in entrypoints.__all__
        assert "get_bronze_cleanup_service" not in entrypoints.__all__

        assert not (SRC_PATH / "composition" / "services_api.py").exists()


def get_runtime_imports_from_file(file_path: Path) -> list[str]:
    """Extract only runtime import statements from a Python file.

    Excludes imports inside TYPE_CHECKING blocks.

    Args:
        file_path: Path to Python file.

    Returns:
        List of imported module paths (runtime only).
    """
    tree = _parsed_import_tree(file_path)
    if tree is None:
        return []

    imports: list[str] = []
    type_checking_imports = _type_checking_import_lines(tree)
    for node in ast.walk(tree):
        imports.extend(
            _runtime_import_from_node(
                node,
                type_checking_imports=type_checking_imports,
            )
        )
    return imports


def _runtime_infrastructure_imports(py_file: Path) -> list[str]:
    imports = get_runtime_imports_from_file(py_file)
    return [imp for imp in imports if "bioetl.infrastructure" in imp]


def _http_runtime_infrastructure_violations(http_dir: Path) -> list[str]:
    violations: list[str] = []
    for py_file in http_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        infrastructure_imports = _runtime_infrastructure_imports(py_file)
        if infrastructure_imports:
            violations.append(f"{py_file.name}: {infrastructure_imports}")
    return violations


@pytest.mark.architecture
class TestHttpInterfaceNoInfrastructure:
    """Test that HTTP interface module doesn't have runtime infrastructure imports."""

    def test_http_init_no_runtime_infrastructure_imports(self):
        """Test that http/__init__.py doesn't import infrastructure at runtime."""
        init_path = SRC_PATH / "interfaces" / "http" / "__init__.py"
        assert init_path.exists(), "http/__init__.py not found"

        imports = get_runtime_imports_from_file(init_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        assert infrastructure_imports == [], (
            f"http/__init__.py should not import from infrastructure at runtime. "
            f"Found: {infrastructure_imports}. "
            f"Use TYPE_CHECKING for type hints or Application services instead."
        )

    def test_http_types_no_runtime_infrastructure_imports(self):
        """Test that http/types.py doesn't import infrastructure at runtime."""
        types_path = SRC_PATH / "interfaces" / "http" / "types.py"
        assert types_path.exists(), "http/types.py not found"

        imports = get_runtime_imports_from_file(types_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        assert infrastructure_imports == [], (
            f"http/types.py should not import from infrastructure at runtime. "
            f"Found: {infrastructure_imports}. "
            f"Types should be independent of infrastructure layer."
        )

    def test_health_server_no_runtime_infrastructure_imports(self):
        """Test that health_server.py doesn't import infrastructure at runtime.

        TYPE_CHECKING imports are allowed for type hints, but runtime imports
        from infrastructure should go through Application services.
        """
        server_path = SRC_PATH / "interfaces" / "http" / "health_server.py"
        assert server_path.exists(), "health_server.py not found"

        imports = get_runtime_imports_from_file(server_path)

        infrastructure_imports = [
            imp for imp in imports if "bioetl.infrastructure" in imp
        ]

        assert infrastructure_imports == [], (
            f"health_server.py should not import from infrastructure at runtime. "
            f"Found: {infrastructure_imports}. "
            f"Use TYPE_CHECKING for type hints or Application services instead."
        )

    def test_all_http_files_no_runtime_infrastructure_imports(self):
        """Test that ALL files in http/ don't import infrastructure at runtime.

        Per architecture best practices, interfaces should not directly
        access infrastructure adapters at runtime. TYPE_CHECKING imports
        for type hints are allowed.
        """
        http_dir = SRC_PATH / "interfaces" / "http"
        assert http_dir.exists(), "http/ directory not found"

        violations = _http_runtime_infrastructure_violations(http_dir)

        assert violations == [], (
            "HTTP interface files should not import from infrastructure at runtime. "
            "Found violations:\n  - " + "\n  - ".join(violations) + "\n"
            "Use TYPE_CHECKING for type hints or Application services instead."
        )

    def test_http_type_checking_uses_domain_ports(self):
        """Verify http/ uses domain ports, not infrastructure imports.

        After refactoring (PR #1542), health_server.py imports from
        domain ports instead of infrastructure adapters.
        This is the correct architectural approach.
        """
        server_path = SRC_PATH / "interfaces" / "http" / "health_server.py"
        assert server_path.exists(), "health_server.py not found"

        with open(server_path) as f:
            content = f.read()

        # Verify domain port imports are used (correct architecture)
        assert "from bioetl.domain.ports import" in content, (
            "health_server.py should import from domain ports, not infrastructure"
        )
        assert "HealthMonitorPort" in content, (
            "health_server.py should use HealthMonitorPort from domain"
        )

        # Verify no infrastructure imports remain
        assert "bioetl.infrastructure.adapters.http.health_monitor" not in content, (
            "health_server.py should not import from infrastructure. "
            "Use domain ports instead."
        )
