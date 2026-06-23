"""Private inspection helpers owned by the manifest inspection package surface."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.manifest.identity_graph_assembly import (
    RunManifestIdentityGraphAssembler,
)
from bioetl.domain.control_plane import RunManifest

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.inspection_models import (
        RunManifestDiffEntry,
    )

_OCCURRENCE_ONLY_DIFF_FIELDS = frozenset({"manifest_id", "run_id", "created_at"})


class RunManifestInspectionIdentityGraphMixin:
    """Build operator-facing identity graph payloads for inspection output."""

    @staticmethod
    def _build_identity_graph(
        manifest: RunManifest,
        diagnostics: dict[str, object],
    ) -> dict[str, object]:
        return RunManifestIdentityGraphAssembler.build(manifest, diagnostics)


class RunManifestInspectionDiffClassificationMixin:
    """Classify manifest diffs into operator-facing semantic buckets."""

    @staticmethod
    def _classify_manifest_diff(
        *,
        left_manifest: RunManifest,
        right_manifest: RunManifest,
        differences: tuple[RunManifestDiffEntry, ...],
    ) -> dict[str, object]:
        diff_fields = tuple(entry.field for entry in differences)
        if not diff_fields:
            return {
                "classification": "identical",
                "semantic_equivalent": True,
                "occurrence_only": False,
                "occurrence_difference_fields": (),
                "semantic_difference_fields": (),
                "noncanonical_difference_fields": (),
                "replay_relationship": "none",
            }

        occurrence_difference_fields = tuple(
            field for field in diff_fields if field in _OCCURRENCE_ONLY_DIFF_FIELDS
        )
        non_occurrence_fields = tuple(
            field for field in diff_fields if field not in _OCCURRENCE_ONLY_DIFF_FIELDS
        )
        semantic_equivalent = (
            left_manifest.execution_fingerprint == right_manifest.execution_fingerprint
        )
        replay_relationship = (
            RunManifestInspectionDiffClassificationMixin._resolve_replay_relationship(
                left_manifest=left_manifest,
                right_manifest=right_manifest,
            )
        )
        if semantic_equivalent:
            return RunManifestInspectionDiffClassificationMixin._semantic_equivalent_diff_payload(
                occurrence_difference_fields=occurrence_difference_fields,
                non_occurrence_fields=non_occurrence_fields,
                replay_relationship=replay_relationship,
            )
        return {
            "classification": "semantic_drift",
            "semantic_equivalent": False,
            "occurrence_only": False,
            "occurrence_difference_fields": occurrence_difference_fields,
            "semantic_difference_fields": non_occurrence_fields or diff_fields,
            "noncanonical_difference_fields": (),
            "replay_relationship": replay_relationship,
        }

    @staticmethod
    def _semantic_equivalent_diff_payload(
        *,
        occurrence_difference_fields: tuple[str, ...],
        non_occurrence_fields: tuple[str, ...],
        replay_relationship: str,
    ) -> dict[str, object]:
        if not non_occurrence_fields:
            return {
                "classification": "occurrence_only",
                "semantic_equivalent": True,
                "occurrence_only": True,
                "occurrence_difference_fields": occurrence_difference_fields,
                "semantic_difference_fields": (),
                "noncanonical_difference_fields": (),
                "replay_relationship": replay_relationship,
            }
        return {
            "classification": "semantic_equivalent_with_noncanonical_differences",
            "semantic_equivalent": True,
            "occurrence_only": False,
            "occurrence_difference_fields": occurrence_difference_fields,
            "semantic_difference_fields": (),
            "noncanonical_difference_fields": non_occurrence_fields,
            "replay_relationship": replay_relationship,
        }

    @staticmethod
    def _manifest_replays_other(
        *,
        manifest: RunManifest,
        other: RunManifest,
    ) -> bool:
        return (
            manifest.replay_of_manifest_id == other.manifest_id
            or manifest.replay_of_run_id == str(other.run_id)
        )

    @staticmethod
    def _resolve_replay_relationship(
        *,
        left_manifest: RunManifest,
        right_manifest: RunManifest,
    ) -> str:
        left_replays_right = (
            RunManifestInspectionDiffClassificationMixin._manifest_replays_other(
                manifest=left_manifest,
                other=right_manifest,
            )
        )
        right_replays_left = (
            RunManifestInspectionDiffClassificationMixin._manifest_replays_other(
                manifest=right_manifest,
                other=left_manifest,
            )
        )
        if left_replays_right and right_replays_left:
            return "mutual_replay_cycle"
        if left_replays_right:
            return "left_is_exact_replay_of_right"
        if right_replays_left:
            return "right_is_exact_replay_of_left"
        if (
            left_manifest.replay_of_manifest_id is not None
            or left_manifest.replay_of_run_id is not None
            or right_manifest.replay_of_manifest_id is not None
            or right_manifest.replay_of_run_id is not None
        ):
            return "external_replay_parentage_present"
        return "none"
