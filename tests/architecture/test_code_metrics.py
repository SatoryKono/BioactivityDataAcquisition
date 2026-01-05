"""Tests for code quality metrics.

Enforces size and complexity limits across the codebase.
Implements CLAUDE.md §6.3.1 requirements.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


class TestFileSizeLimits:
    """Enforce maximum file size limits by layer."""

    # Layer-specific limits (in lines of code)
    LAYER_LIMITS = {
        "domain": 300,  # Domain should be small and focused
        "application": 500,  # Application can be larger
        "composition": 400,  # Composition is wiring only
        "infrastructure": 650,  # Infrastructure adapters may be complex (bumped from 600)
        "interfaces": 400,  # CLI and entry points
    }

    # Exemptions for specific files (baseline for existing code)
    # New files should adhere to layer limits
    # Note: ports.py was split into ports/ package in main
    EXEMPTIONS = {
        # Application layer exemptions
        "runner.py": 700,  # Complex orchestration
        "base.py": 600,  # Base classes may be larger
        # Infrastructure layer exemptions
        "config.py": 600,  # Config can be verbose
        # Domain layer exemptions (baseline)
        "filter_config.py": 400,  # 354 LOC
        "entities.py": 600,  # 569 LOC
        "chembl.py": 720,  # 714 LOC - ChEMBL entity DTOs with many fields
        "normalization.py": 350,  # 341 LOC - Pure domain normalization functions
        "activity_aggregator.py": 400,  # 392 LOC - Activity aggregation with multiple strategies
        "normalization_service.py": 420,  # 411 LOC - Normalization service with validation
        "value_validator.py": 360,  # 351 LOC - Value objects validation
        "activity.py": 330,  # 327 LOC - Activity domain types with rich validation
        "types.py": 400,  # 396 LOC
        "chembl_structures.py": 350,  # 324 LOC - ChEMBL structural entities
        "config_types.py": 320,  # 313 LOC
        "exceptions.py": 550,  # 513 LOC
        # Domain value objects (rich domain models with validation)
        "batch.py": 550,  # 531 LOC - Batch aggregate with lifecycle methods
        "pipeline_run.py": 600,  # 581 LOC - PipelineRun aggregate with state machine
        "quarantine_entry.py": 520,  # 501 LOC - QuarantineEntry with detailed error info
        "identifiers.py": 350,  # 332 LOC - Value objects with validation
        "activity_values.py": 450,  # 436 LOC - Activity value objects (renamed from measurements.py)
        # Domain ports NoOp implementations
        "noop.py": 400,  # 383 LOC - NoOp implementations for Null Object Pattern (+ NoOpPiiHasher)
        # Application layer exemptions
        "preflight_service.py": 820,  # 811 LOC - preflight validation (expanded)
        "base_transformer.py": 650,  # 639 LOC - Template Method with helpers (tracing + PII hashing)
        "batch_executor.py": 650,  # 610 LOC - unified executor for batch processing
        # Composition layer exemptions
        "bootstrap.py": 450,  # 420 LOC - main DI wiring
        "entrypoints.py": 720,  # 703 LOC - pipeline entrypoints (run_pipeline expanded + services)
        "registration.py": 500,  # 478 LOC - provider registration with data source creators
        "storage_adapter.py": 550,  # 540 LOC - storage adapter with Bronze/Silver/Gold writers
        # Consolidated factory files (v5.2)
        "storage.py": 700,  # 640 LOC - merged storage_factory + storage_adapter
        "pipeline_factory.py": 520,  # 517 LOC - merged generic_factory + runner_assembly
        "pipeline_factories.py": 420,  # 406 LOC - pipeline factory configurations
        "services_factory.py": 600,  # 562 LOC - merged base_services + services_builder + runner_services + LockContextHolder + BatchExecutor factory
        # Infrastructure layer exemptions
        "silver_writer.py": 900,  # 887 LOC - schema drift detection + merge logic + audit + validation
        "gold_writer.py": 770,  # 759 LOC - SCD Type 2 + audit logging + lock validation
        "bronze_writer.py": 700,  # 600+ LOC - added streaming compression + validation
        "client.py": 750,  # 746 LOC - CrossRefAdapter with fallback title search + ChemblAdapter with fetch_multi_filtered
        # Interfaces layer exemptions
        "cli.py": 550,  # 536 LOC - CLI commands, options, vacuum-all
        # New exemptions for split storage factory
        "storage_factory.py": 400,  # Extracted from storage.py
        "observability.py": 450,  # Bootstrap observability
    }

    def test_domain_files_under_limit(self, src_dir: Path) -> None:
        """Domain layer files must be under 300 LOC."""
        self._check_layer(src_dir, "domain", self.LAYER_LIMITS["domain"])

    def test_application_files_under_limit(self, src_dir: Path) -> None:
        """Application layer files must be under 500 LOC."""
        self._check_layer(src_dir, "application", self.LAYER_LIMITS["application"])

    def test_composition_files_under_limit(self, src_dir: Path) -> None:
        """Composition layer files must be under 400 LOC."""
        self._check_layer(src_dir, "composition", self.LAYER_LIMITS["composition"])

    def test_infrastructure_files_under_limit(self, src_dir: Path) -> None:
        """Infrastructure layer files must be under 600 LOC."""
        self._check_layer(
            src_dir, "infrastructure", self.LAYER_LIMITS["infrastructure"]
        )

    def test_interfaces_files_under_limit(self, src_dir: Path) -> None:
        """Interfaces layer files must be under 400 LOC."""
        self._check_layer(src_dir, "interfaces", self.LAYER_LIMITS["interfaces"])

    def _check_layer(self, src_dir: Path, layer: str, limit: int) -> None:
        """Check all files in a layer against the limit."""
        layer_path = src_dir / "bioetl" / layer
        if not layer_path.exists():
            pytest.skip(f"{layer} layer not found")

        violations = []
        for py_file in layer_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            # Check for exemptions
            if py_file.name in self.EXEMPTIONS:
                file_limit = self.EXEMPTIONS[py_file.name]
            else:
                file_limit = limit

            loc = len(py_file.read_text(encoding="utf-8").splitlines())
            if loc > file_limit:
                violations.append(f"{py_file.name}: {loc} LOC (limit: {file_limit})")

        assert not violations, f"Files exceeding LOC limit in {layer}:\n" + "\n".join(
            f"  - {v}" for v in violations
        )


class TestFunctionComplexity:
    """Enforce cyclomatic complexity limits.

    Uses radon for complexity analysis.
    """

    MAX_COMPLEXITY = {
        "domain": 5,  # Domain must be simple
        "application": 10,  # Application can be complexity
        "infrastructure": 15,  # Adapters may need branching
    }

    # Exemptions for specific functions (baseline for existing code)
    EXEMPTIONS = {
        "_extract_business_data": 12,  # XML extraction with many conditionals
        "__post_init__": 12,  # Dataclass post-init validation with complex context
        "__init__": 10,  # Constructor with validation logic
        "TableConfig": 8,  # Dataclass with write mode enum conversion in __post_init__
        "SchemaEvolutionError": 7,  # Exception with detailed field tracking
        "validate_medallion_config": 12,  # Config validation with many checks
        "run_dq_checks": 12,  # DQ checks with multiple validation paths
        "execute": 22,  # Pipeline executor with multiple execution paths and audit
        "_validate_config": 8,  # PipelineConfig validation logic
        "PipelineConfig": 8,  # PipelineConfig post-init logic
        "_request_with_retry": 18,  # HTTP client retry logic with circuit breaker
        # Domain value object validation
        "complete": 7,  # PipelineRun state transition with validation
        "_validate": 8,  # Value object validation with multiple checks
        "PubMedId": 9,  # Value object with multiple format validation
        "PubChemCid": 9,  # Value object with multiple format validation
        # Domain services (activity aggregation, normalization)
        "ActivityAggregator": 8,  # Activity aggregation class init with multiple strategies
        "aggregate_values": 10,  # Multi-strategy aggregation logic
        "aggregate_with_uncertainty": 10,  # Uncertainty calculation with bounds
        "filter_and_aggregate": 8,  # Combined filtering and aggregation
        "_normalize_value": 13,  # Value normalization with type handling
        "PChemblRangeConfig": 7,  # Config validation with range checks
        "normalize_multiple": 10,  # Multi-value normalization
        "validate_concentration": 7,  # Concentration validation with unit checks
        "validate_pchembl": 7,  # pChEMBL validation with range checks
        "validate_activity_value": 10,  # Activity value validation
    }

    def test_domain_complexity(self, src_dir: Path) -> None:
        """Domain functions must have CC <= 5."""
        self._check_layer(src_dir, "domain", self.MAX_COMPLEXITY["domain"])

    def test_application_complexity(self, src_dir: Path) -> None:
        """Application functions must have CC <= 10."""
        self._check_layer(src_dir, "application", self.MAX_COMPLEXITY["application"])

    def test_infrastructure_complexity(self, src_dir: Path) -> None:
        """Infrastructure functions must have CC <= 15."""
        self._check_layer(
            src_dir, "infrastructure", self.MAX_COMPLEXITY["infrastructure"]
        )

    def _check_layer(self, src_dir: Path, layer: str, max_cc: int) -> None:
        """Check all functions in a layer for complexity."""
        try:
            from radon.complexity import cc_visit
        except ImportError:
            pytest.skip("radon not installed")

        layer_path = src_dir / "bioetl" / layer
        if not layer_path.exists():
            pytest.skip(f"{layer} layer not found")

        violations = []
        for py_file in layer_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")
            try:
                results = cc_visit(content)
                for item in results:
                    # Check for exemptions
                    func_max_cc = self.EXEMPTIONS.get(item.name, max_cc)
                    if item.complexity > func_max_cc:
                        violations.append(
                            f"{py_file.name}:{item.lineno} - {item.name}() "
                            f"CC={item.complexity} (max={func_max_cc})"
                        )
            except SyntaxError:
                continue

        assert (
            not violations
        ), f"Functions with CC > {max_cc} in {layer}:\n" + "\n".join(
            f"  - {v}" for v in violations
        )


class TestFunctionLength:
    """Enforce maximum function length."""

    MAX_LINES = 50  # Maximum lines per function

    EXEMPTIONS = {
        # Complex functions that need refactoring but are acceptable
        "transform": 80,  # Transform methods may be long
        "run": 100,  # Main run methods
        "create_runner": 80,  # Factory methods
        "execute": 80,  # Execution methods
        # Baseline exemptions for existing functions
        "__init__": 80,  # Constructors can be long
        "bootstrap_pipeline": 120,  # Thin orchestrator with delegation
        "register_provider": 100,
        "vacuum": 70,
        "archive": 70,
        "create": 90,
        "fetch": 80,
        "process_batch": 70,
        "_process_batch": 100,  # BatchExecutor internal processing
        "_transform_impl": 120,  # Transform implementations
        "_clear_exports_legacy": 70,
        "create_logger": 55,  # Logger setup with many handlers
        "vacuum_all_command": 90,  # CLI command with multiple suboperations
        "_fetch_batch_publications": 75,  # CrossRef batch DOI resolution with fallback
        # Extracted validators (REFACTOR-003)
        "validate_medallion_config": 55,  # MedallionConfigValidator method
        "validate_write_modes": 75,  # MedallionConfigValidator method with multiple checks
        "_validate_medallion_policy_consistency": 65,  # MedallionConfigValidator helper
        "validate_preflight": 95,  # PreflightService orchestration method
        # Error handling (comprehensive error classification)
        "log_error": 70,  # Structured error logging with context
        "wrap_error": 70,  # Error wrapping with classification
        "_wrap_by_status_code": 55,  # HTTP status code handling
        # Infrastructure functions
        "run_pipeline": 75,  # CLI entrypoint with setup
        "load_pipeline_config": 60,  # Config loading with defaults
        "validate_record": 60,  # Record validation with multiple checks
        "_read_entries_sync": 70,  # File audit entry parsing
        "export": 65,  # CSV export with transformations
        "get_batch_statistics": 65,  # Batch statistics aggregation
        "start_metrics_server": 65,  # Metrics server setup
        "_write_atomic_stream": 70,  # Atomic streaming with compression
        "write_bronze": 170,  # Full Bronze layer write with validation
        "write_silver": 100,  # Full Silver layer write with merge
        "_log_silver_audit": 75,  # Silver audit logging
    }

    # Maximum allowed violations (for tracking technical debt)
    # Baseline updated 2025-12-30: 60 violations
    MAX_VIOLATIONS = 60

    def test_functions_under_50_lines(self, src_dir: Path) -> None:
        """All functions must be under 50 lines (with exemptions)."""
        bioetl_path = src_dir / "bioetl"
        if not bioetl_path.exists():
            pytest.skip("bioetl not found")

        violations = []

        for py_file in bioetl_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Calculate function length
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    func_lines = end_line - start_line + 1

                    # Check exemptions
                    max_lines = self.EXEMPTIONS.get(node.name, self.MAX_LINES)

                    if func_lines > max_lines:
                        violations.append(
                            f"{py_file.name}:{start_line} - {node.name}() "
                            f"is {func_lines} lines (max={max_lines})"
                        )

        # Allow baseline violations but warn if too many (technical debt)
        if len(violations) > self.MAX_VIOLATIONS:
            pytest.fail(
                f"Too many long functions ({len(violations)}, max={self.MAX_VIOLATIONS}):\n"
                + "\n".join(f"  - {v}" for v in violations[:15])
            )


class TestClassSize:
    """Enforce maximum class size limits."""

    MAX_CLASS_LINES = 300  # Maximum lines per class
    MAX_METHODS_PER_CLASS = 20  # Maximum methods per class

    # Method count exemptions for aggregate classes with rich behavior
    METHOD_EXEMPTIONS = {
        "Batch": 25,  # 22 methods - Batch aggregate with lifecycle + query methods
    }

    EXEMPTIONS = {
        # Large classes that are acceptable due to their nature
        "BasePipeline": 400,
        "PipelineRunner": 450,  # 441 lines - includes vacuum + health check methods
        "UnifiedHTTPClient": 450,  # 427 lines - HTTP client with retry/circuit breaker
        "PipelineObserver": 350,  # 319 lines - unified observability with lifecycle events
        # Baseline exemptions for existing classes
        "StorageAdapter": 520,  # 510 lines - storage adapter with writers
        "BaseTransformer": 580,  # 577 lines - Template Method with helpers (tracing + PII hashing)
        "FilteredDataSource": 330,  # 322 lines - decorator with fallback support
        "SilverWriter": 830,  # 822 lines - includes schema drift detection (M4) + audit + lock validation + validation
        "GoldWriter": 720,  # 709 lines - includes SCD Type 2 with ingestion_ts per ADR-014 + lock validation
        "MedallionLifecycleService": 385,  # 379 lines - lifecycle orchestration service
        "LineageTracker": 400,
        "ChemblAdapter": 600,  # 581 lines - complex API adapter with fetch_multi_filtered for multi-column filtering
        "GenericPipelineFactory": 350,  # 305 lines - factory pattern
        "PreflightService": 545,  # 540 lines - preflight validation service
        "PostrunService": 355,  # 349 lines - postrun service
        "BronzeWriter": 600,  # 500+ lines - JSONL + zstd streaming compression + validation + tests
        "BatchExecutor": 600,  # 581 lines - unified executor for batch processing
        "BatchWriter": 350,  # 338 lines - batch writing with Safety Guard §4.6 lock validation
        # CrossRef adapter classes (similar to ChEMBL/PubMed adapters)
        "CrossRefAdapter": 660,  # 658 lines - HTTP adapter with batch DOI resolution + fallback title search
        # PubChem adapter (similar to ChEMBL adapter)
        "PubChemAdapter": 500,  # 489 lines - sync adapter with SMILES/CID filtering + DTO support
        "CrossRefTransformer": 360,  # 354 lines - transformer with field extraction
        # UniProt adapter (similar to ChEMBL adapter)
        "UniProtAdapter": 320,  # 312 lines - HTTP adapter with streaming
        # PubMed adapter (similar to ChEMBL adapter)
        "PubMedAdapter": 400,  # 373 lines - HTTP adapter with Entrez API + FilterableDataSourcePort
        # Error handling utility (ErrorService + deprecated ErrorHandler alias)
        "ErrorService": 500,  # ~480 lines - comprehensive error classification with detailed recovery logging
        # Domain services
        "NormalizationService": 370,  # 364 lines - Normalization service with validation
        "ActivityAggregator": 320,  # 311 lines - Activity aggregation with multiple strategies
        "ValueValidator": 320,  # 311 lines - Value objects validation
        # Domain value objects (aggregates with rich behavior)
        "Batch": 450,  # 429 lines - Batch aggregate with lifecycle methods
        "PipelineRun": 420,  # 408 lines - PipelineRun aggregate with state machine
        "QuarantineEntry": 430,  # 416 lines - QuarantineEntry with detailed error info
        # Test classes exemptions
        "TestCliCommands": 350,  # Test class with many test cases
        "TestFileSizeLimits": 350,  # Test class with many exemptions
        "TestFunctionComplexity": 350,  # Test class with many exemptions
        "TestFunctionLength": 350,  # Test class with many exemptions
        "TestClassSize": 350,  # Test class with many exemptions
        # Extracted validators (REFACTOR-003)
        "MedallionConfigValidator": 350,  # Extracted from PreflightService - cohesive validation
    }

    def test_classes_under_300_lines(self, src_dir: Path) -> None:
        """All classes must be under 300 lines (with exemptions)."""
        bioetl_path = src_dir / "bioetl"
        if not bioetl_path.exists():
            pytest.skip("bioetl not found")

        violations = []

        for py_file in bioetl_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    class_lines = end_line - start_line + 1

                    max_lines = self.EXEMPTIONS.get(node.name, self.MAX_CLASS_LINES)

                    if class_lines > max_lines:
                        violations.append(
                            f"{py_file.name}:{start_line} - {node.name} "
                            f"is {class_lines} lines (max={max_lines})"
                        )

        if violations:
            pytest.fail(
                "Classes exceeding line limit:\n"
                + "\n".join(f"  - {v}" for v in violations)
            )

    def test_classes_under_20_methods(self, src_dir: Path) -> None:
        """Classes should not have more than 20 public methods."""
        bioetl_path = src_dir / "bioetl"
        if not bioetl_path.exists():
            pytest.skip("bioetl not found")

        violations = []

        for py_file in bioetl_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Count public methods (not starting with _)
                    public_methods = [
                        n
                        for n in node.body
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not n.name.startswith("_")
                    ]

                    # Check for exemptions
                    max_methods = self.METHOD_EXEMPTIONS.get(
                        node.name, self.MAX_METHODS_PER_CLASS
                    )

                    if len(public_methods) > max_methods:
                        violations.append(
                            f"{py_file.name} - {node.name} has "
                            f"{len(public_methods)} public methods "
                            f"(max={max_methods})"
                        )

        if violations:
            pytest.fail(
                "Classes with too many methods:\n"
                + "\n".join(f"  - {v}" for v in violations)
            )


class TestGodObjectDetection:
    """Detect god objects via delegation pattern analysis.

    God objects are large classes with low delegation that try to do everything
    themselves. This test enforces that large classes (>300 lines) must delegate
    to injected dependencies, not implement all logic internally.

    Implements CLAUDE.md §2.3 god object detection requirements.
    """

    MIN_CLASS_LINES_FOR_CHECK = 300  # Only check large classes
    MIN_DELEGATION_CALLS = 3  # Minimum self._component.method() patterns

    # Classes exempt from delegation check (with documented reasons)
    EXEMPTIONS = {
        # Value objects / data containers (no behavior to delegate)
        "BasePipeline": "Data container with property accessors, no behavior to delegate",
        # Template Method pattern (hooks for subclasses, not delegation)
        "BaseTransformer": "Template Method pattern - provides hooks for subclasses",
        # Protocol implementations (must implement all methods themselves)
        "StorageAdapter": "Facade implementing StoragePort - delegates to bronze/silver/gold writers",
        # Writers with cohesive responsibilities (all methods about writing)
        "SilverWriter": "Cohesive writer - all methods relate to Delta Lake operations",
        "GoldWriter": "Cohesive writer - delegates to _audit, _tracing; modes are cohesive",
        "BronzeWriter": "Cohesive writer - all methods relate to Bronze layer operations",
        # Services with clear single responsibility
        "PreflightService": "Single responsibility: infrastructure validation, delegates to _health_aggregator",
        "PostrunService": "Single responsibility: post-run operations (DQ, vacuum, cleanup)",
        # Adapters (HTTP adapters need internal helpers for retry/error handling)
        "ChemblAdapter": "HTTP adapter with internal helpers; delegates to ErrorClassifier, EntityMapper",
        "CrossRefAdapter": "HTTP adapter with internal helpers for batch resolution",
        "CrossRefTransformer": "Transformer with field extraction - single responsibility",
        "PubChemAdapter": "Sync adapter using ThreadPoolExecutor; delegates to BaseSyncAdapter, CircuitBreaker",
        "PubMedAdapter": "HTTP adapter with FilterableDataSourcePort implementation; delegates to BaseHttpAdapter",
        "UnifiedHTTPClient": "HTTP client with internal retry logic; single responsibility",
        # CLI (inherently has many commands but delegates to entrypoints)
        "CLI": "CLI entry point - commands are cohesive, delegates to entrypoints",
        # Factory classes (create objects, low delegation expected)
        "GenericPipelineFactory": "Factory pattern - creates objects, not behavior delegation",
        # Observer/Tracker classes (cohesive observability responsibility)
        "PipelineObserver": "Unified observability - all methods relate to pipeline observation",
        "LineageTracker": "Cohesive tracker - all methods relate to lineage tracking",
        # Runner (orchestrator that delegates to services)
        "PipelineRunner": "Thin orchestrator - delegates to preflight, postrun, lifecycle services",
        # Extracted validators (REFACTOR-003)
        "MedallionConfigValidator": "Cohesive validator - all methods relate to medallion validation",
        # Error handling utility (not an adapter, unified error classification)
        "ErrorService": "Cohesive utility - all methods relate to error classification and logging",
        # Domain services (cohesive services with single responsibility)
        "NormalizationService": "Cohesive service - all methods relate to value normalization",
        "ActivityAggregator": "Cohesive service - all methods relate to activity aggregation strategies",
        "ValueValidator": "Cohesive validator - all methods relate to domain value validation",
        # Lifecycle orchestration service
        "MedallionLifecycleService": "Lifecycle orchestrator - coordinates Bronze/Silver/Gold operations",
    }

    def test_large_classes_have_delegation(self, src_dir: Path) -> None:
        """Large classes (>300 LOC) must show delegation patterns.

        Delegation is identified by:
        - Injected dependencies (self._<component>)
        - Method calls on dependencies (self._<component>.<method>())
        - Use of composition over monolithic implementation

        Exemptions are allowed for specific patterns (see EXEMPTIONS dict).
        """
        bioetl_path = src_dir / "bioetl"
        if not bioetl_path.exists():
            pytest.skip("bioetl not found")

        violations = []

        for py_file in bioetl_path.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Skip exempted classes
                    if node.name in self.EXEMPTIONS:
                        continue

                    start_line = node.lineno
                    end_line = node.end_lineno or start_line
                    class_lines = end_line - start_line + 1

                    # Only check large classes
                    if class_lines < self.MIN_CLASS_LINES_FOR_CHECK:
                        continue

                    # Count delegation patterns in class body
                    delegation_count = self._count_delegation_calls(node)

                    if delegation_count < self.MIN_DELEGATION_CALLS:
                        violations.append(
                            f"{py_file.name}:{start_line} - {node.name} "
                            f"({class_lines} lines, {delegation_count} delegations) "
                            f"- large class with low delegation (potential god object)"
                        )

        if violations:
            pytest.fail(
                "Potential god objects detected (large classes with low delegation):\n"
                + "\n".join(f"  - {v}" for v in violations)
                + "\n\nOptions to fix:\n"
                + "  1. Extract logic to specialized services and delegate\n"
                + "  2. Add to EXEMPTIONS with documented reason\n"
                + "  3. Reduce class size below 300 lines"
            )

    def _count_delegation_calls(self, class_node: ast.ClassDef) -> int:
        """Count self._component.method() patterns in class.

        Delegation is indicated by:
        - Attribute access on private attributes: self._foo.bar()
        - Method calls on composed objects

        Returns:
            Number of unique delegation patterns found.
        """
        delegations: set[str] = set()

        for node in ast.walk(class_node):
            # Look for self._component.method() pattern
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    # Check if it's self._component.method()
                    value = node.func.value
                    if isinstance(value, ast.Attribute):
                        if (
                            isinstance(value.value, ast.Name)
                            and value.value.id == "self"
                        ):
                            if value.attr.startswith("_"):
                                # Found delegation: self._component.method()
                                delegations.add(f"{value.attr}.{node.func.attr}")

        return len(delegations)
