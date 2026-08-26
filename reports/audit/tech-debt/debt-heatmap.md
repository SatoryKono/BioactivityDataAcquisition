# Debt heatmap — 2026-08-26

Легенда: **P1** высокий шанс сломать release integrity / заблокировать фичу; **P2** стоимость изменений; **P3** гигиена.

## По поверхности

| Surface | Control | Residual | Pri | Notes |
| --- | --- | --- | --- | --- |
| `reports/quality/module-coverage-inventory.json` | unmeasured ratchet 0 | **84 unmeasured** | P1 | `coverage_xml_has_no_class_entry`; hash `29bf3d81` |
| `reports/quality/debt-governance-gates.json` | 45 gates | split-brain pass vs summary fail | P1 | regenerate |
| `reports/quality/debt-governance-gates.md` | generated mirror | unmeasured 84 fail vs json 0 pass | P1 | pair drift |
| `reports/quality/architecture-quality-scorecard.json` | 0–10 integral | 7.41 header vs ~9.41 categories | P1 | hash `ef737d02` vs inventory |
| `reports/quality/total-tech-debt-audit-main-current.md` | registry pin | stale 9.41 / 45/45 | P1 | re-pin |
| `scripts/.../report_live_residual_snapshot.py` | shrink-only snapshot | reads `rows` not `summary` | P1 | snapshot unmeasured=0 |
| `configs/quality/debt_scorecard.yaml` | shrink-only | many `current==max` | P1 | do not raise |
| `configs/quality/lazy_import_ratchet.yaml` | max 98 / target 60 | **98/98** | P1 | freeze |
| `configs/quality/private_import_ratchet.yaml` | max 15 | **15/15** | P1 | freeze |
| `configs/quality/assertless_ratchet.yaml` | max 87 / target 77 | **87/87** | P1 | freeze |
| Hotspot control_plane | fan-in max 2 | **2/2** | P1 | #8714 |
| Config surface | 27 / 419 | **27/27**, **419/419** | P1 | #8714 |
| Composition cohesion | max_modules 300 | 295/300 | P2 | near cap |
| Basedpyright cycles | shrink-only | 30 | P2 | review_by 2026-10-28 |
| Constructor waivers | shrink-only | 1 | P2 | ADR-051 |
| Xenon path exemptions | expiry 2026-12-31 | wide prefixes | P2 | |
| `src/bioetl` type: ignore | mypy max 0 | ≥82 ignores | P2 | |
| F403 barrels | ruff F403 | 14 | P2 | |
| Branch coverage | hard 85% | 552 files below | P2 | aggregate 86.152% |
| Lazy public facades | fail-fast unclassified | 52 | P2 | |
| Public entrypoints/facades | sanctioned freeze | 12 + 4 | P2 | review 2026-09-30 |
| Closeout tests | classified ratchet | 51 files / 10k LOC | P2 | |
| Architecture exemptions | empty registries | 0 | — | healthy |
| Flaky / twins / uuid4 / layers | zero | 0 | — | healthy |
| Uncovered modules | max 0 | 0 | — | held |
| Sonar | QG OK | 0 open (2026-08-20) | P3 | freshness |

## По слою `src/`

| Layer | Debt class | Heat |
| --- | --- | --- |
| `application/core` | F403, cycles, 2 unmeasured helpers, 194 files / 23419 LOC | medium-high |
| `application/services/control_plane` | fan-in freeze 2/2; 3 unmeasured | **high** |
| `application/composite` | xenon exemption | medium |
| `composition` | 295/300 modules; pipeline unmeasured 3; lazy facades | **high** |
| `domain` | constructor waiver QuarantineEntry | low |
| `infrastructure` | type ignores; xenon silver/control_plane | medium |
| `interfaces/cli` | click ignores; 12 public entrypoints | medium |

## Paydown order

1. Измерить 84 unmeasured (coverage.xml) — TD-001
2. Связанный refresh gates+scorecard+hashes — TD-002..TD-006
3. Snapshot reader `summary.*` — TD-007
4. Freeze cluster shrink (lazy/private/fan-in) — TD-008
5. F403 + cycles — TD-013/TD-009
6. Branch tail — TD-014
7. Closeout fold — TD-018
