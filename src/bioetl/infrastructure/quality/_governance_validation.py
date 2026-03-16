"""Governance section validator."""

from __future__ import annotations

from datetime import date

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._baseline_validation import (
    _is_valid_rollout_section_key,
)
from bioetl.infrastructure.quality._primitives import (
    _parse_iso_date,
    _validate_gate_mode,
    _validate_non_negative_int,
)
from bioetl.infrastructure.quality.report_formatter import (
    _is_rollout_cutoff_stale,
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
    for field in ("owner", "classification", "linked_rf", "expires_on", "removal_step"):
        if field not in required_set:
            errors.append(
                "governance.review_policy.new_exemption_requires: "
                f"must include '{field}'"
            )


def _validate_baseline_policy(
    governance: dict[str, object], *, errors: list[str]
) -> None:
    """Require explicit separation between enforceable and historical baselines."""
    baseline_policy = governance.get("baseline_policy")
    if not isinstance(baseline_policy, dict):
        errors.append("governance.baseline_policy: expected mapping")
        return

    expected_sections = {
        "enforceable_section": "baseline",
        "historical_section": "historical_baseline",
        "registry_sync_source": "baseline",
    }
    for key, expected_value in expected_sections.items():
        actual_value = baseline_policy.get(key)
        if actual_value != expected_value:
            errors.append(
                f"governance.baseline_policy.{key}: expected {expected_value!r}, "
                f"got {actual_value!r}"
            )

    rationale = baseline_policy.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append("governance.baseline_policy.rationale: expected non-empty string")


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
    today: date | None = None,
) -> None:
    if not isinstance(warn_until, dict):
        errors.append(
            "governance.growth_section_gate_rollout.warn_until_by_section: expected mapping"
        )
        return

    now = today or date.today()
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
            continue
        if _is_rollout_cutoff_stale(cutoff, today=now):
            errors.append(
                "governance.growth_section_gate_rollout.warn_until_by_section."
                f"{section_key}: stale cutoff date {cutoff!r}; "
                "remove it or move it into the future"
            )


def _validate_growth_rollout(
    governance: dict[str, object],
    *,
    baseline_registry_names: set[str],
    group_names: set[str],
    errors: list[str],
    today: date | None = None,
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
        today=today,
    )


def _burn_down_priority_registries(raw: JsonDict) -> set[str]:
    """Return burn-down priority registries declared in governance config."""
    governance = raw.get("governance", {})
    if not isinstance(governance, dict):
        return set()
    burn_down = governance.get("burn_down_priorities", {})
    if not isinstance(burn_down, dict):
        return set()
    raw_registries = burn_down.get("registries", [])
    if not isinstance(raw_registries, list):
        return set()
    return {item for item in raw_registries if isinstance(item, str)}


def _validate_hotspot_name(
    *,
    entry: dict[str, object],
    prefix: str,
    seen_names: set[str],
    errors: list[str],
) -> None:
    """Validate hotspot name presence and uniqueness."""
    hotspot_name = entry.get("name")
    if not isinstance(hotspot_name, str) or not hotspot_name.strip():
        errors.append(f"{prefix}.name: expected non-empty string")
        return
    cleaned_name = hotspot_name.strip()
    if cleaned_name in seen_names:
        errors.append(f"{prefix}.name: duplicate hotspot name '{cleaned_name}'")
    seen_names.add(cleaned_name)


def _validate_hotspot_rationale(
    *,
    entry: dict[str, object],
    prefix: str,
    errors: list[str],
) -> None:
    """Validate hotspot rationale text."""
    rationale = entry.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append(f"{prefix}.rationale: expected non-empty string")


def _validate_hotspot_path_prefixes(
    *,
    entry: dict[str, object],
    prefix: str,
    errors: list[str],
) -> None:
    """Validate hotspot path prefixes point to source-tree locations."""
    path_prefixes = entry.get("path_prefixes")
    if not isinstance(path_prefixes, list) or not path_prefixes:
        errors.append(f"{prefix}.path_prefixes: expected non-empty list")
        return
    for item in path_prefixes:
        if not isinstance(item, str) or not item.startswith("src/bioetl/"):
            errors.append(
                f"{prefix}.path_prefixes: entries must start with 'src/bioetl/'"
            )


def _validate_hotspot_registry_budgets(
    *,
    entry: dict[str, object],
    prefix: str,
    baseline_registry_names: set[str],
    covered_priority_registries: set[str],
    errors: list[str],
) -> None:
    """Validate hotspot registry budgets against known registry names."""
    registry_budgets = entry.get("registry_budgets")
    if not isinstance(registry_budgets, dict) or not registry_budgets:
        errors.append(f"{prefix}.registry_budgets: expected non-empty mapping")
        return

    for registry_name, budget in sorted(registry_budgets.items()):
        if registry_name not in baseline_registry_names:
            errors.append(
                f"{prefix}.registry_budgets: unknown registry '{registry_name}'"
            )
            continue
        covered_priority_registries.add(registry_name)
        _validate_non_negative_int(
            budget,
            field_name=f"{prefix}.registry_budgets.{registry_name}",
            errors=errors,
        )


def _validate_hotspot_budgets_section(
    raw: JsonDict,
    *,
    baseline_registry_names: set[str],
    errors: list[str],
) -> None:
    """Validate hotspot budget declarations tied to concrete source-tree prefixes."""
    hotspot_budgets = raw.get("hotspot_budgets")
    if not isinstance(hotspot_budgets, list) or not hotspot_budgets:
        errors.append("hotspot_budgets: required non-empty list")
        return

    burn_down_registries = _burn_down_priority_registries(raw)
    seen_names: set[str] = set()
    covered_priority_registries: set[str] = set()
    for index, entry in enumerate(hotspot_budgets):
        prefix = f"hotspot_budgets[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix}: expected mapping")
            continue

        _validate_hotspot_name(
            entry=entry,
            prefix=prefix,
            seen_names=seen_names,
            errors=errors,
        )
        _validate_hotspot_rationale(entry=entry, prefix=prefix, errors=errors)
        _validate_hotspot_path_prefixes(entry=entry, prefix=prefix, errors=errors)
        _validate_hotspot_registry_budgets(
            entry=entry,
            prefix=prefix,
            baseline_registry_names=baseline_registry_names,
            covered_priority_registries=covered_priority_registries,
            errors=errors,
        )

    missing_priority_coverage = sorted(
        (burn_down_registries & baseline_registry_names) - covered_priority_registries
    )
    if missing_priority_coverage:
        errors.append(
            "hotspot_budgets: missing coverage for burn_down_priorities registries "
            f"{missing_priority_coverage}"
        )


def _validate_governance_section(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    *,
    baseline_registry_names: set[str],
    group_names: set[str],
    errors: list[str],
    today: date | None = None,
) -> bool:
    governance = raw.get("governance")
    if not isinstance(governance, dict):
        errors.append("governance: required mapping")
        return False

    _validate_baseline_policy(governance, errors=errors)
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
        today=today,
    )
    _validate_hotspot_budgets_section(
        raw,
        baseline_registry_names=baseline_registry_names,
        errors=errors,
    )

    return allow_rf_only_flag
