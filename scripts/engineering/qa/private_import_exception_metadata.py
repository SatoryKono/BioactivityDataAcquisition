"""Metadata checks for the shrink-only private-import ratchet.

Source comments are not waivers. Only YAML pair rows with a matching id,
exact scope, owner, rationale, enforcement test, and dated exit condition
suppress a cross-owner private import.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

_PAIR_ID = re.compile(r"^PIM-[A-Z]+-\d{3}$")
_REQUIRED_FIELDS = (
    "id",
    "importer",
    "target",
    "owner",
    "scope",
    "rationale",
    "sanction",
    "enforcement",
    "classification",
    "exit_condition",
)
_KNOWN_OWNERS = frozenset(
    {
        "@bioetl-application",
        "@bioetl-composition",
        "@bioetl-domain",
        "@bioetl-infrastructure",
    }
)
_VAGUE_EXIT = frozenset(
    {"residual", "tbd", "todo", "later", "n/a", "none", "waived", "temporary"}
)
_MIN_TEXT = 40
_DEFAULT_HORIZON_DAYS = 120


def _text(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    return value.strip() if isinstance(value, str) else ""


def _scope_for(importer: str, target: str) -> str:
    return f"{importer} -> {target}"


def _parse_review_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def validate_exception_metadata(
    config: dict[str, Any],
    *,
    project_root: Path,
    today: date,
) -> list[str]:
    """Return metadata errors. An empty list means the registry is enforceable."""
    errors: list[str] = []
    policy = config.get("metadata_policy")
    if not isinstance(policy, dict):
        return ["metadata_policy must be a mapping"]
    allowed = policy.get("classification_allowed")
    if allowed != ["temporary"]:
        errors.append("private-import pairs cannot be classified permanent")
    horizon = policy.get("review_horizon_days")
    if not isinstance(horizon, int) or horizon < 1 or horizon > _DEFAULT_HORIZON_DAYS:
        errors.append(
            f"review_horizon_days must be an integer from 1 to {_DEFAULT_HORIZON_DAYS}"
        )
        horizon_days = _DEFAULT_HORIZON_DAYS
    else:
        horizon_days = horizon
    if policy.get("waiver_source") != "yaml-pair-metadata":
        errors.append("waiver_source must be yaml-pair-metadata")

    pairs = config.get("pairs")
    if not isinstance(pairs, list):
        return [*errors, "pairs must be a list"]

    seen_ids: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    for index, row in enumerate(pairs):
        label = f"pairs[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be a mapping")
            continue
        pair_id = _text(row, "id") or label
        for field in _REQUIRED_FIELDS:
            if field not in row:
                errors.append(f"{pair_id}: missing {field}")
        if not _PAIR_ID.fullmatch(pair_id):
            errors.append(f"{label}: unknown exception id {pair_id!r}")
        elif pair_id in seen_ids:
            errors.append(f"{pair_id}: duplicate exception id")
        else:
            seen_ids.add(pair_id)

        importer = _text(row, "importer")
        target = _text(row, "target")
        pair_key = (importer, target)
        if pair_key in seen_pairs:
            errors.append(f"{pair_id}: duplicate importer/target")
        elif importer and target:
            seen_pairs.add(pair_key)
        expected_scope = _scope_for(importer, target)
        scope = _text(row, "scope")
        if scope != expected_scope or "*" in scope or scope.endswith("/"):
            errors.append(f"{pair_id}: widened scope {scope!r}")

        owner = _text(row, "owner")
        if owner not in _KNOWN_OWNERS:
            errors.append(f"{pair_id}: unknown owner {owner!r}")

        rationale = _text(row, "rationale")
        if len(rationale) < _MIN_TEXT or rationale.casefold() in _VAGUE_EXIT:
            errors.append(f"{pair_id}: missing actionable rationale")
        exit_condition = _text(row, "exit_condition")
        exit_head = exit_condition.casefold().split(" ", 1)[0].strip(".:")
        if len(exit_condition) < _MIN_TEXT or exit_head in _VAGUE_EXIT:
            errors.append(f"{pair_id}: missing actionable exit_condition")
        elif "public" not in exit_condition.casefold() and "module" not in exit_condition.casefold():
            errors.append(f"{pair_id}: exit_condition does not name a destination")

        sanction = _text(row, "sanction")
        if "9626" not in sanction or "adr waiver" not in sanction.casefold():
            errors.append(f"{pair_id}: sanction must cite #9626 and reject a new ADR waiver")

        enforcement = _text(row, "enforcement").replace("\\", "/")
        enforcement_path = project_root / enforcement
        if not enforcement.endswith(".py") or not enforcement_path.is_file():
            errors.append(f"{pair_id}: enforcement test does not exist: {enforcement}")

        classification = _text(row, "classification")
        if classification != "temporary":
            errors.append(f"{pair_id}: private pair classification must be temporary")
        review = _parse_review_date(row.get("next_review"))
        if review is None:
            errors.append(f"{pair_id}: next_review must be YYYY-MM-DD")
        elif review < today:
            errors.append(f"{pair_id}: stale temporary review {review.isoformat()}")
        elif (review - today).days > horizon_days:
            errors.append(f"{pair_id}: temporary review is outside the horizon")

        if row.get("target_removal_wave") != "residual":
            errors.append(f"{pair_id}: target_removal_wave must stay residual until the pair is removed")

    max_count = config.get("max_count")
    if isinstance(max_count, int) and max_count > 11:
        errors.append(f"max_count={max_count} exceeds the #11978 ceiling 11")
    return errors
