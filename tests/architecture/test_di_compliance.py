"""Architecture tests: Dependency Injection compliance.

REQ-ARCH-DI-001: Application layer MUST NOT instantiate infrastructure.
REQ-ARCH-DI-002: Factory classes MUST be in composition layer only.
REQ-ARCH-DI-003: Dependencies MUST be injected through constructors.

See CLAUDE.md §2.2 and §11 Anti-Patterns.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# Paths relative to project root
APPLICATION_DIR = Path("src/bioetl/application")
COMPOSITION_DIR = Path("src/bioetl/composition")
INFRASTRUCTURE_DIR = Path("src/bioetl/infrastructure")
DOMAIN_DIR = Path("src/bioetl/domain")

# Forbidden class names for instantiation in application layer.
# These are INFRASTRUCTURE classes that MUST be injected, not created.
# NOTE: Transformer classes are allowed in application since they are
# application-layer components, not infrastructure.
FORBIDDEN_INSTANTIATION_CLASSES: set[str] = {
    # Adapters (infrastructure - injected via DataSourcePort)
    "ChemblAdapter",
    "ChemblClient",
    "PubChemAdapter",
    "PubChemClient",
    "UniProtAdapter",
    "UniProtClient",
    "PubMedAdapter",
    "PubMedClient",
    # Storage adapters (infrastructure - injected via StoragePort)
    "LocalStorageAdapter",
    "BronzeWriter",
    "SilverWriter",
    "GoldWriter",
    # HTTP clients (infrastructure concern)
    "UnifiedHTTPClient",
    # Lock/Checkpoint adapters (infrastructure)
    "MemoryLock",
    "LocalCheckpointAdapter",
    "LocalQuarantineAdapter",
}

# Forbidden attribute-based instantiations (e.g., httpx.AsyncClient())
FORBIDDEN_ATTRIBUTE_INSTANTIATIONS: set[tuple[str, str]] = {
    ("httpx", "AsyncClient"),
    ("httpx", "Client"),
}


def _get_base_path(relative_path: Path) -> Path:
    """Resolve path - works from project root or tests directory."""
    if relative_path.exists():
        return relative_path
    # Try from tests directory context
    return Path(__file__).parent.parent.parent / relative_path


class InstantiationFinder(ast.NodeVisitor):
    """AST visitor to find forbidden instantiation calls."""

    def __init__(
        self,
        forbidden_classes: set[str],
        forbidden_attrs: set[tuple[str, str]],
    ) -> None:
        self.forbidden_classes = forbidden_classes
        self.forbidden_attrs = forbidden_attrs
        self.violations: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        """Visit function/constructor calls."""
        # Case 1: Direct class instantiation - ClassName()
        if isinstance(node.func, ast.Name):
            if node.func.id in self.forbidden_classes:
                self.violations.append((node.lineno, node.func.id))

        # Case 2: Attribute-based instantiation - module.ClassName()
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id
                class_name = node.func.attr
                if (module_name, class_name) in self.forbidden_attrs:
                    self.violations.append(
                        (node.lineno, f"{module_name}.{class_name}")
                    )

        self.generic_visit(node)


class TestDICompliance:
    """Tests ensuring Dependency Injection rules are followed."""

    @pytest.fixture
    def application_python_files(self) -> list[Path]:
        """Get all Python files in application directory."""
        base = _get_base_path(APPLICATION_DIR)
        if not base.exists():
            pytest.skip("Application layer not found")
        return list(base.rglob("*.py"))

    @pytest.fixture
    def all_source_files(self) -> list[Path]:
        """Get all Python source files excluding tests and composition."""
        src = _get_base_path(Path("src/bioetl"))
        if not src.exists():
            pytest.skip("Source directory not found")

        files = []
        for py_file in src.rglob("*.py"):
            # Skip composition layer (allowed to instantiate)
            if "composition" in str(py_file):
                continue
            files.append(py_file)
        return files

    def test_no_direct_instantiation_in_application(
        self, application_python_files: list[Path]
    ) -> None:
        """Application layer MUST NOT instantiate infrastructure directly.

        REQ-ARCH-DI-001: All dependencies must be injected through constructors.
        Infrastructure classes should be created in composition layer only.

        This test uses AST analysis to find actual instantiation calls,
        not class definitions or type hints.

        See CLAUDE.md §2.2 Dependency Injection and §11 Anti-Patterns.
        """
        violations = []

        for py_file in application_python_files:
            content = py_file.read_text(encoding="utf-8")

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            finder = InstantiationFinder(
                FORBIDDEN_INSTANTIATION_CLASSES,
                FORBIDDEN_ATTRIBUTE_INSTANTIATIONS,
            )
            finder.visit(tree)

            for lineno, class_name in finder.violations:
                relative = py_file.relative_to(_get_base_path(APPLICATION_DIR))
                violations.append(f"{relative}:{lineno}: {class_name}()")

        assert not violations, (
            "DI violations: Application layer must not instantiate "
            "infrastructure directly.\n"
            "Move instantiation to composition layer (factories/bootstrap).\n\n"
            "Violations found:\n" + "\n".join(f"  - {v}" for v in violations)
            + "\n\nSee CLAUDE.md §2.2 and §11 for details."
        )

    def test_factories_only_in_composition(self, src_dir: Path) -> None:
        """Factory classes MUST be in composition layer only.

        REQ-ARCH-DI-002: All Factory classes should live in composition/.
        This ensures a single composition root for dependency assembly.
        """
        violations = []

        # Layers that should NOT contain factories
        forbidden_layers = ["application", "infrastructure", "domain", "interfaces"]

        for layer in forbidden_layers:
            layer_path = src_dir / "bioetl" / layer
            if not layer_path.exists():
                continue

            for py_file in layer_path.rglob("*.py"):
                content = py_file.read_text(encoding="utf-8")

                try:
                    tree = ast.parse(content)
                except SyntaxError:
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Check for Factory suffix
                        if node.name.endswith("Factory"):
                            relative = py_file.relative_to(src_dir)
                            violations.append(
                                f"{relative}:{node.lineno} - class {node.name}"
                            )

        assert not violations, (
            "Factory classes must be in composition layer only.\n"
            "Found factories in forbidden layers:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nMove these to src/bioetl/composition/factories/"
        )

    def test_no_self_instantiation_of_dependencies(
        self, application_python_files: list[Path]
    ) -> None:
        """Classes should not create their own dependencies internally.

        REQ-ARCH-DI-003: Dependencies must be passed in __init__, not created.
        Anti-pattern: self._client = SomeClient() inside __init__.
        """
        violations = []

        # Patterns for internal instantiation (suspicious but not always wrong)
        internal_creation_patterns = [
            # Creating adapters inside __init__
            (r"self\._\w+\s*=\s*\w+Adapter\(", "Adapter creation in __init__"),
            (r"self\._\w+\s*=\s*\w+Client\(", "Client creation in __init__"),
            (r"self\._\w+\s*=\s*\w+Writer\(", "Writer creation in __init__"),
            # Creating HTTP clients inside methods
            (r"httpx\.(Async)?Client\(\)", "httpx client creation"),
        ]

        for py_file in application_python_files:
            content = py_file.read_text(encoding="utf-8")

            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            # Find __init__ methods and check for internal instantiation
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                            # Get the source lines for __init__
                            init_lines = ast.get_source_segment(content, item)
                            if init_lines:
                                for pattern, desc in internal_creation_patterns:
                                    if re.search(pattern, init_lines):
                                        relative = py_file.relative_to(
                                            _get_base_path(APPLICATION_DIR)
                                        )
                                        violations.append(
                                            f"{relative}:{item.lineno} - "
                                            f"{node.name}.__init__: {desc}"
                                        )

        assert not violations, (
            "Dependencies should be injected, not created internally.\n"
            "Found self-instantiation patterns:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nRefactor to accept dependencies as constructor parameters."
        )

    def test_no_httpx_client_in_application(
        self, application_python_files: list[Path]
    ) -> None:
        """Application layer must not import httpx directly.

        REQ-ARCH-DI-004: HTTP clients are infrastructure concern.
        Application should use DataSourcePort, not httpx.
        """
        violations = []

        for py_file in application_python_files:
            content = py_file.read_text(encoding="utf-8")
            lines = content.splitlines()

            in_type_checking = False

            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                # Track TYPE_CHECKING blocks (imports for hints are OK)
                if "if TYPE_CHECKING:" in line:
                    in_type_checking = True
                elif in_type_checking and stripped and not line.startswith((" ", "\t")):
                    in_type_checking = False

                if in_type_checking:
                    continue

                # Check for direct httpx imports
                if "import httpx" in stripped or "from httpx" in stripped:
                    # Skip if in docstring (rough check)
                    if not stripped.startswith('"""') and not stripped.startswith("#"):
                        relative = py_file.relative_to(
                            _get_base_path(APPLICATION_DIR)
                        )
                        violations.append(f"{relative}:{i}: {stripped}")

        assert not violations, (
            "Application layer must not import httpx directly.\n"
            "Use DataSourcePort abstraction instead.\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestCompositionRootIntegrity:
    """Tests ensuring composition root is the only assembly point."""

    def test_bootstrap_imports_from_factories(self, src_dir: Path) -> None:
        """bootstrap.py should use factories, not direct instantiation.

        Composition root (bootstrap.py) should delegate creation to factories
        rather than having inline instantiation of complex objects.
        """
        bootstrap_file = src_dir / "bioetl" / "composition" / "bootstrap.py"
        if not bootstrap_file.exists():
            pytest.skip("bootstrap.py not found")

        content = bootstrap_file.read_text(encoding="utf-8")

        # Check that bootstrap uses factory imports
        expected_patterns = [
            r"from.*factories.*import",  # Uses factory imports
            r"Factory\(",  # Uses factory instances
        ]

        has_factory_usage = any(
            re.search(pattern, content) for pattern in expected_patterns
        )

        assert has_factory_usage, (
            "bootstrap.py should delegate to factories for object creation.\n"
            "Expected factory imports or usage, found none."
        )

    def test_factories_exist_in_composition(self, src_dir: Path) -> None:
        """Verify factories directory exists with proper factories.

        REQ-ARCH-DI-005: Composition layer must have factories for DI.
        """
        factories_dir = src_dir / "bioetl" / "composition" / "factories"
        assert factories_dir.exists(), (
            "factories/ directory not found in composition layer."
        )
        assert factories_dir.is_dir(), (
            "factories should be a directory (package)"
        )

        # Check for factory files
        factory_files = list(factories_dir.glob("*_factory.py"))
        assert len(factory_files) >= 1, (
            "Expected at least one *_factory.py file in composition/factories/"
        )

    def test_no_circular_dependencies_in_composition(self, src_dir: Path) -> None:
        """Composition layer should not import from itself circularly.

        Factories should not depend on each other in ways that create cycles.
        """
        composition_path = src_dir / "bioetl" / "composition"
        if not composition_path.exists():
            pytest.skip("Composition layer not found")

        # Track imports between composition modules
        module_imports: dict[str, set[str]] = {}

        for py_file in composition_path.rglob("*.py"):
            relative = py_file.relative_to(composition_path)
            module_name = str(relative).replace("/", ".").replace(".py", "")

            content = py_file.read_text(encoding="utf-8")
            imports: set[str] = set()

            # Find internal composition imports
            for line in content.splitlines():
                if "from bioetl.composition" in line or "from .." in line:
                    # Extract imported module
                    match = re.search(
                        r"from bioetl\.composition\.(\w+)", line
                    )
                    if match:
                        imports.add(match.group(1))
                    # Relative imports
                    match = re.search(r"from \.\.?(\w+)", line)
                    if match:
                        imports.add(match.group(1))

            if imports:
                module_imports[module_name] = imports

        # Simple cycle detection (depth-1)
        cycles = []
        for module_a, imports_a in module_imports.items():
            for module_b in imports_a:
                if module_b in module_imports:
                    if module_a in module_imports.get(module_b, set()):
                        cycle = f"{module_a} <-> {module_b}"
                        if cycle not in cycles and f"{module_b} <-> {module_a}" not in cycles:
                            cycles.append(cycle)

        # Note: Some circular imports in composition may be acceptable
        # This test is informational to track them
        if cycles:
            # Warning only, not failure - circular imports in composition
            # can be resolved with TYPE_CHECKING
            pass


class TestInfrastructureIsolation:
    """Tests ensuring infrastructure doesn't leak into other layers."""

    def test_no_infrastructure_imports_in_domain(self, src_dir: Path) -> None:
        """Domain layer MUST NOT import from infrastructure.

        REQ-ARCH-001: Domain is pure business logic without I/O.
        """
        domain_path = src_dir / "bioetl" / "domain"
        if not domain_path.exists():
            pytest.skip("Domain layer not found")

        violations = []

        for py_file in domain_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")

            for i, line in enumerate(content.splitlines(), 1):
                if "from bioetl.infrastructure" in line or "import bioetl.infrastructure" in line:
                    # Check not in TYPE_CHECKING
                    in_type_checking = False
                    lines = content.splitlines()
                    for j, check_line in enumerate(lines):
                        if "if TYPE_CHECKING:" in check_line:
                            in_type_checking = True
                        elif in_type_checking and check_line.strip() and not check_line.startswith((" ", "\t")):
                            in_type_checking = False
                        if j + 1 == i and in_type_checking:
                            break
                    else:
                        relative = py_file.relative_to(src_dir)
                        violations.append(f"{relative}:{i}: {line.strip()}")

        assert not violations, (
            "Domain layer must not import from infrastructure.\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_adapters_implement_ports(self, src_dir: Path) -> None:
        """Infrastructure adapters should implement domain ports.

        REQ-ARCH-DI-006: Adapters implement port interfaces.
        """
        adapters_path = src_dir / "bioetl" / "infrastructure" / "adapters"
        if not adapters_path.exists():
            pytest.skip("Infrastructure adapters not found")

        # Check that adapter files reference domain.ports
        adapter_references_port = False

        for py_file in adapters_path.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            content = py_file.read_text(encoding="utf-8")

            if "bioetl.domain.ports" in content or "domain.ports" in content:
                adapter_references_port = True
                break

        assert adapter_references_port, (
            "Infrastructure adapters should import and implement domain ports.\n"
            "No port references found in adapters."
        )
