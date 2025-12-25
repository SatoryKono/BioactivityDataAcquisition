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
        "infrastructure": 600,  # Infrastructure adapters may be complex
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
        "types.py": 350,  # 314 LOC
        "exceptions.py": 550,  # 513 LOC
        # Composition layer exemptions
        "storage_factory.py": 650,  # 599 LOC
        "bootstrap.py": 450,  # 420 LOC - main DI wiring
        "generic_factory.py": 450,  # 411 LOC - factory with transformer DI
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
        self._check_layer(src_dir, "infrastructure", self.LAYER_LIMITS["infrastructure"])

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

        assert not violations, (
            f"Files exceeding LOC limit in {layer}:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestFunctionComplexity:
    """Enforce cyclomatic complexity limits.

    Uses radon for complexity analysis.
    """

    MAX_COMPLEXITY = {
        "domain": 5,  # Domain must be simple
        "application": 10,  # Application can have some complexity
        "infrastructure": 15,  # Adapters may need branching
    }

    # Exemptions for specific functions (baseline for existing code)
    EXEMPTIONS = {
        "_extract_business_data": 12,  # XML extraction with many conditionals
        "__post_init__": 7,  # Dataclass post-init validation
        "SchemaEvolutionError": 7,  # Exception with detailed field tracking
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

        assert not violations, (
            f"Functions with CC > {max_cc} in {layer}:\n"
            + "\n".join(f"  - {v}" for v in violations)
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
        "bootstrap_pipeline": 70,
        "register_provider": 100,
        "vacuum": 70,
        "archive": 70,
        "create": 90,
        "fetch": 80,
        "process_batch": 70,
        "_transform_impl": 120,  # Transform implementations
        "_clear_exports_legacy": 70,
    }

    # Maximum allowed violations (for tracking technical debt)
    MAX_VIOLATIONS = 30

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

    EXEMPTIONS = {
        # Large classes that are acceptable due to their nature
        "BasePipeline": 400,
        "PipelineRunner": 450,  # 441 lines - includes vacuum + health check methods
        "UnifiedHTTPClient": 350,
        # Baseline exemptions for existing classes
        "StorageAdapter": 500,
        "BaseTransformer": 400,
        "DeltaWriter": 520,  # 500 lines - includes schema drift detection (M4)
        "GoldWriter": 450,
        "LineageTracker": 400,
        "ChemblAdapter": 470,  # 463 lines - complex API adapter
        "GenericPipelineFactory": 350,  # 305 lines - factory pattern
        "RecordProcessor": 350,  # 318 lines - core ETL logic
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
                f"Classes exceeding line limit:\n"
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

                    if len(public_methods) > self.MAX_METHODS_PER_CLASS:
                        violations.append(
                            f"{py_file.name} - {node.name} has "
                            f"{len(public_methods)} public methods "
                            f"(max={self.MAX_METHODS_PER_CLASS})"
                        )

        if violations:
            pytest.fail(
                f"Classes with too many methods:\n"
                + "\n".join(f"  - {v}" for v in violations)
            )
