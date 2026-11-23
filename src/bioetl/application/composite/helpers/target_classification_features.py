"""Row projection for composite target classification."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Final, cast

from bioetl.application.composite.helpers.target_classification_bundle import (
    TARGET_ID_COLUMNS,
    feature_bundle,
)
from bioetl.application.composite.helpers.target_classification_values import (
    text_value,
)
from bioetl.application.services.target_runtime.classification import (
    TargetClassificationRunState,
)
from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.entities.enriched_target_features import (
    COMPOSITE_CLASSIFICATION_BATCH_ID,
    COMPOSITE_CLASSIFICATION_OWNER,
    composite_classification_row_id,
)
from bioetl.domain.types import JsonDict

HASH_ANCHOR: Final = "1970-01-01T00:00:00+00:00"
METADATA_FIELDS: Final = (
    "target_classification_owner",
    "target_classification_completeness",
    "target_classification_absent_features",
)
FRAME_FIELDS: Final = (*TARGET_CLASSIFICATION_FIELDS, *METADATA_FIELDS)
HASH_FIELDS: Final = ("target_id", *FRAME_FIELDS)


def project_row(
    row: Mapping[str, object],
    *,
    source_hashes_index: Mapping[tuple[str, str], str],
    session: TargetClassificationRunState,
    occurrence: str,
    started_at: str,
    seen: set[str],
) -> dict[str, str | None]:
    features = feature_bundle(row, source_hashes_index)
    business = cast(JsonDict, features["business"])
    absent = cast(tuple[str, ...], features["absent"])
    output = empty_output(str(features["completeness"]), absent)
    target_id = text_value(business.get("target_id"))
    if target_id is None:
        return output
    _classify(session, business, output, occurrence, started_at, seen, target_id)
    return output


def empty_output(completeness: str, absent: tuple[str, ...]) -> dict[str, str | None]:
    output: dict[str, str | None] = dict.fromkeys(FRAME_FIELDS)
    output["target_classification_owner"] = COMPOSITE_CLASSIFICATION_OWNER
    output["target_classification_completeness"] = completeness
    output["target_classification_absent_features"] = json.dumps(
        list(absent), separators=(",", ":")
    )
    return output


def _classify(
    session: TargetClassificationRunState,
    business: JsonDict,
    output: dict[str, str | None],
    occurrence: str,
    started_at: str,
    seen: set[str],
    target_id: str,
) -> None:
    row_id = composite_classification_row_id(target_id)
    if row_id in seen:
        raise ValueError("duplicate composite classification target id")
    seen.add(row_id)
    result = session.classify_detached(
        run_id=occurrence,
        batch_id=COMPOSITE_CLASSIFICATION_BATCH_ID,
        row_id=row_id,
        business_data=business,
        run_started_at=started_at,
    )
    if session.mode != "enrich":
        return
    for field_name in TARGET_CLASSIFICATION_FIELDS:
        output[field_name] = text_value(result.projection.get(field_name))


__all__ = [
    "FRAME_FIELDS",
    "HASH_ANCHOR",
    "HASH_FIELDS",
    "METADATA_FIELDS",
    "TARGET_ID_COLUMNS",
    "empty_output",
    "project_row",
]
