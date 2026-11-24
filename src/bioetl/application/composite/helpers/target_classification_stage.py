"""Post-join target classification kept out of the composite top-level freeze."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime

import polars as pl

from bioetl.application.composite.helpers.target_classification_features import (
    HASH_ANCHOR,
    METADATA_FIELDS,
    TARGET_ID_COLUMNS,
    project_row,
)
from bioetl.application.composite.helpers.target_classification_values import (
    source_hashes,
    text_value,
)
from bioetl.application.services.target_runtime.classification import (
    TargetClassificationRunState,
)
from bioetl.domain.behavior.identity_service import generate_content_hash
from bioetl.domain.composite.enriched_target_features import (
    COMPOSITE_CLASSIFICATION_OWNER,
    composite_classification_run_id,
)
from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TARGET_CLASSIFICATION_FIELDS,
)
from bioetl.domain.types import JsonDict


class CompositeTargetClassification:
    """Apply one pure classification pass and retain its evidence until commit."""

    def __init__(
        self, session: TargetClassificationRunState, *, table_contract: str = "3.1.0"
    ) -> None:
        self._session = session
        fields = TARGET_CLASSIFICATION_FIELDS if session.mode == "enrich" else ()
        if fields and table_contract == "3.2.0":
            fields = (*fields, *TARGET_CLASSIFICATION_DETAIL_FIELDS)
        self._classification_fields = fields
        self._write_fields = (*fields, *METADATA_FIELDS)
        self._hash_fields = tuple(
            dict.fromkeys((*TARGET_CLASSIFICATION_FIELDS, *self._write_fields))
        )
        self._decisions: dict[str, dict[str, str | None]] = {}

    def apply(
        self,
        df: pl.DataFrame,
        *,
        run_id: str,
        started_at: datetime | None,
        dependency_frames: Mapping[str, pl.DataFrame] | None = None,
    ) -> pl.DataFrame:
        """Classify joined rows and keep the evidence detached."""
        self._decisions = {}
        if not _has_targets(df):
            return df
        updates, decisions = _collect(
            df,
            session=self._session,
            occurrence=composite_classification_run_id(run_id),
            started_at=_started_at(started_at),
            hashes=source_hashes(dependency_frames),
            classification_fields=self._classification_fields,
        )
        self._decisions = decisions
        return _write_columns(df, updates)

    def seal_decision(self, df: pl.DataFrame) -> pl.DataFrame:
        """Rewrite the decision after seed coalesce, including explicit nulls."""
        if not _can_seal(df, self._decisions):
            return df
        return _write_columns(
            df, _sealed_columns(df, self._decisions, self._write_fields)
        )

    def refresh_content_hash(self, df: pl.DataFrame) -> pl.DataFrame:
        """Bind the surviving classification fields into ``content_hash``."""
        if df.is_empty() or "target_classification_owner" not in df.columns:
            return df
        return df.with_columns(
            pl.Series(
                name="content_hash",
                values=[
                    _row_hash(row, self._hash_fields)
                    for row in df.iter_rows(named=True)
                ],
                dtype=pl.Utf8,
            )
        )

    def commit(self, run_id: str) -> None:
        """Publish evidence after the merge write has succeeded."""
        self._session.commit_detached(composite_classification_run_id(run_id))

    def abandon(self, run_id: str) -> None:
        """Drop unpublished evidence when persistence fails."""
        self._session.abandon_detached(composite_classification_run_id(run_id))


def apply_joined_classification(
    stage: CompositeTargetClassification | None,
    df: pl.DataFrame,
    *,
    run_id: str,
    started_at: datetime | None,
    dependency_frames: Mapping[str, pl.DataFrame] | None,
) -> pl.DataFrame:
    """Classify when a post-join stage is bound."""
    if stage is None:
        return df
    return stage.apply(
        df,
        run_id=run_id,
        started_at=started_at,
        dependency_frames=dependency_frames,
    )


async def commit_joined_classification(
    stage: CompositeTargetClassification | None,
    run_id: str,
    write: Callable[[], Awaitable[None]],
) -> None:
    """Commit evidence only after ``write`` returns."""
    written = False
    try:
        await write()
        written = True
    finally:
        if not written and stage is not None:
            stage.abandon(run_id)
    if stage is not None:
        stage.commit(run_id)


def _has_targets(df: pl.DataFrame) -> bool:
    if df.is_empty():
        return False
    return any(column in df.columns for column in TARGET_ID_COLUMNS)


def _can_seal(df: pl.DataFrame, decisions: Mapping[str, object]) -> bool:
    if df.is_empty() or not decisions:
        return False
    return "target_id" in df.columns


def _started_at(value: datetime | None) -> str:
    if value is None:
        return HASH_ANCHOR
    return value.isoformat()


def _collect(
    df: pl.DataFrame,
    *,
    session: TargetClassificationRunState,
    occurrence: str,
    started_at: str,
    hashes: Mapping[tuple[str, str], str],
    classification_fields: tuple[str, ...],
) -> tuple[dict[str, list[str | None]], dict[str, dict[str, str | None]]]:
    write_fields = (*classification_fields, *METADATA_FIELDS)
    updates: dict[str, list[str | None]] = {name: [] for name in write_fields}
    decisions: dict[str, dict[str, str | None]] = {}
    seen: set[str] = set()
    for row in df.iter_rows(named=True):
        projected = project_row(
            row,
            source_hashes_index=hashes,
            session=session,
            classification_fields=classification_fields,
            occurrence=occurrence,
            started_at=started_at,
            seen=seen,
        )
        target_id = text_value(row.get("target_id")) or text_value(
            row.get("chembl.target.target_id")
        )
        if target_id is not None:
            decisions[target_id] = projected
        for name in write_fields:
            updates[name].append(projected.get(name))
    return updates, decisions


def _sealed_columns(
    df: pl.DataFrame,
    decisions: Mapping[str, dict[str, str | None]],
    fields: tuple[str, ...],
) -> dict[str, list[str | None]]:
    updates: dict[str, list[str | None]] = {name: [] for name in fields}
    for row in df.iter_rows(named=True):
        decision = decisions.get(text_value(row.get("target_id")) or "")
        for name in fields:
            if decision is None:
                updates[name].append(text_value(row.get(name)))
            else:
                updates[name].append(decision.get(name))
    return updates


def _write_columns(
    df: pl.DataFrame, updates: Mapping[str, list[str | None]]
) -> pl.DataFrame:
    result = df
    for name, values in updates.items():
        result = result.with_columns(pl.Series(name=name, values=values, dtype=pl.Utf8))
    return result


def _row_hash(row: Mapping[str, object], fields: tuple[str, ...]) -> str | None:
    if row.get("target_classification_owner") != COMPOSITE_CLASSIFICATION_OWNER:
        return text_value(row.get("content_hash"))
    payload: JsonDict = {"prior_content_hash": text_value(row.get("content_hash"))}
    for field_name in ("target_id", *fields):
        if field_name in row:
            payload[field_name] = row.get(field_name)
    return str(generate_content_hash(payload, "composite_target"))


__all__ = [
    "CompositeTargetClassification",
    "apply_joined_classification",
    "commit_joined_classification",
]
