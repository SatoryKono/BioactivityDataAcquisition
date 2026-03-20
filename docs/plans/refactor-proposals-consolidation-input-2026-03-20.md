# Refactor Proposals Consolidation Input

Date: 2026-03-20
Status: prepared

## Purpose

This document collects the currently relevant refactoring proposals from:
- `docs/reports/evidence/`
- `docs/plans/`

The purpose is not to replace those documents, but to provide one curated input
set for a later consolidation task. Only proposals that still influence future
execution are included. Documents that are implemented, purely analytical,
already decision-closed, or only serve as ledgers/constraints are explicitly
filtered out or downgraded to “context only.”

Important note:
- `docs/reports/plans` does not exist in the current repository.
- This inventory therefore uses `docs/plans` as the intended second source.

## Selection Rule

Included as active proposal sources:
- `active`
- `in progress`
- `proposed`
- `recommended`
- `ready`
- `partially implemented` when meaningful work remains

Excluded from the main proposal set:
- `implemented locally`
- `completed analysis`
- pure seam maps / ledgers without forward proposals
- accepted decisions that now act mainly as constraints

## Selected Proposal Sources

### Structural backlog and execution plans

1. [rf-fs-remaining-backlog-execution-plan-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/rf-fs-remaining-backlog-execution-plan-2026-03-20.md)
   Status: active
   Why keep: still the broadest execution-oriented source for unresolved
   `RF-FS-*` work.

2. [rf-fs-004-execution-plan-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/rf-fs-004-execution-plan-2026-03-20.md)
   Status: active, implementation in progress
   Why keep: still relevant until config-topology normalization is fully
   closed.

3. [rf-04-composition-hotspots-execution-plan-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/rf-04-composition-hotspots-execution-plan-2026-03-20.md)
   Status: partially implemented
   Why keep: composition hotspots remain one of the strongest open structural
   seams.

4. [rf-06-domain-facade-hygiene-plan-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/rf-06-domain-facade-hygiene-plan-2026-03-20.md)
   Status: proposed
   Why keep: not superseded; still a live narrative/architecture hygiene item.

5. [rf-07-provider-registry-migration-plan-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/rf-07-provider-registry-migration-plan-2026-03-20.md)
   Status: in progress
   Why keep: directly overlaps with current technical-debt evidence and remains
   unfinished.

6. [rf-07d-runtime-deferred-wave-plan-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/rf-07d-runtime-deferred-wave-plan-2026-03-20.md)
   Status: in progress
   Why keep: runtime/bootstrap `ProviderRegistry` migration is still deferred,
   not closed.

7. [naming-cleanup-refactor-plan-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/naming-cleanup-refactor-plan-2026-03-20.md)
   Status: proposed
   Why keep: naming debt is still open, though lower priority than structural
   refactoring.

### Evidence-derived proposal sources

8. [BACKLOG-dependency-hotspots-prioritized-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/dependency-hotspots/06-backlog/BACKLOG-dependency-hotspots-prioritized-2026-03-20.md)
   Status: proposed
   Why keep: strongest evidence-backed hotspot prioritization source.

9. [TECHNICAL-DEBT-ROADMAP.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/technical-debt/04-decisions/TECHNICAL-DEBT-ROADMAP.md)
   Status: recommended
   Why keep: current umbrella ranking across dependency, duplication, and
   ownership debt.

10. [TECHNICAL-DEBT-EXECUTION-PLAN.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/technical-debt/05-execution-plan/TECHNICAL-DEBT-EXECUTION-PLAN.md)
    Status: ready
    Why keep: best execution-ready decomposition of the evidence-backed
    roadmap.

11. [BACKLOG-complexity-hotspots-implementation-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/technical-debt/complexity-hotspots/06-backlog/BACKLOG-complexity-hotspots-implementation-2026-03-20.md)
    Status: proposed
    Why keep: active implementation candidate for complexity-specific debt.

12. [EXECUTION-ROADMAP.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/governance-signals/06-roadmap/EXECUTION-ROADMAP.md)
    Status: partially live
    Why keep conditionally: useful where it still proposes future governance
    calibration, but not as the primary structural backlog source.

## Context-Only Sources

