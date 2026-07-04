# Test System Audit 2026-06-22 Issue Pack

This pack converts the 2026-06-22 architecture-strict test-system audit into a
GitHub issue continuation after the existing `TEST-AUDIT-001` through
`TEST-AUDIT-007` set.

## Issue Set

1. `TEST-AUDIT-008` - stabilize architecture drift artifacts - [#5491](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5491)
2. `TEST-AUDIT-009` - split slow governance scanners from fast feedback lanes - [#5493](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5493)
3. `TEST-AUDIT-010` - remove module-scope temp roots from unit import paths - [#5495](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5495)
4. `TEST-AUDIT-011` - consolidate generated schema validation tests with explicit assertions - [#5498](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5498)
5. `TEST-AUDIT-012` - triage and retire stale closeout ratchets - [#5500](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5500)

## Recommended Execution Order

### Phase 1: restore deterministic baseline

1. `TEST-AUDIT-008`

### Phase 2: speed and isolation

2. `TEST-AUDIT-009`
3. `TEST-AUDIT-010`

### Phase 3: signal quality and governance cleanup

4. `TEST-AUDIT-011`
5. `TEST-AUDIT-012`

## Notes

- The pack intentionally preserves hard guards for determinism, idempotency,
  replay, layering, Composition Root, and control-plane contracts.
- The pack does not propose increasing technical-debt budgets.
- The pack treats fixture/VCR governance as mostly healthy based on current
  catalog evidence: VCR metadata sidecars are complete and fixture duplicate
  inventory reports zero duplicate files.
