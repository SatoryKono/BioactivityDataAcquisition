import ast
import inspect
import re
import tomllib
from pathlib import Path
from typing import get_type_hints
from unittest.mock import patch

import pytest

from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    LockPort,
    MetricsPort,
    QuarantinePort,
    StoragePort,
)


# --- REQ-ARCH-001, REQ-ARCH-003 ---
def test_domain_layer_purity(src_dir: Path):
    """Domain layer must not have I/O dependencies."""
    domain_path = src_dir / "bioetl" / "domain"
    disallowed_imports = {
        "httpx",
        "requests",
        "boto3",
        "sqlalchemy",
        "psycopg2",
        "deltalake",
        "polars",
    }

    for py_file in domain_path.rglob("*.py"):
        with py_file.open(encoding="utf-8") as f:
            content = f.read()
            for lib in disallowed_imports:
                assert (
                    f"import {lib}" not in content
                ), f"Disallowed import '{lib}' in {py_file}"
                assert (
                    f"from {lib}" not in content
                ), f"Disallowed import '{lib}' in {py_file}"


# --- REQ-ARCH-001 ---
def test_ports_are_protocols(src_dir: Path):
    """Ports must be defined using typing.Protocol."""
    ports_file = src_dir / "bioetl" / "domain" / "ports.py"
    assert ports_file.exists()
    with ports_file.open(encoding="utf-8") as f:
        content = f.read()
        # Find lines importing from typing
        typing_imports = re.findall(r"from typing import .*", content)
        assert any(
            "Protocol" in line for line in typing_imports
        ), "Protocol not imported from typing"


# --- REQ-ARCH-004 ---
def test_critical_ports_are_runtime_checkable():
    """Critical port protocols should be runtime checkable."""
    critical_ports = [
        DataSourcePort,
        LockPort,
        CheckpointPort,
        StoragePort,
        QuarantinePort,
    ]
    for port in critical_ports:
        assert hasattr(
            port, "_is_runtime_protocol"
        ), f"{port.__name__} is not runtime checkable, add @runtime_checkable"


# --- REQ-STACK-001 ---
def test_httpx_is_http_client(pyproject_toml: Path):
    """httpx must be the declared HTTP client."""
    with pyproject_toml.open("rb") as f:
        data = tomllib.load(f)
    dependencies = data.get("project", {}).get("dependencies", [])
    assert any("httpx" in dep for dep in dependencies)


# --- REQ-STACK-004 ---
def test_ruff_is_linter(pyproject_toml: Path):
    """Ruff must be the declared linter."""
    with pyproject_toml.open("rb") as f:
        data = tomllib.load(f)
    dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    assert any("ruff" in dep for dep in dev_deps)


# --- REQ-SECRET-004 ---
def test_dotenv_is_gitignored(project_root: Path):
    """.env files must be in .gitignore."""
    gitignore_path = project_root / ".gitignore"
    assert gitignore_path.exists()
    with gitignore_path.open(encoding="utf-8") as f:
        content = f.read()
        # Check for exact .env or patterns like *.env or /.env
        assert (
            re.search(r"(^|\n)\.env($|\n)", content)
            or re.search(r"(^|\n)\*\.env($|\n)", content)
            or re.search(r"(^|\n)\.env\*($|\n)", content)
        )


# --- REQ-DX-004, REQ-DX-005 ---
def test_dev_experience_files_exist(project_root: Path):
    """Core DX files must exist."""
    assert (project_root / "Makefile").exists(), "Makefile is missing"
    assert (project_root / "docker-compose.yml").exists() or (
        project_root / "compose.yml"
    ).exists(), "Docker compose file is missing"
    assert (project_root / ".env.example").exists(), ".env.example is missing"


# --- REQ-DEP-001 ---
def test_dependencies_have_version_constraints(pyproject_toml: Path):
    """Dependencies in pyproject.toml should have version constraints."""
    with pyproject_toml.open("rb") as f:
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
    with pyproject_toml.open("rb") as f:
        data = tomllib.load(f)
    dev_deps = data.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    assert any("pip-audit" in dep for dep in dev_deps)


