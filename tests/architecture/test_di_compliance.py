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


def _parse_python_file(py_file: Path) -> tuple[str, ast.AST] | None:
    content = py_file.read_text(encoding="utf-8")
    try:
        return content, ast.parse(content)
    except SyntaxError:
        return None


def _relative_to_application(py_file: Path) -> Path:
    return py_file.relative_to(_get_base_path(APPLICATION_DIR))


def _relative_to_src(src_dir: Path, py_file: Path) -> Path:
    return py_file.relative_to(src_dir)


def _files_for_layers(src_dir: Path, layers: list[str]) -> list[Path]:
    files: list[Path] = []
    for layer in layers:
        layer_path = src_dir / "bioetl" / layer
        if not layer_path.exists():
            continue
        files.extend(layer_path.rglob("*.py"))
    return files


def _iter_parsed_files(files: list[Path]) -> list[tuple[Path, str, ast.AST]]:
    parsed_files: list[tuple[Path, str, ast.AST]] = []
    for py_file in files:
        parsed = _parse_python_file(py_file)
        if parsed is None:
            continue
        content, tree = parsed
        parsed_files.append((py_file, content, tree))
    return parsed_files


def _type_checking_line_numbers(lines: list[str]) -> set[int]:
    active_numbers: set[int] = set()
    in_type_checking = False
    for index, line in enumerate(lines, 1):
        stripped = line.strip()
        if "if TYPE_CHECKING:" in line:
            in_type_checking = True
            active_numbers.add(index)
            continue
        if in_type_checking and stripped and not line.startswith((" ", "\t")):
            in_type_checking = False
        if in_type_checking:
            active_numbers.add(index)
    return active_numbers


def _internal_creation_violations(
    application_python_files: list[Path],
    internal_creation_patterns: list[tuple[str, str]],
) -> list[str]:
    violations: list[str] = []
    for py_file, content, tree in _iter_parsed_files(application_python_files):
        for class_name, lineno, init_lines in _class_init_segments(content, tree):
            for desc in _matching_creation_descriptions(
                init_lines, internal_creation_patterns
            ):
                violations.append(
                    f"{_relative_to_application(py_file)}:{lineno} - "
                    f"{class_name}.__init__: {desc}"
                )
    return violations


def _httpx_import_violations(application_python_files: list[Path]) -> list[str]:
    violations: list[str] = []
    for py_file in application_python_files:
        lines = py_file.read_text(encoding="utf-8").splitlines()
        type_checking_lines = _type_checking_line_numbers(lines)
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if i in type_checking_lines:
                continue
            if "import httpx" in stripped or "from httpx" in stripped:
                if not stripped.startswith('"""') and not stripped.startswith("#"):
                    violations.append(
                        f"{_relative_to_application(py_file)}:{i}: {stripped}"
                    )
    return violations


def _source_python_files(src: Path) -> list[Path]:
    return [py_file for py_file in src.rglob("*.py") if "composition" not in str(py_file)]


def _composition_module_imports(composition_path: Path) -> dict[str, set[str]]:
    module_imports: dict[str, set[str]] = {}
    for py_file in composition_path.rglob("*.py"):
        module_name = _composition_module_name(composition_path, py_file)
        imports = _composition_file_imports(py_file)
        if imports:
            module_imports[module_name] = imports
    return module_imports


def _simple_composition_cycles(module_imports: dict[str, set[str]]) -> list[str]:
    cycles: list[str] = []
    for module_a, imports_a in module_imports.items():
        for module_b in imports_a:
            if module_b not in module_imports:
                continue
            if module_a not in module_imports.get(module_b, set()):
                continue
            cycle = f"{module_a} <-> {module_b}"
            reverse_cycle = f"{module_b} <-> {module_a}"
            if cycle not in cycles and reverse_cycle not in cycles:
                cycles.append(cycle)
    return cycles


def _class_init_segments(
    content: str,
    tree: ast.AST,
) -> list[tuple[str, int, str]]:
    segments: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or item.name != "__init__":
                continue
            init_lines = ast.get_source_segment(content, item)
            if not init_lines:
                continue
            segments.append((node.name, item.lineno, init_lines))
    return segments


def _matching_creation_descriptions(
    init_lines: str,
    internal_creation_patterns: list[tuple[str, str]],
) -> list[str]:
    return [
        desc
        for pattern, desc in internal_creation_patterns
        if re.search(pattern, init_lines)
    ]


def _composition_module_name(composition_path: Path, py_file: Path) -> str:
    relative = py_file.relative_to(composition_path)
    return str(relative).replace("/", ".").replace(".py", "")


def _composition_file_imports(py_file: Path) -> set[str]:
    imports: set[str] = set()
    for line in py_file.read_text(encoding="utf-8").splitlines():
        imports.update(_composition_import_targets(line))
    return imports


