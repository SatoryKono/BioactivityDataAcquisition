"""Architecture tests: Forbidden imports and framework isolation.

These tests verify that certain frameworks and modules are only used
in appropriate layers:
- External orchestration frameworks are not imported in application layer
- Metrics server initialization only in composition
- Ports imported only from facade module

REQ-ARCH-APP-001: External orchestration frameworks must not be used in application layer.
REQ-ARCH-OBS-001: Observability initialization only in composition root.
REQ-ARCH-027: Ports must be imported from facade only.

See CLAUDE.md §2.1 Matrix of Imports and §11 Anti-Patterns.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


class TestOrchestrationIsolation:
    """Tests ensuring orchestration frameworks are properly isolated."""

    def test_application_layer_no_orchestration_imports(self, src_dir: Path) -> None:
        """Application layer must not import external orchestration frameworks.

        REQ-ARCH-APP-001: External workflow frameworks (Celery, Airflow, etc.)
        must not be imported in application layer. BioETL uses its own
        lightweight PipelineRunner for orchestration.
        """
        application_path = src_dir / "bioetl" / "application"
        if not application_path.exists():
            pytest.skip("Application layer not found")

        disallowed = ["prefect", "celery", "airflow", "dagster"]
        violations = []

        for py_file in application_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for lib in disallowed:
                if f"from {lib}" in content or f"import {lib}" in content:
                    violations.append(f"{py_file.relative_to(src_dir)}: imports {lib}")

        assert not violations, (
            "Application layer has direct orchestration imports:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nMove orchestration code to bioetl/interfaces/orchestration/"
        )


class TestObservabilityInitialization:
    """Tests ensuring observability is initialized in correct layer."""

    def test_metrics_server_only_in_composition(self, src_dir: Path) -> None:
        """Verify start_metrics_server is only called from composition layer.

        REQ-ARCH-OBS-001: Observability initialization should only happen
        in the composition root to ensure single point of responsibility.
        """
        forbidden_layers = ["interfaces", "application", "domain"]
        allowed_patterns = [
            r"def start_metrics_server",  # Definition is allowed
            r"from.*import.*start_metrics_server",  # Import is allowed
            r"#.*start_metrics_server",  # Comments are allowed
            r"\"\"\".*start_metrics_server",  # Docstrings are allowed
        ]

        violations = []

        for layer in forbidden_layers:
            layer_path = src_dir / "bioetl" / layer
            if not layer_path.exists():
                continue

            for py_file in layer_path.rglob("*.py"):
                with py_file.open(encoding="utf-8") as f:
                    content = f.read()
                    lines = content.splitlines()

                for i, line in enumerate(lines, 1):
                    # Check if line contains actual call to start_metrics_server
                    if "start_metrics_server(" in line:
                        # Skip if matches allowed patterns
                        if any(re.search(p, line) for p in allowed_patterns):
                            continue

                        relative_path = py_file.relative_to(src_dir)
                        violations.append(f"{relative_path}:{i} - {line.strip()}")

        assert not violations, (
            "start_metrics_server() should only be called from composition layer.\n"
            "Found calls in forbidden layers:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestPortImportFacade:
    """Tests ensuring ports are imported from the facade module."""

    def test_ports_imported_only_from_facade(self, src_dir: Path) -> None:
        """All layers MUST import ports from facade, not internal modules.

        REQ-ARCH-027: Ports are accessible only via bioetl.domain.ports,
        not via bioetl.domain.ports.storage etc.
        This provides a single entry point and simplifies navigation.
        """
        # Forbidden import patterns (internal port modules)
        internal_port_modules = [
            "bioetl.domain.ports.storage",
            "bioetl.domain.ports.locking",
            "bioetl.domain.ports.checkpoint",
            "bioetl.domain.ports.quarantine",
            "bioetl.domain.ports.observability",
            "bioetl.domain.ports.data_source",
            "bioetl.domain.ports.validation",
            "bioetl.domain.ports.filtering",
        ]

        violations = []

        # Check all layers except the ports package itself
        for layer in ["application", "composition", "infrastructure", "interfaces"]:
            layer_path = src_dir / "bioetl" / layer
            if not layer_path.exists():
                continue

            for py_file in layer_path.rglob("*.py"):
                content = py_file.read_text(encoding="utf-8")
                for module in internal_port_modules:
                    if f"from {module}" in content:
                        relative_path = py_file.relative_to(src_dir)
                        violations.append(f"{relative_path}: imports from {module}")

        assert not violations, (
            "Ports must be imported only from facade bioetl.domain.ports.\n"
            "Correct: from bioetl.domain.ports import StoragePort\n"
            "Wrong: from bioetl.domain.ports.storage import StoragePort\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestBootstrapAdapterIsolation:
    """Tests ensuring bootstrap doesn't directly import adapters."""

    def test_bootstrap_no_direct_adapter_imports(self, src_dir: Path) -> None:
        """bootstrap.py MUST NOT import concrete adapters directly.

        REQ-ARCH-COMP-001: Composition Root delegates adapter creation to factories.
        Adding a new provider should only require changes in:
        - providers/registration.py (ProviderRegistry)
        - factories/data_source_registry.py (DataSourceRegistry)

        This prevents tight coupling and ensures the factory pattern is enforced.
        """
        bootstrap_file = src_dir / "bioetl" / "composition" / "bootstrap.py"
        if not bootstrap_file.exists():
            pytest.skip("bootstrap.py not found")

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
            "bootstrap.py must not import concrete adapters directly.\n"
            "Use ProviderRegistry and factories "
            "(DataSourceFactory, HttpClientFactory) instead.\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestInterfacesFilesystemAccess:
    """Tests ensuring interfaces layer doesn't access filesystem directly."""

    def test_interfaces_no_direct_filesystem_traversal(self, src_dir: Path) -> None:
        """Interfaces layer MUST NOT use direct filesystem traversal.

        REQ-ARCH-023: CLI delegates to StoragePort, not Path.rglob.
        """
        interfaces_path = src_dir / "bioetl" / "interfaces"
        if not interfaces_path.exists():
            pytest.skip("Interfaces layer not found")

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
            "Delegate to StoragePort instead.\n"
            "Violations:\n" + "\n".join(f"  - {e}" for e in errors)
        )


