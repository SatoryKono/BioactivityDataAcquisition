# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture test: structlog только в infrastructure/composition слоях.

REQ-ARCH-001: Application, domain и interfaces слои используют LoggerPort абстракцию.
См. ADR-006 для обоснования.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

APPLICATION_DIR = Path("src/bioetl/application")
DOMAIN_DIR = Path("src/bioetl/domain")
INTERFACES_DIR = Path("src/bioetl/interfaces")

# Baseline exemptions for existing files (technical debt)
# These files need refactoring to use LoggerPort instead of direct structlog
# NOTE: As of 2025-12-26, all exemptions have been resolved.
EXEMPTED_FILES: set[str] = set()


def _check_structlog_imports(
    directory: Path,
    exempted: set[str] | None = None,
    *,
    trees: Mapping[Path, ast.Module] | None = None,
) -> list[str]:
    """Check for direct structlog imports in a directory.

    Args:
        directory: Directory to scan for Python files.
        exempted: Set of file paths to exempt from checking.

    Returns:
        List of violation messages with file path and line number.
    """
    if exempted is None:
        exempted = set()

    violations = []

    if not directory.exists():
        return violations

    for py_file in directory.rglob("*.py"):
        rel_path = py_file.relative_to(Path("src"))
        if _normalize_rel_path(rel_path) in exempted:
            continue

        tree = _read_ast_or_none(py_file, trees)
        if tree is None:
            continue

        violations.extend(_iter_structlog_import_violations(tree, rel_path))

    return violations


def _normalize_rel_path(rel_path: Path) -> str:
    return str(rel_path).replace("\\", "/")


