# Cross-Synthesis: project-evidence-rebaseline

Date: 2026-03-27
Status: rebaselined-current-state plus root-pack sweep

## Overall Readout

The 2026-03-21 re-baseline wave supports a `managed-and-recalibrated evidence estate` interpretation.
Most mutable evidence families now describe the current repository state rather than pre-fix or
pre-refactor snapshots. The repo still contains active debt, but that debt is narrower and more
localized than many earlier packs implied.

The 2026-03-26 cleanup/docs follow-up strengthens that interpretation further: the previously
tracked merged docs export has been retired from the default git surface, so one of the most
visible derivative-lag findings is now historical-trigger evidence rather than current on-disk drift.

The 2026-03-27 root-pack sweep adds one more calibration layer: every root pack now carries an
explicit freshness note, and the estate has a parent review matrix that separates `materially reopened`
packages from `reviewed-retained` packages. This means the evidence estate is now not only
rebaselined by shard history, but also explicitly review-tracked at the package inventory level.

## Cross-Shard Patterns

- Naming and documentation packs shifted the most from `open-remediation framing` to
  `current-baseline plus residual watchlist` framing.
- The root evidence layer now has a uniform freshness mechanism: package-local `SUMMARY.md` review
  notes plus one parent review matrix for the full estate.
- Compatibility and governance packs now read as calibration work, not greenfield refactor design:
  the YAML compatibility SSOT, shared loader, and generated snapshot model are already live.
- Structure and topology packs did not materially change their architectural conclusions; the
  re-baseline mostly refreshed timestamps, RAW notes, and EV language to the current tree.
- Architecture and diagram packs still support targeted work, but primarily on derived artifacts,
  stale descriptions, and snapshot undercount rather than foundational architecture confusion.
- Quality and health packs still show concentrated pressure in hotspots, duplication, and generated
  debt, but the strongest controls remain green and architecture-policy enforcement stays intact.

## What Closed Out

- Previously open naming seams such as `validate_publication_entity_type`,
  `create_run_all_execution_plan`, `get_quarantine_store(pipeline)`, and several orchestration-local
  variable names are no longer current-baseline findings.
- The active documentation baseline now treats `project-and-ai-doc-drift` and
  `reference-guide-doc-drift` largely as resolved active-source corrections, not still-open
  remediation queues.
- `documentation-internal-surface-governance` was materially reopened on 2026-03-27 and now records
  the current `published` vs `repo-only` boundary model instead of the older broader
  `internal-published` interpretation for `plans/**` and `reports/**`.
- Compatibility-registry evidence now clearly reflects the live baseline:
  YAML ledger, shared loader, generated snapshot, and narrowed `freeze guards` posture.

## What Remains Live

- `architecture-doc-drift` remains a real active family: the issue is breadth undercount and stale
  architectural snapshots, not broken architecture rules.
- `operations-generated-doc-drift` remains a derivative-lag family, but it is now centered on
  on-demand exports, generated maps, and historical verification artifacts rather than a committed
  stale merged export.
- Import and dependency governance remain mostly healthy, but topology and assembly pressure stay
  concentrated in a small number of composition, provider-registry, CLI, and large-file seams.
- Second-wave convergence topics remain open by design:
  object-family vocabulary convergence, broader helper/factory naming families, and selected
  structural hotspot decomposition.

## Recommended Interpretation

- Treat the evidence estate as re-synchronized to the current repo state.
- Read the 2026-03-27 review matrix as the parent control plane for package freshness.
- Use older RAW/EV timestamps and claims as historical triggers only when a pack was not materially
  reopened; otherwise, prefer the refreshed 2026-03-21 RAW/EV baseline.
- Prioritize follow-up work from the still-live families rather than reopening already-closed
  naming or documentation first-wave slices.