class TestInterfacesBootstrapIsolation:
    """Tests ensuring interfaces layer doesn't import bootstrap directly."""

    def test_cli_no_bootstrap_import(self, src_dir: Path) -> None:
        """Interfaces layer MUST NOT import from bootstrap.py directly.

        REQ-ARCH-C1: CLI должен использовать entrypoints, не bootstrap.
        The CLI should only import from composition/entrypoints.py,
        which acts as a facade for all composition operations.

        This separation ensures:
        - Clean layer boundaries (interfaces → entrypoints → bootstrap)
        - Easier testing of CLI without full bootstrap machinery
        - Single entry point for orchestration layers (CLI, REST API)
        """
        interfaces_path = src_dir / "bioetl" / "interfaces"
        if not interfaces_path.exists():
            pytest.skip("Interfaces layer not found")

        forbidden_patterns = [
            r"from bioetl\.composition\.bootstrap import",
            r"from bioetl\.composition\.bootstrap\s+import",
            r"import bioetl\.composition\.bootstrap",
        ]

        violations = []
        for py_file in interfaces_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                if re.search(pattern, content):
                    relative_path = py_file.relative_to(src_dir)
                    violations.append(
                        f"{relative_path}: imports from bootstrap directly"
                    )
                    break

        assert not violations, (
            "Interfaces layer must not import from bootstrap.py directly.\n"
            "Use bioetl.composition.entrypoints instead.\n\n"
            "Correct:\n"
            "  from bioetl.composition.entrypoints import create_pipeline_runner\n\n"
            "Wrong:\n"
            "  from bioetl.composition.bootstrap import bootstrap_pipeline\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )
