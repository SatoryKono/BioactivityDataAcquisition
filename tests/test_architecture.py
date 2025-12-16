import re
import subprocess
import tomllib
from pathlib import Path

import pytest

from bioetl.domain.ports import (
    CheckpointPort,
    DataSourcePort,
    LockPort,
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

    src_providers = {d.name for d in src_providers_path.iterdir() if d.is_dir()}
    docs_providers = {d.name for d in docs_providers_path.iterdir() if d.is_dir()}

    assert src_providers.issubset(
        docs_providers
    ), f"Missing doc folders for providers: {src_providers - docs_providers}"


# --- REQ-COMPLEXITY-001 ---
def test_code_complexity_with_xenon(src_dir: Path):
    """Code complexity must meet xenon thresholds (max-absolute B, max-modules B, max-average B).

    Runs: xenon --max-absolute B --max-modules B --max-average B --exclude "tests/*,src/tools/*" src

    Grade thresholds:
    - A: CC <= 5 (simple, low risk)
    - B: 6 <= CC <= 10 (more complex, moderate risk)
    - C: 11 <= CC <= 20 (complex, high risk)
    - D: 21 <= CC <= 30 (very complex, very high risk)
    - F: CC > 30 (unmaintainable)
    """
    try:
        result = subprocess.run(
            [
                "xenon",
                "--max-absolute",
                "B",
                "--max-modules",
                "B",
                "--max-average",
                "B",
                "--exclude",
                "tests/*,src/tools/*",
                str(src_dir),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        pytest.skip("xenon not installed, run: pip install xenon")

    assert result.returncode == 0, (
        f"Code complexity check failed.\n"
        f"xenon output:\n{result.stdout}\n{result.stderr}\n\n"
        f"Functions/modules exceed complexity threshold B (CC > 10).\n"
        f"Refactor complex code to reduce cyclomatic complexity."
    )


# --- REQ-LINT-001 ---
def test_ruff_check_passes(src_dir: Path, project_root: Path):
    """Code must pass ruff linting without errors.

    Runs: ruff check --fix src tests
    """
    tests_dir = project_root / "tests"
    try:
        result = subprocess.run(
            ["ruff", "check", "--fix", str(src_dir), str(tests_dir)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(project_root),
        )
    except FileNotFoundError:
        pytest.skip("ruff not installed, run: pip install ruff")

    # After fixing, run check again to ensure no errors remain
    if result.returncode != 0:
        try:
            result = subprocess.run(
                ["ruff", "check", str(src_dir), str(tests_dir)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(project_root),
            )
        except FileNotFoundError:
            pytest.skip("ruff not installed, run: pip install ruff")

    assert result.returncode == 0, (
        f"Ruff linting failed.\n"
        f"ruff output:\n{result.stdout}\n{result.stderr}\n\n"
        f"Fix linting errors before committing."
    )


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
                                                                            "  - get_aws_config()\n"
                                                                            "  - get_s3_config()\n"
                                                                            "  - get_redis_config()\n"
                                                                            "  - get_storage_options()"
    )


# --- REQ-ARCH-CLI-001 ---
@pytest.mark.xfail(
    reason="CLI has direct infrastructure imports - architectural debt to be refactored",
    strict=False,
)
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
        r"from\s+bioetl\.infrastructure\.observability\b",
        r"import\s+bioetl\.infrastructure\.adapters\b",
        r"import\s+bioetl\.infrastructure\.checkpoint\b",
        r"import\s+bioetl\.infrastructure\.locking\b",
        r"import\s+bioetl\.infrastructure\.storage\b",
        r"import\s+bioetl\.infrastructure\.quarantine\b",
        r"import\s+bioetl\.infrastructure\.observability\b",
    ]

    violations = []

    for pattern in disallowed_infrastructure_modules:
        matches = re.finditer(pattern, content)
        for match in matches:
            line_num = content[: match.start()].count("\n") + 1
            violations.append(f"Line {line_num}: {match.group()}")

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

    All os.getenv calls in config.py should either:
    - Provide a default value for optional settings
    - Be documented as required (will cause clear error if missing)

    This test checks that config functions return valid typed objects
    even with no environment variables set.

    Runs: Import and call config functions
    """
    # Import config module
    import sys

    sys.path.insert(0, str(src_dir))

    from bioetl.config import (
        get_aws_config,
        get_redis_config,
        get_s3_config,
        get_storage_options,
    )

    # Test that all config functions can be called without environment variables
    # (they should return objects with sensible defaults or None for optional values)
    aws_config = get_aws_config()
    assert aws_config is not None
    assert isinstance(aws_config.region, str)
    # endpoint_url can be None (optional)

    s3_config = get_s3_config()
    assert s3_config is not None
    assert s3_config.bucket_bronze == "bioetl-bronze"
    assert s3_config.bucket_silver == "bioetl-silver"
    assert s3_config.bucket_gold == "bioetl-gold"
    assert s3_config.bucket_checkpoints == "bioetl-checkpoints"

    redis_config = get_redis_config()
    assert redis_config is not None
    assert redis_config.host == "localhost"
    assert redis_config.port == 6379

    storage_options = get_storage_options()
    # Should be None when endpoint_url is not set
    assert storage_options is None or isinstance(storage_options, dict)


# --- REQ-CONFIG-002 ---
def test_config_dataclasses_are_frozen(src_dir: Path):
    """Configuration dataclasses must be immutable (frozen=True).

    This ensures configuration cannot be accidentally modified at runtime.
    """
    import sys

    sys.path.insert(0, str(src_dir))

    from bioetl.config import AWSConfig, RedisConfig, S3Config

    config_classes = [AWSConfig, S3Config, RedisConfig]

    for config_class in config_classes:
        assert hasattr(
            config_class, "__dataclass_fields__"
        ), f"{config_class.__name__} is not a dataclass"

        # Check frozen attribute
        # In Python 3.10+, we can check __dataclass_params__.frozen
        if hasattr(config_class, "__dataclass_params__"):
            assert (
                config_class.__dataclass_params__.frozen
            ), f"{config_class.__name__} dataclass must be frozen"
        else:
            # Fallback: try to modify an instance and expect error
            if config_class == AWSConfig:
                instance = config_class(
                    endpoint_url=None,
                    access_key_id=None,
                    secret_access_key=None,
                    region="us-east-1",
                )
            elif config_class == S3Config:
                instance = config_class(
                    bucket_bronze="b",
                    bucket_silver="s",
                    bucket_gold="g",
                    bucket_checkpoints="c",
                )
            else:  # RedisConfig
                instance = config_class(host="localhost", port=6379)

            with pytest.raises((TypeError, AttributeError)):  # FrozenInstanceError
                instance.region = "changed"  # type: ignore[attr-defined]
