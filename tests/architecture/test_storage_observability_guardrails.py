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
    Path("src/bioetl/composition/factories/services/common_service_wiring.py"),
    Path("src/bioetl/composition/factories/storage/factory.py"),
    Path("src/bioetl/composition/factories/transformer_dependencies.py"),
    Path("src/bioetl/composition/factories/pipeline/transformer_dependencies.py"),
    Path("src/bioetl/composition/runtime_builders/observability_builder.py"),
)
ADAPTERS_ROOT = Path("src/bioetl/infrastructure/adapters")
FORBIDDEN_ADAPTER_NOOP_PATHS = (
    Path("src/bioetl/infrastructure/adapters/base.py"),
    Path("src/bioetl/infrastructure/adapters/http/client.py"),
    Path("src/bioetl/infrastructure/adapters/sync_base.py"),
    Path("src/bioetl/infrastructure/adapters/error_handling.py"),
    Path("src/bioetl/infrastructure/adapters/_health_check_observability.py"),
)
FORBIDDEN_COMPOSITION_NOOP_METRICS_PATHS = (
    Path("src/bioetl/composition/factories/datasource/adapter_helpers.py"),
    Path("src/bioetl/composition/factories/_observability_wiring.py"),
    Path("src/bioetl/composition/factories/services/port_factories.py"),
)
FORBIDDEN_STORAGE_LOCAL_AUDIT_CONSTRUCTION_PATHS = (
    Path("src/bioetl/composition/factories/storage/_helpers.py"),
)
FORBIDDEN_RUNTIME_NOOP_AUDIT_BOOTSTRAP_PATHS = (
    Path("src/bioetl/composition/bootstrap/runtime/runner.py"),
)
FORBIDDEN_UNIFIED_EVENT_COUNTER_DIRECT_PATHS = (
    Path("src/bioetl/infrastructure/storage/silver/merge_resilience_helpers.py"),
    Path("src/bioetl/infrastructure/storage/metadata/writer_operations.py"),
)
PARALLEL_PUBLICATION_HELPER_PATH = Path(
    "src/bioetl/application/observability/domain_event_publication.py"
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


def _iter_increment_counter_metric_names(tree: ast.AST) -> set[str]:
    metric_names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "increment_counter"):
            continue
        if not node.args:
            continue
        metric_name_arg = node.args[0]
        if isinstance(metric_name_arg, ast.Constant) and isinstance(
            metric_name_arg.value, str
        ):
            metric_names.add(metric_name_arg.value)
    return metric_names


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


def test_composition_factories_delegate_noop_metrics_resolution() -> None:
    """Composition factory seams must use centralized observability resolution helpers."""
    for path in FORBIDDEN_COMPOSITION_NOOP_METRICS_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = _iter_called_names(tree)
        assert "NoOpMetrics" not in calls and "NoOpTracing" not in calls, (
            f"{path} must delegate NoOp observability resolution to the shared "
            "composition helper instead of constructing null objects inline."
        )


def test_storage_factories_do_not_construct_audit_locally() -> None:
    """Canonical runtime audit must be injected from composition-owned wiring."""
    for path in FORBIDDEN_STORAGE_LOCAL_AUDIT_CONSTRUCTION_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = _iter_called_names(tree)
        assert "create_audit_port" not in calls, (
            f"{path} must not construct AuditPort locally. "
            "Inject the canonical runtime audit from ObservabilityBundle wiring."
        )


def test_runtime_bootstrap_does_not_inline_noop_audit() -> None:
    """Pipeline runner bootstrap must use runtime observability wiring for audit."""
    for path in FORBIDDEN_RUNTIME_NOOP_AUDIT_BOOTSTRAP_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = _iter_called_names(tree)
        assert "NoOpAudit" not in calls, (
            f"{path} must not inline NoOpAudit. "
            "Bootstrap the canonical runtime audit dependency instead."
        )


def test_adapter_measure_request_labels_do_not_embed_record_identity() -> None:
    """Prometheus endpoint labels must stay bounded and never encode record IDs."""
    for path in ADAPTERS_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "measure_request"):
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


def test_storage_helpers_do_not_increment_unified_observability_event_counter() -> None:
    """Storage-local retry/final telemetry must use dedicated counters only."""
    for path in FORBIDDEN_UNIFIED_EVENT_COUNTER_DIRECT_PATHS:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        metric_names = _iter_increment_counter_metric_names(tree)
        assert "bioetl_observability_events_total" not in metric_names, (
            f"{path} must not increment bioetl_observability_events_total directly. "
            "Unified runtime event publication belongs to canonical "
            "PipelineObserver paths only."
        )


def test_parallel_domain_event_publication_helper_is_removed() -> None:
    """Application must not keep a ports-only domain-event publication backdoor."""
    assert not PARALLEL_PUBLICATION_HELPER_PATH.exists(), (
        "src/bioetl/application/observability/domain_event_publication.py must "
        "remain absent so canonical observer emitters stay the only runtime "
        "event publication seam."
    )
