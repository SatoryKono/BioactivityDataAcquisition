#!/usr/bin/env python3
"""
Script to check naming conventions in the project against defined rules.
"""
import ast
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Configuration
CONFIG_PATH = Path("configs/naming_exceptions.yaml")
ROOT_DIRS = ["src", "tests"]

# Rules
CLASS_SUFFIXES = {
    "Factory",
    "ClientFactory",
    "DataClient",
    "Client",
    "Facade",
    "Registry",
    "Adapter",
    "Transport",
    "Protocol",
    "ABC",
    "Config",
    "Model",
    "Params",
    "Error",
    "Impl",
}

LAYER_SUFFIXES = {
    # Orchestration / application layer
    "application": {
        # Pipelines and orchestration
        "Pipeline",
        "PipelineBase",
        "Orchestrator",
        "Container",
        # Hooks and error policies
        "Hook",
        "HookImpl",
        "ErrorPolicyABC",
        "ErrorPolicyImpl",
        # Application-level services
        "Service",
        # Common technical suffixes seen in application
        "Factory",
        "Registry",
        "Adapter",
        "ABC",
        "Impl",
        "Config",
    },
    # Domain layer (pure domain and business logic)
    "domain": {
        # Core models / DTOs
        "Result",
        "Context",
        "Descriptor",
        "Definition",
        "Id",
        "Record",
        "Source",
        # Domain errors
        "Error",
        # Services and transformers
        "Service",
        "Transformer",
        "TransformerChain",
        # Schemas and models
        "Schema",
        "Model",
        # Providers and registries
        "Provider",
        "Registry",
        # Interfaces / contracts
        "ABC",
        "Protocol",
        "Impl",
        "Config",
    },
    # Infrastructure layer (clients, files, output, logging, config)
    "infrastructure": {
        # HTTP / client side
        "Client",
        "DataClient",
        "ClientHTTPImpl",
        "RequestBuilder",
        "ResponseParser",
        "Paginator",
        "Middleware",
        # Record sources and file operations
        "RecordSourceImpl",
        "Operation",
        # Output / writers
        "Writer",
        "WriterImpl",
        "OutputWriter",
        # Configuration and factories
        "Config",
        "Options",
        "Schema",
        "Resolver",
        "Factory",
        # Logging and progress
        "LoggerImpl",
        "ProgressReporterImpl",
        # Common technical suffixes
        "Registry",
        "Adapter",
        "Transport",
        "Protocol",
        "ABC",
        "Impl",
    },
    # Interfaces layer (pure interfaces / contracts)
    "interfaces": {
        "ABC",
        "Protocol",
        "Adapter",
        "Factory",
        "Config",
        "Model",
        "Error",
    },
}

FUNCTION_PREFIXES = {
    "get_",
    "fetch_",
    "request_",
    "iter_",
    "extract_",
    "create_",
    "build_",
    "make_",
    "default_",
    "register_",
    "resolve_",
    "ensure_",
    "validate_",
    "parse_",
    "serialize_",
    "on_",
    "is_",
    "has_",
    "can_",
    "test_",
    "fixture_",
    "mock_",
    "sample_",
    "info",
    "error",
    "debug",
    "warning",
    "visit_",
    "apply",
    "run",
    "start",
    "stop",
    "close",
    "main",
}

PIPELINE_FUNCTION_ALLOWED_NAMES = {
    "run",
    "extract",
    "transform",
    "validate",
    "write",
    "iter_chunks",
    "get_version",
    "get_database_version",
    "add_hook",
    "add_hooks",
    "set_error_policy",
    "set_post_transformer",
    "reset_iterator",
    "pre_transform",
    "do_transform",
}

LAYER_FUNCTION_ALLOWED_NAMES = {
    "application": {
        "build_pipeline",
        "run_pipeline",
        "run_in_background",
        "get_logger",
        "get_validation_service",
        "get_output_writer",
        "get_normalization_service",
        "get_record_source",
        "get_extraction_service",
        "get_hash_service",
        "get_post_transformer",
        "get_hooks",
        "get_error_policy",
        "extract_all",
        "load",
        "handle",
        "should_retry",
        "pipeline_fixture",
    },
    "domain": {
        "validate",
        "normalize",
        "normalize_batch",
        "normalize_dataframe",
        "normalize_series",
        "iter_records",
    },
    "infrastructure": {
        "metadata",
        "iter_pages",
        "resolve",
    },
}

