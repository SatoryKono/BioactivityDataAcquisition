# RF-07A Provider Registry Call-Site Ledger

Date: 2026-03-20  
Status: retained historical context

## Purpose

This retained note preserves the execution-trace reference used by
[`rf-07-provider-registry-migration-plan-2026-03-20.md`](rf-07-provider-registry-migration-plan-2026-03-20.md).

It records that the initial RF-07 wave started from an explicit classification
of `ProviderRegistry` consumers rather than from a broad singleton-removal
rewrite.

## Ledger Summary

- production runtime/bootstrap callers were treated as higher-risk and later
  deferred into the named runtime bootstrap seam
- datasource/factory callers were treated as the first safe explicit-registry
  migration slice
- class-level compatibility APIs remained sanctioned during the migration wave
  and were later constrained by narrow ratchets

## Related Documents

- [rf-07-provider-registry-migration-plan-2026-03-20.md](rf-07-provider-registry-migration-plan-2026-03-20.md)
- [rf-07d-runtime-deferred-wave-plan-2026-03-20.md](rf-07d-runtime-deferred-wave-plan-2026-03-20.md)
- [consolidated-open-tasks-plan-2026-03-21.md](consolidated-open-tasks-plan-2026-03-21.md)
