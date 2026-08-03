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
"""Architecture guardrails for composition runtime boundary policy."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
COMPOSITION_RUNTIME_ROOTS = (
    ROOT / "src/bioetl/composition/runtime_builders",
    ROOT / "src/bioetl/composition/bootstrap/runtime",
    ROOT / "src/bioetl/composition/factories/pipeline",
)
FORBIDDEN_LIFECYCLE_EVENTS = {
    "BatchCreated",
    "BatchSealed",
    "BatchWritten",
    "BatchFailed",
    "PipelineCompleted",
    "PipelineFailed",
}
FORBIDDEN_LIFECYCLE_EMITTERS = {"emit_domain_event"}
FORBIDDEN_LIFECYCLE_EMITTER_PREFIXES = ("emit_batch_", "emit_pipeline_")


def _called_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _is_forbidden_lifecycle_emitter(called_name: str | None) -> bool:
    if called_name is None:
        return False
    return called_name in FORBIDDEN_LIFECYCLE_EMITTERS or called_name.startswith(
        FORBIDDEN_LIFECYCLE_EMITTER_PREFIXES
    )


def _composition_runtime_policy_violations() -> list[str]:
    violations: list[str] = []
    for root in COMPOSITION_RUNTIME_ROOTS:
        for py_file in sorted(root.rglob("*.py")):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                called_name = _called_name(node)
                if called_name in FORBIDDEN_LIFECYCLE_EVENTS:
                    violations.append(
                        f"{py_file.relative_to(ROOT)}:{node.lineno} constructs "
                        f"{called_name}; lifecycle events belong to domain/application"
                    )
                if _is_forbidden_lifecycle_emitter(called_name):
                    violations.append(
                        f"{py_file.relative_to(ROOT)}:{node.lineno} calls "
                        f"{called_name}; runtime event emission belongs to application"
                    )
    return violations


def test_composition_runtime_builders_remain_wiring_not_lifecycle_publishers() -> None:
    """Composition may assemble collaborators but must not publish lifecycle events."""
    violations = _composition_runtime_policy_violations()

    assert not violations, (
        "Composition runtime builders must stay wiring/assembly surfaces.\n"
        + "\n".join(f"  - {violation}" for violation in violations)
    )
