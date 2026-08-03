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
"""Architecture tests: Documentation and docstring requirements.

These tests verify that code is properly documented:
- Public classes have docstrings
- Public methods have docstrings
- Port interfaces have method docstrings
- Modules have module-level docstrings

REQ-DOC-001: Public API must be documented with docstrings.
REQ-DOC-002: Port methods must describe contracts.

See CLAUDE.md §12 Self-Review Checklist.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


# A cold recursive source read on cloud-synced Windows worktrees can exceed the
# global 60-second per-test guard even though the scan is bounded to src/bioetl.
# Keep the assertion strict while allowing the supported Windows/GDrive lane to
# finish its filesystem I/O.
pytestmark = [pytest.mark.architecture, pytest.mark.timeout(180)]


def _iter_parsed_python_modules(
    base_dir: Path,
    *,
    recursive: bool,
    excluded_files: set[str],
) -> list[tuple[Path, ast.Module]]:
    pattern = "**/*.py" if recursive else "*.py"
    parsed: list[tuple[Path, ast.Module]] = []
    for py_file in base_dir.glob(pattern):
        if py_file.name in excluded_files:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        parsed.append((py_file, tree))
    return parsed


def _is_protocol_class(node: ast.ClassDef) -> bool:
    return any(
        (isinstance(base, ast.Name) and base.id == "Protocol")
        or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
        for base in node.bases
    )


def _missing_module_docstrings(
    parsed_modules: list[tuple[Path, ast.Module]],
    *,
    src_dir: Path,
) -> list[str]:
    missing: list[str] = []
    for py_file, tree in parsed_modules:
        if not ast.get_docstring(tree):
            missing.append(str(py_file.relative_to(src_dir)))
    return missing


def _missing_protocol_class_docstrings(
    parsed_modules: list[tuple[Path, ast.Module]],
    *,
    src_dir: Path,
) -> list[str]:
    missing: list[str] = []
    for py_file, tree in parsed_modules:
        relative_path = py_file.relative_to(src_dir)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and _is_protocol_class(node):
                if not ast.get_docstring(node):
                    missing.append(f"{relative_path}:{node.lineno} - class {node.name}")
    return missing


def _missing_protocol_method_docstrings(
    parsed_modules: list[tuple[Path, ast.Module]],
    *,
    src_dir: Path,
) -> list[str]:
    missing: list[str] = []
    for py_file, tree in parsed_modules:
        relative_path = py_file.relative_to(src_dir)
        for node in ast.walk(tree):
            if not _is_protocol_class_node(node):
                continue
            missing.extend(_missing_protocol_methods_for_class(relative_path, node))
    return missing


def _is_protocol_class_node(node: ast.AST) -> bool:
    return isinstance(node, ast.ClassDef) and _is_protocol_class(node)


def _is_public_method_without_docstring(item: ast.stmt) -> bool:
    if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    if item.name.startswith("_"):
        return False
    return not ast.get_docstring(item)


def _missing_protocol_methods_for_class(
    relative_path: Path,
    node: ast.ClassDef,
) -> list[str]:
    return [
        f"{relative_path}:{item.lineno} - {node.name}.{item.name}()"
        for item in node.body
        if _is_public_method_without_docstring(item)
    ]


def _missing_exception_docstrings(
    exception_files: list[Path],
    *,
    src_dir: Path,
) -> list[str]:
    missing: list[str] = []
    for py_file in exception_files:
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        relative_path = py_file.relative_to(src_dir)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            is_exception = any(
                isinstance(base, ast.Name)
                and ("Error" in base.id or "Exception" in base.id)
                for base in node.bases
            )
            if is_exception and not ast.get_docstring(node):
                missing.append(f"{relative_path}:{node.lineno} - class {node.name}")
    return missing


def _iter_public_class_defs(tree: ast.AST) -> list[ast.ClassDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_")
    ]


def _looks_like_adapter_class(node: ast.ClassDef) -> bool:
    return any(marker in node.name for marker in ("Adapter", "Client", "Fetcher"))


def _missing_adapter_class_docstrings(py_file: Path, *, src_dir: Path) -> list[str]:
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return []

    relative_path = py_file.relative_to(src_dir)
    return [
        f"{relative_path}:{node.lineno} - class {node.name}"
        for node in _iter_public_class_defs(tree)
        if _looks_like_adapter_class(node) and not ast.get_docstring(node)
    ]


def _iter_adapter_python_files(adapters_dir: Path) -> list[Path]:
    excluded_files = {
        "__init__.py",
        "base.py",
        "types.py",
        "exceptions.py",
    }
    return [
        py_file
        for py_file in adapters_dir.rglob("*.py")
        if py_file.name not in excluded_files
    ]


class TestModuleDocstrings:
    """Tests ensuring modules have proper documentation."""

    def test_port_modules_have_docstrings(self, src_dir: Path) -> None:
        """Port modules MUST have module-level docstrings.

        REQ-DOC-001: Port files should document what contracts they define.
        """
        ports_dir = src_dir / "bioetl" / "domain" / "ports"
        assert ports_dir.exists(), "Domain ports not found"
        parsed_modules = _iter_parsed_python_modules(
            ports_dir, recursive=False, excluded_files={"__init__.py"}
        )
        missing_docstrings = _missing_module_docstrings(parsed_modules, src_dir=src_dir)

        assert not missing_docstrings, (
            "Port modules must have module-level docstrings.\n"
            "Missing docstrings in:\n"
            + "\n".join(f"  - {f}" for f in missing_docstrings)
        )

    def test_pipeline_modules_have_docstrings(self, src_dir: Path) -> None:
        """Pipeline modules MUST have module-level docstrings.

        REQ-DOC-001: Pipeline files should document their purpose.
        """
        pipelines_dir = src_dir / "bioetl" / "application" / "pipelines"
        assert pipelines_dir.exists(), "Application pipelines not found"
        parsed_modules = _iter_parsed_python_modules(
            pipelines_dir, recursive=True, excluded_files={"__init__.py"}
        )
        missing_docstrings = _missing_module_docstrings(parsed_modules, src_dir=src_dir)

        assert not missing_docstrings, (
            "Pipeline modules must have module-level docstrings.\n"
            "Missing docstrings in:\n"
            + "\n".join(f"  - {f}" for f in missing_docstrings)
        )


class TestClassDocstrings:
    """Tests ensuring classes have proper documentation."""

    def test_port_protocols_have_docstrings(self, src_dir: Path) -> None:
        """Port Protocol classes MUST have class-level docstrings.

        REQ-DOC-002: Port interfaces should document their contracts.
        """
        ports_dir = src_dir / "bioetl" / "domain" / "ports"
        assert ports_dir.exists(), "Domain ports not found"
        parsed_modules = _iter_parsed_python_modules(
            ports_dir, recursive=False, excluded_files={"__init__.py"}
        )
        missing_docstrings = _missing_protocol_class_docstrings(
            parsed_modules, src_dir=src_dir
        )

        assert not missing_docstrings, (
            "Port Protocol classes must have docstrings.\n"
            "Missing docstrings in:\n"
            + "\n".join(f"  - {f}" for f in missing_docstrings)
        )

    def test_adapter_classes_have_docstrings(self, src_dir: Path) -> None:
        """Adapter classes MUST have class-level docstrings.

        REQ-DOC-001: Adapters should document what port they implement.
        """
        adapters_dir = src_dir / "bioetl" / "infrastructure" / "adapters"
        assert adapters_dir.exists(), "Infrastructure adapters not found"
        missing_docstrings = [
            missing
            for py_file in _iter_adapter_python_files(adapters_dir)
            for missing in _missing_adapter_class_docstrings(py_file, src_dir=src_dir)
        ]

        assert not missing_docstrings, (
            "Adapter classes must have docstrings.\n"
            "Missing docstrings in:\n"
            + "\n".join(f"  - {f}" for f in missing_docstrings)
        )


class TestMethodDocstrings:
    """Tests ensuring key methods have proper documentation."""

    def test_port_methods_have_docstrings(self, src_dir: Path) -> None:
        """Port Protocol methods MUST have docstrings describing contracts.

        REQ-DOC-002: Each port method should document its contract.
        """
        ports_dir = src_dir / "bioetl" / "domain" / "ports"
        assert ports_dir.exists(), "Domain ports not found"
        parsed_modules = _iter_parsed_python_modules(
            ports_dir, recursive=False, excluded_files={"__init__.py"}
        )
        missing_docstrings = _missing_protocol_method_docstrings(
            parsed_modules, src_dir=src_dir
        )

        assert not missing_docstrings, (
            "Port Protocol methods must have docstrings.\n"
            "Missing docstrings in:\n"
            + "\n".join(f"  - {f}" for f in missing_docstrings)
        )


class TestExceptionDocstrings:
    """Tests ensuring exceptions have proper documentation."""

    def test_domain_exceptions_have_docstrings(self, src_dir: Path) -> None:
        """Domain exception classes SHOULD have docstrings.

        REQ-DOC-001: Exceptions should document when they are raised.
        """
        # Support both single file and package structure
        exceptions_dir = src_dir / "bioetl" / "domain" / "exceptions"
        exceptions_file = src_dir / "bioetl" / "domain" / "exceptions.py"

        exception_files: list[Path] = []
        if exceptions_dir.is_dir():
            exception_files = [
                f for f in exceptions_dir.glob("*.py") if f.name != "__init__.py"
            ]
        elif exceptions_file.exists():
            exception_files = [exceptions_file]
        else:
            pytest.fail("Domain exceptions not found")

        missing_docstrings = _missing_exception_docstrings(
            exception_files, src_dir=src_dir
        )

        # This is a SHOULD, not a MUST, so we only warn
        if missing_docstrings:
            pytest.skip(
                f"Found {len(missing_docstrings)} exception classes without docstrings "
                "(SHOULD have docstrings): "
                + ", ".join(m.split(" - ")[1] for m in missing_docstrings[:5])
            )
