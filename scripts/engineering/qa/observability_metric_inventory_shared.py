"""Shared constants, caches, and types for observability metric inventory.

This module is the acyclic leaf imported by scan/report/runtime/cli helpers.
The historical facade ``report_observability_metric_inventory`` re-exports
these names so tests and patch seams keep working.
"""

from __future__ import annotations

import sys
import re
from pathlib import Path
from typing import Final, Protocol, TypedDict

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from bioetl.infrastructure.observability import (
    metrics_definitions as _metric_defs,
)
from bioetl.infrastructure.observability.metrics_export_names import (
    METRICS_DEFINITION_EXPORT_NAMES,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
)


class _StartupInfoLike(Protocol):
    dwFlags: int
    wShowWindow: int


_CANONICAL_METRIC_RE = re.compile(r"\bbioetl_[a-z0-9_]+\b")
_PROMETHEUS_METRIC_NAME_RE = re.compile(r"^[A-Za-z_:][A-Za-z0-9_:]*$")

_RUNTIME_SCAN_ROOT = Path("src/bioetl")
_INFRASTRUCTURE_PATH_PREFIX = "src/bioetl/infrastructure"
_REGISTERED_SCAN_ROOT = Path("src/bioetl/infrastructure/observability")
_DOC_SCAN_ROOTS = (
    Path("docs/02-architecture"),
    Path("docs/03-guides"),
    Path("docs/04-reference"),
    Path("docs/05-operations"),
    Path("grafana/dashboards"),
    Path("grafana/README.md"),
)
_RULE_SCAN_ROOT = Path("grafana/prometheus-rules")
_DEFAULT_DRIFT_ALLOWLIST = Path(
    "configs/quality/observability_metric_inventory_allowlist.yaml"
)
_DEFAULT_DECLARED_METRIC_DEFINITIONS = Path(
    "configs/quality/observability_metric_declarations.yaml"
)
_DEFAULT_OBSERVABILITY_GOVERNANCE = Path(
    "configs/quality/observability_metric_governance.yaml"
)
_POLICY_ALIAS_CATALOG = Path("docs/04-reference/observability/metrics-catalog.md")
_PANEL_CONTRACT_INVENTORY = Path(
    "docs/03-guides/dashboards/panel-contract-inventory.json"
)
_RUNTIME_EXCLUDE_PARTS = (
    "src/bioetl/infrastructure/observability",
    "src/bioetl/domain",
)
_TEXT_SUFFIXES = {".py", ".md", ".json", ".yml", ".yaml"}
MetricInventoryReport = dict[str, list[str] | dict[str, list[str]]]


class _ObservabilityEventInventory(TypedDict):
    declared_observability_events: list[str]
    emitted_observability_events: list[str]
    retired_declared_observability_events: list[str]
    retired_declared_observability_events_emitted: list[str]
    raw_unused_declared_observability_events: list[str]
    emitted_observability_events_without_contract: list[str]
    observability_event_emitters: dict[str, list[str]]
    domain_event_emitters: list[str]


class _CardinalityReviewFields(TypedDict):
    runtime_cardinality_candidates: list[str]
    runtime_cardinality_reviewed: list[str]
    runtime_cardinality_review_required: list[str]
    runtime_cardinality_evidence: dict[str, list[str]]
    runtime_cardinality_threshold_violations: list[str]


class _RiskyLabelReviewFields(TypedDict):
    declared_risky_label_candidates: list[str]
    contract_bounded_risky_labels: set[str]
    declared_risky_label_reviewed: list[str]
    declared_risky_label_review_required: list[str]