def _read_ast_or_none(
    py_file: Path, trees: Mapping[Path, ast.Module] | None = None
) -> ast.Module | None:
    # Layer constants are relative, whereas the shared fixture keys are absolute.
    # Do not resolve each path through the mounted filesystem again.
    key = py_file.absolute()
    if trees is not None and key in trees:
        return trees[key]
    try:
        return ast.parse(py_file.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return None


def _iter_structlog_import_violations(tree: ast.Module, rel_path: Path) -> list[str]:
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(
                f"{rel_path}:{node.lineno}: import structlog"
                for alias in node.names
                if alias.name == "structlog"
            )
            continue
        if isinstance(node, ast.ImportFrom) and _is_structlog_import_from(node):
            violations.append(
                f"{rel_path}:{node.lineno}: from {node.module} import ..."
            )
    return violations


def _is_structlog_import_from(node: ast.ImportFrom) -> bool:
    return bool(node.module and node.module.startswith("structlog"))


class TestNoStructlogInApplicationLayer:
    """Test that application layer does not import structlog directly."""

    def test_no_structlog_in_application_layer(
        self, source_ast_cache: dict[Path, ast.Module]
    ) -> None:
        """Application layer MUST NOT import structlog directly.

        REQ-ARCH-001: Use LoggerPort abstraction instead.
        See ADR-006 for rationale.
        """
        violations = _check_structlog_imports(
            APPLICATION_DIR, EXEMPTED_FILES, trees=source_ast_cache
        )

        assert not violations, (
            "Direct structlog imports found in application layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nUse LoggerPort from domain.ports instead. See ADR-006."
        )


class TestNoStructlogInInterfacesLayer:
    """Test that interfaces layer does not import structlog directly."""

    def test_no_structlog_in_interfaces_layer(
        self, source_ast_cache: dict[Path, ast.Module]
    ) -> None:
        """Interfaces layer MUST NOT import structlog directly.

        REQ-ARCH-001: Use LoggerPort abstraction instead.
        See ADR-006 for rationale.
        """
        violations = _check_structlog_imports(
            INTERFACES_DIR, EXEMPTED_FILES, trees=source_ast_cache
        )

        assert not violations, (
            "Direct structlog imports found in interfaces layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nUse LoggerPort from domain.ports instead. See ADR-006."
        )


class TestNoStructlogInDomainLayer:
    """Test that domain layer does not import structlog directly."""

    def test_no_structlog_in_domain_layer(
        self, source_ast_cache: dict[Path, ast.Module]
    ) -> None:
        """Domain layer MUST NOT import structlog directly."""
        violations = _check_structlog_imports(
            DOMAIN_DIR, EXEMPTED_FILES, trees=source_ast_cache
        )

        assert not violations, (
            "Direct structlog imports found in domain layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nDomain layer MUST use pure business logic or LoggerPort-owned boundaries."
        )


@pytest.mark.parametrize(
    "layer_name,layer_dir",
    [
        ("application", APPLICATION_DIR),
        ("domain", DOMAIN_DIR),
        ("interfaces", INTERFACES_DIR),
    ],
)
def test_no_structlog_parametrized(
    layer_name: str, layer_dir: Path, source_ast_cache: dict[Path, ast.Module]
) -> None:
    """Parametrized test for structlog imports in multiple layers.

    Args:
        layer_name: Name of the layer being tested.
        layer_dir: Directory path of the layer.
    """
    violations = _check_structlog_imports(
        layer_dir, EXEMPTED_FILES, trees=source_ast_cache
    )

    assert not violations, (
        f"Direct structlog imports found in {layer_name} layer:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + f"\n\nThe {layer_name} layer MUST use LoggerPort abstraction. See ADR-006."
    )


def _check_structlog_boundlogger_usage(
    directory: Path, content: Mapping[Path, str] | None = None
) -> list[str]:
    """Check for structlog.BoundLogger type annotations in source code.

    Scans Python files for usage of 'structlog.BoundLogger' as type annotation.
    This catches cases where structlog types are used even inside TYPE_CHECKING blocks.

    Args:
        directory: Directory to scan for Python files.

    Returns:
        List of violation messages with file path and line number.
    """
    if not directory.exists():
        return []

    violations: list[str] = []
    for py_file in directory.rglob("*.py"):
        rel_path = py_file.relative_to(Path("src"))
        violations.extend(_iter_boundlogger_line_violations(py_file, rel_path, content))

    return violations


def _iter_boundlogger_line_violations(
    py_file: Path, rel_path: Path, content: Mapping[Path, str] | None = None
) -> list[str]:
    try:
        key = py_file.absolute()
        source = (
            content[key]
            if content is not None and key in content
            else py_file.read_text(encoding="utf-8")
        )
        lines = source.splitlines()
    except (UnicodeDecodeError, OSError):
        return []
    return [
        f"{rel_path}:{lineno}: {line.strip()}"
        for lineno, line in enumerate(lines, start=1)
        if "structlog.BoundLogger" in line
    ]


def test_no_structlog_boundlogger_in_application(
    source_content_cache: dict[Path, str],
) -> None:
    """Application layer MUST use LoggerPort, not structlog.BoundLogger.

    REQ-ARCH-001: The application layer should be decoupled from
    concrete logging implementations. Use LoggerPort from domain.ports.

    This test ensures that structlog.BoundLogger is not used as a type
    annotation anywhere in the application layer, including in
    TYPE_CHECKING blocks.
    """
    violations = _check_structlog_boundlogger_usage(
        APPLICATION_DIR, source_content_cache
    )

    assert not violations, (
        "structlog.BoundLogger usage found in application layer:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nApplication layer MUST use LoggerPort, not structlog.BoundLogger."
        + "\nImport LoggerPort from bioetl.domain.ports instead."
    )


def test_structlog_snapshot_retains_relative_path_violations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = Path("src/package/source.py")
    source.parent.mkdir(parents=True)
    text = "from structlog.contextvars import bind_contextvars\n"
    source.write_text(text, encoding="utf-8")
    trees = {source.absolute(): ast.parse(text)}

    observed = _check_structlog_imports(Path("src"), trees=trees)

    assert observed == _check_structlog_imports(Path("src"))
    assert observed == [
        f"{Path('package/source.py')}:1: from structlog.contextvars import ..."
    ]


def test_structlog_snapshot_miss_scans_new_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = Path("src/new.py")
    source.parent.mkdir()
    source.write_text("import structlog\n", encoding="utf-8")

    assert _check_structlog_imports(Path("src"), trees={}) == [
        "new.py:1: import structlog"
    ]


def test_structlog_snapshot_miss_preserves_invalid_syntax_policy(
    tmp_path: Path,
) -> None:
    source = tmp_path / "invalid.py"
    source.write_text("def invalid(:\n", encoding="utf-8")

    assert _read_ast_or_none(source, {}) is None


def test_boundlogger_snapshot_retains_relative_path_violations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    source = Path("src/logger.py")
    source.parent.mkdir()
    text = "logger: structlog.BoundLogger\n"
    source.write_text(text, encoding="utf-8")

    observed = _check_structlog_boundlogger_usage(
        Path("src"), {source.absolute(): text}
    )

    assert observed == _check_structlog_boundlogger_usage(Path("src"))
    assert observed == ["logger.py:1: logger: structlog.BoundLogger"]
