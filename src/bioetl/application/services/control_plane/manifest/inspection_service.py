"""Application service for inspecting run manifests and ledger history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from bioetl.application.services.control_plane._run_manifest_inspection_mixins import (
    RunManifestInspectionDiffClassificationMixin,
    RunManifestInspectionIdentityGraphMixin,
)
from bioetl.application.services.control_plane.manifest.diagnostics import (
    build_diagnostics_summary,
)
from bioetl.application.services.control_plane.manifest.inspection_models import (
    RunManifestDiffEntry,
    RunManifestDiffResult,
    RunManifestInspectionCorruptionError,
    RunManifestInspectionResult,
    RunManifestVerifyResult,
)
from bioetl.application.services.control_plane.run_manifest_inspection_helpers import (
    build_authoritative_replay_dossier,
)
from bioetl.application.services.control_plane.run_manifest_inspection_verification import (
    build_cross_surface_replay_diff,
    build_effective_config_store_verification,
    json_equal,
    parse_run_id,
    resolve_verify_verdict,
)
from bioetl.application.services.control_plane.run_manifest_reproducibility_scoring import (
    build_reproducibility_audit_scoring,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.ports import (
    EffectiveConfigArtifactStorePort,
    RunLedgerPort,
    RunManifestPort,
)

__all__ = [
    "RunManifestDiffEntry",
    "RunManifestDiffResult",
    "RunManifestInspectionCorruptionError",
    "RunManifestInspectionResult",
    "RunManifestInspectionService",
    "RunManifestVerifyResult",
]


class _HistoricalReplayUniverseReportLoader(Protocol):
    def load_latest_report(self) -> dict[str, object] | None: ...


@dataclass(slots=True)
class RunManifestInspectionService(
    RunManifestInspectionIdentityGraphMixin,
    RunManifestInspectionDiffClassificationMixin,
):
    """Resolve run manifests and compute CLI-facing diffs."""

    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort | None = None
    effective_config_artifact_port: EffectiveConfigArtifactStorePort | None = None
    historical_replay_universe_report_loader: (
        _HistoricalReplayUniverseReportLoader | None
    ) = None

    def show(self, identifier: str) -> RunManifestInspectionResult:
        """Resolve one manifest by manifest_id or run_id."""
        manifest = self._resolve_manifest(identifier)
        ledger_entries: tuple[RunLedgerEntry, ...] = ()
        if self.ledger_port is not None:
            ledger_entries = tuple(self.ledger_port.list_entries(manifest.manifest_id))
        diagnostics = build_diagnostics_summary(manifest, ledger_entries)
        self._attach_historical_replay_universe_claim(diagnostics)
        self._attach_reproducibility_claim_views(diagnostics)
        identity_graph = self._build_identity_graph(manifest, diagnostics)
        dossier = build_authoritative_replay_dossier(
            manifest=manifest,
            diagnostics=diagnostics,
            identity_graph=identity_graph,
        )
        diagnostics["authoritative_replay_dossier"] = dossier
        identity_graph["authoritative_replay_dossier"] = dossier
        diagnostics["identity_graph"] = identity_graph
        return RunManifestInspectionResult(
            manifest=manifest,
            ledger_entries=ledger_entries,
            diagnostics=diagnostics,
            identity_graph=identity_graph,
        )

    def _attach_historical_replay_universe_claim(
        self,
        diagnostics: dict[str, object],
    ) -> None:
        """Attach the latest authoritative historical-universe claim when available."""
        loader = self.historical_replay_universe_report_loader
        if loader is None:
            return
        report = loader.load_latest_report()
        if not isinstance(report, dict):
            return
        universal_claim = report.get("universal_claim")
        durable_claim = report.get("durable_evidence_coverage_claim")
        if not isinstance(universal_claim, dict) or not isinstance(durable_claim, dict):
            return
        diagnostics["historical_replay_universe_claim"] = dict(universal_claim)
        diagnostics["historical_replay_universe_claim_source"] = str(
            report.get("_artifact_path") or report.get("report_id") or ""
        )
        governed_gate = report.get("governed_full_corpus_gate")
        if isinstance(governed_gate, dict):
            diagnostics["historical_replay_universe_governed_full_corpus_gate"] = dict(
                governed_gate
            )
        diagnostics["historical_replay_universe_durable_evidence_claimed"] = bool(
            durable_claim.get("claimed")
        )
        score = build_reproducibility_audit_scoring(diagnostics)
        diagnostics["reproducibility_audit_score"] = score
        self._attach_reproducibility_claim_views(diagnostics)

    def _attach_reproducibility_claim_views(
        self,
        diagnostics: dict[str, object],
    ) -> None:
        """Project the explicit claim surfaces from score payload to top-level diagnostics."""
        score = diagnostics.get("reproducibility_audit_score")
        if not isinstance(score, dict):
            return
        diagnostics["historical_replay_universe_exact_replay_claim"] = score.get(
            "historical_replay_universe_exact_replay_claim",
            {},
        )
        diagnostics["executable_run_contract_claim"] = score.get(
            "executable_run_contract_claim",
            {},
        )

    def resolve_produced_artifacts(
        self,
        identifier: str,
    ) -> tuple[dict[str, object], ...]:
        """Resolve concrete produced artifacts from a manifest-id rooted lookup."""
        result = self.show(identifier)
        trace = result.diagnostics.get("produced_artifact_trace")
        if not isinstance(trace, dict):
            return ()
        artifacts = trace.get("artifacts")
        if not isinstance(artifacts, list):
            return ()
        return tuple(artifact for artifact in artifacts if isinstance(artifact, dict))

    def diff(
        self, left_identifier: str, right_identifier: str
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
                left_artifact_refs=self._artifact_refs_from_diagnostics(
                    left_result.diagnostics
                ),
                right_artifact_refs=self._artifact_refs_from_diagnostics(
                    right_result.diagnostics
                ),
            ),
        )

    def verify(
        self, left_identifier: str, right_identifier: str
    ) -> RunManifestVerifyResult:
        """Verify replay evidence across manifest and effective-config stores."""
        left_result = self.show(left_identifier)
        right_result = self.show(right_identifier)
        diff_result = self.diff(left_identifier, right_identifier)
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

    def _resolve_manifest(self, identifier: str) -> RunManifest:
        """Resolve manifest_id first, then run_id lookup when identifier is UUID-like."""
        try:
            manifest = self.manifest_port.get(identifier)
        except ValueError as exc:
            raise RunManifestInspectionCorruptionError(identifier, str(exc)) from exc
        if manifest is not None:
            return manifest
        run_id = parse_run_id(identifier)
        if run_id is not None:
            try:
                manifest = self.manifest_port.get_by_run_id(run_id)
            except ValueError as exc:
                raise RunManifestInspectionCorruptionError(
                    identifier, str(exc)
                ) from exc
            if manifest is not None:
                return manifest
        raise ValueError(f"Run manifest not found for identifier: {identifier}")

    @staticmethod
    def _artifact_refs_from_diagnostics(
        diagnostics: dict[str, object],
    ) -> tuple[dict[str, object], ...]:
        refs = diagnostics.get("artifact_refs")
        if not isinstance(refs, list):
            return ()
        return tuple(dict(ref) for ref in refs if isinstance(ref, dict))
