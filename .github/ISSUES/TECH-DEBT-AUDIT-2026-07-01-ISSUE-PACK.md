# Tech Debt Audit 2026-07-01 Issue Pack

This pack converts the `2026-07-01` full technical-debt audit on current
`main` into a publish-ready GitHub issue set.

## Decision Summary

| Finding theme | Current repo actuality | Action |
| --- | --- | --- |
| Blocking contract drift | `0` blocking issues in `reports/quality/contract-registry-diagnostics.json` | Do not create issue |
| Active VCR fixture gap backlog | `configs/base/bronze_fixture_gaps.yaml` is empty | Do not create issue |
| Flaky test backlog | `reports/quality/flaky-test-burndown-review.json` reports `0` flaky tests | Do not create issue |
| Unused observability events or metrics | `reports/quality/unused-observability-event-debt.json` reports `0` unused declared signals | Do not create issue |
| Layering violations | `docs/02-architecture/generated/module-dependency-map.md` reports `0` policy violations | Do not create issue |
| Retained compatibility/public seams | `12` retained entrypoints and `4` public export facades remain | Create issue |
| Adapter duplication | `54` duplicate clusters remain in `src/bioetl/infrastructure/adapters` | Create issue |
| Pipeline transformer duplication | `11` duplicate clusters remain in `src/bioetl/application/pipelines` | Create issue |
| Classified zero-import dead code | `9` zero-import candidates remain classified but not fully removed | Create issue |
| Composite config sanctioned duplication | shared policy blocks still repeated across five composite configs | Create issue |
| Replay-sensitive coverage tails | `855` partially covered modules and live hotspot tails remain | Create issue |
| Supporting scripts backlog | `81` supporting scripts remain, many with `reference_count = 0` | Create issue |

## Publish-Ready Set

### Wave 1 — residual structural debt (closed)

1. `TDX-AUDIT-001` Ratchet retained public entrypoints and lazy export facades to canonical imports — [#5839](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5839) **closed**
2. `TDX-AUDIT-002` Collapse adapter fetch and resilience duplication under canonical template owners — [#5840](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5840) **closed**
3. `TDX-AUDIT-003` Consolidate pipeline transformer contract duplication across provider families — [#5841](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5841) **closed**
4. `TDX-AUDIT-004` Remove classified zero-import domain ports after importer proof — [#5842](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5842) **closed**
5. `TDX-AUDIT-005` Extract shared composite config policy blocks into a canonical authority surface — [#5843](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5843) **closed**
6. `TDX-AUDIT-006` Reopen hotspot tail coverage ratchet for replay-sensitive runtime seams — [#5844](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5844) **closed**
7. `TDX-AUDIT-007` Turn zero-reference supporting scripts into explicit owner-or-removal governance — [#5845](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5845) **closed**

### Wave 2 — determinism and hotspot follow-up (closed)

8. `TDX-AUDIT-008` Strengthen DQ rule evaluator determinism with golden and property tests — [#5861](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5861) **closed**
9. `TDX-AUDIT-009` Add domain contract registry and ledger invariant tests — [#5862](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5862) **closed**
10. `TDX-AUDIT-010` Ratchet control-plane hotspot LOC and fan-in ceilings — [#5863](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5863) **closed**
11. `TDX-AUDIT-011` Explicitize composition runtime builder registration and ratchet DI fan-in — [#5864](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/5864) **closed**

## Recommended Execution Order

### Phase 1: determinism safety

1. `TDX-AUDIT-008`
2. `TDX-AUDIT-009`

### Phase 2: hotspot ratchet

3. `TDX-AUDIT-010`
4. `TDX-AUDIT-011`

### Phase 3: structural debt wave

5. `TDX-AUDIT-002`
6. `TDX-AUDIT-003`
7. `TDX-AUDIT-001`
8. `TDX-AUDIT-004`
9. `TDX-AUDIT-005`
10. `TDX-AUDIT-006`
11. `TDX-AUDIT-007`

## Why Only These Eleven

The audit found that formal governance is mostly green on current `main`. The
residual debt is concentrated in sanctioned compatibility seams, duplication
families, sanctioned config repetition, classified dead code, partial-coverage
tails, long-lived supporting helper surfaces, and determinism-sensitive domain
invariants.

Wave 1 reopens the structural-debt owners that were prematurely closed while
live artifacts still show residual work. Wave 2 adds focused owners for the
highest-risk determinism and hotspot tails from the prioritized backlog.
