# Decision: `QuarantineEntry` wide constructor is intentional domain surface

**Date:** 2026-07-27  
**Linked issue:** #6685 (TD-R-09)  
**Related:** #6679 (TD-R-03 constructor waiver burn-down)  
**ADR:** [ADR-051](../ADR-051-quarantine-entry-aggregate-surface.md)

## Decision

Classify `QuarantineEntry.__init__` (`max_args: 9`) as an **intentional_exception**, not residual accidental coupling debt.
Canonical accepted record: **ADR-051** (ADR-051 remains the Silver/Gold filter boundary decision).

## Rationale

The aggregate intentionally materializes a complete, explicit quarantine identity and payload snapshot:

- entry identity (`entry_id`)
- pipeline / error classification
- immutable payload + content hash
- run/batch lineage ids
- explicit `created_at`
- optional metadata bag

Collapsing these into opaque bag objects would hide domain invariants and weaken auditability of quarantine records.

## Policy

- Waiver remains in `configs/quality/constructor_waivers.yaml` with `classification: intentional_exception`.
- `max_args` is **frozen** (no growth).
- Domain stays I/O-free; no infrastructure types in the aggregate constructor.
- Revisit only if the aggregate identity model changes via ADR.

## Exit criteria for this decision

- [x] Written decision linked from waiver metadata
- [x] Waiver retained with non-growth freeze
- [x] No layer-boundary violation introduced