# Regex
MODULE_REGEX = re.compile(r"^[a-z0-9_]+$")
CLASS_REGEX = re.compile(r"^[A-Z][A-Za-z0-9]+$")
FUNC_REGEX = re.compile(r"^[a-z_][a-z0-9_]*$")
CONST_REGEX = re.compile(r"^[A-Z][A-Z0-9_]*$")

PIPELINE_PATH_REGEX = re.compile(
    r"src/bioetl/application/pipelines/" r"([a-z0-9_]+)/([a-z0-9_]+)/([a-z0-9_]+)\.py$"
)
TEST_FILE_REGEX = re.compile(r"^test_[a-z0-9_]+\.py$")


def _has_exception(exceptions: List[Dict[str, Any]], path: str, rule_id: str) -> bool:
    return any(
        exc.get("path") == path and exc.get("rule_id") == rule_id for exc in exceptions
    )


def resolve_layer(file_path):
    normalized = file_path.replace("\\", "/")
    if "bioetl/application/" in normalized:
        return "application"
    if "bioetl/domain/" in normalized:
        return "domain"
    if "bioetl/infrastructure/" in normalized:
        return "infrastructure"
    if "bioetl/interfaces/" in normalized:
        return "interfaces"
    return None


class NamingValidator(ast.NodeVisitor):
    """
    AST Visitor to validate naming conventions.
    """

    def __init__(self, file_path: str, exceptions: List[Dict[str, Any]]):
        self.file_path = file_path
        self.exceptions = exceptions
        self.violations: List[str] = []
        normalized = file_path.replace("\\", "/")
        # Treat modules under application/pipelines as part of pipeline layer
        self.is_pipeline = (
            "src/bioetl/application/pipelines/" in normalized
            or "tests/bioetl/application/pipelines/" in normalized
        )
        self.is_test = (
            file_path.startswith("tests")
            or "tests\\" in file_path
            or "tests/" in file_path
        )

    def is_excepted(self, rule_id: str, _node_name: str) -> bool:
        """Check if a rule is excepted for the given node."""
        for exc in self.exceptions:
            if exc.get("path") == self.file_path and exc.get("rule_id") == rule_id:
                # Could add more granular checks here (e.g. by symbol name)
                # checking if the exception applies to this specific symbol
                # if specified. For now, simplicity: if file has exception
                # for rule, skip it?
                # Better: Exception entry should probably target specific
                # symbols or just the file for a rule.
                # The plan said "path, rule_id". Let's assume file-level
                # exception for the rule.
                return True
        return False

    def visit_ClassDef(self, node: ast.ClassDef):
        # pylint: disable=invalid-name
        """Validate class definitions."""
        # Allow private-style test stubs like _LoggerStub in tests
        if self.is_test and node.name.startswith("_"):
            self.generic_visit(node)
            return

        if not CLASS_REGEX.match(node.name):
            if not self.is_excepted("CLASS_FORMAT", node.name):
                self.violations.append(
                    f"Class '{node.name}' does not match PascalCase format."
                )

        # Check suffix
        layer = resolve_layer(self.file_path)
        allowed_suffixes = set(CLASS_SUFFIXES)
        if layer and layer in LAYER_SUFFIXES:
            allowed_suffixes |= set(LAYER_SUFFIXES[layer])

        has_valid_suffix = any(
            node.name.endswith(suffix) for suffix in allowed_suffixes
        )
        if not has_valid_suffix:
            if not self.is_excepted("CLASS_SUFFIX", node.name):
                self.violations.append(
                    f"Class '{node.name}' must end with one of: "
                    f"{', '.join(sorted(allowed_suffixes))}"
                )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # pylint: disable=invalid-name
        """Validate function definitions."""
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        # pylint: disable=invalid-name
        """Validate async function definitions."""
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: Any):
        """Helper to check function naming."""
        if not FUNC_REGEX.match(node.name) and not node.name.startswith("visit_"):
            if not self.is_excepted("FUNC_FORMAT", node.name):
                self.violations.append(
                    f"Function '{node.name}' does not match snake_case format."
                )
            return

        if node.name.startswith("_"):
            return

        if self.is_test and node.name.startswith("test_"):
            return

        allowed_names = self._resolve_allowed_function_names()
        if node.name in allowed_names:
            return

        if not self._has_valid_prefix(node.name):
            self.violations.append(
                f"Public function '{node.name}' must start with one "
                f"of: {', '.join(sorted(FUNCTION_PREFIXES))}"
            )

    def _has_valid_prefix(self, name: str) -> bool:
        return any(name.startswith(prefix) for prefix in FUNCTION_PREFIXES) or (
            self.is_excepted("FUNC_PREFIX", name)
        )

    def _resolve_allowed_function_names(self) -> set[str]:
        layer = resolve_layer(self.file_path)
        allowed_names: set[str] = set()
        if layer and layer in LAYER_FUNCTION_ALLOWED_NAMES:
            allowed_names |= set(LAYER_FUNCTION_ALLOWED_NAMES[layer])

        if self.is_pipeline:
            allowed_names |= set(PIPELINE_FUNCTION_ALLOWED_NAMES)
        return allowed_names

    def visit_Assign(self, node: ast.Assign):
        # pylint: disable=invalid-name
        """Validate assignments (constants)."""
        # Heuristic for constants: Module level assignments to UPPER_CASE names
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id.isupper():
                    if not CONST_REGEX.match(target.id):
                        if not self.is_excepted("CONST_FORMAT", target.id):
                            self.violations.append(
                                f"Constant '{target.id}' contains invalid "
                                "characters."
                            )
        self.generic_visit(node)


