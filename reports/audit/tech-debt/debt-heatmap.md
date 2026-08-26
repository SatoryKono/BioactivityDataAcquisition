# Debt heatmap — 2026-08-26

Легенда риска: **P0** блокирует доказательность релиза; **P1** высокий шанс инцидента/feature-block; **P2** стоимость изменений; **P3** локальная гигиена.

## По поверхности

| Surface | Control | Residual | Pri | Notes |
| --- | --- | --- | --- | --- |
| `reports/quality/module-coverage-inventory.json` | hash + unmeasured ratchet 0 | **merge conflicts** | P0 | JSON invalid |
| `reports/quality/debt-governance-gates.json` | 45 gates | split-brain pass vs summary fail | P1 | regenerate |
| `reports/quality/architecture-quality-scorecard.json` | 0–10 integral | 7.41 header vs ~9.41 categories | P1 | regenerate |
| `reports/quality/total-tech-debt-audit-main-current.md` | registry pin | stale 9.41 / 45/45 | P1 | re-pin after refresh |
| `configs/quality/debt_scorecard.yaml` | shrink-only | many `current==max` | P1 | do not raise |
| `configs/quality/lazy_import_ratchet.yaml` | max 98 / target 60 | **98/98** | P1 | freeze |
| `configs/quality/private_import_ratchet.yaml` | max 15 | **15/15** | P1 | freeze |
| `configs/quality/assertless_ratchet.yaml` | max 87 / target 77 | **87/87** | P1 | freeze |
| Hotspot `application_services_control_plane` | fan-in max 2 | **2/2** | P1 | #8714 |
| Config surface | 27 / 419 | **27/27**, **419/419** | P1 | #8714 |
| Composition package cohesion | max_modules 300 | 295/300 | P2 | near cap |
| Basedpyright cycles | shrink-only allowlist | 30 | P2 | review_by 2026-10-28 |
| Constructor waivers | shrink-only | 1 | P2 | ADR-051 |
| Xenon path exemptions | expiry 2026-12-31 | wide prefixes | P2 | |
| `src/bioetl` type: ignore | mypy max 0 | ≥82 ignores | P2 | |
| F403 barrels | ruff F403 | 14 | P2 | |
| Branch coverage | hard 85% | 552 files below | P2 | aggregate 86.152% |
| Lazy public facades | fail-fast unclassified | 52 | P2 | |
| Public entrypoints/facades | sanctioned freeze | 12 + 4 | P2 | review 2026-09-30 |
| Closeout tests | classified ratchet | 51 files / 10k LOC | P2 | |
| Architecture exemptions | empty registries | 0 | — | healthy |
| Flaky tests | zero budget | 0 | — | healthy |
| Uncovered modules | max 0 | 0 (when inventory valid) | — | held |
| Twins / uuid4 / layer violations | zero | 0 | — | healthy |
| Sonar | QG OK | 0 open (2026-08-20) | P3 | freshness |

## По слою `src/`

| Layer | Debt class | Heat |
| --- | --- | --- |
| `application/core` | F403 barrels, typing cycles, hotspot 194 files / 23419 LOC | medium |
| `application/services/control_plane` | fan-in freeze 2/2, 133 files | **high** (freeze) |
| `application/composite` | xenon exemption, constructor-adjacent orchestration | medium |
| `composition` | 295/300 modules, lazy facades, `_services.py` conflict metadata | **high** (near cap + inventory conflict) |
| `domain` | constructor waiver QuarantineEntry; otherwise clean | low |
| `infrastructure` | type ignores on writers/adapters; xenon silver/control_plane | medium |
| `interfaces/cli` | click type ignores; 12 public entrypoints | medium |
| `src/memory` | xenon exemption; out of bioetl runtime | low (scoped) |

## Paydown order (probability × blast radius)

1. TD-001 inventory conflicts (без этого остальное не доказать)
2. TD-002/003/004/005 regenerate gates+scorecard+hashes
3. TD-007 residual snapshot reader
4. TD-006 re-pin audit registry
5. TD-008 freeze cluster shrink (lazy/private/fan-in) — strategic
6. TD-013 F403, TD-009 cycles — maintainability
7. TD-014 branch tail — test debt
8. TD-018 closeout fold — operational cost of the debt system