# --- REQ-DOC-002 ---
def test_doc_naming_convention(src_dir: Path, docs_dir: Path):
    """Provider doc folders should mirror src folders."""
    src_providers_path = src_dir / "bioetl" / "infrastructure" / "adapters"
    docs_providers_path = docs_dir / "providers"  # Assuming this is the convention

    if not src_providers_path.exists() or not docs_providers_path.exists():
        pytest.skip("Provider directories not found, skipping test.")

    # Exclude __pycache__ and 'http' (base adapter, not a provider)
    excluded = {"__pycache__", "http"}
    src_providers = {
        d.name
        for d in src_providers_path.iterdir()
        if d.is_dir() and d.name not in excluded
    }
    docs_providers = {d.name for d in docs_providers_path.iterdir() if d.is_dir()}

    assert src_providers.issubset(
        docs_providers
    ), f"Missing doc folders for providers: {src_providers - docs_providers}"


# --- REQ-ENV-001 ---
def test_env_var_access_only_in_config(src_dir: Path):
    """os.getenv and os.environ must only be used in config.py.

    All environment variable access must be centralized in
    src/bioetl/config.py to ensure:
    - Single source of truth for configuration
    - Easier testing (mock config functions, not env vars)
    - Clear documentation of required environment variables

    Runs: Static analysis of source files
    """
    config_file = src_dir / "bioetl" / "config.py"
    disallowed_patterns = [
        r"\bos\.getenv\s*\(",
        r"\bos\.environ\s*\[",
        r"\bos\.environ\.get\s*\(",
    ]

    violations = []

    for py_file in (src_dir / "bioetl").rglob("*.py"):
        # Skip the config.py file - it's allowed to use os.getenv
        if py_file.resolve() == config_file.resolve():
            continue

        with py_file.open(encoding="utf-8") as f:
            content = f.read()

        for pattern in disallowed_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                # Get line number
                line_num = content[: match.start()].count("\n") + 1
                violations.append(
                    f"{py_file.relative_to(src_dir)}:{line_num}: "
                    f"Disallowed env var access '{match.group()}'"
                )

    assert not violations, (
        "Environment variable access must be centralized in config.py.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
                                                                            "Refactor to use functions from bioetl.config instead:\n"
                                                                            "  - get_settings().aws\n"
                                                                            "  - get_settings().s3\n"
                                                                            "  - get_settings().redis\n"
                                                                            "  - get_settings().storage_options"
    )


# --- REQ-ARCH-CLI-001 ---
def test_cli_no_direct_infrastructure_imports(src_dir: Path):
    """CLI module must not import directly from infrastructure adapters.

    The CLI should work through:
    - Abstractions (domain ports)
    - Bootstrap/factory patterns
    - Centralized config (bioetl.config is allowed)

    This ensures the CLI remains decoupled from concrete implementations
    and can be easily tested with mocks.

    Runs: Static analysis of cli.py
    """
    cli_file = src_dir / "bioetl" / "cli.py"
    if not cli_file.exists():
        pytest.skip("CLI module not found")

    with cli_file.open(encoding="utf-8") as f:
        content = f.read()

    # Infrastructure modules that CLI should not import directly
    # (except for config which is allowed)
    disallowed_infrastructure_modules = [
        r"from\s+bioetl\.infrastructure\.adapters\b",
        r"from\s+bioetl\.infrastructure\.checkpoint\b",
        r"from\s+bioetl\.infrastructure\.locking\b",
        r"from\s+bioetl\.infrastructure\.storage\b",
        r"from\s+bioetl\.infrastructure\.quarantine\b",
        r"import\s+bioetl\.infrastructure\.adapters\b",
        r"import\s+bioetl\.infrastructure\.checkpoint\b",
        r"import\s+bioetl\.infrastructure\.locking\b",
        r"import\s+bioetl\.infrastructure\.storage\b",
        r"import\s+bioetl\.infrastructure\.quarantine\b",
    ]

    violations = []

    for pattern in disallowed_infrastructure_modules:
        matches = re.finditer(pattern, content)
        for match in matches:
            line_num = content[: match.start()].count("\n") + 1
            violations.append(f"Line {line_num}: {match.group()}")

    # Allow importing create_logger from observability
    allowed_observability_import = (
        "from bioetl.infrastructure.observability.logging import create_logger"
    )
    violations = [v for v in violations if allowed_observability_import not in v]

    assert not violations, (
        "CLI must not import directly from infrastructure modules.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
                                                                            "Refactor to use:\n"
                                                                            "  - Factory patterns in bioetl.application or bioetl.infrastructure.factories\n"
                                                                            "  - Bootstrap functions that wire up dependencies\n"
                                                                            "  - Domain ports for type hints\n"
                                                                            "  - bioetl.config for configuration (allowed)"
    )


