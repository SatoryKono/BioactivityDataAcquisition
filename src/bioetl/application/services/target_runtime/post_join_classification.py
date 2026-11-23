"""Opt-in classification after dependency joins.

The stage reads an explicit feature whitelist. It does not publish evidence and
does not run unless a caller attaches a classifier to the merge service.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping

import polars as pl

FEATURE_FIELDS: tuple[str, ...] = (
    "target_ec_numbers",
    "protein_classifications",
    "target_protein_keywords",
    "taxonomy_id",
    "component_accessions",
    "target_xref_uniprot_ids",
    "organism",
    "pref_name",
    "target_id",
)

RowClassifier = Callable[[Mapping[str, object], str, int], Mapping[str, object]]


def project_enriched_features(row: Mapping[str, object]) -> dict[str, object]:
    """Keep present whitelist fields. Absence is explicit and is not invented."""
    features = {
        key: row[key] for key in FEATURE_FIELDS if key in row and row[key] is not None
    }
    return {
        "features": features,
        "feature_provenance": "post_join" if features else "absent",
    }


def occurrence_id(run_id: str, index: int, features: Mapping[str, object]) -> str:
    """Deterministic occurrence identity. Publication remains a separate step."""
    payload = json.dumps(
        {"features": features, "index": index, "run_id": run_id},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def apply_post_join_classification(
    frame: pl.DataFrame, run_id: str, classifier: RowClassifier
) -> pl.DataFrame:
    """Append classifier columns after conflict resolution has finished."""
    projected = [
        dict(classifier(features, run_id, index))
        for index, row in enumerate(frame.iter_rows(named=True))
        if isinstance(features := project_enriched_features(row)["features"], Mapping)
    ]
    if not projected:
        return frame
    extra = pl.DataFrame(projected)
    overlap = [name for name in extra.columns if name in frame.columns]
    base = frame.drop(overlap) if overlap else frame
    return pl.concat([base, extra], how="horizontal")


def attach_post_join_target_classifier(service: object, classifier: object) -> None:
    """Opt in. Composite target merges stay unchanged until a caller attaches."""
    service.target_post_join_classifier = classifier  # type: ignore[attr-defined]


__all__ = [
    "FEATURE_FIELDS",
    "RowClassifier",
    "apply_post_join_classification",
    "attach_post_join_target_classifier",
    "occurrence_id",
    "project_enriched_features",
]
