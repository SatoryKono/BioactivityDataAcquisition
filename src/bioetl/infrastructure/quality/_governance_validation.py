"""Governance section validator."""

from __future__ import annotations

from typing import Any

from bioetl.domain.types import JsonDict

from bioetl.infrastructure.quality._baseline_validation import (
    _is_valid_rollout_section_key,
)
from bioetl.infrastructure.quality._primitives import (
    _parse_iso_date,
    _validate_gate_mode,
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

    rollout = governance.get("growth_section_gate_rollout", {})
    if not isinstance(rollout, dict):
        errors.append("governance.growth_section_gate_rollout: expected mapping")
        return allow_rf_only_flag

    _validate_gate_mode(
        value=rollout.get(
            "default_mode", governance.get("growth_gate_default_mode", "block")
        ),
        field_name="governance.growth_section_gate_rollout.default_mode",
        errors=errors,
    )

    warn_until = rollout.get("warn_until_by_section", {})
    if not isinstance(warn_until, dict):
        errors.append(
            "governance.growth_section_gate_rollout.warn_until_by_section: expected mapping"
        )
        return allow_rf_only_flag

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

    return allow_rf_only_flag