# --- REQ-CONFIG-001 ---
def test_config_parameters_have_defaults_or_validation(src_dir: Path):
    """Configuration parameters should have sensible defaults or validation.

    This test checks that config functions return valid typed objects
    even with no environment variables set.
    """
    # Import config module
    import sys

    sys.path.insert(0, str(src_dir))

    from bioetl.config import get_settings

    # Test that all config functions can be called without environment variables
    # (they should return objects with sensible defaults or None for optional values)
    with patch("bioetl.config.Settings.check_s3_endpoint_for_dev", return_value=True):
        settings = get_settings()

        aws_config = settings.aws
        assert aws_config is not None
        assert isinstance(aws_config.region, str)
        # endpoint_url can be None (optional)

        s3_config = settings.s3
        assert s3_config is not None
        assert s3_config.bucket_bronze == "bioetl-bronze"
        assert s3_config.bucket_silver == "bioetl-silver"
        assert s3_config.bucket_gold == "bioetl-gold"
        assert s3_config.bucket_checkpoints == "bioetl-checkpoints"

        redis_config = settings.redis
        assert redis_config is not None
        assert redis_config.host == "localhost"
        assert redis_config.port == 6379

        storage_options = settings.storage_options
        # Should be None when endpoint_url is not set
        assert storage_options is None or isinstance(storage_options, dict)


# --- REQ-CONFIG-002 ---
def test_config_dataclasses_are_frozen(src_dir: Path):
    """Configuration dataclasses must be immutable (frozen=True).

    This ensures configuration cannot be accidentally modified at runtime.
    """
    import sys

    sys.path.insert(0, str(src_dir))

    from bioetl.config import AWSSettings, RedisSettings, S3Settings

    config_classes = [AWSSettings, RedisSettings, S3Settings]

    for config_class in config_classes:
        assert (
            "frozen" in config_class.model_config
            and config_class.model_config["frozen"] is True
        ), f"{config_class.__name__} must be frozen"


# =============================================================================
# Async/Domain Purity Architecture Tests
# =============================================================================


# --- REQ-ARCH-005 ---
def test_domain_no_asyncio_import(src_dir: Path):
    """Domain layer must not import asyncio directly.

    The domain layer should remain pure and use abstract async types from
    collections.abc (AsyncIterator, Awaitable) instead of asyncio runtime.
    This ensures domain logic is testable without async event loops.

    Allowed: collections.abc.AsyncIterator, typing.Awaitable
    Forbidden: asyncio, anyio, trio
    """
    domain_path = src_dir / "bioetl" / "domain"
    forbidden_async_imports = {"asyncio", "anyio", "trio"}

    violations = []

    for py_file in domain_path.rglob("*.py"):
        with py_file.open(encoding="utf-8") as f:
            content = f.read()

        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            # Check "import asyncio" style
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    if module_name in forbidden_async_imports:
                        violations.append(
                            f"{py_file.relative_to(src_dir)}:{node.lineno}: "
                            f"Forbidden import 'import {alias.name}'"
                        )
            # Check "from asyncio import ..." style
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split(".")[0]
                    if module_name in forbidden_async_imports:
                        violations.append(
                            f"{py_file.relative_to(src_dir)}:{node.lineno}: "
                            f"Forbidden import 'from {node.module} import ...'"
                        )

    assert not violations, (
        "Domain layer must not import async runtime libraries.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
                                                                            "Use abstract types instead:\n"
                                                                            "  - collections.abc.AsyncIterator (for async generators)\n"
                                                                            "  - typing.Awaitable (for awaitable results)\n"
                                                                            "  - typing.Coroutine (for coroutine type hints)"
    )


