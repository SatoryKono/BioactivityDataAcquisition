"""Architecture guardrails for storage observability ownership."""

from __future__ import annotations

import ast
from pathlib import Path


FORBIDDEN_TRACING_DEFAULT_PATHS = (
    Path("src/bioetl/infrastructure/storage/bronze_writer.py"),
    Path("src/bioetl/infrastructure/storage/silver/runtime_helpers.py"),
    Path("src/bioetl/infrastructure/storage/silver/pipeline_helpers.py"),
    Path("src/bioetl/infrastructure/storage/gold/runtime_helpers.py"),
    Path("src/bioetl/infrastructure/storage/gold_writer.py"),
    Path("src/bioetl/composition/factories/storage/_bronze.py"),
    Path("src/bioetl/composition/factories/storage/_silver.py"),
    Path("src/bioetl/composition/factories/storage/_gold.py"),
)
ADAPTERS_ROOT = Path("src/bioetl/infrastructure/adapters")
FORBIDDEN_ADAPTER_NOOP_PATHS = (
    Path("src/bioetl/infrastructure/adapters/base.py"),
    Path("src/bioetl/infrastructure/adapters/http/client.py"),
    Path("src/bioetl/infrastructure/adapters/sync_base.py"),
    Path("src/bioetl/infrastructure/adapters/error_handling.py"),
    Path("src/bioetl/infrastructure/adapters/_health_check_observability.py"),
)
FORBIDDEN_ENDPOINT_IDENTIFIERS = {
    "record_id",
    "run_id",
    "batch_id",
    "payload_hash",
    "doi",
    "pmid",
    "chembl_id",
}


def _iter_called_names(tree: ast.AST) -> set[str]:
    calls: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            calls.add(func.id)
        elif isinstance(func, ast.Attribute):
            calls.add(func.attr)
    return calls


def test_storage_layers_do_not_construct_noop_tracing_defaults() -> None:
    """Storage observability defaults must be owned by composition entrypoints only."""
    for path in FORBIDDEN_TRACING_DEFAULT_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = _iter_called_names(tree)
        assert "NoOpTracing" not in calls, (
            f"{path} must not construct NoOpTracing. "
            "Resolve tracing in top-level composition wiring instead."
        )


def test_infra_adapters_do_not_construct_noop_observability_defaults() -> None:
    """Adapter observability fallbacks must be resolved above infrastructure adapters."""
    for path in FORBIDDEN_ADAPTER_NOOP_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = _iter_called_names(tree)
        assert "NoOpMetrics" not in calls and "NoOpTracing" not in calls, (
            f"{path} must not construct NoOpMetrics/NoOpTracing. "
            "Resolve null-object observability in composition-owned wiring."
        )


def test_adapter_measure_request_labels_do_not_embed_record_identity() -> None:
    """Prometheus endpoint labels must stay bounded and never encode record IDs."""
    for path in ADAPTERS_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute) and func.attr == "measure_request"
            ):
                continue
            if not node.args:
                continue
            endpoint_expr = node.args[0]
            names = {
                inner.id
                for inner in ast.walk(endpoint_expr)
                if isinstance(inner, ast.Name)
            }
            forbidden = sorted(names & FORBIDDEN_ENDPOINT_IDENTIFIERS)
            assert not forbidden, (
                f"{path} uses forbidden dynamic identifiers in measure_request "
                f"endpoint labels: {', '.join(forbidden)}"
            )
