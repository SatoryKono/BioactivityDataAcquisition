"""Validation helpers for architecture metric exemptions registry."""

from __future__ import annotations

import re
from datetime import date

from bioetl.domain.types import JsonDict

_DEFAULT_REQUIRED_FIELDS = (
    "value",
    "owner",
    "reason",
    "classification",
    "linked_rf",
    "expires_on",
    "removal_step",
)
_DUE_DATE_FIELDS = ("expires_on", "due_on")
_ALLOWED_CLASSIFICATIONS = frozenset({"technical_debt", "intentional_exception"})
_PLACEHOLDER_NAME_RE = re.compile(
    r"^(todo|tbd|unknown|temp|fixme|example|placeholder)$",
    re.IGNORECASE,
)
_PLACEHOLDER_OWNER_RE = re.compile(
    r"^(todo|tbd|unknown|none|unassigned|team)$",
    re.IGNORECASE,
)
_TRACKING_ID_RE = re.compile(r"^(?:RF|QG|AUD|DOC|CFG|DBG)-\d{3}$")


def _validate_required_fields(
    prefix: str,
    entry: JsonDict,  # Any: DQ check values vary by check type
    required_fields: tuple[str, ...],
    metadata_errors: list[str],
) -> None:
    """Validate presence and non-empty values for required entry fields."""
    for field_name in required_fields:
        if field_name in _DUE_DATE_FIELDS:
            continue
        value = entry.get(field_name)
        if value is None:
            metadata_errors.append(f"{prefix}: missing required field '{field_name}'")
            continue
        if isinstance(value, str) and not value.strip():
            metadata_errors.append(f"{prefix}: empty required field '{field_name}'")


def _normalize_required_fields(
    raw_fields: object,
    metadata_errors: list[str],
) -> tuple[str, ...]:
    """Normalize policy.required_fields into stable tuple with fallbacks."""
    if not isinstance(raw_fields, list) or not raw_fields:
        metadata_errors.append(
            "policy.required_fields: expected non-empty list, "
            f"falling back to default {list(_DEFAULT_REQUIRED_FIELDS)}"
        )
        return _DEFAULT_REQUIRED_FIELDS

    normalized: list[str] = []
    for item in raw_fields:
        if not isinstance(item, str) or not item.strip():
            metadata_errors.append(
                "policy.required_fields: field names must be non-empty strings"
            )
            continue
        normalized.append(item.strip())

    return tuple(normalized) if normalized else _DEFAULT_REQUIRED_FIELDS


def get_policy_required_fields(
    raw: JsonDict,  # Any: DQ check values vary by check type
    metadata_errors: list[str],
) -> tuple[str, ...]:
    """Read required field policy and enforce tracking/removal governance."""
    required_fields: tuple[str, ...]
    policy = raw.get("policy", {})
    if not isinstance(policy, dict):
        metadata_errors.append("policy: expected mapping, falling back to defaults")
        required_fields = _DEFAULT_REQUIRED_FIELDS
    else:
        required_fields = _normalize_required_fields(
            policy.get("required_fields", list(_DEFAULT_REQUIRED_FIELDS)),
            metadata_errors,
        )

    if "owner" not in required_fields:
        metadata_errors.append("policy.required_fields must include 'owner'")
    if "classification" not in required_fields:
        metadata_errors.append("policy.required_fields must include 'classification'")
    if "linked_rf" not in required_fields:
        metadata_errors.append("policy.required_fields must include 'linked_rf'")
    if "removal_step" not in required_fields:
        metadata_errors.append("policy.required_fields must include 'removal_step'")
    if not any(field in required_fields for field in _DUE_DATE_FIELDS):
        metadata_errors.append(
            "policy.required_fields must include due date field "
            "('expires_on' or 'due_on')"
        )
    return required_fields


def _validate_owner(
    prefix: str,
    entry: JsonDict,  # Any: DQ check values vary by check type
    metadata_errors: list[str],
) -> None:
    """Validate owner field is not using placeholders."""
    owner = entry.get("owner")
    if isinstance(owner, str) and _PLACEHOLDER_OWNER_RE.match(owner.strip()):
        metadata_errors.append(f"{prefix}: owner placeholder is not allowed")


