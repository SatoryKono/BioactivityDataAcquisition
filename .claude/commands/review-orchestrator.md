---
description: "Иерархический code review BioETL по 8 секторам (S1-S8) с scoring matrix."
---

# /review-orchestrator

## Использование
```
/review-orchestrator [mode] [scope]
```

**Режимы:** `full` (default), `sector`, `wave1` (S1-S4), `wave2` (S5-S8)
**Scope:** `S1`..`S8`, layer name, or all.

## Sectors

| ID | Sector | Scope | Weight |
|:--:|--------|-------|:------:|
| S1 | Domain | `src/bioetl/domain/` | 20% |
| S2 | Application | `src/bioetl/application/` | 20% |
| S3 | Infrastructure | `src/bioetl/infrastructure/` | 20% |
| S4 | Composition+Interfaces | `src/bioetl/composition/` + `interfaces/` | 10% |
| S5 | Cross-cutting | Import matrix, anti-patterns | 10% |
| S6 | Tests | `tests/` | 8% |
| S7 | Configs | `configs/` | 5% |
| S8 | Documentation | `docs/` | 7% |

## Инструкции

Launch via Agent tool with `subagent_type="py-review-orchestrator"`:
```
Read `.claude/agents/py-review-orchestrator.md` and execute as L1 orchestrator.
mode: {mode}, scope: {scope}
Save reports to reports/review/.
```

## Scoring
| Score | Status |
|:-----:|:------:|
| ≥ 8.0 | PASS |
| 6.0-7.9 | WARN |
| < 6.0 | FAIL |

Deductions: CRITICAL=-2.0, HIGH=-1.0, MEDIUM=-0.5, LOW=-0.25

## Artifacts
```
reports/review/
├── S1-domain.md ... S8-documentation.md
└── FINAL-REVIEW.md
```
