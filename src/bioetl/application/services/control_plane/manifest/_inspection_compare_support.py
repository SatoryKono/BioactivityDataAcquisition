"""Diff/verify collaborators for run-manifest inspection service."""

from __future__ import annotations

from typing import Protocol, cast

from bioetl.application.services.control_plane.manifest.inspection_models import (
    RunManifestDiffEntry,
    RunManifestDiffResult,
    RunManifestInspectionResult,
    RunManifestVerifyResult,
)
from bioetl.application.services.control_plane.manifest.inspection_verification import (
    build_cross_surface_replay_diff,
    build_effective_config_store_verification,
    json_equal,
    resolve_verify_verdict,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.ports import EffectiveConfigArtifactStorePort


class _InspectionCompareHost(Protocol):
    effective_config_artifact_port: EffectiveConfigArtifactStorePort | None

    def show(self, identifier: str) -> RunManifestInspectionResult: ...

    def _classify_manifest_diff(
        self,
        *,
        left_manifest: RunManifest,
        right_manifest: RunManifest,
        differences: tuple[RunManifestDiffEntry, ...],
    ) -> dict[str, object]: ...


class RunManifestInspectionCompareMixin:
    """Compute stable diffs and cross-surface verification for two manifests."""

    effective_config_artifact_port: EffectiveConfigArtifactStorePort | None

    def diff(
        self: _InspectionCompareHost, left_identifier: str, right_identifier: str
    ) -> RunManifestDiffResult:
        """Compute a stable top-level diff between two manifests."""
        left_result = self.show(left_identifier)
        right_result = self.show(right_identifier)
        left_manifest = left_result.manifest
        right_manifest = right_result.manifest
        left_payload = left_manifest.to_dict()
        right_payload = right_manifest.to_dict()
        diff_fields = tuple(
            RunManifestDiffEntry(
                field=field,
                left=left_payload.get(field),
                right=right_payload.get(field),
            )
            for field in sorted(set(left_payload) | set(right_payload))
            if not json_equal(left_payload.get(field), right_payload.get(field))
        )
        classification = self._classify_manifest_diff(
            left_manifest=left_manifest,
            right_manifest=right_manifest,
            differences=diff_fields,
        )
        return RunManifestDiffResult(
            left_manifest_id=left_manifest.manifest_id,
            right_manifest_id=right_manifest.manifest_id,
            differences=diff_fields,
            classification=str(classification["classification"]),
            semantic_equivalent=bool(classification["semantic_equivalent"]),
            occurrence_only=bool(classification["occurrence_only"]),
            occurrence_difference_fields=cast(
                tuple[str, ...],
                classification["occurrence_difference_fields"],
            ),
            semantic_difference_fields=cast(
                tuple[str, ...],
                classification["semantic_difference_fields"],
            ),
            noncanonical_difference_fields=cast(
                tuple[str, ...],
                classification["noncanonical_difference_fields"],
            ),
            replay_relationship=str(classification["replay_relationship"]),
            cross_surface_replay_diff=build_cross_surface_replay_diff(
                left_manifest=left_manifest,
                right_manifest=right_manifest,
                classification=classification,
                left_artifact_refs=RunManifestInspectionCompareMixin._artifact_refs_from_diagnostics(
                    left_result.diagnostics
                ),
                right_artifact_refs=RunManifestInspectionCompareMixin._artifact_refs_from_diagnostics(
                    right_result.diagnostics
                ),
            ),
        )

    def verify(
        self: _InspectionCompareHost, left_identifier: str, right_identifier: str
    ) -> RunManifestVerifyResult:
        """Verify replay evidence across manifest and effective-config stores."""
        left_result = self.show(left_identifier)
        right_result = self.show(right_identifier)
        diff_result = RunManifestInspectionCompareMixin.diff(
            self, left_identifier, right_identifier
        )
        left_manifest = left_result.manifest
        right_manifest = right_result.manifest
        effective_config = build_effective_config_store_verification(
            self.effective_config_artifact_port,
            left_manifest=left_manifest,
            right_manifest=right_manifest,
        )
        raw_missing_evidence = effective_config.get("missing_evidence", ())
        missing_evidence_items = (
            raw_missing_evidence
            if isinstance(raw_missing_evidence, (list, tuple))
            else ()
        )
        missing_evidence = tuple(
            item for item in missing_evidence_items if isinstance(item, str)
        )
        effective_config_semantic_equivalent = bool(
            effective_config.get("semantic_equivalent")
        )
        effective_config_occurrence_only = bool(effective_config.get("occurrence_only"))
        semantic_equivalent = (
            diff_result.semantic_equivalent and effective_config_semantic_equivalent
        )
        occurrence_only = (
            diff_result.occurrence_only or effective_config_occurrence_only
        )
        verified = semantic_equivalent and not missing_evidence
        verdict = resolve_verify_verdict(
            manifest_classification=diff_result.classification,
            manifest_semantic_equivalent=diff_result.semantic_equivalent,
            effective_config_semantic_equivalent=effective_config_semantic_equivalent,
            missing_evidence=missing_evidence,
            occurrence_only=occurrence_only,
        )
        return RunManifestVerifyResult(
            left_manifest_id=left_manifest.manifest_id,
            right_manifest_id=right_manifest.manifest_id,
            left_run_id=str(left_manifest.run_id),
            right_run_id=str(right_manifest.run_id),
            verdict=verdict,
            verified=verified,
            semantic_equivalent=semantic_equivalent,
            occurrence_only=occurrence_only,
            missing_evidence=missing_evidence,
            manifest_diff=diff_result.to_dict(),
            effective_config=effective_config,
            left_authoritative_replay_dossier=cast(
                "dict[str, object]",
                left_result.diagnostics.get("authoritative_replay_dossier", {}),
            ),
            right_authoritative_replay_dossier=cast(
                "dict[str, object]",
                right_result.diagnostics.get("authoritative_replay_dossier", {}),
            ),
        )

    @staticmethod
    def _artifact_refs_from_diagnostics(
        diagnostics: dict[str, object],
    ) -> tuple[dict[str, object], ...]:
        refs = diagnostics.get("artifact_refs")
        if not isinstance(refs, list):
            return ()
        return tuple(dict(ref) for ref in refs if isinstance(ref, dict))


__all__ = ["RunManifestInspectionCompareMixin"]
