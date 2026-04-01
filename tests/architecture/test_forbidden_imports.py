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

import ast
import re
from pathlib import Path

import pytest


def _discover_internal_port_modules(src_dir: Path) -> list[str]:
    """Return all concrete domain ports submodules (excluding facade __init__)."""
    ports_dir = src_dir / "bioetl" / "domain" / "ports"
    if not ports_dir.exists():
        return []
    sanctioned_public_modules = {"bioetl.domain.ports.noop"}
    return sorted(
        "bioetl.domain.ports."
        + ".".join(py_file.relative_to(ports_dir).with_suffix("").parts)
        for py_file in ports_dir.rglob("*.py")
        if py_file.stem != "__init__"
        and "bioetl.domain.ports."
        + ".".join(py_file.relative_to(ports_dir).with_suffix("").parts)
        not in sanctioned_public_modules
    )


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

        # Walk through all python files
        for py_file in source_path.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")

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
                        relative_path = py_file.relative_to(src_dir)
                        violations.append(f"{relative_path}: imports '{lib}'")

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
            r"maybe_start_metrics_server",  # Entrypoint wrapper is allowed
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
        """All layers MUST import contracts from sanctioned facades only.

        REQ-ARCH-027: Port protocols are accessible via ``bioetl.domain.ports``.
        Operational null objects are accessible via ``bioetl.domain.ports.noop``.
        Deeper internal modules remain forbidden to preserve clear public entry points.
        """
        # Discover internal port modules dynamically to avoid stale allowlists.
        # All modules under domain/ports (except __init__.py facade) are internal.
        internal_port_modules = _discover_internal_port_modules(src_dir)
        assert internal_port_modules, "No internal port modules found"

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
            "Ports must be imported only from sanctioned facades.\n"
            "Correct: from bioetl.domain.ports import StoragePort\n"
            "Correct: from bioetl.domain.ports.noop import NoOpMetrics\n"
            "Wrong: from bioetl.domain.ports.storage import StoragePort\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestBootstrapAdapterIsolation:
    """Tests ensuring bootstrap doesn't directly import adapters."""

    def test_bootstrap_no_direct_adapter_imports(self, src_dir: Path) -> None:
        """bootstrap_pipeline_runner MUST NOT import concrete adapters directly.

        REQ-ARCH-COMP-001: Composition Root delegates adapter creation to factories.
        Adding a new provider should only require changes in:
        - providers/registration.py (ProviderRegistry)
        - factories/datasource/data_source_factory.py (DataSourceRegistry)

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

        REQ-ARCH-023: CLI delegates to StoragePort, not Path.rglob.
        """
        interfaces_path = src_dir / "bioetl" / "interfaces"
        assert interfaces_path.exists(), "Interfaces layer not found"

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
            "Use sanctioned composition public APIs instead.\n\n"
            "Correct:\n"
            "  from bioetl.composition.execution_api import create_pipeline_runner\n\n"
            "Wrong:\n"
            "  from bioetl.composition.bootstrap import bootstrap_pipeline_runner\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_interfaces_no_direct_entrypoints_imports(self, src_dir: Path) -> None:
        """Interfaces must consume narrow composition APIs, not entrypoints façade."""
        interfaces_path = src_dir / "bioetl" / "interfaces"
        assert interfaces_path.exists(), "Interfaces layer not found"

        violations: list[str] = []
        for py_file in interfaces_path.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module == "bioetl.composition.entrypoints":
                        violations.append(
                            f"{py_file.relative_to(src_dir)}:{node.lineno}"
                        )
                elif isinstance(node, ast.Import):
                    if any(
                        alias.name == "bioetl.composition.entrypoints"
                        for alias in node.names
                    ):
                        violations.append(
                            f"{py_file.relative_to(src_dir)}:{node.lineno}"
                        )

        assert not violations, (
            "Interfaces layer must not import bioetl.composition.entrypoints.\n"
            "Use sanctioned modules such as:\n"
            "  - bioetl.composition.execution_api\n"
            "  - bioetl.composition.services_api\n"
            "  - bioetl.composition.resources_api\n"
            "  - bioetl.composition.composite_api\n"
            "  - bioetl.composition.observability_api\n\n"
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

        for py_file in source_path.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for pattern in self.FORBIDDEN_PATTERNS:
                if pattern.search(content):
                    relative_path = py_file.relative_to(src_dir)
                    violations.append(str(relative_path))
                    break

        assert not violations, (
            "RF-043 violation: legacy_normalizers references found in production code.\n"
            "Use bioetl.infrastructure.config.source_normalizers instead.\n\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )
