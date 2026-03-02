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


class TestModuleDocstrings:
    """Tests ensuring modules have proper documentation."""

    def test_port_modules_have_docstrings(self, src_dir: Path) -> None:
        """Port modules MUST have module-level docstrings.

        REQ-DOC-001: Port files should document what contracts they define.
        """
        ports_dir = src_dir / "bioetl" / "domain" / "ports"
        if not ports_dir.exists():
            pytest.skip("Domain ports not found")

        missing_docstrings = []

        for py_file in ports_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            with py_file.open(encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read())
                except SyntaxError:
                    continue

            # Check for module docstring
            if not ast.get_docstring(tree):
                relative_path = py_file.relative_to(src_dir)
                missing_docstrings.append(str(relative_path))

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
        if not pipelines_dir.exists():
            pytest.skip("Application pipelines not found")

        missing_docstrings = []

        for py_file in pipelines_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            with py_file.open(encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read())
                except SyntaxError:
                    continue

            # Check for module docstring
            if not ast.get_docstring(tree):
                relative_path = py_file.relative_to(src_dir)
                missing_docstrings.append(str(relative_path))

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
        if not ports_dir.exists():
            pytest.skip("Domain ports not found")

        missing_docstrings = []

        for py_file in ports_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            with py_file.open(encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read())
                except SyntaxError:
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a Protocol class
                    is_protocol = any(
                        (isinstance(base, ast.Name) and base.id == "Protocol")
                        or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
                        for base in node.bases
                    )

                    if is_protocol and not ast.get_docstring(node):
                        relative_path = py_file.relative_to(src_dir)
                        missing_docstrings.append(
                            f"{relative_path}:{node.lineno} - class {node.name}"
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
        if not adapters_dir.exists():
            pytest.skip("Infrastructure adapters not found")

        # Excluded utility files
        excluded_files = {
            "__init__.py",
            "base.py",
            "types.py",
            "exceptions.py",
        }

        missing_docstrings = []

        for py_file in adapters_dir.rglob("*.py"):
            if py_file.name in excluded_files:
                continue

            with py_file.open(encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read())
                except SyntaxError:
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Skip private classes
                    if node.name.startswith("_"):
                        continue

                    # Check if it looks like an adapter
                    is_adapter = (
                        "Adapter" in node.name
                        or "Client" in node.name
                        or "Fetcher" in node.name
                    )

                    if is_adapter and not ast.get_docstring(node):
                        relative_path = py_file.relative_to(src_dir)
                        missing_docstrings.append(
                            f"{relative_path}:{node.lineno} - class {node.name}"
                        )

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
        if not ports_dir.exists():
            pytest.skip("Domain ports not found")

        missing_docstrings = []

        for py_file in ports_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            with py_file.open(encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read())
                except SyntaxError:
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's a Protocol class
                    is_protocol = any(
                        (isinstance(base, ast.Name) and base.id == "Protocol")
                        or (isinstance(base, ast.Attribute) and base.attr == "Protocol")
                        for base in node.bases
                    )

                    if not is_protocol:
                        continue

                    # Check methods in Protocol
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            # Skip private methods
                            if item.name.startswith("_"):
                                continue

                            if not ast.get_docstring(item):
                                relative_path = py_file.relative_to(src_dir)
                                missing_docstrings.append(
                                    f"{relative_path}:{item.lineno} - "
                                    f"{node.name}.{item.name}()"
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
            pytest.skip("Domain exceptions not found")

        missing_docstrings = []

        for py_file in exception_files:
            with py_file.open(encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read())
                except SyntaxError:
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it looks like an exception
                    is_exception = any(
                        (isinstance(base, ast.Name) and "Error" in base.id)
                        or (isinstance(base, ast.Name) and "Exception" in base.id)
                        for base in node.bases
                    )

                    if is_exception and not ast.get_docstring(node):
                        relative_path = py_file.relative_to(src_dir)
                        missing_docstrings.append(
                            f"{relative_path}:{node.lineno} - class {node.name}"
                        )

        # This is a SHOULD, not a MUST, so we only warn
        if missing_docstrings:
            pytest.skip(
                f"Found {len(missing_docstrings)} exception classes without docstrings "
                "(SHOULD have docstrings): "
                + ", ".join(m.split(" - ")[1] for m in missing_docstrings[:5])
            )
