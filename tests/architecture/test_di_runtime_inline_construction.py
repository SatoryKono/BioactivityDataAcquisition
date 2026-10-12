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
"""Architecture test: runtime inline dependency construction in application layer.

P1 DI hardening guard:
- application layer must not assemble dependency objects at runtime via
  inline assignments such as ``x = SomeService(...)``.
- composition layer remains the only assembly root.

Temporary exemptions:
- annotate source line with ``EXC-002`` or ``EXC-003``.
"""

from __future__ import annotations

import pytest

import ast
from pathlib import Path
from typing import NamedTuple


pytestmark = pytest.mark.architecture

APPLICATION_DIR = Path("src/bioetl/application")
EXEMPTION_MARKERS = ("EXC-002", "EXC-003")
DEPENDENCY_SUFFIXES = (
    "Service",
    "Factory",
    "Adapter",
    "Client",
    "Manager",
    "Policy",
    "Monitor",
    "Observer",
    "Validator",
)
EXCLUDED_CONSTRUCTOR_NAMES = {"MedallionPolicy"}


class RuntimeInlineConstructionViolation(NamedTuple):
    """Violation for runtime dependency construction in assignment."""

    file_path: Path
    line_number: int
    containing_class: str
    containing_function: str
    assignment_target: str
    constructor_name: str
    source_line: str


def _get_base_path(relative_path: Path) -> Path:
    if relative_path.exists():
        return relative_path
    return Path(__file__).parent.parent.parent / relative_path


def _extract_constructor_name(call_node: ast.Call) -> str | None:
    if isinstance(call_node.func, ast.Name):
        return call_node.func.id
    if isinstance(call_node.func, ast.Attribute):
        return call_node.func.attr
    return None


def _extract_target_name(target: ast.expr) -> str:
    if isinstance(target, ast.Attribute):
        if isinstance(target.value, ast.Name):
            return f"{target.value.id}.{target.attr}"
        return target.attr
    if isinstance(target, ast.Name):
        return target.id
    return "<complex>"


class _RuntimeInlineConstructionFinder(ast.NodeVisitor):
    def __init__(self, source_lines: list[str]) -> None:
        self._source_lines = source_lines
        self._current_class = "<module>"
        self._current_function = "<module>"
        self.violations: list[RuntimeInlineConstructionViolation] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        prev = self._current_class
        self._current_class = node.name
        self.generic_visit(node)
        self._current_class = prev

    def _visit_function_scope(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        prev = self._current_function
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = prev

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_scope(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_scope(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        target = node.targets[0] if node.targets else None
        self._check_assignment(target, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._check_assignment(node.target, node.value, node.lineno)
        self.generic_visit(node)

    def _check_assignment(
        self,
        target: ast.expr | None,
        value: ast.expr | None,
        lineno: int,
    ) -> None:
        if target is None or value is None or not isinstance(value, ast.Call):
            return

        constructor_name = _extract_constructor_name(value)
        if constructor_name is None:
            return
        if constructor_name in EXCLUDED_CONSTRUCTOR_NAMES:
            return
        if not constructor_name.endswith(DEPENDENCY_SUFFIXES):
            return

        source_line = self._source_lines[lineno - 1]
        if any(marker in source_line for marker in EXEMPTION_MARKERS):
            return

        self.violations.append(
            RuntimeInlineConstructionViolation(
                file_path=Path(""),
                line_number=lineno,
                containing_class=self._current_class,
                containing_function=self._current_function,
                assignment_target=_extract_target_name(target),
                constructor_name=constructor_name,
                source_line=source_line.strip(),
            )
        )


def _collect_runtime_inline_construction_violations() -> list[
    RuntimeInlineConstructionViolation
]:
    base = _get_base_path(APPLICATION_DIR)
    violations: list[RuntimeInlineConstructionViolation] = []

    for py_file in sorted(base.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        source_lines = source.splitlines()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        finder = _RuntimeInlineConstructionFinder(source_lines)
        finder.visit(tree)

        for violation in finder.violations:
            violations.append(
                violation._replace(
                    file_path=py_file.relative_to(base),
                )
            )

    return violations


def test_application_runtime_inline_dependency_construction_is_zero() -> None:
    """Disallow inline runtime construction of dependency classes in application."""
    violations = _collect_runtime_inline_construction_violations()
    assert not violations, (
        "P1 DI hardening violation: runtime inline dependency construction found in "
        "application layer.\n"
        "Move construction to composition/factory and inject through constructor.\n"
        "For temporary exceptions annotate line with EXC-002 or EXC-003.\n\n"
        "Violations:\n"
        + "\n".join(
            "  - "
            f"{v.file_path}:{v.line_number}: {v.containing_class}.{v.containing_function}: "
            f"{v.assignment_target} = {v.constructor_name}(...) :: {v.source_line}"
            for v in violations
        )
    )