_TEXT_FILE_DISCOVERY_CACHE: dict[str, tuple[Path, ...]] = {}
_METRIC_INVENTORY_CACHE: dict[str, MetricInventoryReport] = {}
_SOURCE_TEXT_CACHE: dict[str, str | None] = {}
_RUNTIME_CANDIDATE_TEXT_CACHE: dict[str, str | None] = {}
_RUNTIME_CANDIDATE_PATH_CACHE: dict[str, tuple[Path, ...]] = {}
_RUNTIME_EVENT_CANDIDATE_PATH_CACHE: dict[str, tuple[Path, ...]] = {}
_TEXT_DISCOVERY_TIMEOUT_SECONDS: Final[float] = 20.0
_METRIC_MENTION_GREP_TIMEOUT_SECONDS: Final[float] = 20.0
_METRIC_MENTION_GREP_CHUNK_SIZE: Final[int] = 128
_PROMETHEUS_QUERY_TIMEOUT_SECONDS: Final[float] = 5.0
_PROMETHEUS_BASE_URL_ENV_VAR: Final[str] = "BIOETL_OBSERVABILITY_PROMETHEUS_URL"
_PROMETHEUS_BEARER_TOKEN_ENV_VAR: Final[str] = "BIOETL_OBSERVABILITY_PROMETHEUS_TOKEN"
_RUNTIME_METRIC_METHODS = frozenset(
    {"increment_counter", "observe_histogram", "set_gauge"}
)
_RUNTIME_METRIC_NAME_KEYWORDS = frozenset(
    {
        "metric_name",
        "phase_duration_metric",
        "phase_events_metric",
        "state_metric_name",
        "trip_metric_name",
    }
)
_RUNTIME_SCAN_MARKERS: Final[tuple[str, ...]] = (
    "bioetl_",
    "increment_counter",
    "observe_histogram",
    "set_gauge",
    ".inc(",
    ".observe(",
    ".set(",
    ".labels(",
    "metric_name",
    "phase_duration_metric",
    "phase_events_metric",
    "state_metric_name",
    "trip_metric_name",
)
_STATIC_RUNTIME_EMITTERS: Final[dict[str, tuple[str, ...]]] = {
    # This family is emitted through a prometheus_client Counter collector in the
    # metrics server rather than through the MetricsPort helper methods scanned
    # below. Keep it explicit so registry declarations remain tied to a concrete
    # runtime path without treating all registry modules as emitters.
    "bioetl_metrics_publication_events_total": (
        "src/bioetl/infrastructure/observability/server.py",
    ),
    "bioetl_gold_lifecycle_state_total": (
        "src/bioetl/composition/factories/services/pipeline_batch_executor_builder.py",
    ),
}
_PROMETHEUS_FAMILY_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        "_bytes",
        "_count",
        "_enabled",
        "_ms",
        "_passed",
        "_rate",
        "_records",
        "_score",
        "_seconds",
        "_size",
        "_state",
        "_status",
        "_total",
        "_validated",
    }
)
_PROMETHEUS_ALIAS_SUFFIXES: Final[frozenset[str]] = frozenset(
    {
        "_bytes",
        "_seconds",
        "_total",
    }
)
_RUNTIME_EVENT_SCAN_MARKERS: Final[tuple[str, ...]] = (
    "emit_event(",
    "emit_domain_event(",
    "PipelineEvent.",
)
_NON_METRIC_ALIAS_PREFIXES: Final[tuple[str, ...]] = (
    "get_",
    "set_",
    "track_",
    "resolve_",
    "build_",
    "collect_",
    "render_",
    "validate_",
    "latest_",
    "missing_",
    "degraded_",
    "run_manifest_",
    "run_ledger_",
)
_IGNORED_DOC_METRIC_NAMES: Final[frozenset[str]] = frozenset(
    {
        "bioetl_alerts",
        "bioetl_observability",
        "bioetl_pipeline",
    }
)
_CHECK_DRIFT_KEYS: Final[tuple[str, ...]] = (
    "registered_without_runtime",
    "runtime_without_registry",
    "dead_metrics",
    "documented_without_registry",
    "rules_without_registry",
    "dashboarded_without_emission",
    "alerted_without_emission",
    "runtime_cardinality_review_required",
    "declared_risky_label_review_required",
    "runtime_label_contract_violations",
    "runtime_label_contract_unresolved",
    "runtime_cardinality_threshold_violations",
    "unused_declared_metrics",
    "unused_declared_observability_events",
)
_ALLOWLIST_METADATA_REQUIRED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "runtime_cardinality_review_required",
        "declared_risky_label_review_required",
    }
)
_CARDINALITY_RISK_LABEL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "endpoint",
        "field",
        "pipeline_context",
        "provider_context",
        "run_type_context",
        "table",
    }
)
_DIRECT_COLLECTOR_TERMINAL_METHODS: Final[frozenset[str]] = frozenset(
    {"inc", "observe", "set"}
)
_METRIC_OBJECT_NAME_BY_ID: Final[dict[int, str]] = {
    id(metric): metric_name
    for registry in (COUNTERS, GAUGES, HISTOGRAMS)
    for metric_name, metric in registry.items()
}
_EXPORTED_PROMETHEUS_METRIC_NAME_BINDINGS: Final[dict[str, str]] = {
    export_name: metric_name
    for export_name in METRICS_DEFINITION_EXPORT_NAMES
    if isinstance(
        metric_name := _METRIC_OBJECT_NAME_BY_ID.get(
            id(getattr(_metric_defs, export_name))
        ),
        str,
    )
}
