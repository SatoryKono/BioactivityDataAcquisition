"""Allowlist parsing and deterministic drift validation for diagnostics."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from bioetl.infrastructure.observability.metric_inventory_report import (
    _drift_allowlist_token,
)
from bioetl.infrastructure.observability.metric_inventory_shared import (
    _ALLOWLIST_METADATA_REQUIRED_KEYS,
    _CHECK_DRIFT_KEYS,
)
from bioetl.infrastructure.time.system_clock import current_utc_time


def _parse_allowlist_metric_name(
    key: str, item: object
) -> str | None:  # pragma: no cover - exercised through _load_drift_allowlist
    if isinstance(item, str):
        if key in _ALLOWLIST_METADATA_REQUIRED_KEYS:
            raise ValueError(
                f"{key} entries must be mappings with metric/owner/reason/review_date"
            )
        return item
    if not isinstance(item, dict):
        raise ValueError(f"{key} entries must be strings or mappings")

    metric_name = item.get("metric")
    if not isinstance(metric_name, str) or not metric_name:
        raise ValueError(f"{key} mapping entries must declare a non-empty metric")

    if key in _ALLOWLIST_METADATA_REQUIRED_KEYS:
        for field_name in ("owner", "reason", "review_date"):
            field_value = item.get(field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(
                    f"{key} metric {metric_name!r} is missing required {field_name}"
                )
        _validate_allowlist_review_date(
            key=key,
            metric_name=metric_name,
            raw_review_date=str(item["review_date"]),
        )
    return metric_name


def _validate_allowlist_review_date(
    *,
    key: str,
    metric_name: str,
    raw_review_date: str,
    today: date | None = None,
) -> None:
    try:
        review_date = date.fromisoformat(raw_review_date)
    except ValueError as exc:
        raise ValueError(
            f"{key} metric {metric_name!r} has invalid review_date "
            f"{raw_review_date!r}; expected ISO YYYY-MM-DD"
        ) from exc
    if review_date < (
        today if today is not None else current_utc_time().astimezone().date()
    ):
        raise ValueError(
            f"{key} metric {metric_name!r} has expired review_date "
            f"{raw_review_date}; refresh or remove this lifecycle exception"
        )


def _load_drift_allowlist(path: Path) -> dict[str, set[str]]:
    safe = path.expanduser().resolve()
    if not safe.exists():
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    # Resolve again immediately before the read sink (pythonsecurity:S8707).
    payload = yaml.safe_load(
        safe.read_text(encoding="utf-8")  # NOSONAR - path confined
    )
    if not isinstance(payload, dict):
        return {}
    raw_allowed = payload.get("allowed", payload)
    if not isinstance(raw_allowed, dict):
        return {}
    allowlist: dict[str, set[str]] = {}
    for key in _CHECK_DRIFT_KEYS:
        values = raw_allowed.get(key, [])
        if not isinstance(values, list):
            continue
        allowlist[key] = {
            metric_name
            for metric_name in (
                _parse_allowlist_metric_name(key, value) for value in values
            )
            if metric_name
        }
    return allowlist


def validate_metric_inventory(
    report: dict[str, list[str] | dict[str, list[str]]],
    *,
    allowlist: dict[str, set[str]] | None = None,
) -> dict[str, list[str]]:
    """Return unallowed metric drift grouped by deterministic check category."""
    allowed = allowlist or {}
    violations: dict[str, list[str]] = {}
    for key in _CHECK_DRIFT_KEYS:
        values = report.get(key, [])
        if not isinstance(values, list):
            continue
        allowed_values = allowed.get(key, set())
        unallowed = sorted(
            {
                value
                for value in values
                if _drift_allowlist_token(key, value) not in allowed_values
            }
        )
        if unallowed:
            violations[key] = unallowed
    return violations
