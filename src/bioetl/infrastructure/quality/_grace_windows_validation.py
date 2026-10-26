"""Grace windows section validator."""

from __future__ import annotations

from datetime import date

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality._primitives import (
    _parse_iso_date,
    _validate_non_negative_int,
)


def _validate_allowances(
    *,
    allowances: object,
    prefix: str,
    baseline_registry_names: set[str],
    group_names: set[str],
    errors: list[str],
) -> None:
    if not isinstance(allowances, dict):
        errors.append(f"{prefix}.allowances: expected mapping")
        return

    _validate_non_negative_int(
        allowances.get("total_exemptions", 0),
        field_name=f"{prefix}.allowances.total_exemptions",
        errors=errors,
    )

    registry_allowances = allowances.get("registry_budgets", {})
    if not isinstance(registry_allowances, dict):
        errors.append(f"{prefix}.allowances.registry_budgets: expected mapping")
    else:
        for registry_name, value in registry_allowances.items():
            if registry_name not in baseline_registry_names:
                errors.append(
                    f"{prefix}.allowances.registry_budgets: unknown registry '{registry_name}'"
                )
                continue
            _validate_non_negative_int(
                value,
                field_name=f"{prefix}.allowances.registry_budgets.{registry_name}",
                errors=errors,
            )

    group_allowances = allowances.get("group_budgets", {})
    if not isinstance(group_allowances, dict):
        errors.append(f"{prefix}.allowances.group_budgets: expected mapping")
        return
    for group_name, value in group_allowances.items():
        if group_name not in group_names:
            errors.append(
                f"{prefix}.allowances.group_budgets: unknown group '{group_name}'"
            )
            continue
        _validate_non_negative_int(
            value,
            field_name=f"{prefix}.allowances.group_budgets.{group_name}",
            errors=errors,
        )


def _validate_grace_window_metadata(
    *,
    prefix: str,
    window: JsonDict,  # Any: YAML values are heterogeneous
    allow_rf_only_for_rf: bool,
    errors: list[str],
) -> None:
    rf_id = window.get("rf_id")
    approved = window.get("approved")
    starts_on = _parse_iso_date(window.get("starts_on"))
    ends_on = _parse_iso_date(window.get("ends_on"))

    _validate_grace_window_identity_fields(
        prefix=prefix,
        rf_id=rf_id,
        approved=approved,
        allow_rf_only_for_rf=allow_rf_only_for_rf,
        errors=errors,
    )
    _validate_grace_window_dates(
        prefix=prefix,
        starts_on=starts_on,
        ends_on=ends_on,
        errors=errors,
    )


def _parse_rf_id(rf_id: object) -> tuple[str | None, bool]:
    """Return (rf_id_str, is_rf_ref) from raw rf_id value."""
    if not isinstance(rf_id, str) or not rf_id.strip():
        return None, False
    return rf_id, rf_id.startswith("RF-")


def _validate_approved_field(
    *,
    prefix: str,
    approved: object,
    allow_rf_only_for_rf: bool,
    errors: list[str],
) -> None:
    if not isinstance(approved, bool):
        errors.append(f"{prefix}.approved: expected bool")
        return
    if allow_rf_only_for_rf and approved is False:
        errors.append(
            f"{prefix}.approved: must be true when "
            "governance.allow_grace_windows_only_for_rf=true"
        )


def _validate_rf_id_reference(
    *,
    prefix: str,
    rf_id_valid: bool,
    is_rf_ref: bool,
    approved: object,
    allow_rf_only_for_rf: bool,
    errors: list[str],
) -> None:
    if not rf_id_valid:
        return
    if isinstance(approved, bool) and approved and not is_rf_ref:
        errors.append(f"{prefix}.rf_id: approved grace window must reference RF-*")
    if allow_rf_only_for_rf and not is_rf_ref:
        errors.append(
            f"{prefix}.rf_id: must reference RF-* when "
            "governance.allow_grace_windows_only_for_rf=true"
        )


def _validate_grace_window_identity_fields(
    *,
    prefix: str,
    rf_id: object,
    approved: object,
    allow_rf_only_for_rf: bool,
    errors: list[str],
) -> None:
    rf_id_str, is_rf_ref = _parse_rf_id(rf_id)
    rf_id_valid = rf_id_str is not None

    if not rf_id_valid:
        errors.append(f"{prefix}.rf_id: required non-empty string")

    _validate_approved_field(
        prefix=prefix,
        approved=approved,
        allow_rf_only_for_rf=allow_rf_only_for_rf,
        errors=errors,
    )
    _validate_rf_id_reference(
        prefix=prefix,
        rf_id_valid=rf_id_valid,
        is_rf_ref=is_rf_ref,
        approved=approved,
        allow_rf_only_for_rf=allow_rf_only_for_rf,
        errors=errors,
    )


def _validate_grace_window_dates(
    *,
    prefix: str,
    starts_on: date | None,
    ends_on: date | None,
    errors: list[str],
) -> None:
    if starts_on is None:
        errors.append(f"{prefix}.starts_on: expected ISO date")
    if ends_on is None:
        errors.append(f"{prefix}.ends_on: expected ISO date")
    if starts_on is not None and ends_on is not None and ends_on < starts_on:
        errors.append(f"{prefix}: ends_on must be >= starts_on")


def _validate_grace_windows_section(
    raw: JsonDict,  # Any: YAML values are heterogeneous
    *,
    baseline_registry_names: set[str],
    group_names: set[str],
    allow_rf_only_for_rf: bool,
    errors: list[str],
) -> None:
    grace_windows = raw.get("grace_windows", [])
    if grace_windows is None:
        grace_windows = []
    if not isinstance(grace_windows, list):
        errors.append("grace_windows: expected list")
        return

    for index, window in enumerate(grace_windows):
        prefix = f"grace_windows[{index}]"
        if not isinstance(window, dict):
            errors.append(f"{prefix}: expected mapping")
            continue

        _validate_grace_window_metadata(
            prefix=prefix,
            window=window,
            allow_rf_only_for_rf=allow_rf_only_for_rf,
            errors=errors,
        )
        _validate_allowances(
            allowances=window.get("allowances", {}),
            prefix=prefix,
            baseline_registry_names=baseline_registry_names,
            group_names=group_names,
            errors=errors,
        )
