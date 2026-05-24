"""Private control-plane helpers for pipeline factory methods."""

from __future__ import annotations

from bioetl.domain.config import RuntimeConfig
from bioetl.infrastructure.config.settings_api import Settings


def apply_optional_control_plane_kwargs(
    kwargs: dict[str, object],
    *,
    manifest_id: str | None = None,
    execution_fingerprint: str | None = None,
    config_hash: str | None = None,
    resolved_config_hash: str | None = None,
    effective_config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
) -> None:
    """Attach only populated control-plane references to a kwargs bag."""
    for key, value in {
        "manifest_id": manifest_id,
        "execution_fingerprint": execution_fingerprint,
        "config_hash": config_hash,
        "resolved_config_hash": resolved_config_hash,
        "effective_config_hash": effective_config_hash,
        "dq_contract_compatibility_hash": dq_contract_compatibility_hash,
        "effective_config_artifact_id": effective_config_artifact_id,
    }.items():
        if value is not None:
            kwargs[key] = value


def resolve_strict_gold_validation(
    *,
    runtime: RuntimeConfig,
    settings: Settings,
) -> bool:
    """Resolve production/default strict-gold validation policy."""
    return (
        settings.env == "prod" and not settings.test_mode
    ) or runtime.strict_gold_validation