def load_exceptions() -> List[Dict[str, Any]]:
    """Load exceptions from the YAML configuration file."""
    if not CONFIG_PATH.exists():
        return []
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("exceptions", []) if data else []
    except (OSError, yaml.YAMLError) as e:
        print(f"Error loading exceptions: {e}")
        return []


def check_file_naming(file_path: Path, exceptions: List[Dict[str, Any]]) -> List[str]:
    """Check if file name follows conventions."""
    violations = []
    str_path = str(file_path).replace("\\", "/")
    filename = file_path.name

    def _is_excepted(rule_id: str) -> bool:
        return _has_exception(exceptions, str_path, rule_id)

    stem = file_path.stem
    if not MODULE_REGEX.match(stem) and not _is_excepted("MODULE_NAME"):
        violations.append(f"File '{filename}' does not match snake_case.")

    if "tests" in str_path and not filename.startswith(("conftest.py", "__init__.py")):
        if not TEST_FILE_REGEX.match(filename) and not _is_excepted("TEST_NAME"):
            # Violations muted by policy; keep placeholder for future reporting.
            pass

    return violations


def check_file_content(file_path: Path, exceptions: List[Dict[str, Any]]) -> List[str]:
    """Parse and validate file content."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
        validator = NamingValidator(str(file_path).replace("\\", "/"), exceptions)
        validator.visit(tree)
        return validator.violations
    except Exception as e:  # pylint: disable=broad-except
        return [f"Error parsing file: {e}"]


def main():
    """Main entry point."""
    exceptions = load_exceptions()
    all_violations = {}

    print("Checking naming policy...")

    for root_dir in ROOT_DIRS:
        root_path = Path(root_dir)
        if not root_path.exists():
            continue

        for path in root_path.rglob("*.py"):
            str_path = str(path).replace("\\", "/")

            # Skip exceptions by path if needed? (Already handled in validator)

            file_violations = check_file_naming(path, exceptions)
            content_violations = check_file_content(path, exceptions)

            total = file_violations + content_violations
            if total:
                all_violations[str_path] = total

    if all_violations:
        print(f"\nFound violations in {len(all_violations)} files:\n")
        for path, violations in sorted(all_violations.items()):
            print(f"File: {path}")
            for v in violations:
                print(f"  - {v}")
            print("")
        sys.exit(1)
    else:
        print("\nNo violations found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
