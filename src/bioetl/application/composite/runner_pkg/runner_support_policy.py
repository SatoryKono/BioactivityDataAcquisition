"""Pure policy helpers for composite runner support logic."""

from __future__ import annotations

from collections.abc import Collection, Iterable
from datetime import datetime

from bioetl.application.composite.preflight_validator import (
    CompositePreflightValidationService,
)
from bioetl.application.composite.runner_pkg.runner_result_types import (
    CompositeResultBuildRequest,
)
from bioetl.application.composite.runner_pkg.runner_support_types import (
    _PreparedPreflightValidationContext,
)
from bioetl.application.composite.runtime_models import (
    CompositeExecutionContext,
)
from bioetl.domain.composite import EnricherConfig
from bioetl.domain.composite.result import EnrichmentResult

__all__ = [
    "build_enrichers_to_run",
    "build_preflight_validation_context",
    "build_result_build_request",
    "can_run_enricher",
    "get_preflight_skip_reason",
    "get_required_enricher_failure",
]


def build_result_build_request(
    *,
    artifacts: CompositeExecutionContext,
    composite_name: str,
    run_id: str,
    start_time: float | None,
    started_at: datetime | None,
    original_run_id: str | None,
    required_enrichers: Collection[str],
    required_dependencies: Collection[str],
) -> CompositeResultBuildRequest:
    """Build the canonical result-assembly request for completion helpers."""
    return CompositeResultBuildRequest(
        artifacts=artifacts,
        composite_name=composite_name,
        run_id=run_id,
        start_time=start_time,
        started_at=started_at,
        original_run_id=original_run_id,
        required_enrichers=frozenset(required_enrichers),
        required_dependencies=frozenset(required_dependencies),
    )


def get_preflight_skip_reason(
    *,
    validator: CompositePreflightValidationService | None,
    field_priorities: Collection[str],
) -> str | None:
    """Return the reason preflight validation should be skipped, if any."""
    if validator is None:
        return "preflight_validator not configured"
    if not field_priorities:
        return "no field_priorities configured"
    return None


def build_preflight_validation_context(
    *,
    validator: CompositePreflightValidationService | None,
    field_priorities: Collection[str],
) -> _PreparedPreflightValidationContext | None:
    """Build validation context when preflight validation can run."""
    if (
        get_preflight_skip_reason(
            validator=validator,
            field_priorities=field_priorities,
        )
        is not None
    ):
        return None

    assert validator is not None
    return _PreparedPreflightValidationContext(
        validator=validator,
        field_count=len(field_priorities),
    )


def can_run_enricher(
    enricher: EnricherConfig,
    *,
    completed_enrichers: Collection[str],
    required_only: bool,
    enrich_only: Collection[str] | None,
    force_enricher: str | None,
) -> bool:
    """Return whether an enricher should run under the current runtime policy."""
    if enricher.pipeline in completed_enrichers and force_enricher != enricher.pipeline:
        return False

    if required_only and not enricher.required:
        return False

    return not (enrich_only and enricher.pipeline not in enrich_only)


def build_enrichers_to_run(
    enrichers: Iterable[EnricherConfig],
    *,
    completed_enrichers: Collection[str],
    required_only: bool,
    enrich_only: Collection[str] | None,
    force_enricher: str | None,
) -> list[EnricherConfig]:
    """Return the enrichers selected for execution."""
    return [
        enricher
        for enricher in enrichers
        if can_run_enricher(
            enricher,
            completed_enrichers=completed_enrichers,
            required_only=required_only,
            enrich_only=enrich_only,
            force_enricher=force_enricher,
        )
    ]


def get_required_enricher_failure(
    *,
    required_enrichers: Iterable[str],
    enrichment_results: dict[str, EnrichmentResult],
) -> str | None:
    """Return failure reason for required enricher validation, if any."""
    for enricher_name in required_enrichers:
        result = enrichment_results.get(enricher_name)
        if result is None:
            return f"Required enricher '{enricher_name}' did not run"
        if not result.is_success:
            return (
                f"Required enricher '{enricher_name}' failed: "
                f"{result.error_message or result.status.value}"
            )
    return None
