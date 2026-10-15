# Test System Audit 2026-07-03 Issue Pack

This pack continues the test-system audit backlog after `TEST-AUDIT-001` through
`TEST-AUDIT-012` (see `TEST-AUDIT-2026-06-22-ISSUE-PACK.md`).

Source audit: `main` @ `84a42c127`, verdict `PASS_WITH_GAPS`.

## Issue Set

1. `TEST-AUDIT-013` - persist architecture governance scan cache in CI [#5925](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5925)
2. `TEST-AUDIT-014` - consolidate duplicate Batch event unit tests [#5926](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5926)
3. `TEST-AUDIT-015` - expand integration determinism matrix beyond single gate [#5927](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5927)
4. `TEST-AUDIT-016` - coverage tail burn-down for replay-sensitive modules [#5928](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5928)
5. `TEST-AUDIT-017` - observability emission integration for composite/checkpoint [#5929](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5929)
6. `TEST-AUDIT-018` - E2E PR smoke vs nightly full matrix split [#5930](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5930)
7. `TEST-AUDIT-019` - retire or archive stale closeout architecture tests (51-file pass) [#5931](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5931)

## Recommended Execution Order

### Phase 1: CI latency and replay safety (P0)

1. `TEST-AUDIT-013`
2. `TEST-AUDIT-016`

### Phase 2: signal quality and determinism proof (P1)

3. `TEST-AUDIT-014`
4. `TEST-AUDIT-015`
5. `TEST-AUDIT-017`

### Phase 3: lane economics and governance cleanup (P1)

6. `TEST-AUDIT-018`
7. `TEST-AUDIT-019`

## Notes

- Preserves hard guards for determinism, idempotency, replay, layering, Composition Root, and control-plane contracts.
- Does not propose increasing technical-debt budgets.
- `TEST-AUDIT-019` extends `TEST-AUDIT-012` ([#5500](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5500)) with refreshed closeout inventory (51 files).
- `TEST-AUDIT-013` continues `TEST-AUDIT-009` ([#5493](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5493)) with persisted CI cache.

## Publish

```bash
python scripts/engineering/repo/publish_test_audit_issues.py --apply --update-pack
```

## Closeout

```bash
python scripts/engineering/repo/close_test_audit_issues.py
```
