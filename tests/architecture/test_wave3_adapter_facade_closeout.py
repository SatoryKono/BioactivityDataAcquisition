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
"""Closeout ratchets for Wave 3 adapter facade seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

FACADE_RATCHETS: dict[str, tuple[int, set[str]]] = {
    "src/bioetl/infrastructure/adapters/health_check_mixin.py": (
        350,
        {
            "bioetl.infrastructure.adapters._health_check_observability",
            "bioetl.infrastructure.adapters._health_check_policy",
        },
    ),
    "src/bioetl/infrastructure/adapters/http/client_retry_mixin.py": (
        335,
        {
            "bioetl.infrastructure.adapters.http._client_retry_flow",
            "bioetl.infrastructure.adapters.http._client_retry_models",
            "bioetl.infrastructure.adapters.http._client_retry_policy",
        },
    ),
    "src/bioetl/infrastructure/adapters/http/health_monitor.py": (
        300,
        {"bioetl.infrastructure.adapters.http._health_monitor_support"},
    ),
    "src/bioetl/infrastructure/adapters/error_handling.py": (
        280,
        {"bioetl.infrastructure.adapters._error_handling_support"},
    ),
    "src/bioetl/infrastructure/adapters/chembl/fetch_resilience_mixin.py": (
        270,
        {
            "bioetl.infrastructure.adapters.chembl._fetch_resilience_fallback",
            "bioetl.infrastructure.adapters.common.fetch_resilience_template",
        },
    ),
    "src/bioetl/infrastructure/adapters/pubmed/adapter_filter_fetch_mixin.py": (
        240,
        {"bioetl.infrastructure.adapters.pubmed._filter_fetch_support"},
    ),
    "src/bioetl/infrastructure/adapters/pubchem/fetch_strategies.py": (
        295,
        {"bioetl.infrastructure.adapters.pubchem._fetch_strategy_search"},
    ),
    "src/bioetl/infrastructure/adapters/chembl/fetch_paging_mixin.py": (
        160,
        {"bioetl.infrastructure.adapters.chembl._fetch_paging_filtered"},
    ),
    "src/bioetl/infrastructure/adapters/semanticscholar/fetch_adapter_mixin.py": (
        240,
        {"bioetl.infrastructure.adapters.semanticscholar._search_fetch_flow"},
    ),
    "src/bioetl/infrastructure/adapters/crossref/client.py": (
        295,
        {"bioetl.infrastructure.adapters.crossref._client_fallback_policy"},
    ),
    "src/bioetl/infrastructure/adapters/crossref/batch.py": (
        35,
        {
            "bioetl.infrastructure.adapters.crossref._batch_support",
            "bioetl.infrastructure.adapters.crossref._doi_batch_processor",
            "bioetl.infrastructure.adapters.crossref._search_paginator",
        },
    ),
    "src/bioetl/infrastructure/adapters/pubmed/models.py": (
        280,
        {"bioetl.infrastructure.adapters.pubmed._search_models"},
    ),
    "src/bioetl/infrastructure/adapters/crossref/models.py": (
        260,
        {"bioetl.infrastructure.adapters.crossref._response_models"},
    ),
}

MODEL_FACADE_FORBIDDEN_LOCAL_CLASSES: dict[str, set[str]] = {
    "src/bioetl/infrastructure/adapters/pubmed/models.py": {
        "PubMedSearchResponse",
        "PubMedSearchResult",
    },
    "src/bioetl/infrastructure/adapters/crossref/models.py": {
        "CrossRefMessage",
        "CrossRefPublicationResponse",
        "CrossRefPublicationsResponse",
    },
}


def _path(relative_path: str) -> Path:
    return ROOT / relative_path


def _tree(relative_path: str) -> ast.Module:
    return ast.parse(_path(relative_path).read_text(encoding="utf-8"))


def _imported_modules(relative_path: str) -> set[str]:
    imported_modules: set[str] = set()
    for node in ast.walk(_tree(relative_path)):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
    return imported_modules


def _top_level_class_names(relative_path: str) -> set[str]:
    return {
        node.name
        for node in _tree(relative_path).body
        if isinstance(node, ast.ClassDef)
    }


def _src_importers_of(module_name: str) -> set[str]:
    src_root = ROOT / "src"
    importers: set[str] = set()
    for path in src_root.rglob("*.py"):
        relative_path = path.relative_to(ROOT).as_posix()
        if relative_path == "src/bioetl/infrastructure/adapters/crossref/batch.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.add(node.module)
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
        if module_name in imported_modules:
            importers.add(relative_path)
    return importers


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "max_lines", "required_modules"),
    [
        (relative_path, max_lines, required_modules)
        for relative_path, (max_lines, required_modules) in FACADE_RATCHETS.items()
    ],
)
def test_wave3_adapter_facades_stay_bounded_and_helper_backed(
    relative_path: str,
    max_lines: int,
    required_modules: set[str],
) -> None:
    """Wave 3 facades should stay thin and routed through extracted helpers."""
    path = _path(relative_path)
    source = path.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= max_lines, (
        f"{relative_path} regrew to {line_count} lines "
        f"(max {max_lines}). Keep Wave 3 facade seams narrow and move new "
        "logic into extracted helper modules."
    )

    imported_modules = _imported_modules(relative_path)
    missing_modules = required_modules - imported_modules
    assert not missing_modules, (
        f"{relative_path} no longer imports required extracted helpers:\n"
        + "\n".join(sorted(missing_modules))
    )


@pytest.mark.architecture
@pytest.mark.parametrize(
    ("relative_path", "forbidden_classes"),
    list(MODEL_FACADE_FORBIDDEN_LOCAL_CLASSES.items()),
)
def test_wave3_model_facades_do_not_reabsorb_split_response_dtos(
    relative_path: str,
    forbidden_classes: set[str],
) -> None:
    """Model facades should keep split response DTOs in their private helpers."""
    class_names = _top_level_class_names(relative_path)
    unexpected_local_classes = forbidden_classes & class_names
    assert not unexpected_local_classes, (
        f"{relative_path} reintroduced split response/search DTOs into the "
        "public facade:\n" + "\n".join(sorted(unexpected_local_classes))
    )


@pytest.mark.architecture
def test_crossref_batch_shim_is_not_used_by_first_party_src_modules() -> None:
    """First-party src modules should use CrossRef private owners, not batch shim."""
    importers = _src_importers_of("bioetl.infrastructure.adapters.crossref.batch")
    assert not importers, (
        "crossref.batch should now be a compatibility/testing facade only. "
        "First-party src modules must import private owners instead:\n"
        + "\n".join(sorted(importers))
    )
