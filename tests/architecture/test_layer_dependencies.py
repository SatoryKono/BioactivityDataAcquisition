"""Tests for architectural layer dependencies.

These tests verify that the clean architecture layer boundaries are respected:
- Domain layer: No dependencies on infrastructure or external I/O libraries
- Application layer: Can depend on Domain, but not on Infrastructure or Composition
- Infrastructure layer: Implements Domain ports, can depend on external libraries

Uses both static analysis and import-linter for comprehensive checks.

Note: Tests for domain purity (frozen dataclasses, I/O checks, complexity) have been
moved to test_domain_purity.py. Adapter contract tests moved to test_adapter_contracts.py.
Forbidden import tests moved to test_forbidden_imports.py.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

# Infrastructure/I/O libraries that should NOT be in the domain layer
INFRASTRUCTURE_IMPORTS = {
    "httpx",
    "requests",
    "sqlalchemy",
    "psycopg2",
    "deltalake",
    "polars",
    "asyncpg",
    "motor",
    "prometheus_client",
    "pymongo",
}

# Application-specific imports that should NOT be in the domain layer
APPLICATION_IMPORTS = {
    "bioetl.application",
    "bioetl.infrastructure",
}


def _iter_python_content_under(
    root_path: Path,
    source_content_cache: dict[Path, str] | None = None,
) -> list[tuple[Path, str]]:
    """Return python file contents under ``root_path``, preferring session cache."""
    if source_content_cache is not None:
        return sorted(
            (
                (path, content)
                for path, content in source_content_cache.items()
                if root_path in path.parents
            ),
            key=lambda item: item[0],
        )
    return sorted(
        ((path, path.read_text(encoding="utf-8")) for path in root_path.rglob("*.py")),
        key=lambda item: item[0],
    )


def _import_errors_under(
    *,
    root_path: Path,
    disallowed: set[str],
    source_content_cache: dict[Path, str],
    skip: Callable[[Path], bool] | None = None,
) -> list[str]:
    errors: list[str] = []
    for py_file, content in _iter_python_content_under(root_path, source_content_cache):
        if skip is not None and skip(py_file):
            continue
        errors.extend(_check_imports_in_content(py_file, content, disallowed))
    return errors


def _check_imports_in_content(
    file_path: Path,
    content: str,
    disallowed: set[str],
) -> list[str]:
    """Check file content for disallowed imports."""
    errors = []
    for lib in disallowed:
        # Check for 'import lib' or 'from lib import ...'
        if re.search(rf"^\s*import\s+{re.escape(lib)}\b", content, re.MULTILINE):
            errors.append(f"Disallowed import 'import {lib}' in {file_path}")
        if re.search(rf"^\s*from\s+{re.escape(lib)}\b", content, re.MULTILINE):
            errors.append(f"Disallowed import 'from {lib}' in {file_path}")

    return errors


def _find_lint_imports_cmd(project_root: Path) -> str | None:
    """Resolve the lint-imports executable from PATH or the local virtualenv."""
    import shutil

    lint_imports_cmd = shutil.which("lint-imports")
    if lint_imports_cmd is not None:
        return lint_imports_cmd

    candidates = (
        project_root / ".venv" / "bin" / "lint-imports",
        project_root / ".venv" / "Scripts" / "lint-imports.exe",
        project_root / ".venv" / "Scripts" / "lint-imports",
    )
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _import_linter_skip_reason(result: subprocess.CompletedProcess[str]) -> str | None:
    """Return a skip reason for known environment-related import-linter failures."""
    combined_output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if any(
        marker in combined_output
        for marker in ("ModuleNotFoundError", "ImportError", "No module named")
    ):
        return (
            "Skipping import-linter due to missing optional dependencies. "
            "Install test extras and rerun lint-imports."
        )
    if result.stderr and (
        "UnicodeEncodeError" in result.stderr or "charmap" in result.stderr
    ):
        return (
            "Skipping due to Windows encoding issue with rich library. "
            "Run manually: lint-imports --config .importlinter"
        )
    return None


def _require_import_linter_capabilities() -> bool:
    """Return whether capability drift must fail instead of skip.

    Local/dev runs may still degrade when optional architecture-test dependencies
    are missing. Required CI paths export ``BIOETL_REQUIRE_TEST_CAPABILITIES=1``
    and must fail fast instead of silently skipping import-linter coverage.
    """
    return os.environ.get("BIOETL_REQUIRE_TEST_CAPABILITIES") == "1"


def _handle_import_linter_capability_gap(message: str) -> None:
    """Skip locally but fail fast when full test capabilities are required."""
    if _require_import_linter_capabilities():
        pytest.fail(message)
    pytest.skip(message)


def _mark_contentful_dirs(
    *,
    bioetl_path: Path,
    source_content_cache: dict[Path, str],
) -> set[Path]:
    """Mark directories whose subtree contains at least one non-empty module."""
    contentful_dirs: set[Path] = set()
    for py_file, content in _iter_python_content_under(
        bioetl_path, source_content_cache
    ):
        if py_file.name == "__init__.py" or not content.strip():
            continue
        current = py_file.parent
        while current != bioetl_path.parent:
            contentful_dirs.add(current)
            if current == bioetl_path:
                break
            current = current.parent
    return contentful_dirs


def _is_type_checking_import(
    *,
    lines: list[str],
    line_number: int,
) -> bool:
    """Return True when the target line is nested in an if TYPE_CHECKING block."""
    in_type_checking = False
    for current_line_number, check_line in enumerate(lines, 1):
        if "if TYPE_CHECKING:" in check_line:
            in_type_checking = True
        elif (
            in_type_checking
            and check_line.strip()
            and not check_line.startswith((" ", "\t"))
        ):
            in_type_checking = False
        if current_line_number == line_number:
            return in_type_checking
    return False


def _application_infra_import_violations(
    *,
    application_path: Path,
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> list[str]:
    """Collect application imports of infrastructure outside TYPE_CHECKING blocks."""
    violations: list[str] = []
    for py_file, content in _iter_python_content_under(
        application_path, source_content_cache
    ):
        lines = content.splitlines()
        for line_number, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith((">>>", "#")):
                continue
            if "from bioetl.infrastructure" not in line:
                continue
            if _is_type_checking_import(lines=lines, line_number=line_number):
                continue
            violations.append(
                f"{py_file.relative_to(src_dir)}:{line_number}: {stripped}"
            )
    return violations


def _is_orphan_directory(
    *,
    dir_path: Path,
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> str | None:
    """Return the relative orphan path when a leaf directory has only an empty __init__.py."""
    # Mounted/parallel test runs can prune transient cache dirs between discovery and scan.
    if not dir_path.exists():
        return None
    try:
        py_files = list(dir_path.glob("*.py"))
        subdirs = [child for child in dir_path.iterdir() if child.is_dir()]
    except FileNotFoundError:
        return None
    if subdirs or not py_files:
        return None

    init_file = dir_path / "__init__.py"
    if not init_file.exists() or len(py_files) != 1:
        return None

    init_content = source_content_cache.get(init_file, "").strip()
    if init_content and ("__all__" in init_content or "import" in init_content):
        return None
    return str(dir_path.relative_to(src_dir))


def _orphan_directories_from_python_cache(
    *,
    bioetl_path: Path,
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> list[str]:
    """Return orphan package directories using the session Python-file cache."""
    python_files_by_dir: dict[Path, list[Path]] = {}
    for py_file in source_content_cache:
        if bioetl_path not in py_file.parents:
            continue
        python_files_by_dir.setdefault(py_file.parent, []).append(py_file)

    dirs_with_python_children = {
        parent
        for py_dir in python_files_by_dir
        for parent in py_dir.parents
        if parent != py_dir and bioetl_path in parent.parents
    }
    contentful_dirs = _mark_contentful_dirs(
        bioetl_path=bioetl_path,
        source_content_cache=source_content_cache,
    )

    orphan_dirs = []
    for dir_path, py_files in sorted(python_files_by_dir.items()):
        if dir_path in contentful_dirs or dir_path in dirs_with_python_children:
            continue
        init_file = dir_path / "__init__.py"
        if py_files != [init_file]:
            continue
        init_content = source_content_cache.get(init_file, "").strip()
        if init_content and ("__all__" in init_content or "import" in init_content):
            continue
        orphan_dirs.append(dir_path.relative_to(src_dir).as_posix())
    return orphan_dirs


BASE_EXCEPTION_CLASSES = {
    "BioETLError",
    "CriticalError",
    "RecoverableError",
    "DataQualityError",
}

BIOETL_EXCEPTION_BASES = {
    "BioETLError",
    "CriticalError",
    "RecoverableError",
    "DataQualityError",
    "StorageError",
    "ApiError",
}

PORT_METHOD_PATTERNS = (
    "clear_",
    "write_",
    "read_",
    "load_",
    "save_",
    "delete_",
    "health_",
    "acquire",
    "release",
)

ALLOWED_HASATTR_CHECKS: set[str] = set()

VULTURE_IGNORED_NAMES = {
    "__init__",
    "__str__",
    "__repr__",
    "__hash__",
    "__eq__",
    "__lt__",
    "__le__",
    "__gt__",
    "__ge__",
    "__aenter__",
    "__aexit__",
    "__enter__",
    "__exit__",
    "exc_type",
    "exc_val",
    "exc_tb",
    "kind",
    "attributes",
    "links",
    "set_status_on_exception",
    "end_on_exit",
    "fetch",
    "write_bronze",
    "write_silver",
    "write_gold",
    "acquire",
    "release",
    "save_checkpoint",
    "load_checkpoint",
    "delete_checkpoint",
    "quarantine_record",
    "model_config",
    "main",
    "param",
    "execute",
    "awaitable",
}

RESERVED_API_PARAMS = {
    "overrides",
    "config_path",
    "watermark",
    "allows_retry",
    "compensation_required",
    "degraded_mode_allowed",
}


def _exception_files(src_dir: Path) -> list[Path]:
    exceptions_dir = src_dir / "bioetl" / "domain" / "exceptions"
    exceptions_file = src_dir / "bioetl" / "domain" / "exceptions.py"
    if exceptions_dir.is_dir():
        return [f for f in exceptions_dir.glob("*.py") if f.name != "__init__.py"]
    if exceptions_file.exists():
        return [exceptions_file]
    pytest.fail("Domain exceptions not found")


def _exception_class_bases(node: ast.ClassDef) -> list[str]:
    bases: list[str] = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            bases.append(base.id)
        elif isinstance(base, ast.Attribute):
            bases.append(base.attr)
    return bases


def _has_error_type_assignment(node: ast.ClassDef) -> bool:
    for stmt in node.body:
        if (
            isinstance(stmt, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "error_type"
                for target in stmt.targets
            )
        ) or (
            isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Name)
            and stmt.target.id == "error_type"
        ):
            return True
    return False


def _missing_exception_error_types(src_dir: Path) -> list[str]:
    missing_error_type: list[str] = []
    for path in _exception_files(src_dir):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if node.name in BASE_EXCEPTION_CLASSES:
                continue
            if not any(
                base in BIOETL_EXCEPTION_BASES for base in _exception_class_bases(node)
            ):
                continue
            if not _has_error_type_assignment(node):
                missing_error_type.append(node.name)
    return missing_error_type


def _hasattr_attr_name(node: ast.Call) -> str | None:
    if not (
        isinstance(node.func, ast.Name)
        and node.func.id == "hasattr"
        and len(node.args) >= 2
    ):
        return None
    attr_arg = node.args[1]
    if isinstance(attr_arg, ast.Constant) and isinstance(attr_arg.value, str):
        return attr_arg.value
    return None


def _is_suspicious_hasattr(attr_name: str) -> bool:
    if attr_name.startswith("_"):
        return False
    if attr_name in ALLOWED_HASATTR_CHECKS:
        return False
    return any(attr_name.startswith(pattern) for pattern in PORT_METHOD_PATTERNS)


def _application_hasattr_violations(
    application_path: Path,
    source_content_cache: dict[Path, str],
) -> list[str]:
    violations: list[str] = []
    for py_file, content in _iter_python_content_under(
        application_path, source_content_cache
    ):
        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            attr_name = _hasattr_attr_name(node)
            if attr_name and _is_suspicious_hasattr(attr_name):
                violations.append(
                    f"{py_file.name}:{node.lineno} - "
                    f"hasattr check for '{attr_name}' suggests missing port contract"
                )
    return violations


def _is_reportable_vulture_item(item: object) -> bool:
    name = getattr(item, "name", "")
    filename = str(getattr(item, "filename", ""))
    item_type = getattr(item, "typ", "")
    confidence = int(getattr(item, "confidence", 0))
    if name in VULTURE_IGNORED_NAMES or name in RESERVED_API_PARAMS:
        return False
    if str(name).startswith("_"):
        return False
    if "test" in filename.lower():
        return False
    if item_type == "import" and confidence < 100:
        return False
    return item_type != "unreachable_code"


def _dead_code_findings(src_dir: Path) -> list[object]:
    try:
        from vulture import Vulture
    except ImportError:
        pytest.skip("vulture not installed - run: pip install vulture")

    bioetl_path = src_dir / "bioetl"
    if not bioetl_path.exists():
        pytest.skip("bioetl source not found")

    vulture = Vulture()
    vulture.scavenge([str(bioetl_path)])
    return [
        item
        for item in vulture.get_unused_code(min_confidence=80)
        if _is_reportable_vulture_item(item)
    ]


def _format_dead_code_messages(unused: list[object]) -> list[str]:
    messages = [
        f"{item.filename}:{item.first_lineno} - "
        f"unused {item.typ} '{item.name}' "
        f"(confidence: {item.confidence}%)"
        for item in unused[:20]
    ]
    if len(unused) > 20:
        messages.append(f"... and {len(unused) - 20} more")
    return messages


def test_domain_layer_no_infrastructure_imports(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Domain layer must not import infrastructure/I/O libraries.

    REQ-ARCH-001: The domain layer should contain only pure business logic
    with no dependencies on external I/O libraries.
    """
    domain_path = src_dir / "bioetl" / "domain"
    assert domain_path.exists(), "Domain layer not found"

    all_errors = _import_errors_under(
        root_path=domain_path,
        disallowed=INFRASTRUCTURE_IMPORTS,
        source_content_cache=source_content_cache,
    )
    assert not all_errors, "\n".join(all_errors)