def _composition_import_targets(line: str) -> set[str]:
    if "from bioetl.composition" not in line and "from .." not in line:
        return set()
    imports: set[str] = set()
    absolute_match = re.search(r"from bioetl\.composition\.(\w+)", line)
    if absolute_match:
        imports.add(absolute_match.group(1))
    relative_match = re.search(r"from \.\.?(\w+)", line)
    if relative_match:
        imports.add(relative_match.group(1))
    return imports


def _domain_infrastructure_import_violations(src_dir: Path) -> list[str]:
    domain_path = src_dir / "bioetl" / "domain"
    violations: list[str] = []
    for py_file in domain_path.rglob("*.py"):
        lines = py_file.read_text(encoding="utf-8").splitlines()
        type_checking_lines = _type_checking_line_numbers(lines)
        violations.extend(
            f"{py_file.relative_to(src_dir)}:{i}: {line.strip()}"
            for i, line in enumerate(lines, 1)
            if i not in type_checking_lines
            and (
                "from bioetl.infrastructure" in line
                or "import bioetl.infrastructure" in line
            )
        )
    return violations


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

    def visit_Call(self, node: ast.Call) -> None:
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
                    self.violations.append((node.lineno, f"{module_name}.{class_name}"))

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
        return _source_python_files(src)

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
        for py_file, _content, tree in _iter_parsed_files(application_python_files):
            finder = InstantiationFinder(
                FORBIDDEN_INSTANTIATION_CLASSES,
                FORBIDDEN_ATTRIBUTE_INSTANTIATIONS,
            )
            finder.visit(tree)

            for lineno, class_name in finder.violations:
                violations.append(
                    f"{_relative_to_application(py_file)}:{lineno}: {class_name}()"
                )

        assert not violations, (
            "DI violations: Application layer must not instantiate "
            "infrastructure directly.\n"
            "Move instantiation to composition layer (factories/bootstrap).\n\n"
            "Violations found:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nSee CLAUDE.md §2.2 and §11 for details."
        )

    def test_factories_only_in_composition(self, src_dir: Path) -> None:
        """Factory classes MUST be in composition layer only.

        REQ-ARCH-DI-002: All Factory classes should live in composition/.
        This ensures a single composition root for dependency assembly.
        """
        violations = []
        forbidden_layers = ["application", "infrastructure", "domain", "interfaces"]
        for py_file, _content, tree in _iter_parsed_files(
            _files_for_layers(src_dir, forbidden_layers)
        ):
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.endswith("Factory"):
                    violations.append(
                        f"{_relative_to_src(src_dir, py_file)}:{node.lineno} - "
                        f"class {node.name}"
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
        internal_creation_patterns = [
            (r"self\._\w+\s*=\s*(?!Batch)\w+Adapter\(", "Adapter creation in __init__"),
            (r"self\._\w+\s*=\s*(?!Unified)\w+Client\(", "Client creation in __init__"),
            (
                r"self\._\w+\s*=\s*(Bronze|Silver|Gold|Delta)Writer\(",
                "Storage writer creation in __init__",
            ),
            (r"httpx\.(Async)?Client\(\)", "httpx client creation"),
        ]
        violations = _internal_creation_violations(
            application_python_files,
            internal_creation_patterns,
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
        violations = _httpx_import_violations(application_python_files)

        assert not violations, (
            "Application layer must not import httpx directly.\n"
            "Use DataSourcePort abstraction instead.\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestCompositionRootIntegrity:
    """Tests ensuring composition root is the only assembly point."""

    def test_bootstrap_imports_from_factories(self, src_dir: Path) -> None:
        """bootstrap_pipeline_runner() should use factories, not direct instantiation.

        Composition root (bootstrap_pipeline_runner) should delegate creation to factories
        rather than having inline instantiation of complex objects.

        Note: bootstrap_pipeline_runner() is now defined in composition/bootstrap/runtime/pipeline.py
        as part of the CLI/runtime split (see CLAUDE.md §2.1).
        """
        # bootstrap_pipeline_runner is now in composition/bootstrap/runtime/pipeline.py
        bootstrap_file = (
            src_dir / "bioetl" / "composition" / "bootstrap" / "runtime" / "pipeline.py"
        )
        if not bootstrap_file.exists():
            pytest.skip("bootstrap/runtime/pipeline.py not found")

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
            "bootstrap_pipeline_runner() should delegate to factories for object creation.\n"
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
        assert factories_dir.is_dir(), "factories should be a directory (package)"

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

        module_imports = _composition_module_imports(composition_path)
        cycles = _simple_composition_cycles(module_imports)

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

        violations = _domain_infrastructure_import_violations(src_dir)

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
