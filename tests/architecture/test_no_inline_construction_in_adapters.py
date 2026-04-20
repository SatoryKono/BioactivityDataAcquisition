"""DI guard for provider adapters: no inline helper service construction."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

TARGET_ADAPTERS: dict[str, Path] = {
    "OpenAlexAdapter": Path("src/bioetl/infrastructure/adapters/openalex/client.py"),
    "CrossRefAdapter": Path("src/bioetl/infrastructure/adapters/crossref/client.py"),
    "PubMedAdapter": Path("src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py"),
    "SemanticScholarAdapter": Path(
        "src/bioetl/infrastructure/adapters/semanticscholar/adapter.py"
    ),
    "UniProtAdapter": Path("src/bioetl/infrastructure/adapters/uniprot/client.py"),
    "PubChemAdapter": Path("src/bioetl/infrastructure/adapters/pubchem/client.py"),
    "OpenAlexFallbackOrchestrator": Path(
        "src/bioetl/infrastructure/adapters/openalex/fallback_orchestrator.py"
    ),
}

FORBIDDEN_HELPER_CONSTRUCTORS = {
    # Cross-cutting services (existing guard)
    "FallbackFetchOrchestratorService",
    "ErrorService",
    "AdapterMetricsRecorder",
    "APIRequestCollector",
    # OpenAlex provider-specific helpers
    "OpenAlexQueryExecutor",
    "OpenAlexResponseMapper",
    "OpenAlexCursorFlowService",
    "OpenAlexTitleFallbackHandler",
    "CrossRefTitleFallbackHandler",
    "PubMedTitleFallbackHandler",
    "OpenAlexFallbackOrchestrator",
    # CrossRef provider-specific helpers
    "CrossRefQueryBuilder",
    "CrossRefResponseMapper",
    "DoiBatchProcessor",
    "SearchPaginator",
    "CrossRefFetchFlow",
    # SemanticScholar provider-specific helpers
    "SemanticScholarTitleFallbackHandler",
    # PubChem provider-specific helpers
    "PubChemEntityMapper",
    "PubChemFetchStrategies",
    # Shared fallback infrastructure
    "DefaultFallbackExecution",
    "ComposableFallbackDecorator",
    # Error mapping
    "DomainInfraExceptionMapper",
}


@dataclass(frozen=True)
class InlineConstructionViolation:
    """Represents inline concrete helper construction in adapter constructor."""

    class_name: str
    file_path: Path
    function_name: str
    line_number: int
    constructor_name: str


def _extract_constructor_name(call_node: ast.Call) -> str | None:
    if isinstance(call_node.func, ast.Name):
        return call_node.func.id
    if isinstance(call_node.func, ast.Attribute):
        return call_node.func.attr
    return None


def _target_adapter_class(
    tree: ast.AST,
    *,
    adapter_class_name: str,
) -> ast.ClassDef | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == adapter_class_name:
            return node
    return None


def _lifecycle_methods(
    node: ast.ClassDef,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        class_member
        for class_member in node.body
        if isinstance(class_member, (ast.FunctionDef, ast.AsyncFunctionDef))
        and class_member.name in {"__init__", "__post_init__"}
    ]


def _call_violation(
    candidate: ast.AST,
    *,
    adapter_class_name: str,
    source_file: Path,
    function_name: str,
) -> InlineConstructionViolation | None:
    if not isinstance(candidate, ast.Call):
        return None
    constructor_name = _extract_constructor_name(candidate)
    if constructor_name not in FORBIDDEN_HELPER_CONSTRUCTORS:
        return None
    return InlineConstructionViolation(
        class_name=adapter_class_name,
        file_path=source_file,
        function_name=function_name,
        line_number=candidate.lineno,
        constructor_name=constructor_name,
    )


def _find_inline_construction_violations(
    source_file: Path,
    adapter_class_name: str,
) -> list[InlineConstructionViolation]:
    source_text = source_file.read_text(encoding="utf-8")
    tree = ast.parse(source_text)
    violations: list[InlineConstructionViolation] = []
    adapter_class = _target_adapter_class(tree, adapter_class_name=adapter_class_name)
    if adapter_class is None:
        return violations

    for class_member in _lifecycle_methods(adapter_class):
        for candidate in ast.walk(class_member):
            violation = _call_violation(
                candidate,
                adapter_class_name=adapter_class_name,
                source_file=source_file,
                function_name=class_member.name,
            )
            if violation is not None:
                violations.append(violation)
    return violations


def test_no_inline_helper_construction_in_provider_adapters() -> None:
    """Adapters must receive helper services via DI, not construct concrete helpers."""
    violations: list[InlineConstructionViolation] = []
    for adapter_name, relative_path in TARGET_ADAPTERS.items():
        source_file = Path(relative_path)
        if not source_file.exists():
            pytest.skip(f"Adapter source not found: {relative_path}")
        violations.extend(
            _find_inline_construction_violations(
                source_file=source_file,
                adapter_class_name=adapter_name,
            )
        )

    assert not violations, (
        "Inline helper construction detected in provider adapter constructors. "
        "Move helper creation to composition/factory and inject via constructor.\n"
        + "\n".join(
            "  - "
            f"{item.file_path}:{item.line_number} "
            f"{item.class_name}.{item.function_name} -> {item.constructor_name}(...)"
            for item in violations
        )
    )