# --- REQ-ARCH-006 ---
def test_port_async_methods_are_properly_typed():
    """Port async methods must have proper return type annotations.

    Async methods in ports must:
    1. Return AsyncIterator for streaming data (not just Iterator)
    2. Return Awaitable[T] or use async def for single values
    3. Never return raw coroutine objects without type hints

    This enables mypy to verify await usage at call sites.
    """
    async_ports = [
        (DataSourcePort, ["fetch", "health_check"]),
        (LockPort, ["acquire", "release", "heartbeat"]),
    ]

    violations = []

    for port_class, async_methods in async_ports:
        for method_name in async_methods:
            if not hasattr(port_class, method_name):
                violations.append(
                    f"{port_class.__name__}.{method_name}: Method not found"
                )
                continue

            method = getattr(port_class, method_name)

            # Check if method is defined as async or has async return type
            # For Protocol methods, check annotations
            try:
                hints = get_type_hints(method)
                return_type = hints.get("return")

                if return_type is None:
                    violations.append(
                        f"{port_class.__name__}.{method_name}: "
                        "Missing return type annotation"
                    )
            except Exception as e:
                # Type hints might not be resolvable in all contexts
                violations.append(
                    f"{port_class.__name__}.{method_name}: "
                    f"Could not resolve type hints: {e}"
                )

    assert not violations, (
        "Port async methods must have proper type annotations.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
                                                                            "Ensure async methods have:\n"
                                                                            "  - async def with proper return type\n"
                                                                            "  - AsyncIterator[T] for streaming methods\n"
                                                                            "  - Awaitable[T] for single-value async methods"
    )


# --- REQ-ARCH-007 ---
def test_io_ports_are_async():
    """I/O ports must have async methods for non-blocking operations.

    All ports that perform I/O operations (network, storage) should use
    async methods to enable concurrent execution without blocking.

    This ensures the pipeline can efficiently handle multiple concurrent
    operations (fetching data, writing to storage, acquiring locks, etc.).

    Note: MetricsPort is excluded as it uses sync methods for low-overhead
    metric collection (no actual I/O, just in-memory counters).
    """
    # Ports that should have async methods for I/O operations
    # MetricsPort excluded - uses sync methods for low-overhead operations
    async_io_ports = [
        (DataSourcePort, ["fetch", "health_check"]),
        (LockPort, ["acquire", "release", "heartbeat"]),
        (StoragePort, ["write_bronze", "write_silver", "write_gold"]),
        (CheckpointPort, ["save", "load", "list_all", "delete"]),
    ]

    violations = []

    for port_class, expected_async_methods in async_io_ports:
        for method_name in expected_async_methods:
            if not hasattr(port_class, method_name):
                violations.append(
                    f"{port_class.__name__}.{method_name}: Method not found"
                )
                continue

            method = getattr(port_class, method_name)

            # Check if it's an async method or async generator
            is_async = (
                inspect.iscoroutinefunction(method)
                or inspect.isasyncgenfunction(method)
            )
            if not is_async:
                violations.append(
                    f"{port_class.__name__}.{method_name}: "
                    "I/O port method should be async"
                )

    assert not violations, (
        "I/O ports must have async methods for non-blocking operations.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations) + "\n\n"
                                                                            "All ports performing I/O should use 'async def' for methods."
    )


# --- REQ-ARCH-009 ---
def test_metrics_port_is_sync():
    """MetricsPort must be synchronous for low-overhead operations.

    Unlike I/O ports, MetricsPort uses synchronous methods because:
    1. Metric collection should have minimal overhead
    2. Prometheus/StatsD clients use thread-safe in-memory counters
    3. No actual I/O happens during metric recording (batched export)
    """
    sync_methods = ["observe_histogram", "increment_counter"]

    violations = []

    for method_name in sync_methods:
        if not hasattr(MetricsPort, method_name):
            violations.append(f"MetricsPort.{method_name}: Method not found")
            continue

        method = getattr(MetricsPort, method_name)

        # Check if it's NOT an async method (should be sync)
        if inspect.iscoroutinefunction(method):
            violations.append(
                f"MetricsPort.{method_name}: "
                "Must be synchronous for low-overhead operations"
            )

    assert not violations, (
        "MetricsPort must be synchronous for low-overhead operations.\n"
        "Violations found:\n" + "\n".join(f"  - {v}" for v in violations)
    )


# --- REQ-ARCH-008 ---
def test_import_linter_contracts_exist(project_root: Path):
    """Import-linter configuration must exist with required contracts.

    Ensures architectural boundaries are enforced via import-linter.
    """
    importlinter_path = project_root / ".importlinter"
    assert importlinter_path.exists(), ".importlinter configuration file is missing"

    with importlinter_path.open(encoding="utf-8") as f:
        content = f.read()

    required_contracts = [
        "domain-independence",
        "domain-pure",
        "application-no-infrastructure-imports",
        "infrastructure-no-application",
    ]

    for contract in required_contracts:
        assert (
            f"[importlinter:contract:{contract}]" in content
        ), f"Missing import-linter contract: {contract}"

    # Check that asyncio is forbidden in domain
    assert "asyncio" in content, "asyncio should be forbidden in domain-pure contract"
