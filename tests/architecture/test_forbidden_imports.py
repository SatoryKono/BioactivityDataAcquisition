"""Architecture tests: Forbidden imports and framework isolation.

These tests verify that certain frameworks and modules are only used
in appropriate layers:
- External orchestration frameworks are not imported in application layer
- Metrics server initialization only in composition
- Ports imported only from facade module
- Legacy normalizers module must not be re-introduced (RF-043)

REQ-ARCH-APP-001: External orchestration frameworks must not be used in application layer.
REQ-ARCH-OBS-001: Observability initialization only in composition root.
REQ-ARCH-027: Port protocols must be imported from the facade, with the
sanctioned ``bioetl.domain.ports.noop`` sub-facade for operational null objects.
RF-043: legacy_normalizers path is permanently forbidden.

See CLAUDE.md §2.1 Matrix of Imports and §11 Anti-Patterns.
"""

from __future__ import annotations

import pytest

import ast
import os
import re
from pathlib import Path


pytestmark = pytest.mark.architecture


def _python_files(path: Path, *, skip_private: bool = False) -> list[Path]:
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(path):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in {"__pycache__", ".worktrees"}
        ]
        current_path = Path(current_root)
        for filename in filenames:
            if filename.endswith(".py"):
                files.append(current_path / filename)
    files.sort()
    if skip_private:
        files = [py_file for py_file in files if not py_file.name.startswith("_")]
    return files


def _read_file(py_file: Path) -> str:
    return py_file.read_text(encoding="utf-8")


def _parse_file(py_file: Path) -> ast.AST:
    return ast.parse(_read_file(py_file))


def _relative(src_dir: Path, py_file: Path) -> Path:
    return py_file.relative_to(src_dir)


def _interfaces_path(src_dir: Path) -> Path:
    interfaces_path = src_dir / "bioetl" / "interfaces"
    assert interfaces_path.exists(), "Interfaces layer not found"
    return interfaces_path


def _module_import_violations(
    py_file: Path,
    src_dir: Path,
    *,
    exact_modules: set[str] | None = None,
    startswith_modules: tuple[str, ...] = (),
) -> list[str]:
    """Check for violations of module imports."""
    exact_modules = exact_modules or set()
    violations: list[str] = []
    tree = _parse_file(py_file)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            _check_import_from(
                node, py_file, src_dir, exact_modules, startswith_modules, violations
            )
        elif isinstance(node, ast.Import):
            _check_import(
                node, py_file, src_dir, exact_modules, startswith_modules, violations
            )

    return violations


def _check_import_from(
    node: ast.ImportFrom,
    py_file: Path,
    src_dir: Path,
    exact_modules: set[str],
    startswith_modules: tuple[str, ...],
    violations: list[str],
) -> None:
    """Check ImportFrom node for violations."""
    module = node.module
    if module is None:
        return
    if module in exact_modules or module.startswith(startswith_modules):
        violations.append(f"{_relative(src_dir, py_file)}:{node.lineno}")


def _check_import(
    node: ast.Import,
    py_file: Path,
    src_dir: Path,
    exact_modules: set[str],
    startswith_modules: tuple[str, ...],
    violations: list[str],
) -> None:
    """Check Import node for violations."""
    for alias in node.names:
        module = alias.name
        if module in exact_modules or module.startswith(startswith_modules):
            violations.append(f"{_relative(src_dir, py_file)}:{node.lineno}")


def _composition_module_violations(
    py_file: Path,
    src_dir: Path,
    *,
    allowed_modules: set[str],
) -> list[str]:
    """Check for violations of composition module imports."""
    violations: list[str] = []
    tree = _parse_file(py_file)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            _check_composition_import_from(
                node, py_file, src_dir, allowed_modules, violations
            )
        elif isinstance(node, ast.Import):
            _check_composition_import(
                node, py_file, src_dir, allowed_modules, violations
            )

    return violations


def _check_composition_import_from(
    node: ast.ImportFrom,
    py_file: Path,
    src_dir: Path,
    allowed_modules: set[str],
    violations: list[str],
) -> None:
    """Check ImportFrom node for composition violations."""
    module = node.module
    if module is not None and module.startswith("bioetl.composition."):
        if module not in allowed_modules:
            violations.append(
                f"{_relative(src_dir, py_file)}:{node.lineno} -> {module}"
            )