def _validate_classification(
    prefix: str,
    entry: JsonDict,  # Any: DQ check values vary by check type
    metadata_errors: list[str],
) -> None:
    """Validate exemption classification uses the approved vocabulary."""
    classification = entry.get("classification")
    if not isinstance(classification, str) or not classification.strip():
        metadata_errors.append(
            f"{prefix}: classification must be non-empty string "
            f"({', '.join(sorted(_ALLOWED_CLASSIFICATIONS))})"
        )
        return

    normalized = classification.strip()
    if normalized not in _ALLOWED_CLASSIFICATIONS:
        metadata_errors.append(
            f"{prefix}: classification must be one of "
            f"{', '.join(sorted(_ALLOWED_CLASSIFICATIONS))}"
        )


def _validate_linked_rf(
    prefix: str,
    entry: JsonDict,  # Any: DQ check values vary by check type
    metadata_errors: list[str],
) -> None:
    """Validate tracking link format for exemption follow-up work."""
    linked_rf = entry.get("linked_rf")
    if not isinstance(linked_rf, str) or not linked_rf.strip():
        metadata_errors.append(
            f"{prefix}: linked_rf must be non-empty tracking id like RF-001 or QG-001"
        )
        return
    if _TRACKING_ID_RE.match(linked_rf.strip()) is None:
        metadata_errors.append(
            f"{prefix}: linked_rf must match RF-001/QG-001 style tracking id"
        )


def _resolve_due_field(
    entry: JsonDict,  # Any: DQ check values vary by check type
    required_fields: tuple[str, ...],
) -> str:
    """Determine the most appropriate due-date field name for an entry."""
    candidates = list(
        dict.fromkeys(
            [f for f in required_fields if f in _DUE_DATE_FIELDS]
            + list(_DUE_DATE_FIELDS)
        )
    )
    return next((f for f in candidates if f in entry), candidates[0])


def _validate_due_date(
    prefix: str,
    entry: JsonDict,  # Any: DQ check values vary by check type
    required_fields: tuple[str, ...],
    now: date,
    metadata_errors: list[str],
    expired_entries: list[str],
) -> None:
    """Validate due-date field format and expiration status."""
    selected_field = _resolve_due_field(entry, required_fields)
    due_value = entry.get(selected_field)

    if not isinstance(due_value, str):
        metadata_errors.append(
            f"{prefix}: due date field '{selected_field}' must be ISO date string (YYYY-MM-DD)"
        )
        return

    try:
        expiry_date = date.fromisoformat(due_value)
    except ValueError:
        metadata_errors.append(
            f"{prefix}: due date field '{selected_field}' must be ISO date (YYYY-MM-DD)"
        )
        return

    if expiry_date < now:
        expired_entries.append(
            f"{prefix} expired on {due_value} (field={selected_field}, owner={entry.get('owner')})"
        )


def validate_exemption_entry(
    registry_name: str,
    exemption_name: object,
    entry: object,
    required_fields: tuple[str, ...],
    now: date,
    metadata_errors: list[str],
    expired_entries: list[str],
) -> None:
    """Validate one exemption entry and append issues into result lists."""
    prefix = f"{registry_name}.{exemption_name}"

    if not isinstance(exemption_name, str) or not exemption_name.strip():
        metadata_errors.append(f"{prefix}: exemption key must be non-empty string")
        return

    if _PLACEHOLDER_NAME_RE.match(exemption_name.strip()):
        metadata_errors.append(f"{prefix}: placeholder exemption name is not allowed")

    if not isinstance(entry, dict):
        metadata_errors.append(f"{prefix}: entry must be mapping")
        return

    _validate_required_fields(prefix, entry, required_fields, metadata_errors)
    _validate_owner(prefix, entry, metadata_errors)
    _validate_classification(prefix, entry, metadata_errors)
    _validate_linked_rf(prefix, entry, metadata_errors)
    _validate_due_date(
        prefix,
        entry,
        required_fields,
        now,
        metadata_errors,
        expired_entries,
    )
