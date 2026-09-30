"""Module-level JSON payload projectors for effective-config serialization."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
    DQPolicySnapshot,
    EffectiveExecutionConfig,
    ResolvedConfigSnapshot,
    RuntimeOverrideSnapshot,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQPolicyRef

__all__ = [
    "_dq_policy_ref_payload",
    "_dq_policy_snapshot_payload",
    "_effective_config_payload",
    "_resolution_policy_payload",
    "_resolved_config_payload",
    "_runtime_overrides_payload",
]


def _resolution_policy_payload(policy: ConfigResolutionPolicy) -> JsonDict:
    """Project a resolution policy snapshot to a JSON dict."""
    return {
        "merge_strategy": policy.merge_strategy,
        "default_materialization": policy.default_materialization,
        "strict_validation": policy.strict_validation,
        "allow_runtime_overrides": policy.allow_runtime_overrides,
    }


def _resolved_config_payload(
    config: ResolvedConfigSnapshot,
    normalize: Callable[[object], JsonDict],
) -> JsonDict:
    """Project a resolved config snapshot to a JSON dict."""
    return {
        "config_type": config.config_type,
        "config_data": normalize(config.config_data),
        "config_hash": config.config_hash,
    }


def _runtime_overrides_payload(
    overrides: RuntimeOverrideSnapshot,
    normalize: Callable[[object], JsonDict],
) -> JsonDict:
    """Project runtime overrides to a JSON dict."""
    result: JsonDict = {}
    for field_name, key in (
        ("cli_overrides", "cli_overrides"),
        ("env_overrides", "env_overrides"),
        ("runtime_adjustments", "runtime_adjustments"),
    ):
        raw = getattr(overrides, field_name)
        if raw:
            result[key] = normalize(raw)
    if result and overrides.override_hash:
        result["override_hash"] = overrides.override_hash
    return result


def _effective_config_payload(
    config: EffectiveExecutionConfig,
    normalize: Callable[[object], JsonDict],
) -> JsonDict:
    """Project an effective execution config to a JSON dict."""
    return {
        "config_data": normalize(config.config_data),
        "effective_hash": config.effective_hash,
    }


def _dq_policy_ref_payload(policy_ref: DQPolicyRef) -> JsonDict:
    """Project a DQ policy reference to a JSON dict."""
    return {
        "contract_ref": policy_ref.contract_ref,
        "contract_version": policy_ref.contract_version,
        "rule_bundle_version": policy_ref.rule_bundle_version,
        "policy_hash": policy_ref.policy_hash,
    }


def _dq_policy_snapshot_payload(snapshot: DQPolicySnapshot) -> JsonDict:
    """Project a DQ policy snapshot to a JSON dict."""
    return {
        "contract_ref": snapshot.contract_ref,
        "contract_version": snapshot.contract_version,
        "rule_bundle_version": snapshot.rule_bundle_version,
        "policy_hash": snapshot.policy_hash,
        "default_disposition": snapshot.default_disposition.value,
        "disposition_overrides": {
            str(key): value.value
            for key, value in snapshot.disposition_overrides.items()
        },
        "strictness_mode": snapshot.strictness_mode,
    }
