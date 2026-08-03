"""Artifact-recorder closure policy for runner control-plane assembly."""

from __future__ import annotations

from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)


def requires_artifact_publication_closure(required_profile: object) -> bool:
    return (
        normalize_required_persistence_profile(required_profile)
        in STRICT_PERSISTENCE_PROFILES
    )


def validate_artifact_recorder_attachment(
    *,
    required_profile: object,
    candidate_count: int,
    attached_count: int,
    missing_attach_method_count: int,
    failed_count: int,
) -> None:
    if not requires_artifact_publication_closure(required_profile):
        return
    profile = normalize_required_persistence_profile(required_profile)
    if candidate_count == 0:
        raise RuntimeError(
            f"Required persistence profile '{profile}' requires artifact publication "
            "closure, but no metadata-writer candidates were discovered for recorder attachment"
        )
    if (
        attached_count < candidate_count
        or missing_attach_method_count > 0
        or failed_count > 0
    ):
        raise RuntimeError(
            f"Required persistence profile '{profile}' requires artifact publication "
            "closure, but recorder attachment was incomplete "
            f"(candidates={candidate_count}, attached={attached_count}, "
            f"missing_attach_method_count={missing_attach_method_count}, "
            f"failed_count={failed_count})"
        )
