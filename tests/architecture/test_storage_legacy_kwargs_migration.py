"""Guardrails for storage writer legacy kwargs migration."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GOLD_WRITER = ROOT / "src" / "bioetl" / "infrastructure" / "storage" / "gold_writer.py"
SILVER_WRITER = (
    ROOT / "src" / "bioetl" / "infrastructure" / "storage" / "silver_writer.py"
)
GOLD_RUNTIME = (
    ROOT
    / "src"
    / "bioetl"
    / "infrastructure"
    / "storage"
    / "gold"
    / "writer_runtime.py"
)
GOLD_FACTORY = (
    ROOT / "src" / "bioetl" / "composition" / "factories" / "storage" / "_gold.py"
)
STORAGE_ASSEMBLY = (
    ROOT / "src" / "bioetl" / "composition" / "bootstrap" / "assembly" / "storage.py"
)
WORKFLOW_SERVICES = ROOT / "src" / "bioetl" / "composition" / "_workflow_services.py"

LEGACY_GOLD_COLLABORATORS = {
    "audit",
    "contract_rollout_policy",
    "csv_exporter",
    "lineage_store",
    "metadata_coordinator",
    "metadata_writer",
    "metrics",
    "tracing",
}
LEGACY_SILVER_COLLABORATORS = {
    "audit",
    "contract_rollout_policy",
    "csv_exporter",
    "dq_calculator",
    "lineage_store",
    "merge_resilience_policy",
    "metadata_coordinator",
    "metadata_writer",
    "metrics",
    "silver_validator",
    "tracing",
    "write_policy",
}


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _class_method(
    tree: ast.Module, class_name: str, method_name: str
) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for body_node in node.body:
                if (
                    isinstance(body_node, ast.FunctionDef)
                    and body_node.name == method_name
                ):
                    return body_node
    raise AssertionError(f"{class_name}.{method_name} not found")


def _named_calls(tree: ast.Module, name: str) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == name:
            calls.append(node)
        elif isinstance(func, ast.Attribute) and func.attr == name:
            calls.append(node)
    return calls


def _keyword_names(call: ast.Call) -> set[str]:
    return {keyword.arg for keyword in call.keywords if keyword.arg is not None}


def test_gold_writer_constructor_uses_canonical_runtime_services_only() -> None:
    """GoldWriter must not reopen the retired constructor kwargs surface."""
    init = _class_method(_parse(GOLD_WRITER), "GoldWriter", "__init__")

    parameters = {
        argument.arg
        for argument in [
            *init.args.args,
            *init.args.kwonlyargs,
        ]
    }

    assert "runtime_services" in parameters
    assert init.args.kwarg is None


def test_gold_runtime_resolver_has_no_legacy_kwargs_normalization() -> None:
    """Gold runtime resolution no longer adapts legacy constructor kwargs."""
    text = GOLD_RUNTIME.read_text(encoding="utf-8")

    assert "legacy_kwargs" not in text
    assert "Unexpected GoldWriter options" not in text


def test_silver_writer_constructor_uses_runtime_request_or_services_only() -> None:
    """SilverWriter constructor must not expose direct collaborator kwargs."""
    init = _class_method(_parse(SILVER_WRITER), "SilverWriter", "__init__")

    parameters = {
        argument.arg
        for argument in [
            *init.args.args,
            *init.args.kwonlyargs,
        ]
    }

    assert {"runtime_request", "runtime_services"} <= parameters
    assert not (parameters & LEGACY_SILVER_COLLABORATORS)
    assert init.args.kwarg is None


def test_gold_composition_wiring_passes_grouped_runtime_services() -> None:
    """Composition must inject Gold collaborators through GoldWriterRuntimeServices."""
    factory_calls = _named_calls(_parse(GOLD_FACTORY), "writer_cls")
    assembly_calls = _named_calls(_parse(STORAGE_ASSEMBLY), "GoldWriter")

    assert factory_calls
    assert assembly_calls

    for call in [*factory_calls, *assembly_calls]:
        keyword_names = _keyword_names(call)
        assert "runtime_services" in keyword_names
        assert not (keyword_names & LEGACY_GOLD_COLLABORATORS)


def test_silver_composition_wiring_passes_grouped_runtime_services() -> None:
    """Production Silver composition must not use direct collaborator kwargs."""
    assembly_calls = _named_calls(_parse(STORAGE_ASSEMBLY), "SilverWriter")
    workflow_calls = _named_calls(_parse(WORKFLOW_SERVICES), "SilverWriter")

    assert assembly_calls
    assert workflow_calls

    for call in [*assembly_calls, *workflow_calls]:
        keyword_names = _keyword_names(call)
        assert "runtime_services" in keyword_names
        assert not (keyword_names & LEGACY_SILVER_COLLABORATORS)
