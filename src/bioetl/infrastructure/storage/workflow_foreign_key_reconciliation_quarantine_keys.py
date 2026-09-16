"""Pure key/column helpers for workflow FK reconciliation quarantine path."""

from __future__ import annotations

import re

__all__ = [
    "CURRENT_FLAG_COLUMNS",
    "VALID_TO_COLUMNS",
    "build_orphan_key_rows",
    "require_sql_identifier",
    "resolve_mutation_identity_keys",
    "resolve_present_column",
]

CURRENT_FLAG_COLUMNS = ("_is_current", "is_current")
VALID_TO_COLUMNS = ("_valid_to", "valid_to")
_OPTIONAL_MUTATION_IDENTITY_COLUMNS = (
    "_run_id",
    "run_id",
    "composite_run_id",
    "_composite_run_id",
    "workflow_run_id",
)
_SQL_IDENTIFIER_RE = re.compile(
    r"^[A-Za-z_]\w*$"
)  # NOSONAR - requires non-digit first char, \w+ alone is insufficient


def require_sql_identifier(name: str, field_name: str) -> str:
    """Reject identifiers that are unsafe to interpolate into Delta merge SQL."""
    if not _SQL_IDENTIFIER_RE.fullmatch(name):
        raise ValueError(f"{field_name} is not a safe SQL identifier: {name!r}")
    return name


def resolve_present_column(
    rows: list[dict[str, object]],
    candidates: tuple[str, ...],
    *,
    table_columns: frozenset[str] | None = None,
) -> str:
    """Pick the first SCD2 metadata column present on the Gold table schema.

    Prefer the live Delta schema. Fall back to orphan-row keys only when the
    schema cannot be inspected, so unit fakes and partial environments still work.
    """
    if table_columns is not None:
        for candidate in candidates:
            if candidate in table_columns:
                return candidate
    for candidate in candidates:
        if any(candidate in row for row in rows):
            return candidate
    raise ValueError(
        "Gold foreign-key reconciliation requires SCD2 metadata column "
        f"from {candidates}"
    )


def resolve_mutation_identity_keys(
    orphan_rows: list[dict[str, object]],
    primary_keys: tuple[str, ...],
    *,
    source_scope: str,
) -> tuple[str, ...]:
    """Extend primary keys with uniform run-identity columns.

    Mixed or blank identity on ``current_run`` blocks instead of widening the
    mutation predicate to primary keys alone.
    """
    extra: list[str] = []
    for column in _OPTIONAL_MUTATION_IDENTITY_COLUMNS:
        present = sum(1 for row in orphan_rows if column in row)
        if present == 0:
            continue
        if present != len(orphan_rows):
            if source_scope == "current_run":
                raise ValueError(
                    "workflow foreign-key reconciliation mixed row identity; "
                    "mutation blocked"
                )
            continue
        values = [row.get(column) for row in orphan_rows]
        if any(value is None or not str(value).strip() for value in values):
            if source_scope == "current_run":
                raise ValueError(
                    "workflow foreign-key reconciliation blank row identity; "
                    "mutation blocked"
                )
            continue
        extra.append(column)
    return primary_keys + tuple(extra)


def build_orphan_key_rows(
    orphan_rows: list[dict[str, object]],
    primary_keys: tuple[str, ...],
    *,
    operation: str,
) -> list[dict[str, object]]:
    """Project unique non-null identity-key rows for orphan mutations."""
    key_rows: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for row in orphan_rows:
        key_values: list[object] = []
        for primary_key in primary_keys:
            if primary_key not in row or row[primary_key] is None:
                raise ValueError(
                    f"{operation} orphan row without non-null primary key {primary_key}"
                )
            key_values.append(row[primary_key])
        key_tuple = tuple(key_values)
        if key_tuple in seen:
            continue
        seen.add(key_tuple)
        key_rows.append(dict(zip(primary_keys, key_values, strict=True)))
    return key_rows
