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

A line comment ``EXC-002`` or ``EXC-003`` suppresses a hit only when that
same line also cites a pair id present in
``configs/quality/private_import_ratchet.yaml``.
"""

from __future__ import annotations

import pytest

import ast
import re
from functools import cache
from pathlib import Path
from typing import NamedTuple

import yaml


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
SANCTIONED_NULL_CONSTRUCTORS = frozenset({"NoOpStructuralPolicy"})
_WAIVER_ID = re.compile(r"\bPIM-[A-Z]+-\d{3}\b")


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


@cache
def known_private_import_ids() -> frozenset[str]:
    """Return pair ids that already exist in the private-import ratchet."""
    payload = yaml.safe_load(
        _get_base_path(Path("configs/quality/private_import_ratchet.yaml")).read_text(
            encoding="utf-8"
        )
    )
    pairs = payload.get("pairs", ()) if isinstance(payload, dict) else ()
    return frozenset(
        str(pair.get("id"))
        for pair in pairs
        if isinstance(pair, dict) and pair.get("id")
    )


def line_has_metadata_waiver(
    source_line: str,
    known_ids: frozenset[str] | None = None,
) -> bool:
    """True when the line cites an existing PIM id next to an EXC marker."""
    if not any(marker in source_line for marker in EXEMPTION_MARKERS):
        return False
    ids = known_private_import_ids() if known_ids is None else known_ids
    return any(match.group(0) in ids for match in _WAIVER_ID.finditer(source_line))


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
        if line_has_metadata_waiver(source_line):
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
        "A temporary exception needs EXC-002 or EXC-003 plus an existing PIM id.\n\n"
        "Violations:\n"
        + "\n".join(
            "  - "
            f"{v.file_path}:{v.line_number}: {v.containing_class}.{v.containing_function}: "
            f"{v.assignment_target} = {v.constructor_name}(...) :: {v.source_line}"
            for v in violations
        )
    )


class DependencyCallSite(NamedTuple):
    """One constructor call that is not the direct value of an assignment."""

    line_number: int
    qualname: str
    constructor_name: str


def _function_parameter_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    args = node.args
    names = {arg.arg for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)}
    if args.vararg is not None:
        names.add(args.vararg.arg)
    if args.kwarg is not None:
        names.add(args.kwarg.arg)
    return names


def _ast_parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _is_direct_assignment_value(
    node: ast.Call,
    parents: dict[ast.AST, ast.AST],
) -> bool:
    parent = parents.get(node)
    if isinstance(parent, ast.Assign):
        return parent.value is node
    if isinstance(parent, ast.AnnAssign):
        return parent.value is node
    return False


def _is_injected_fallback(
    node: ast.Call,
    parents: dict[ast.AST, ast.AST],
    parameters: set[str],
) -> bool:
    injected = parameters - {"self", "cls"}
    current: ast.AST | None = parents.get(node)
    while current is not None and not isinstance(
        current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
    ):
        if isinstance(current, ast.BoolOp):
            if any(
                isinstance(value, ast.Name) and value.id in injected
                for value in current.values
            ):
                return True
        if isinstance(current, ast.IfExp):
            for branch in (current.body, current.orelse):
                if isinstance(branch, ast.Name) and branch.id in injected:
                    return True
        current = parents.get(current)
    return False


class _NonAssignmentDependencyFinder(ast.NodeVisitor):
    def __init__(
        self, source_lines: list[str], parents: dict[ast.AST, ast.AST]
    ) -> None:
        self._source_lines = source_lines
        self._parents = parents
        self._class_name = "<module>"
        self._function_name = "<module>"
        self._parameters: set[str] = set()
        self.dependencies: list[DependencyCallSite] = []
        self.unresolved: list[DependencyCallSite] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        previous = self._class_name
        self._class_name = node.name
        self.generic_visit(node)
        self._class_name = previous

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        previous_name = self._function_name
        previous_params = self._parameters
        self._function_name = node.name
        self._parameters = _function_parameter_names(node)
        self.generic_visit(node)
        self._function_name = previous_name
        self._parameters = previous_params

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        self._consider(node)
        self.generic_visit(node)

    def _qualname(self) -> str:
        if self._class_name == "<module>":
            return self._function_name
        if self._function_name == "<module>":
            return self._class_name
        return f"{self._class_name}.{self._function_name}"

    def _consider(self, node: ast.Call) -> None:
        if _is_direct_assignment_value(node, self._parents):
            return
        source_line = (
            self._source_lines[node.lineno - 1]
            if 0 < node.lineno <= len(self._source_lines)
            else ""
        )
        if line_has_metadata_waiver(source_line):
            return
        constructor_name = _extract_constructor_name(node)
        if constructor_name is None:
            if isinstance(node.func, (ast.Call, ast.Subscript)):
                self.unresolved.append(
                    DependencyCallSite(node.lineno, self._qualname(), "<dynamic>")
                )
            return
        if constructor_name in EXCLUDED_CONSTRUCTOR_NAMES:
            return
        if constructor_name in SANCTIONED_NULL_CONSTRUCTORS:
            return
        if not constructor_name.endswith(DEPENDENCY_SUFFIXES):
            return
        if _is_injected_fallback(node, self._parents, self._parameters):
            return
        self.dependencies.append(
            DependencyCallSite(node.lineno, self._qualname(), constructor_name)
        )


def analyze_dependency_construction(
    source: str,
) -> tuple[list[DependencyCallSite], list[DependencyCallSite]]:
    """Classify non-assignment dependency construction in one module."""
    tree = ast.parse(source)
    finder = _NonAssignmentDependencyFinder(source.splitlines(), _ast_parents(tree))
    finder.visit(tree)
    return finder.dependencies, finder.unresolved


def _assignment_constructors(source: str) -> list[RuntimeInlineConstructionViolation]:
    finder = _RuntimeInlineConstructionFinder(source.splitlines())
    finder.visit(ast.parse(source))
    return finder.violations


def collect_non_assignment_dependency_counts() -> dict[tuple[str, str, str], int]:
    """Count classified non-assignment dependency constructors under application."""
    base = _get_base_path(APPLICATION_DIR)
    counts: dict[tuple[str, str, str], int] = {}
    for py_file in sorted(base.rglob("*.py")):
        source = py_file.read_text(encoding="utf-8")
        try:
            dependencies, _unresolved = analyze_dependency_construction(source)
        except SyntaxError:
            continue
        relative = py_file.relative_to(base).as_posix()
        for site in dependencies:
            key = (relative, site.qualname, site.constructor_name)
            counts[key] = counts.get(key, 0) + 1
    return counts


# Shrink-only census of constructors outside Assign/AnnAssign. Removing a site
# is allowed. A new site or a higher count fails until it is moved to composition.
_CLASSIFIED_NON_ASSIGNMENT: dict[tuple[str, str, str], int] = {
    (
        "composite/runner_pkg/runner_execution_orchestrator.py",
        "execute_locked_run_phases",
        "CompositeRunPhaseService",
    ): 1,
    (
        "composite/runner_pkg/runner_runtime_helpers.py",
        "bind_runner_dependencies",
        "CompositeLifecycleObserverService",
    ): 1,
    (
        "core/base_transformer/_structural_policy_support.py",
        "build_structural_policy",
        "SchemaAwareStructuralPolicy",
    ): 1,
    (
        "core/base_transformer/field_policy.py",
        "FieldPolicyResolver.resolve",
        "ResolvedFieldPolicy",
    ): 2,
    (
        "core/lifecycle/shutdown.py",
        "create_shutdown_service",
        "ShutdownService",
    ): 1,
    (
        "observability/control_plane_evidence/service.py",
        "ControlPlaneEvidenceService._bounded_retention_plan",
        "ControlPlaneArtifactLifecyclePolicy",
    ): 2,
    (
        "services/control_plane/effective_config/context.py",
        "resolve_resolution_policy",
        "ConfigResolutionPolicy",
    ): 1,
    (
        "services/control_plane/effective_config/service.py",
        "create_effective_config_service",
        "EffectiveConfigService",
    ): 1,
    (
        "services/control_plane/forensic/diagnostics_support.py",
        "inspection_service_factory_from_ports",
        "RunManifestInspectionService",
    ): 1,
    (
        "services/control_plane/replay/_historical_certification_support.py",
        "HistoricalReplayCertificationValidator.build_ledger_service",
        "RunLedgerService",
    ): 1,
    (
        "services/control_plane/replay/historical_certification_service.py",
        "HistoricalReplayCertificationService._validator",
        "HistoricalReplayCertificationValidator",
    ): 1,
    (
        "services/lineage/metadata_coordinator.py",
        "MetadataCoordinator._gold_metadata_service",
        "GoldMetadataService",
    ): 1,
    (
        "services/lineage/metadata_coordinator.py",
        "MetadataCoordinator._silver_metadata_service",
        "SilverMetadataService",
    ): 1,
    (
        "services/quality/config_dq_service.py",
        "ConfigDQService.get_effective_config_artifact",
        "ConfigResolutionPolicy",
    ): 1,
    (
        "services/quality/config_dq_service.py",
        "_build_resolution_policy",
        "ConfigResolutionPolicy",
    ): 1,
}


def test_non_assignment_dependency_construction_does_not_grow() -> None:
    """Keep return, nested, and attribute construction inside the census."""
    found = collect_non_assignment_dependency_counts()
    unexpected = [
        f"{path}:{qualname} {constructor} count={count} allowed={allowed}"
        for (path, qualname, constructor), count in sorted(found.items())
        for allowed in [_CLASSIFIED_NON_ASSIGNMENT.get((path, qualname, constructor))]
        if allowed is None or count > allowed
    ]
    assert not unexpected, "\n".join(unexpected)


def test_dependency_constructor_shapes_and_waivers() -> None:
    """Shape fixtures for the extended constructor scan."""
    returned, _ = analyze_dependency_construction(
        "def build():\n    return WidgetService()\n"
    )
    nested, _ = analyze_dependency_construction(
        "def build():\n    return helper(WidgetService())\n"
    )
    attribute, _ = analyze_dependency_construction(
        "def build(mod):\n    return mod.WidgetService()\n"
    )
    conditional, _ = analyze_dependency_construction(
        "def build():\n    if True:\n        return WidgetService()\n"
    )
    ternary, _ = analyze_dependency_construction(
        "def build(ready):\n    return WidgetService() if ready else OtherService()\n"
    )
    fallback, _ = analyze_dependency_construction(
        "def build(metrics=None):\n    return metrics or MetricsClient()\n"
    )
    injected, _ = analyze_dependency_construction(
        "def build(policy=None):\n"
        "    return policy if policy is not None else LocalPolicy()\n"
    )
    value_object, _ = analyze_dependency_construction(
        "def build():\n    return ColumnSpec('id')\n"
    )
    null_object, _ = analyze_dependency_construction(
        "def build():\n    return NoOpStructuralPolicy()\n"
    )
    bare, _ = analyze_dependency_construction(
        "def build():\n    return WidgetService()  # EXC-002\n"
    )
    waived, _ = analyze_dependency_construction(
        "def build():\n    return WidgetService()  # EXC-002 PIM-APP-001\n"
    )
    _deps, unresolved = analyze_dependency_construction(
        "def build(ns):\n    return getattr(ns, 'WidgetService')()\n"
    )
    bare_assignment = _assignment_constructors(
        "def build():\n    service = WidgetService()  # EXC-002\n"
    )
    waived_assignment = _assignment_constructors(
        "def build():\n    service = WidgetService()  # EXC-002 PIM-APP-001\n"
    )

    assert [site.constructor_name for site in returned] == ["WidgetService"]
    assert [site.constructor_name for site in nested] == ["WidgetService"]
    assert [site.constructor_name for site in attribute] == ["WidgetService"]
    assert [site.constructor_name for site in conditional] == ["WidgetService"]
    assert [site.constructor_name for site in ternary] == [
        "WidgetService",
        "OtherService",
    ]
    assert fallback == []
    assert injected == []
    assert value_object == []
    assert null_object == []
    assert [site.constructor_name for site in bare] == ["WidgetService"]
    assert waived == []
    assert len(unresolved) == 1
    assert unresolved[0].constructor_name == "<dynamic>"
    assert bare_assignment
    assert waived_assignment == []
