"""Application service for inspecting run manifests and ledger history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bioetl.application.services.control_plane.manifest._inspection_compare_support import (
    RunManifestInspectionCompareMixin,
)
from bioetl.application.services.control_plane.manifest._inspection_support import (
    RunManifestInspectionDiffClassificationMixin,
    RunManifestInspectionIdentityGraphMixin,
)
from bioetl.application.services.control_plane.manifest.diagnostics import (
    build_diagnostics_summary,
)
from bioetl.application.services.control_plane.manifest.inspection_helpers import (
    build_authoritative_replay_dossier,
)
from bioetl.application.services.control_plane.manifest.inspection_verification import (
    _RUN_MANIFEST_INSPECTION_MODEL_EXPORTS as _RUN_MANIFEST_INSPECTION_MODEL_EXPORTS,
)
from bioetl.application.services.control_plane.manifest.inspection_verification import (
    RunManifestDiffEntry as RunManifestDiffEntry,
)
from bioetl.application.services.control_plane.manifest.inspection_verification import (
    RunManifestDiffResult as RunManifestDiffResult,
)
from bioetl.application.services.control_plane.manifest.inspection_verification import (
    RunManifestInspectionCorruptionError as RunManifestInspectionCorruptionError,
)
from bioetl.application.services.control_plane.manifest.inspection_verification import (
    RunManifestInspectionResult as RunManifestInspectionResult,
)
from bioetl.application.services.control_plane.manifest.inspection_verification import (
    RunManifestVerifyResult as RunManifestVerifyResult,
)
from bioetl.application.services.control_plane.manifest.inspection_verification import (
    parse_run_id,
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
    *_RUN_MANIFEST_INSPECTION_MODEL_EXPORTS,
    "RunManifestInspectionService",
]


class _HistoricalReplayUniverseReportLoader(Protocol):
    def load_latest_report(self) -> dict[str, object] | None: ...


@dataclass(slots=True)
class RunManifestInspectionService(
    RunManifestInspectionIdentityGraphMixin,
    RunManifestInspectionDiffClassificationMixin,
    RunManifestInspectionCompareMixin,
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
