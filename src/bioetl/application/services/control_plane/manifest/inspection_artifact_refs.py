"""Artifact-ref semantic diff helpers for run-manifest inspection."""

from __future__ import annotations

from collections.abc import Mapping

_ARTIFACT_OCCURRENCE_ONLY_FIELDS = frozenset({"run_id", "manifest_id"})


def _artifact_ref_sort_key(ref: Mapping[str, object]) -> tuple[str, ...]:
    return (
        str(ref.get("stage") or ""),
        str(ref.get("dataset_ref") or ref.get("artifact_id") or ""),
        str(ref.get("lineage_fragment_id") or ""),
        str(ref.get("artifact_path") or ""),
        str(ref.get("metadata_path") or ""),
        str(ref.get("event_type") or ""),
    )


def _semantic_artifact_ref(ref: Mapping[str, object]) -> dict[str, object]:
    return {
        str(key): value
        for key, value in ref.items()
        if key not in _ARTIFACT_OCCURRENCE_ONLY_FIELDS
    }


def _artifact_ref_identity_label(ref: Mapping[str, object], index: int) -> str:
    return str(ref.get("artifact_id") or ref.get("dataset_ref") or index)


def _artifact_ref_pair_label(
    left_ref: Mapping[str, object],
    right_ref: Mapping[str, object],
    *,
    index: int,
) -> str:
    return (
        f"{_artifact_ref_identity_label(left_ref, index)} == "
        f"{_artifact_ref_identity_label(right_ref, index)}"
    )


def _artifact_ref_occurrence_difference_fields(
    *,
    index: int,
    left_ref: Mapping[str, object],
    right_ref: Mapping[str, object],
) -> list[str]:
    return [
        f"artifact_refs[{index}].{key}"
        for key in sorted(set(left_ref) | set(right_ref))
        if left_ref.get(key) != right_ref.get(key)
        and key in _ARTIFACT_OCCURRENCE_ONLY_FIELDS
    ]


def _analyze_artifact_ref_pair(
    *,
    index: int,
    left_ref: Mapping[str, object],
    right_ref: Mapping[str, object],
) -> tuple[str, str | None, list[str]]:
    compared_artifact = _artifact_ref_pair_label(
        left_ref,
        right_ref,
        index=index,
    )
    if _semantic_artifact_ref(left_ref) != _semantic_artifact_ref(right_ref):
        return compared_artifact, f"artifact_refs[{index}]", []
    return (
        compared_artifact,
        None,
        _artifact_ref_occurrence_difference_fields(
            index=index,
            left_ref=left_ref,
            right_ref=right_ref,
        ),
    )


def build_artifact_ref_semantic_diff(
    *,
    left_artifact_refs: tuple[Mapping[str, object], ...],
    right_artifact_refs: tuple[Mapping[str, object], ...],
) -> dict[str, object]:
    """Compare artifact refs by semantic fields while tracking occurrence drift."""
    left_sorted = tuple(sorted(left_artifact_refs, key=_artifact_ref_sort_key))
    right_sorted = tuple(sorted(right_artifact_refs, key=_artifact_ref_sort_key))
    semantic_difference_fields: list[str] = []
    occurrence_difference_fields: list[str] = []
    compared_artifacts: list[str] = []

    if len(left_sorted) != len(right_sorted):
        semantic_difference_fields.append("artifact_ref_count")

    for index, (left_ref, right_ref) in enumerate(
        zip(left_sorted, right_sorted, strict=False)
    ):
        (
            compared_artifact,
            semantic_difference_field,
            occurrence_fields,
        ) = _analyze_artifact_ref_pair(
            index=index,
            left_ref=left_ref,
            right_ref=right_ref,
        )
        compared_artifacts.append(compared_artifact)
        if semantic_difference_field is not None:
            semantic_difference_fields.append(semantic_difference_field)
            continue
        occurrence_difference_fields.extend(occurrence_fields)

    semantic_equivalent = not semantic_difference_fields
    occurrence_only = semantic_equivalent and bool(occurrence_difference_fields)
    return {
        "artifact_refs_available": bool(left_artifact_refs or right_artifact_refs),
        "left_artifact_ref_count": len(left_sorted),
        "right_artifact_ref_count": len(right_sorted),
        "artifact_ref_semantic_equivalent": semantic_equivalent,
        "artifact_ref_occurrence_only": occurrence_only,
        "artifact_ref_semantic_difference_fields": semantic_difference_fields,
        "artifact_ref_occurrence_difference_fields": occurrence_difference_fields,
        "artifact_ref_pairs": compared_artifacts,
    }
