"""Runtime policy decisions relocated out of composition (#11241)."""

from __future__ import annotations

from typing import Literal

HealthCheckMode = Literal["strict", "probe"]

DEFAULT_UNIPROT_MAPPING_DATABASES = ("ChEMBL", "UniProtKB")


def resolve_metrics_publication_modes(
    *,
    metrics_enabled: bool,
    metrics_server_enabled: bool,
) -> tuple[str, str]:
    """Return ``(metrics_server_mode, pushgateway_mode)``."""
    metrics_server_mode = (
        "auto_managed_during_pipeline_runs"
        if metrics_enabled and metrics_server_enabled
        else "disabled"
    )
    pushgateway_mode = (
        "best_effort_on_run_completion" if metrics_enabled else "disabled"
    )
    return metrics_server_mode, pushgateway_mode


def resolve_seed_run_type(run_type: str | None, workflow_name: str | None) -> str:
    """Default publication run-type seed used by observability profiles."""
    if isinstance(run_type, str) and run_type.strip():
        return run_type.strip()
    if workflow_name is None:
        return "incremental"
    return ""


def resolve_health_check_mode(
    *,
    test_mode: bool,
    configured_mode: object,
    default_health_check_mode: HealthCheckMode,
) -> HealthCheckMode:
    """Resolve health-check mode from settings with an explicit default."""
    if test_mode:
        return "probe"
    if configured_mode in ("strict", "probe"):
        return configured_mode  # type: ignore[return-value]
    return default_health_check_mode


def resolve_skip_gold(*, cli_skip_gold: bool, gold_sink_enabled: bool) -> bool:
    """Return whether Gold writes should be skipped."""
    if cli_skip_gold:
        return True
    return not gold_sink_enabled


def memory_adaptive_sizing_allowed(*, exact_replay: bool) -> bool:
    """Exact replay disables adaptive memory sizing."""
    return not exact_replay


def pipeline_name_fallbacks(pipeline_name: str) -> tuple[str, str]:
    """Split ``provider_entity`` pipeline names into fallback components."""
    if "_" in pipeline_name:
        provider, entity = pipeline_name.split("_", 1)
        return provider, entity
    return pipeline_name, pipeline_name


def resolve_uniprot_mapping_databases(
    *,
    configured_from_db: str | None,
    configured_to_db: str | None,
) -> tuple[str, str]:
    """Apply ChEMBL/UniProtKB defaults when API databases are unset."""
    from_db, to_db = DEFAULT_UNIPROT_MAPPING_DATABASES
    return configured_from_db or from_db, configured_to_db or to_db