def _check_composition_import(
    node: ast.Import,
    py_file: Path,
    src_dir: Path,
    allowed_modules: set[str],
    violations: list[str],
) -> None:
    """Check Import node for composition violations."""
    for alias in node.names:
        module = alias.name
        if module.startswith("bioetl.composition."):
            if module not in allowed_modules:
                violations.append(
                    f"{_relative(src_dir, py_file)}:{node.lineno} -> {module}"
                )


def _is_forbidden_port_import_target(module_name: str) -> bool:
    """Return True for non-sanctioned port submodule imports.

    Public imports must go through ``bioetl.domain.ports``. The only sanctioned
    sub-facade is ``bioetl.domain.ports.noop`` for null-object helpers.
    """
    if not module_name.startswith("bioetl.domain.ports."):
        return False
    return module_name != "bioetl.domain.ports.noop"


def _iter_metrics_server_call_violations(src_dir: Path) -> list[str]:
    """Collect forbidden start_metrics_server invocations outside composition."""
    forbidden_layers = ("interfaces", "application", "domain")
    allowed_patterns = (
        r"def start_metrics_server",
        r"from.*import.*start_metrics_server",
        r"#.*start_metrics_server",
        r"\"\"\".*start_metrics_server",
        r"maybe_start_metrics_server",
    )
    violations: list[str] = []

    for layer in forbidden_layers:
        layer_path = src_dir / "bioetl" / layer
        if not layer_path.exists():
            continue
        for py_file in _python_files(layer_path):
            violations.extend(
                _iter_file_metrics_server_call_violations(
                    py_file,
                    src_dir,
                    allowed_patterns=allowed_patterns,
                )
            )
    return violations


def _port_import_violations(layer_path: Path, src_dir: Path) -> list[str]:
    """Collect imports of forbidden deep port modules for a single layer."""
    violations: list[str] = []
    for py_file in _python_files(layer_path):
        tree = _parse_file(py_file)
        relative_path = _relative(src_dir, py_file)
        if relative_path.parts[:3] == ("bioetl", "domain", "ports"):
            continue
        violations.extend(_port_import_violations_for_tree(relative_path, tree))
    return violations


def _port_import_violations_for_tree(
    relative_path: Path,
    tree: ast.AST,
) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        violations.extend(_port_import_violations_for_node(relative_path, node))
    return violations


def _port_import_violations_for_node(
    relative_path: Path,
    node: ast.AST,
) -> list[str]:
    if isinstance(node, ast.Import):
        return _import_node_port_violations(relative_path, node)
    if isinstance(node, ast.ImportFrom) and node.module:
        return _import_from_port_violations(relative_path, node)
    return []


def _import_node_port_violations(
    relative_path: Path,
    node: ast.Import,
) -> list[str]:
    return [
        f"{relative_path}:{node.lineno} imports {alias.name}"
        for alias in node.names
        if _is_forbidden_port_import_target(alias.name)
    ]


def _import_from_port_violations(
    relative_path: Path,
    node: ast.ImportFrom,
) -> list[str]:
    if not _is_forbidden_port_import_target(node.module or ""):
        return []
    return [f"{relative_path}:{node.lineno} imports from {node.module}"]


def _iter_file_metrics_server_call_violations(
    py_file: Path,
    src_dir: Path,
    *,
    allowed_patterns: tuple[str, ...],
) -> list[str]:
    relative_path = _relative(src_dir, py_file)
    return [
        f"{relative_path}:{line_number} - {line.strip()}"
        for line_number, line in enumerate(_read_file(py_file).splitlines(), 1)
        if _is_forbidden_metrics_server_call_line(line, allowed_patterns)
    ]


def _is_forbidden_metrics_server_call_line(
    line: str,
    allowed_patterns: tuple[str, ...],
) -> bool:
    if "start_metrics_server(" not in line:
        return False
    return not any(re.search(pattern, line) for pattern in allowed_patterns)


