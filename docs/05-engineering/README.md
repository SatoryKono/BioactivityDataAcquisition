______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-10'

______________________________________________________________________

# Engineering Documentation

## Purpose

This section contains implementation-facing engineering references that sit
between architecture policy and code seams.

Use this section when one rule spans multiple layers or rollout phases and must
be expressed as one canonical engineering plan instead of being scattered across
service files, ADRs, and config fragments.

## Current entry points

| Document                                                | Purpose                                                                                                                                                        |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [Normalization Plan P0–P6](normalization_plan_P0_P6.md) | Canonical engineering plan for RunManifest, RunLedger, runtime anchors, shipped normalization profiles, join-key normalization, and generated matrix artifacts |

## Related published surfaces

- [RULES.md](../00-project/RULES.md)
- [Content Hash Identity Policy](../02-architecture/policies/content-hash-identity-policy.md)
- [ADR-014 Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-044 Run Manifest and Run Ledger](../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md)
- [Checkpoint Debugging](../05-operations/runbooks/checkpoint-debugging.md)
- [Run Manifest Inspection](../05-operations/runbooks/run-manifest-inspection.md)
