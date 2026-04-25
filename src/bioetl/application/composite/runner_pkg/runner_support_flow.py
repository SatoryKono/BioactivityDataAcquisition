"""Correlation and preflight helpers for composite runner support flow."""

from __future__ import annotations

__all__ = [
    "build_correlation_log_context",
    "get_expected_contract_ref",
    "get_expected_contract_version",
    "get_expected_effective_config_hash",
    "run_preflight_validation",
    "validate_config_consistency",
]

from bioetl.application.composite.runner_pkg.runner_support_types import (
    _CompositeRunnerSupportHostProtocol,
)
from bioetl.domain.normalization import (
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_sha256,
)


def _normalize_optional_anchor(value: object) -> str | None:
    """Return stripped text anchors while ignoring mock/empty placeholders."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def get_expected_effective_config_hash(
    host: _CompositeRunnerSupportHostProtocol,
) -> str | None:
    """Return effective-config hash anchor when checkpoint manager exposes it."""
    checkpoint_manager = getattr(host, "_checkpoint_manager", None)
    return normalize_control_plane_sha256(
        _normalize_optional_anchor(
            getattr(checkpoint_manager, "expected_effective_config_hash", None)
        ),
    )


def get_expected_contract_ref(host: _CompositeRunnerSupportHostProtocol) -> str | None:
    """Return contract-ref anchor from checkpoint manager or composite config."""
    checkpoint_manager = getattr(host, "_checkpoint_manager", None)
    return normalize_contract_ref(
        _normalize_optional_anchor(
            getattr(checkpoint_manager, "expected_contract_ref", None)
        )
        or normalize_contract_ref(
            _normalize_optional_anchor(getattr(host._config, "name", None))
        )
    )


def get_expected_contract_version(
    host: _CompositeRunnerSupportHostProtocol,
) -> str | None:
    """Return contract-version anchor from checkpoint manager or config."""
    checkpoint_manager = getattr(host, "_checkpoint_manager", None)
    return normalize_contract_version(
        _normalize_optional_anchor(
            getattr(checkpoint_manager, "expected_contract_version", None)
        )
        or normalize_contract_version(
            _normalize_optional_anchor(getattr(host._config, "version", None))
        )
    )


def build_correlation_log_context(
    host: _CompositeRunnerSupportHostProtocol,
    **extra: object,
) -> dict[str, object]:
    """Build a stable correlation envelope for composite critical logs."""
    context: dict[str, object] = {
        "composite": host._config.name,
        "run_id": host._run_id_str,
        "composite_run_id": host._run_id_str,
    }
    effective_config_hash = get_expected_effective_config_hash(host)
    if effective_config_hash is not None:
        context["effective_config_hash"] = effective_config_hash
    contract_ref = get_expected_contract_ref(host)
    if contract_ref is not None:
        context["contract_ref"] = contract_ref
    contract_version = get_expected_contract_version(host)
    if contract_version is not None:
        context["contract_version"] = contract_version
    context.update(extra)
    return context


def validate_config_consistency(host: _CompositeRunnerSupportHostProtocol) -> None:
    """Validate configuration consistency and log anomalies."""
    expected_required = frozenset(
        enricher.pipeline for enricher in host._config.enrichers if enricher.required
    )
    actual_required = frozenset(host._config.required_enrichers)

    if expected_required != actual_required:
        host._logger.warning(
            "Config inconsistency: required_enrichers mismatch",
            **host._build_correlation_log_context(
                expected_required=list(expected_required),
                actual_required=list(actual_required),
                note="This may indicate a bug in CompositeConfig",
            ),
        )

    if not expected_required and host._config.enrichers:
        host._logger.info(
            "All enrichers are optional",
            **host._build_correlation_log_context(
                enricher_count=len(host._config.enrichers),
                note="Pipeline will succeed even if all enrichers fail",
            ),
        )


def run_preflight_validation(host: _CompositeRunnerSupportHostProtocol) -> None:
    """Run preflight validation for field priorities when configured."""
    context = host._prepare_preflight_validation_context()
    if context is None:
        host._logger.debug(
            "Preflight validation skipped",
            **host._build_correlation_log_context(
                stage="preflight_validation",
                reason=host._get_preflight_skip_reason(),
            ),
        )
        return

    host._observer.emit_phase_started(
        composite_name=host._config.name,
        run_id=host._run_id_str,
        phase_name="preflight_validation",
        details=host._build_correlation_log_context(
            stage="preflight_validation",
            field_count=context.field_count,
        ),
    )

    result = context.validator.validate(
        host._config,
        fail_on_error=True,
    )
    context.validator.log_resolved_field_sources(result, host._config.name)

    host._observer.emit_phase_completed(
        composite_name=host._config.name,
        run_id=host._run_id_str,
        phase_name="preflight_validation",
        details=host._build_correlation_log_context(
            stage="preflight_validation",
            fields_validated=len(result.resolved_fields),
            warnings=len(result.warnings),
        ),
    )