class TestLocalOnlyPolicy:
    """Tests enforcing the Local-Only Architecture (ADR-010)."""

    def test_no_cloud_or_distributed_libs(self, src_dir: Path) -> None:
        """Verify no usage of cloud SDKs or distributed systems clients.

        REQ-ARCH-010: The system must run entirely locally without external
        dependencies like S3, Redis, Kafka, or cloud provider APIs.
        """
        # List of forbidden packages/modules
        forbidden_libs = [
            # Cloud SDKs
            "boto3",
            "botocore",
            "s3fs",
            "minio",
            "azure",
            "azure.storage",
            "azure.identity",
            "google.cloud",
            "google.storage",
            # Distributed Systems
            "redis",
            "aioredis",
            "upstash",
            "kafka",
            "confluent_kafka",
            "aiokafka",
            "celery",
            "dask.distributed",
        ]

        # Scan the entire bioetl package
        source_path = src_dir / "bioetl"
        assert source_path.exists(), "Source directory not found"

        violations = []

        for py_file in _python_files(source_path):
            content = _read_file(py_file)

            for lib in forbidden_libs:
                # Check for various import forms:
                # import boto3
                # from boto3 import ...
                patterns = [
                    f"import {lib}",
                    f"from {lib}",
                ]

                for pattern in patterns:
                    # Simple check - could be improved with AST if false positives occur
                    # but these libs are distinct enough.
                    if re.search(r"^" + pattern + r"\b", content, re.MULTILINE):
                        violations.append(
                            f"{_relative(src_dir, py_file)}: imports '{lib}'"
                        )

        assert not violations, (
            "Violation of Local-Only Architecture (ADR-010).\n"
            "Cloud SDKs and distributed system clients are STRICTLY PROHIBITED.\n"
            "Use local filesystem (pathlib), SQLite, or internal memory structures.\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestOrchestrationIsolation:
    """Tests ensuring orchestration frameworks are properly isolated."""

    def test_application_layer_no_orchestration_imports(self, src_dir: Path) -> None:
        """Application layer must not import external orchestration frameworks.

        REQ-ARCH-APP-001: External workflow frameworks (Celery, Airflow, etc.)
        must not be imported in application layer. BioETL uses its own
        lightweight PipelineRunner for orchestration.
        """
        application_path = src_dir / "bioetl" / "application"
        assert application_path.exists(), "Application layer not found"

        disallowed = ["prefect", "celery", "airflow", "dagster"]
        violations = []

        for py_file in _python_files(application_path):
            content = _read_file(py_file)
            for lib in disallowed:
                if f"from {lib}" in content or f"import {lib}" in content:
                    violations.append(f"{_relative(src_dir, py_file)}: imports {lib}")

        assert not violations, (
            "Application layer has direct orchestration imports:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nMove orchestration code to interfaces-layer command/runtime boundaries."
        )


class TestObservabilityInitialization:
    """Tests ensuring observability is initialized in correct layer."""

    def test_metrics_server_only_in_composition(self, src_dir: Path) -> None:
        """Verify start_metrics_server is only called from composition layer.

        REQ-ARCH-OBS-001: Observability initialization should only happen
        in the composition root to ensure single point of responsibility.
        """
        violations = _iter_metrics_server_call_violations(src_dir)

        assert not violations, (
            "start_metrics_server() should only be called from composition layer.\n"
            "Found calls in forbidden layers:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestPortImportFacade:
    """Tests ensuring ports are imported from the facade module."""

    def test_ports_imported_only_from_facade(self, src_dir: Path) -> None:
        """All layers MUST import contracts from sanctioned facades only.

        REQ-ARCH-027: Port protocols are accessible via ``bioetl.domain.ports``.
        Operational null objects are accessible via ``bioetl.domain.ports.noop``.
        Deeper internal modules remain forbidden to preserve clear public entry points.
        """
        violations = []
        for layer in [
            "application",
            "composition",
            "domain",
            "infrastructure",
            "interfaces",
        ]:
            layer_path = src_dir / "bioetl" / layer
            if not layer_path.exists():
                continue
            violations.extend(_port_import_violations(layer_path, src_dir))

        assert not violations, (
            "Ports must be imported only from sanctioned facades.\n"
            "Correct: from bioetl.domain.ports import SilverStoragePort\n"
            "Correct: from bioetl.domain.ports.noop import NoOpMetrics\n"
            "Wrong: from bioetl.domain.ports.runtime import ClockPort\n"
            "Wrong: import bioetl.domain.ports.storage as storage_ports\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestBootstrapAdapterIsolation:
    """Tests ensuring bootstrap doesn't directly import adapters."""

    def test_bootstrap_no_direct_adapter_imports(self, src_dir: Path) -> None:
        """bootstrap_pipeline_runner MUST NOT import concrete adapters directly.

        REQ-ARCH-COMP-001: Composition Root delegates adapter creation to factories.
        Adding a new provider should only require changes in:
        - providers/registration.py (ProviderRegistry)
        - factories/datasource/data_source_factory.py (get_data_source_creator / DataSourceFactory)

        This prevents tight coupling and ensures the factory pattern is enforced.

        Note: bootstrap_pipeline_runner() is now defined in composition/bootstrap/runtime/pipeline.py
        as part of the CLI/runtime split (see CLAUDE.md §2.1).
        """
        # bootstrap_pipeline_runner is now in composition/bootstrap/runtime/pipeline.py
        bootstrap_file = (
            src_dir / "bioetl" / "composition" / "bootstrap" / "runtime" / "pipeline.py"
        )
        assert bootstrap_file.exists(), "bootstrap/runtime/pipeline.py not found"

        content = bootstrap_file.read_text(encoding="utf-8")

        # Forbidden: direct imports of concrete adapter classes from provider packages
        # Pattern: from bioetl.infrastructure.adapters.{provider}.{module} import {Class}
        forbidden_patterns = [
            (
                r"from bioetl\.infrastructure\.adapters\.chembl\.\w+ import",
                "ChEMBL adapter",
            ),
            (
                r"from bioetl\.infrastructure\.adapters\.pubchem\.\w+ import",
                "PubChem adapter",
            ),
            (
                r"from bioetl\.infrastructure\.adapters\.uniprot\.\w+ import",
                "UniProt adapter",
            ),
            (
                r"from bioetl\.infrastructure\.adapters\.pubmed\.\w+ import",
                "PubMed adapter",
            ),
        ]

        violations = []
        for pattern, description in forbidden_patterns:
            matches = re.findall(pattern, content)
            if matches:
                violations.append(f"{description}: {matches}")

        assert not violations, (
            "bootstrap_pipeline_runner() must not import concrete adapters directly.\n"
            "Use ProviderRegistry and factories "
            "(DataSourceFactory, HttpClientFactory) instead.\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestInterfacesFilesystemAccess:
    """Tests ensuring interfaces layer doesn't access filesystem directly."""

    def test_interfaces_no_direct_filesystem_traversal(self, src_dir: Path) -> None:
        """Interfaces layer MUST NOT use direct filesystem traversal.

        REQ-ARCH-023: CLI delegates to storage ports, not Path.rglob.
        """
        interfaces_path = _interfaces_path(src_dir)

        forbidden_patterns = [
            r"\.rglob\(",
            r"\.glob\(",
            r"os\.walk\(",
            r"os\.listdir\(",
        ]

        errors = []
        for py_file in interfaces_path.rglob("*.py"):
            if py_file.name.startswith("_"):
                continue

            with py_file.open(encoding="utf-8") as f:
                content = f.read()

            for pattern in forbidden_patterns:
                if re.search(pattern, content):
                    relative_path = py_file.relative_to(src_dir)
                    errors.append(f"{relative_path}: contains '{pattern}'")

        assert not errors, (
            "Interfaces layer must not use direct filesystem traversal.\n"
            "Delegate to storage ports instead.\n"
            "Violations:\n" + "\n".join(f"  - {e}" for e in errors)
        )


class TestInterfacesBootstrapIsolation:
    """Tests ensuring interfaces layer doesn't import bootstrap directly."""

    def test_cli_no_bootstrap_import(self, src_dir: Path) -> None:
        """Interfaces layer MUST NOT import from bootstrap.py directly.

        REQ-ARCH-C1: Interfaces must use sanctioned composition public APIs,
        never composition.bootstrap directly.

        This separation ensures:
        - Clean layer boundaries (interfaces → composition public APIs → bootstrap)
        - Easier testing of CLI without full bootstrap machinery
        - Stable composition API seams with explicit ownership
        """
        interfaces_path = src_dir / "bioetl" / "interfaces"
        assert interfaces_path.exists(), "Interfaces layer not found"

        forbidden_patterns = [
            r"from bioetl\.composition\.bootstrap import",
            r"from bioetl\.composition\.bootstrap\s+import",
            r"import bioetl\.composition\.bootstrap",
        ]

        violations = []
        for py_file in _python_files(interfaces_path):
            content = _read_file(py_file)
            for pattern in forbidden_patterns:
                if re.search(pattern, content):
                    violations.append(
                        f"{_relative(src_dir, py_file)}: imports from bootstrap directly"
                    )
                    break

        assert not violations, (
            "Interfaces layer must not import from bootstrap.py directly.\n"
            "Use sanctioned composition public APIs instead.\n\n"
            "Correct:\n"
            "  from bioetl.composition.execution_api import create_pipeline_runner\n\n"
            "Wrong:\n"
            "  from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_interfaces_no_direct_entrypoints_imports(self, src_dir: Path) -> None:
        """Interfaces must consume narrow composition APIs, not entrypoints façade."""
        violations: list[str] = []
        for py_file in _python_files(_interfaces_path(src_dir)):
            violations.extend(
                _module_import_violations(
                    py_file,
                    src_dir,
                    exact_modules={"bioetl.composition.entrypoints"},
                )
            )

        assert not violations, (
            "Interfaces layer must not import bioetl.composition.entrypoints.\n"
            "Use sanctioned modules such as:\n"
            "  - bioetl.composition.execution_api\n"
            "  - bioetl.composition.registry_api\n"
            "  - bioetl.composition.control_plane_api\n"
            "  - bioetl.composition.health_api\n"
            "  - bioetl.composition.maintenance_api\n"
            "  - bioetl.composition.composite_api\n"
            "  - bioetl.composition.observability_api\n\n"
            "Violations:\n" + "\n".join(f"  - {item}" for item in violations)
        )

    def test_interfaces_no_direct_composition_root_imports(self, src_dir: Path) -> None:
        """Interfaces must use specialized composition APIs instead of package root imports."""
        violations: list[str] = []
        for py_file in _python_files(_interfaces_path(src_dir)):
            violations.extend(
                _module_import_violations(
                    py_file,
                    src_dir,
                    exact_modules={"bioetl.composition"},
                )
            )

        assert not violations, (
            "Interfaces layer must not import the bioetl.composition package root.\n"
            "Use specialized public APIs instead:\n"
            "  - bioetl.composition.execution_api\n"
            "  - bioetl.composition.registry_api\n"
            "  - bioetl.composition.control_plane_api\n"
            "  - bioetl.composition.health_api\n"
            "  - bioetl.composition.maintenance_api\n"
            "  - bioetl.composition.composite_api\n"
            "  - bioetl.composition.observability_api\n\n"
            "Violations:\n" + "\n".join(f"  - {item}" for item in violations)
        )

    def test_interfaces_no_direct_services_api_imports(self, src_dir: Path) -> None:
        """Interfaces must consume narrow service APIs instead of services_api."""
        violations: list[str] = []
        for py_file in _python_files(_interfaces_path(src_dir)):
            violations.extend(
                _module_import_violations(
                    py_file,
                    src_dir,
                    exact_modules={"bioetl.composition.services_api"},
                )
            )

        assert not violations, (
            "Interfaces layer must not import bioetl.composition.services_api.\n"
            "Use narrow public APIs instead:\n"
            "  - bioetl.composition.execution_api\n"
            "  - bioetl.composition.control_plane_api\n"
            "  - bioetl.composition.health_api\n"
            "  - bioetl.composition.maintenance_api\n"
            "  - bioetl.composition.registry_api\n"
            "  - bioetl.composition.composite_api\n"
            "  - bioetl.composition.observability_api\n\n"
            "Violations:\n" + "\n".join(f"  - {item}" for item in violations)
        )

    def test_interfaces_no_direct_resources_api_imports(self, src_dir: Path) -> None:
        """Interfaces must consume owner-focused APIs instead of resources_api."""
        violations: list[str] = []
        for py_file in _python_files(_interfaces_path(src_dir)):
            violations.extend(
                _module_import_violations(
                    py_file,
                    src_dir,
                    exact_modules={"bioetl.composition.resources_api"},
                )
            )

        assert not violations, (
            "Interfaces layer must not import bioetl.composition.resources_api.\n"
            "Use owner-focused public APIs instead:\n"
            "  - bioetl.composition.control_plane_api\n"
            "  - bioetl.composition.health_api\n"
            "  - bioetl.composition.maintenance_api\n\n"
            "Violations:\n" + "\n".join(f"  - {item}" for item in violations)
        )

    def test_interfaces_no_direct_registry_internal_imports(
        self, src_dir: Path
    ) -> None:
        """Interfaces must consume registry_api instead of registry internals."""
        forbidden_modules = {
            "bioetl.composition.registry",
        }
        violations: list[str] = []
        for py_file in _python_files(_interfaces_path(src_dir)):
            violations.extend(
                _module_import_violations(
                    py_file,
                    src_dir,
                    exact_modules=forbidden_modules,
                )
            )

        assert not violations, (
            "Interfaces layer must not import composition registry internals.\n"
            "Use bioetl.composition.registry_api instead.\n\n"
            "Violations:\n" + "\n".join(f"  - {item}" for item in violations)
        )

    def test_interfaces_no_direct_composition_factories_imports(
        self, src_dir: Path
    ) -> None:
        """Interfaces must not import composition factories directly."""
        violations: list[str] = []
        for py_file in _python_files(_interfaces_path(src_dir)):
            violations.extend(
                _module_import_violations(
                    py_file,
                    src_dir,
                    startswith_modules=("bioetl.composition.factories",),
                )
            )

        assert not violations, (
            "Interfaces layer must not import composition factory internals.\n"
            "Use sanctioned public APIs such as bioetl.composition.registry_api.\n\n"
            "Violations:\n" + "\n".join(f"  - {item}" for item in violations)
        )

    def test_interfaces_composition_imports_stay_within_sanctioned_modules(
        self, src_dir: Path
    ) -> None:
        """Interfaces may import only the approved composition public API modules."""
        allowed_modules = {
            "bioetl.composition.composite_api",
            "bioetl.composition.control_plane_api",
            "bioetl.composition.execution_api",
            "bioetl.composition.health_api",
            "bioetl.composition.maintenance_api",
            "bioetl.composition.observability_api",
            "bioetl.composition.registry_api",
            # Internal composition modules used by interfaces for runtime access
            "bioetl.composition._resource_management",
            "bioetl.composition._service_protocols",
            "bioetl.composition._services",
            "bioetl.composition.runtime_builders.config_access",
        }
        violations: list[str] = []
        for py_file in _python_files(_interfaces_path(src_dir)):
            violations.extend(
                _composition_module_violations(
                    py_file,
                    src_dir,
                    allowed_modules=allowed_modules,
                )
            )

        assert not violations, (
            "Interfaces layer imported non-sanctioned composition modules.\n"
            "Allowed modules:\n"
            "  - bioetl.composition.composite_api\n"
            "  - bioetl.composition.control_plane_api\n"
            "  - bioetl.composition.execution_api\n"
            "  - bioetl.composition.health_api\n"
            "  - bioetl.composition.maintenance_api\n"
            "  - bioetl.composition.observability_api\n"
            "  - bioetl.composition.registry_api\n"
            "  - bioetl.composition._resource_management (internal runtime access)\n"
            "  - bioetl.composition._service_protocols (internal runtime access)\n"
            "  - bioetl.composition._services (internal runtime access)\n"
            "  - bioetl.composition.runtime_builders.config_access (internal runtime access)\n\n"
            "Violations:\n" + "\n".join(f"  - {item}" for item in violations)
        )


class TestLegacyNormalizersGuardrail:
    """RF-043: legacy_normalizers module must not be re-introduced.

    The legacy_normalizers path was removed; all normalisation now lives in
    ``infrastructure.config.source_normalizers``.  This guardrail prevents
    accidental re-introduction of the deleted module.
    """

    FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"legacy_normalizers"),
    )

    def test_no_legacy_normalizers_directory(self, src_dir: Path) -> None:
        """The legacy_normalizers directory must not exist."""
        forbidden = src_dir / "bioetl" / "infrastructure" / "legacy_normalizers"
        assert not forbidden.exists(), (
            f"RF-043 violation: {forbidden} must not exist.\n"
            "All normalisation belongs in infrastructure.config.source_normalizers."
        )

    def test_no_legacy_normalizers_imports(self, src_dir: Path) -> None:
        """No production code may reference legacy_normalizers."""
        violations: list[str] = []
        source_path = src_dir / "bioetl"

        for py_file in _python_files(source_path):
            try:
                content = _read_file(py_file)
            except (OSError, UnicodeDecodeError):
                continue
            for pattern in self.FORBIDDEN_PATTERNS:
                if pattern.search(content):
                    violations.append(str(_relative(src_dir, py_file)))
                    break

        assert not violations, (
            "RF-043 violation: legacy_normalizers references found in production code.\n"
            "Use bioetl.infrastructure.config.source_normalizers instead.\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )
