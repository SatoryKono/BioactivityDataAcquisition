# [docs] Sync ChEMBL provider docs with active normalization surfaces

**Status**: Draft
**Priority**: P2 (Medium)
**Labels**: `provider:chembl`, `docs`, `docs-drift`, `governance`
**Epic**: ChEMBL Normalization Residuals 2026Q2
**Last audited**: 2026-05-19

## Problem

Part of the ChEMBL provider reference docs no longer matches the active runtime
config and normalization surfaces.

The audit confirmed at least one concrete stale example:

- `docs/04-reference/providers/chembl/activity.md` still says
  `sink.gold.enabled: false`
- active config `configs/entities/chembl/activity.yaml` has `gold.enabled: true`

This is not a runtime normalization defect, but it degrades governance trust
and makes architecture-strict audits noisier than necessary.

## Evidence

- `reports/quality/chembl_normalization_audit_2026-05-19.md`
- `docs/04-reference/providers/chembl/activity.md`
- `configs/entities/chembl/activity.yaml`

## Current Fact Base

- The audit recorded the activity provider doc drift explicitly as a residual
  P2 item.
- ChEMBL provider docs are used as contributor guidance, but runtime truth
  lives in shipped configs, schemas, and contracts.
- Stale provider docs increase the chance of future incorrect normalization or
  Gold-surface assumptions during maintenance.

## Required Outcome

- ChEMBL provider docs describe the active runtime surfaces rather than stale
  historical snippets.
- At minimum, the audited drift around activity Gold enablement is removed.
- Similar stale normalization/governance snippets are reconciled in the same
  pass so the docs stop lagging behind the shipped configs.

## Implementation Plan

1. Diff each ChEMBL provider reference page against the active entity config.
2. Correct stale runtime snippets and normalization descriptions.
3. Prefer generated or config-sourced excerpts where the docs currently copy
   mutable runtime state by hand.
4. Re-run docs drift checks relevant to provider references.

## Suggested File Targets

- `docs/04-reference/providers/chembl/activity.md`
- other affected files under `docs/04-reference/providers/chembl/`
- `configs/entities/chembl/*.yaml`
- `docs/reports/generated/` if any provider-summary artifacts are regenerated

## Testing Expectations

- Re-run the relevant docs drift or link checks for touched provider docs.
- Re-scan affected provider configs to confirm the docs now match runtime
  surfaces.

## Done When

- The documented activity Gold posture matches the active config.
- No known stale normalization/config snippets remain in the touched ChEMBL
  provider docs.

## Dependencies

- Independent docs-governance follow-up from `reports/quality/chembl_normalization_audit_2026-05-19.md`.
