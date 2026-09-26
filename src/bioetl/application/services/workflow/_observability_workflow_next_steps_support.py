"""Next-step projection helpers for observability workflow dossiers."""

from __future__ import annotations

from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionResult,
)


def build_next_steps(
    *,
    run_manifest: RunManifestInspectionResult | None,
    missing_evidence: tuple[str, ...],
    degraded_evidence: tuple[str, ...],
) -> tuple[str, ...]:
    steps = list(_manifest_next_steps(run_manifest))
    steps.extend(_missing_evidence_steps(missing_evidence))
    steps.extend(_degraded_evidence_steps(degraded_evidence))
    seen: dict[str, None] = {}
    return tuple(
        step for step in steps if not (step in seen or seen.setdefault(step, None))
    )


def _manifest_next_steps(
    run_manifest: RunManifestInspectionResult | None,
) -> tuple[str, ...]:
    if run_manifest is None:
        return ()
    diagnostics_steps = run_manifest.diagnostics.get("next_steps")
    if not isinstance(diagnostics_steps, list):
        return ()
    return tuple(str(step) for step in diagnostics_steps)


def _missing_evidence_steps(missing_evidence: tuple[str, ...]) -> tuple[str, ...]:
    if "run_manifest" not in missing_evidence:
        return ()
    return ("Persist and inspect run-manifest/ledger artifacts for this run.",)


def _degraded_evidence_steps(degraded_evidence: tuple[str, ...]) -> tuple[str, ...]:
    steps: list[str] = []
    if any(item.startswith("persistence_profile:") for item in degraded_evidence):
        steps.append(
            "Review required persistence profile before treating this run as "
            "forensic-grade."
        )
    if "critical_dossier_evidence_gap" in degraded_evidence:
        steps.append(
            "Resolve dossier evidence gaps before marking this critical run "
            "operationally successful."
        )
    if "trace_identifiers_unavailable" in degraded_evidence:
        steps.append(
            "Use audit, manifest, and lineage sections as the current traceability "
            "fallback."
        )
    if "composite_correlation_policy_gap" in degraded_evidence:
        steps.append(
            "Repair composite_run_id correlation anchors before using the dossier "
            "as authoritative composite traceability evidence."
        )
    return tuple(steps)
