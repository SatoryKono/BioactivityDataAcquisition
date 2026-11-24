"""RF-003 (#13311): classify composite targets after dependency joins.

Runs after conflict resolution so ``seed_priority`` cannot clobber IUPHAR
projection columns. Evidence publish/finalize stay outside pure compute and
follow successful persistence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import datetime
from typing import Protocol

import polars as pl

from bioetl.domain.context import PipelineContext
from iuphar_target_class.composite_features import build_classification_business_data

_COMPOSITE_PIPELINE_NAME = "composite_target"
_COMPOSITE_WORKFLOW_ID = "composite_post_join"
# Sync with domain.config.target_classification.TARGET_CLASSIFICATION_FIELDS.
# Local copy avoids a new application.composite → domain.config edge.
_PROJECTION_FIELDS: tuple[str, ...] = (
    "iuphar_target_id",
    "iuphar_class",
    "iuphar_match_status",
    "iuphar_annotation_status",
    "local_class",
    "effective_class",
    "effective_source",
    "decision_status",
    "target_class_profile_sha256",
)


class _ClassificationHost(Protocol):
    _logger: object
    _target_classification_session: object | None


@dataclass(slots=True)
class PostJoinClassificationOutcome:
    """DataFrame after optional post-join classification plus publish bookkeeping."""

    merged_df: pl.DataFrame
    classified_rows: int = 0
    mode: str | None = None
    _pending_indices: list[int] = dataclass_field(default_factory=list)


def _row_mapping(row: Mapping[str, object]) -> dict[str, object]:
    return {str(key): value for key, value in row.items()}


def _classification_context(
    host: _ClassificationHost,
    *,
    run_id: str,
    metadata_timestamp: datetime | None,
) -> PipelineContext:
    return PipelineContext.create(
        run_id=run_id,  # type: ignore[arg-type]
        run_type="composite",  # type: ignore[arg-type]
        logger=host._logger,  # type: ignore[arg-type]
        started_at=metadata_timestamp,
        source_batch_id="composite_merge",  # type: ignore[arg-type]
        replay_timestamp_anchor=metadata_timestamp,
        pipeline_name=_COMPOSITE_PIPELINE_NAME,
        workflow_id=_COMPOSITE_WORKFLOW_ID,
    )


def _projection_from_enrich(
    enriched: Mapping[str, object], *, shadow: bool
) -> dict[str, object]:
    if shadow:
        return {}
    return {
        name: enriched.get(name) for name in _PROJECTION_FIELDS if name in enriched
    }


def _apply_projections(
    merged_df: pl.DataFrame, projections: Sequence[Mapping[str, object]]
) -> pl.DataFrame:
    updates = {
        name: [projection.get(name) for projection in projections]
        for name in _PROJECTION_FIELDS
        if any(name in projection for projection in projections)
    }
    result_df = merged_df
    for column_name, values in updates.items():
        result_df = result_df.with_columns(pl.Series(name=column_name, values=values))
    return result_df


def apply_post_join_target_classification(
    host: _ClassificationHost,
    *,
    merged_df: pl.DataFrame,
    run_id: str,
    metadata_timestamp: datetime | None,
) -> PostJoinClassificationOutcome:
    """Classify rows with a whitelist built from post-join features.

    No-op when Composition did not bind a classification session (mode ``off``).
    """
    session = getattr(host, "_target_classification_session", None)
    if session is None or merged_df.is_empty():
        return PostJoinClassificationOutcome(merged_df=merged_df)

    context = _classification_context(
        host, run_id=run_id, metadata_timestamp=metadata_timestamp
    )
    shadow = session.mode == "shadow"
    projections: list[dict[str, object]] = []
    pending: list[int] = []
    for index, raw in enumerate(merged_df.to_dicts()):
        business = build_classification_business_data(_row_mapping(raw))
        enriched = session.enrich(context, index, business)
        pending.append(index)
        projections.append(_projection_from_enrich(enriched, shadow=shadow))

    if shadow:
        host._logger.info(  # type: ignore[union-attr]
            "RF-003 post-join classification computed in shadow mode",
            classified_rows=len(pending),
            run_id=run_id,
        )
        return PostJoinClassificationOutcome(
            merged_df=merged_df,
            classified_rows=len(pending),
            mode=session.mode,
            _pending_indices=pending,
        )

    result_df = _apply_projections(merged_df, projections)
    host._logger.info(  # type: ignore[union-attr]
        "RF-003 post-join classification applied after dependency joins",
        classified_rows=len(pending),
        projection_fields=sorted({n for p in projections for n in p}),
        run_id=run_id,
    )
    return PostJoinClassificationOutcome(
        merged_df=result_df,
        classified_rows=len(pending),
        mode=session.mode,
        _pending_indices=pending,
    )


def publish_post_join_classification(
    host: _ClassificationHost,
    *,
    run_id: str,
    metadata_timestamp: datetime | None,
    indices: Sequence[int],
) -> None:
    """Publish pending evidence after a successful merge persist."""
    session = getattr(host, "_target_classification_session", None)
    if session is None or not indices:
        return
    context = _classification_context(
        host, run_id=run_id, metadata_timestamp=metadata_timestamp
    )
    for index in indices:
        session.publish(context, index)


def finalize_post_join_classification(
    host: _ClassificationHost,
    *,
    run_id: str,
    metadata_timestamp: datetime | None,
) -> None:
    """Finalize evidence only after merge outputs are written."""
    session = getattr(host, "_target_classification_session", None)
    if session is None:
        return
    context = _classification_context(
        host, run_id=run_id, metadata_timestamp=metadata_timestamp
    )
    session.finalize(context)


def discard_post_join_classification(
    host: _ClassificationHost,
    *,
    run_id: str,
    metadata_timestamp: datetime | None,
    indices: Sequence[int],
) -> None:
    """Drop unpublished evidence when persistence fails."""
    session = getattr(host, "_target_classification_session", None)
    if session is None or not indices:
        return
    context = _classification_context(
        host, run_id=run_id, metadata_timestamp=metadata_timestamp
    )
    for index in indices:
        session.discard(context, index)


__all__ = [
    "PostJoinClassificationOutcome",
    "apply_post_join_target_classification",
    "discard_post_join_classification",
    "finalize_post_join_classification",
    "publish_post_join_classification",
]
