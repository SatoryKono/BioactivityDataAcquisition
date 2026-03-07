"""Governance section validator."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._baseline_validation import (
    _is_valid_rollout_section_key,
)
from bioetl.infrastructure.quality._primitives import (
    _parse_iso_date,
    _validate_gate_mode,
)


def _validate_review_policy(review_policy: object, *, errors: list[str]) -> None:
    if not isinstance(review_policy, dict):
        errors.append("governance.review_policy: expected mapping")
        return

    required = review_policy.get("new_exemption_requires")
    if not isinstance(required, list) or not required:
        errors.append(
            "governance.review_policy.new_exemption_requires: expected non-empty list"
        )
        return

    required_set = {
        item.strip() for item in required if isinstance(item, str) and item.strip()
    }
    for field in ("owner", "expires_on", "removal_step"):
        if field not in required_set:
            errors.append(
                "governance.review_policy.new_exemption_requires: "
                f"must include '{field}'"
            )


def _validate_owner_registry_subsystems(
    owner_subsystems: object,
    *,
    errors: list[str],
) -> None:
    if not isinstance(owner_subsystems, dict):
        errors.append("governance.owner_registry_q2_subsystems: expected mapping")
        return

    if len(owner_subsystems) < 3:
        errors.append(
            "governance.owner_registry_q2_subsystems: expected at least 3 subsystems"
        )

    owners: set[str] = set()
    for subsystem, cfg in owner_subsystems.items():
        if not isinstance(subsystem, str) or not subsystem.strip():
            errors.append(
                "governance.owner_registry_q2_subsystems: "
                "subsystem key must be non-empty string"
            )
            continue
        if not isinstance(cfg, dict):
            errors.append(
                f"governance.owner_registry_q2_subsystems.{subsystem}: expected mapping"
            )
            continue
        owner = cfg.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            errors.append(
                "governance.owner_registry_q2_subsystems."
                f"{subsystem}.owner: expected non-empty string"
            )
            continue
        owners.add(owner.strip())

    if len(owners) < 3:
        errors.append(
            "governance.owner_registry_q2_subsystems: expected at least 3 distinct owners"
        )


def _validate_warn_until_by_section(
    warn_until: object,
    *,
    baseline_registry_names: set[str],
    group_names: set[str],
    errors: list[str],
) -> None:
    if not isinstance(warn_until, dict):
        errors.append(
            "governance.growth_section_gate_rollout.warn_until_by_section: expected mapping"
        )
        return

    for section_key, cutoff in sorted(warn_until.items()):
        if not isinstance(section_key, str) or not section_key.strip():
            errors.append(
                "governance.growth_section_gate_rollout.warn_until_by_section: "
                "section key must be non-empty string"
            )
            continue
        if not _is_valid_rollout_section_key(
            key=section_key,
            baseline_registry_names=baseline_registry_names,
            group_names=group_names,
        ):
            errors.append(
                "governance.growth_section_gate_rollout.warn_until_by_section: "
                f"unknown section key '{section_key}'"
            )
            continue
        if _parse_iso_date(cutoff) is None:
            errors.append(
                "governance.growth_section_gate_rollout.warn_until_by_section."
                f"{section_key}: expected ISO date (YYYY-MM-DD)"
            )


def _validate_growth_rollout(
    governance: dict[str, object],
    *,
    baseline_registry_names: set[str],
    group_names: set[str],
    errors: list[str],
) -> None:
    rollout = governance.get("growth_section_gate_rollout", {})
    if not isinstance(rollout, dict):
        errors.append("governance.growth_section_gate_rollout: expected mapping")
        return

    _validate_gate_mode(
        value=rollout.get(
            "default_mode", governance.get("growth_gate_default_mode", "block")
        ),
        field_name="governance.growth_section_gate_rollout.default_mode",
        errors=errors,
    )
    _validate_warn_until_by_section(
        rollout.get("warn_until_by_section", {}),
        baseline_registry_names=baseline_registry_names,
        group_names=group_names,
        errors=errors,
    )


def _validate_governance_section(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    *,
    baseline_registry_names: set[str],
    group_names: set[str],
    errors: list[str],
) -> bool:
    governance = raw.get("governance")
    if not isinstance(governance, dict):
        errors.append("governance: required mapping")
        return False

    _validate_review_policy(governance.get("review_policy"), errors=errors)
    _validate_owner_registry_subsystems(
        governance.get("owner_registry_q2_subsystems"),
        errors=errors,
    )

    _validate_gate_mode(
        value=governance.get("growth_gate_default_mode", "block"),
        field_name="governance.growth_gate_default_mode",
        errors=errors,
    )

    allow_rf_only = governance.get("allow_grace_windows_only_for_rf")
    allow_rf_only_flag = False
    if not isinstance(allow_rf_only, bool):
        errors.append("governance.allow_grace_windows_only_for_rf: expected bool")
    else:
        allow_rf_only_flag = allow_rf_only

    _validate_growth_rollout(
        governance,
        baseline_registry_names=baseline_registry_names,
        group_names=group_names,
        errors=errors,
    )

    return allow_rf_only_flag