These documents are still important, but should be treated as constraints,
inputs, or already-closed context rather than as standalone future proposals:

- [pipeline-config-loader-ownership/04-decisions/SUMMARY.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/pipeline-config-loader-ownership/04-decisions/SUMMARY.md)
- [provider-registry-runtime-ownership/04-decisions/SUMMARY.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/provider-registry-runtime-ownership/04-decisions/SUMMARY.md)
- [refactor-backlog-calibration/SUMMARY.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/refactor-backlog-calibration/SUMMARY.md)
- [technical-debt/SUMMARY.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/technical-debt/SUMMARY.md)

These should constrain consolidation, not compete with it.

## Excluded As Already Implemented Or Non-Proposal

- [rf-fs-005-wave-1-hotspot-execution-plan-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/rf-fs-005-wave-1-hotspot-execution-plan-2026-03-20.md)
  Reason: implemented locally, verification passed.

- [rf-04a-composition-seam-map-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/rf-04a-composition-seam-map-2026-03-20.md)
  Reason: completed analysis, useful as supporting map only.

- [rf-07a-provider-registry-call-site-ledger-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/rf-07a-provider-registry-call-site-ledger-2026-03-20.md)
  Reason: operational ledger, not an independent proposal.

## Consolidated Proposal Themes

### Theme 1: Structural RF-FS backlog

Keep and consolidate:
- `rf-fs-remaining-backlog-execution-plan`
- `rf-fs-004-execution-plan`

Meaning:
- This theme remains the canonical source for unresolved structural
  refactoring waves and should anchor any master consolidation.

### Theme 2: Provider-registry and composition seam work

Keep and consolidate:
- `rf-04-composition-hotspots-execution-plan`
- `rf-07-provider-registry-migration-plan`
- `rf-07d-runtime-deferred-wave-plan`
- technical-debt roadmap / execution plan

Meaning:
- These documents overlap strongly and should almost certainly collapse into one
  shared cluster during consolidation.

### Theme 3: Evidence-backed hotspot reduction

Keep and consolidate:
- dependency-hotspots backlog
- technical-debt roadmap
- technical-debt execution plan
- complexity-hotspots backlog

Meaning:
- These are different views of the same future work queue and should become one
  prioritized hotspot program.

### Theme 4: Domain and naming hygiene

Keep but lower priority:
- `rf-06-domain-facade-hygiene-plan`
- `naming-cleanup-refactor-plan`

Meaning:
- Still active, but should probably remain behind structural/provider/hotspot
  work in the consolidated ordering.

### Theme 5: Governance follow-up

Keep conditionally:
- governance-signals execution roadmap

Meaning:
- include only the still-open calibration or ratchet proposals, not already
  completed waves.

## Recommended Consolidation Strategy

1. Use `rf-fs-remaining-backlog-execution-plan` and
   `TECHNICAL-DEBT-EXECUTION-PLAN` as the two primary parents.
2. Merge provider-registry and composition-seam proposals into one sectioned
   program.
3. Merge dependency-hotspots and complexity-hotspots into one hotspot backlog
   with explicit subtracks.
4. Preserve accepted decision summaries only as constraints and assumptions.
5. Mark implemented or analysis-only plans as “absorbed context,” not as active
   proposal rows.

## Best Current Starting Set For Consolidation

If a later consolidation task wants the smallest still-complete input set, the
best starting documents are:

1. [rf-fs-remaining-backlog-execution-plan-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/rf-fs-remaining-backlog-execution-plan-2026-03-20.md)
2. [rf-07-provider-registry-migration-plan-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/rf-07-provider-registry-migration-plan-2026-03-20.md)
3. [TECHNICAL-DEBT-EXECUTION-PLAN.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/technical-debt/05-execution-plan/TECHNICAL-DEBT-EXECUTION-PLAN.md)
4. [BACKLOG-dependency-hotspots-prioritized-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/dependency-hotspots/06-backlog/BACKLOG-dependency-hotspots-prioritized-2026-03-20.md)
5. [BACKLOG-complexity-hotspots-implementation-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/reports/evidence/technical-debt/complexity-hotspots/06-backlog/BACKLOG-complexity-hotspots-implementation-2026-03-20.md)

Everything else should be merged in only as detail, constraint, or context.
