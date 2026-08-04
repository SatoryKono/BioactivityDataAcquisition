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
"""Architecture test: inline instantiation budget in application layer.

REQ-ARCH-DI-012:
- Application code must avoid ``self.attr = ClassName(...)`` assignments.
- Dependencies should be assembled in composition and injected.
- Temporary exceptions may be annotated inline with ``EXC-002``/``EXC-003``.
"""

from __future__ import annotations

import pytest

import ast
from pathlib import Path
from typing import NamedTuple


pytestmark = pytest.mark.architecture

APPLICATION_DIR = Path("src/bioetl/application")
EXCEPTION_MARKERS = ("EXC-002", "EXC-003")


class InlineInstantiationViolation(NamedTuple):
    """Represents an inline object-construction violation."""

    file_path: Path
    line_number: int
    containing_class: str
    containing_function: str
    assignment_target: str
    constructor_name: str
    source_line: str


def _get_base_path(relative_path: Path) -> Path:
    """Resolve path - works from project root or tests directory."""
    if relative_path.exists():
        return relative_path
    return Path(__file__).parent.parent.parent / relative_path


def _extract_constructor_name(call_node: ast.Call) -> str | None:
    """Extract class-like constructor name from a Call node."""
    if isinstance(call_node.func, ast.Name):
        name = call_node.func.id
    elif isinstance(call_node.func, ast.Attribute):
        name = call_node.func.attr
    else:
        return None
    return name if name[:1].isupper() else None


def _extract_target_name(target: ast.expr) -> str:
    """Extract assignment target representation."""
    if isinstance(target, ast.Attribute):
        if isinstance(target.value, ast.Name):
            return f"{target.value.id}.{target.attr}"
        return target.attr
    if isinstance(target, ast.Name):
        return target.id
    return "<unknown>"


class _InlineInstantiationFinder(ast.NodeVisitor):
    """Find ``self.attr = ClassName(...)`` assignments via AST."""

    def __init__(self, source_lines: list[str]) -> None:
        self._source_lines = source_lines
        self._current_class = "<module>"
        self._current_function = "<module>"
        self.violations: list[InlineInstantiationViolation] = []

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
        self._check_assignment(
            node.targets[0] if node.targets else None, node.value, node.lineno
        )
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
        if target is None or value is None:
            return
        if not (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            return
        if not isinstance(value, ast.Call):
            return

        constructor_name = _extract_constructor_name(value)
        if constructor_name is None:
            return

        source_line = self._source_lines[lineno - 1]
        if any(marker in source_line for marker in EXCEPTION_MARKERS):
            return

        self.violations.append(
            InlineInstantiationViolation(
                file_path=Path(""),
                line_number=lineno,
                containing_class=self._current_class,
                containing_function=self._current_function,
                assignment_target=_extract_target_name(target),
                constructor_name=constructor_name,
                source_line=source_line.strip(),
            )
        )


def _collect_inline_instantiation_violations() -> list[InlineInstantiationViolation]:
    """Collect all disallowed inline instantiations under application layer."""
    base = _get_base_path(APPLICATION_DIR)
    violations: list[InlineInstantiationViolation] = []

    for py_file in sorted(base.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        lines = source.splitlines()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        finder = _InlineInstantiationFinder(lines)
        finder.visit(tree)

        for violation in finder.violations:
            violations.append(
                violation._replace(
                    file_path=py_file.relative_to(base),
                )
            )

    return violations


def test_application_inline_instantiation_budget_is_zero() -> None:
    """Disallow new inline class instantiation assignments in application layer."""
    violations = _collect_inline_instantiation_violations()

    assert not violations, (
        "REQ-ARCH-DI-012 violation: inline class instantiations found in application "
        "layer (`self.attr = ClassName(...)`).\n"
        "Move creation to composition/factory or inject constructor/factory callable.\n"
        "For temporary exceptions annotate line with EXC-002 or EXC-003.\n\n"
        "Violations:\n"
        + "\n".join(
            "  - "
            f"{v.file_path}:{v.line_number}: {v.containing_class}.{v.containing_function}: "
            f"{v.assignment_target} = {v.constructor_name}(...) :: {v.source_line}"
            for v in violations
        )
    )
