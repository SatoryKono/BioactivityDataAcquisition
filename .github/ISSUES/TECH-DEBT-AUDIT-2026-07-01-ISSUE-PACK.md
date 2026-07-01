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

1. `TDX-AUDIT-001` Ratchet retained public entrypoints and lazy export facades to canonical imports
2. `TDX-AUDIT-002` Collapse adapter fetch and resilience duplication under canonical template owners
3. `TDX-AUDIT-003` Consolidate pipeline transformer contract duplication across provider families
4. `TDX-AUDIT-004` Remove classified zero-import domain ports after importer proof
5. `TDX-AUDIT-005` Extract shared composite config policy blocks into a canonical authority surface
6. `TDX-AUDIT-006` Reopen hotspot tail coverage ratchet for replay-sensitive runtime seams
7. `TDX-AUDIT-007` Turn zero-reference supporting scripts into explicit owner-or-removal governance

## Why Only These Seven

The audit found that formal governance is mostly green on current `main`. The
residual debt is concentrated in sanctioned compatibility seams, duplication
families, sanctioned config repetition, classified dead code, partial-coverage
tails, and long-lived supporting helper surfaces.

This pack therefore publishes only the still-actionable residual work and does
not reopen categories that are already governed to zero on the live tree.
