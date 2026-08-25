# Debt heatmap (SCOPE `src/bioetl/` + `configs/quality/`)

| Area | Signal | Priority | Notes |
| --- | --- | --- | --- |
| Quality audit pin | stale SHA/hash/headlines | P2 | Paid down on branch; #9646 |
| Remote-main baseline | SHA e57d281869 vs cdff5b63e6 | P1 | Paid down on branch; #9647 |
| Composition entrypoints | wrapper_contract_drift=1 | P2 | Already #9643; not duplicated |
| control_plane hotspot | at_budget fan-in 2/2 | P2 | Already #9618 |
| Constructor waivers | 1 intentional | P3 | ADR-051; do not remove without ADR |
| Exemptions | 0 | — | Hold |
| TODO/FIXME/HACK | 0 real | — | — |
| Unmeasured/uncovered modules | 0/0 | — | Hold |
| Compat transition/sunset/expired | 0/0/0 | — | Hold |

Quick wins: this PR (pin + baseline). Strategic: #9618 control_plane shrink, #9643 entrypoints contract. Dependency debt: none proven in SCOPE.
