"""No-op (stub) factory functions for testing and fallback scenarios."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from bioetl.domain.clients.base.output.contracts import RunMetadataBuilderProtocol
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.domain.validation import ValidatorFactoryABC
from bioetl.domain.validation.contracts import ValidationResult

__all__ = [
    "create_noop_logger",
    "create_noop_metadata_builder",
    "create_noop_metrics_port",
    "create_noop_validator_factory",
]


def create_noop_logger() -> LoggingPortABC:
    """Return a no-op logger respecting the logging port contract."""

    def _bound_logger(**_: Any) -> LoggingPortABC:
        return create_noop_logger()

    return cast(
        LoggingPortABC,
        SimpleNamespace(
            info=lambda _msg, **__ctx: None,
            error=lambda _msg, **__ctx: None,
            debug=lambda _msg, **__ctx: None,
            warning=lambda _msg, **__ctx: None,
            apply_bind=_bound_logger,
        ),
    )


def create_noop_metadata_builder() -> RunMetadataBuilderProtocol:
    """Return metadata builder that emits minimal deterministic payloads."""

    return cast(
        RunMetadataBuilderProtocol,
        SimpleNamespace(
            build_run_metadata=lambda context, write_result: {
                "run_id": getattr(context, "run_id", None),
                "row_count": getattr(write_result, "row_count", 0),
            },
            build_dry_run_metadata=lambda context, row_count: {
                "run_id": getattr(context, "run_id", None),
                "row_count": row_count,
            },
        ),
    )


def create_noop_metrics_port() -> MetricsPortABC:
    """Return metrics port that records nothing (for tests/fallback)."""

    return cast(
        MetricsPortABC,
        SimpleNamespace(
            inc_counter=lambda *_args, **_kwargs: None,
            observe_histogram=lambda *_args, **_kwargs: None,
            update_stage_duration=lambda **_kwargs: None,
            update_stage_total=lambda **_kwargs: None,
        ),
    )


def create_noop_validator_factory() -> ValidatorFactoryABC:
    """Return validator factory that treats all data as valid (for tests)."""

    def _validate(df: Any) -> ValidationResult:
        return ValidationResult(
            is_valid=True, errors=[], warnings=[], validated_data=df
        )

    validator = SimpleNamespace(validate=_validate, is_valid=lambda _df: True)
    return cast(
        ValidatorFactoryABC,
        SimpleNamespace(create_validator=lambda _schema: validator),
    )