def test_domain_layer_no_application_imports(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Domain layer must not import from application layer.

    REQ-ARCH-002: Domain layer should be independent of application layer
    to maintain proper dependency direction (inward).
    """
    domain_path = src_dir / "bioetl" / "domain"
    assert domain_path.exists(), "Domain layer not found"

    all_errors = _import_errors_under(
        root_path=domain_path,
        disallowed=APPLICATION_IMPORTS,
        source_content_cache=source_content_cache,
    )
    assert not all_errors, "\n".join(all_errors)


def test_domain_layer_no_infrastructure_layer_imports(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Domain layer must not import from infrastructure layer.

    REQ-ARCH-003: Domain layer should not depend on infrastructure
    implementations, only define ports (interfaces).
    """
    domain_path = src_dir / "bioetl" / "domain"
    assert domain_path.exists(), "Domain layer not found"

    all_errors = _import_errors_under(
        root_path=domain_path,
        disallowed={"bioetl.infrastructure"},
        source_content_cache=source_content_cache,
    )
    assert not all_errors, "\n".join(all_errors)


def test_application_layer_no_common_infrastructure_adapter_imports(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Fast smoke check for historically regressed infrastructure imports.

    The authoritative rule is enforced by ``test_application_layer_no_infrastructure_imports``
    and import-linter. This test keeps a smaller, explicit denylist for the most
    architecture-sensitive infrastructure modules that previously regressed.
    """
    application_path = src_dir / "bioetl" / "application"
    assert application_path.exists(), "Application layer not found"

    implementation_imports = {
        "bioetl.infrastructure.adapters.chembl",
        "bioetl.infrastructure.adapters.pubchem",
        "bioetl.infrastructure.adapters.uniprot",
        "bioetl.infrastructure.adapters.pubmed",
        "bioetl.infrastructure.locking.memory_lock",
        "bioetl.infrastructure.checkpoint.local_checkpoint",
        "bioetl.infrastructure.quarantine.unified_quarantine",
    }

    all_errors = _import_errors_under(
        root_path=application_path,
        disallowed=implementation_imports,
        source_content_cache=source_content_cache,
        skip=lambda py_file: py_file.name == "__init__.py",
    )
    assert not all_errors, "\n".join(all_errors)


def test_ports_defined_in_domain_layer(src_dir: Path) -> None:
    """Ports (interfaces) must be defined in the domain layer.

    REQ-ARCH-005: All port definitions should live in domain/ports/ package
    """
    ports_dir = src_dir / "bioetl" / "domain" / "ports"
    assert ports_dir.exists(), "Domain ports package (domain/ports/) not found"
    assert ports_dir.is_dir(), "domain/ports should be a directory (package)"

    # Verify __init__.py exists (proper package)
    init_file = ports_dir / "__init__.py"
    assert init_file.exists(), "domain/ports/__init__.py not found"

    # Verify Protocol is used in at least one port file
    protocol_found = False
    for port_file in ports_dir.glob("*.py"):
        if port_file.name == "__init__.py":
            continue
        with port_file.open(encoding="utf-8") as f:
            if "Protocol" in f.read():
                protocol_found = True
                break

    assert protocol_found, "Ports should be defined using typing.Protocol"


@pytest.mark.slow
def test_import_linter_contracts(project_root: Path, src_dir: Path) -> None:
    """Run import-linter to verify all architectural contracts.

    REQ-ARCH-007: All import-linter contracts must pass.
    This provides a secondary layer of validation beyond static checks.
    """
    importlinter_config = project_root / ".importlinter"
    if not importlinter_config.exists():
        _handle_import_linter_capability_gap(".importlinter config not found")
        return

    lint_imports_cmd = _find_lint_imports_cmd(project_root)
    if lint_imports_cmd is None:
        _handle_import_linter_capability_gap("lint-imports executable not found")
        return

    # Override PYTHONPATH to ensure correct project is used
    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_dir)

    try:
        result = subprocess.run(
            [
                lint_imports_cmd,
                "--config",
                str(importlinter_config),
                "--cache-dir",
                "/tmp/bioetl-importlinter-cache",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(project_root),
            env=env,
        )
    except PermissionError:
        _handle_import_linter_capability_gap(
            "lint-imports executable exists but is not runnable in this environment"
        )
        return

    if result.returncode != 0:
        skip_reason = _import_linter_skip_reason(result)
        if skip_reason is not None:
            _handle_import_linter_capability_gap(skip_reason)
            return
        # When output is empty (e.g. Windows console capture), run without capture for diagnostics
        out = result.stdout.strip() or result.stderr.strip() or "(no output captured)"
        pytest.fail(
            f"import-linter contracts violated (exit {result.returncode}):\n{out}\n\n"
            "Run manually: lint-imports --config .importlinter"
        )


def test_infrastructure_does_not_import_application(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Infrastructure layer must not import from application layer.

    REQ-ARCH-008: Infrastructure is at the outer layer and should only
    implement domain ports, not depend on application services.
    """
    infra_path = src_dir / "bioetl" / "infrastructure"
    assert infra_path.exists(), "Infrastructure layer not found"

    all_errors = _import_errors_under(
        root_path=infra_path,
        disallowed={"bioetl.application"},
        source_content_cache=source_content_cache,
        skip=lambda py_file: py_file.name == "config.py",
    )
    assert not all_errors, "\n".join(all_errors)


def test_no_empty_source_files(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Source tree must not contain empty Python files (except __init__.py).

    REQ-ARCH-011: Empty files indicate dead code or incomplete implementation.
    Only __init__.py files are allowed to be empty (for package markers).
    """
    bioetl_path = src_dir / "bioetl"
    assert bioetl_path.exists(), "bioetl source not found"

    empty_files = []
    for py_file, raw_content in _iter_python_content_under(
        bioetl_path, source_content_cache
    ):
        # Skip __init__.py - allowed to be empty for package markers
        if py_file.name == "__init__.py":
            continue

        # Check if file is empty or contains only whitespace/comments
        content = raw_content.strip()

        # Remove comments and docstrings for content check
        lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]

        if not lines:
            empty_files.append(str(py_file.relative_to(src_dir)))

    assert not empty_files, (
        f"Found {len(empty_files)} empty source file(s) "
        "(excluding __init__.py):\n" + "\n".join(f"  - {f}" for f in empty_files)
    )


def test_no_orphan_directories(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Source tree must not contain orphan directories with only empty files.

    REQ-ARCH-012: Directories with only __init__.py or empty files are dead code.
    Directories that have subdirectories with content are not considered orphan.
    """
    bioetl_path = src_dir / "bioetl"
    assert bioetl_path.exists(), "bioetl source not found"

    orphan_dirs = _orphan_directories_from_python_cache(
        bioetl_path=bioetl_path,
        src_dir=src_dir,
        source_content_cache=source_content_cache,
    )

    assert not orphan_dirs, (
        f"Found {len(orphan_dirs)} orphan directory(s) with no real content:\n"
        + "\n".join(f"  - {d}" for d in orphan_dirs)
    )


def test_orphan_directory_detection_uses_cached_python_inventory(
    tmp_path: Path,
) -> None:
    """Synthetic regression guard for the cache-based orphan scan."""
    src_dir = tmp_path / "src"
    bioetl_path = src_dir / "bioetl"
    source_content_cache = {
        bioetl_path / "empty_pkg" / "__init__.py": "",
        bioetl_path / "export_pkg" / "__init__.py": "__all__ = ['value']\n",
        bioetl_path / "real_pkg" / "__init__.py": "",
        bioetl_path / "real_pkg" / "module.py": "VALUE = 1\n",
        bioetl_path / "parent_pkg" / "__init__.py": "",
        bioetl_path / "parent_pkg" / "child" / "module.py": "VALUE = 1\n",
    }

    assert _orphan_directories_from_python_cache(
        bioetl_path=bioetl_path,
        src_dir=src_dir,
        source_content_cache=source_content_cache,
    ) == ["bioetl/empty_pkg"]


@pytest.mark.slow
def test_dead_code_vulture(src_dir: Path) -> None:
    """Detect dead code using vulture static analysis (slow).

    REQ-ARCH-013: No unused code should exist in the codebase.
    """
    unused = _dead_code_findings(src_dir)

    if unused:
        pytest.fail(
            f"Found {len(unused)} potentially dead code item(s):\n"
            + "\n".join(_format_dead_code_messages(unused))
        )


def test_application_layer_no_infrastructure_imports(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Application layer must not import from infrastructure.

    REQ-ARCH-APP-002: Application layer depends on domain ports,
    not concrete infrastructure implementations.
    """
    application_path = src_dir / "bioetl" / "application"
    assert application_path.exists(), "Application layer not found"

    violations = _application_infra_import_violations(
        application_path=application_path,
        src_dir=src_dir,
        source_content_cache=source_content_cache,
    )

    assert not violations, (
        "Application layer imports infrastructure directly:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nUse dependency injection via domain ports instead."
    )


# I/O libraries that must NOT appear in the application layer.
# polars is intentionally excluded: it is a data-manipulation library used for
# in-memory DataFrame operations throughout the application layer, not an I/O
# or infrastructure concern.
_APPLICATION_FORBIDDEN_THIRD_PARTY = {
    "deltalake",
    "httpx",
    "requests",
    "sqlalchemy",
    "psycopg2",
    "asyncpg",
    "motor",
    "pymongo",
}


def test_application_layer_no_third_party_infrastructure_libs(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Application layer must not import third-party infrastructure libraries.

    REQ-ARCH-APP-003: Libraries like deltalake, httpx, requests belong in the
    infrastructure layer only. Application code must use domain ports to access
    their functionality.
    """
    application_path = src_dir / "bioetl" / "application"
    assert application_path.exists(), "Application layer not found"

    all_errors = _import_errors_under(
        root_path=application_path,
        disallowed=_APPLICATION_FORBIDDEN_THIRD_PARTY,
        source_content_cache=source_content_cache,
    )
    assert not all_errors, (
        "Application layer imports third-party infrastructure libraries:\n"
        + "\n".join(f"  - {e}" for e in all_errors)
        + "\n\nUse domain ports instead (ARCH-001)."
    )


def test_infrastructure_does_not_import_interfaces(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Infrastructure layer must not import from interfaces layer.

    REQ-ARCH-015: Interfaces (Driving Adapters) depend on Infrastructure,
    not the other way around. Prevents circular dependencies.
    """
    infra_path = src_dir / "bioetl" / "infrastructure"
    assert infra_path.exists(), "Infrastructure layer not found"

    all_errors = _import_errors_under(
        root_path=infra_path,
        disallowed={"bioetl.interfaces"},
        source_content_cache=source_content_cache,
    )
    assert not all_errors, "\n".join(all_errors)


def test_infrastructure_does_not_import_composition(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Infrastructure layer must not import from composition layer.

    REQ-ARCH-017: Composition is the assembly layer. Infrastructure
    must not depend on it to maintain proper dependency direction.
    See CLAUDE.md §2.1 Matrix of Imports.
    """
    infra_path = src_dir / "bioetl" / "infrastructure"
    assert infra_path.exists(), "Infrastructure layer not found"

    all_errors = _import_errors_under(
        root_path=infra_path,
        disallowed={"bioetl.composition"},
        source_content_cache=source_content_cache,
    )
    assert not all_errors, "Infrastructure must not import composition.\n" + "\n".join(
        all_errors
    )


def test_no_hasattr_duck_typing_in_application(
    src_dir: Path,
    source_content_cache: dict[Path, str],
) -> None:
    """Application layer should not use hasattr for port method checks.

    REQ-ARCH-017: The application layer should rely on explicit port contracts
    (Protocols) instead of duck-typing with hasattr. Using hasattr to check
    for port methods indicates missing contract definitions.

    Allowed exceptions:
    - TYPE_CHECKING blocks (static analysis only)
    - Checking for dunder methods (__enter__, __aiter__, etc.)
    - Checking for private attributes (_internal)
    - fetch_filtered: Extension method for filterable adapters (ChEMBL-specific)
    """
    application_path = src_dir / "bioetl" / "application"
    assert application_path.exists(), "Application layer not found"
    violations = _application_hasattr_violations(application_path, source_content_cache)

    assert not violations, (
        "Found hasattr duck-typing in application layer. "
        "Add missing methods to port contracts in domain/ports/ package:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


# ============================================================================
# Refactoring Tests (added for architecture cleanup)
# ============================================================================


def test_all_bioetl_exceptions_have_error_type(src_dir: Path) -> None:
    """All BioETLError subclasses MUST have explicit error_type attribute.

    REQ-ARCH-020: Deterministic error classification requires explicit mapping.
    This ensures ErrorClassifier uses the error_type attribute instead of
    keyword matching for domain exceptions.
    """
    missing_error_type = _missing_exception_error_types(src_dir)

    assert not missing_error_type, (
        "BioETLError subclasses must have explicit error_type attribute.\n"
        "Missing error_type:\n" + "\n".join(f"  - {c}" for c in missing_error_type)
    )


def test_observability_ports_have_close_method(src_dir: Path) -> None:
    """MetricsPort and TracingPort MUST define close() method.

    REQ-ARCH-021: Proper lifecycle management for observability resources.
    """
    observability_pkg = src_dir / "bioetl" / "domain" / "ports" / "observability"
    observability_file = src_dir / "bioetl" / "domain" / "ports" / "observability.py"
    if observability_pkg.is_dir():
        # Read all .py files in the package
        parts = [
            p.read_text(encoding="utf-8")
            for p in sorted(observability_pkg.rglob("*.py"))
        ]
        content = "\n".join(parts)
    elif observability_file.exists():
        with observability_file.open(encoding="utf-8") as f:
            content = f.read()
    else:
        pytest.fail("Domain ports observability file not found")

    import ast

    tree = ast.parse(content)

    required_ports = {"MetricsPort", "TracingPort"}
    found_close: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name in required_ports:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "close":
                    found_close.add(node.name)

    missing = required_ports - found_close
    assert not missing, f"Observability ports missing close() method: {missing}"


def test_storage_maintenance_port_has_preview_cleanup(src_dir: Path) -> None:
    """StorageMaintenancePort MUST define preview_cleanup() for CLI dry-run.

    REQ-ARCH-022: CLI delegates all storage operations to port.
    """
    storage_file = src_dir / "bioetl" / "domain" / "ports" / "storage_maintenance.py"
    assert storage_file.exists(), "Domain storage maintenance port file not found"
    content = storage_file.read_text(encoding="utf-8")

    assert "def preview_cleanup(" in content, (
        "StorageMaintenancePort must define preview_cleanup() for CLI dry-run support"
    )


def test_error_classifier_uses_error_type_attribute(src_dir: Path) -> None:
    """ErrorClassifier SHOULD use error_type attribute for BioETLError.

    REQ-ARCH-024: Deterministic error classification.
    """
    classifier_file = src_dir / "bioetl" / "domain" / "error_classifier.py"
    assert classifier_file.exists(), "Error classifier not found"

    with classifier_file.open(encoding="utf-8") as f:
        content = f.read()

    # Should have get_error_type() call for domain errors
    assert "get_error_type()" in content or "error_type" in content, (
        "ErrorClassifier should use error_type attribute for domain exceptions"
    )
