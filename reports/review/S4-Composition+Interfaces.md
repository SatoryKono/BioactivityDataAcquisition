# Consolidated Review — S4: Composition & Interfaces
**Date**: 2026-03-05
**Sub-reviews**: 5 agents
**Status**: WARN
**Consolidated Score**: 7.5

## Sub-review Summary
| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S4.1 — Bootstrap & Factories | 48 | 7.5 | WARN | 0 | 1 |
| S4.2 — Providers & DQ | 48 | 7.5 | WARN | 0 | 0 |
| S4.3 — Storage & Data Sources | 48 | 7.5 | WARN | 0 | 0 |
| S4.4 — Runtimes | 48 | 7.5 | WARN | 0 | 0 |
| S4.5 — CLI Interfaces | 48 | 7.5 | WARN | 0 | 0 |

## Aggregated Issues

### High (MUST fix)
- **AP-002** in `src/bioetl/composition/bootstrap_logger.py:25`: Direct structlog import outside infra

## Cross-subzone Observations
- `bootstrap_logger.py` uses `structlog` directly which normally strictly belongs to the Infrastructure layer, although Composition wiring is often an edge case.
- `ADR-014` missing future annotations occasionally (e.g. `src/bioetl/interfaces/__init__.py`).

## Top 5 Recommendations
1. Validate whether the structlog import in `bootstrap_logger.py` is fully compliant with dependency injection and composition standards. If so, apply an exemption (EXC-xxx). If not, move logging initialization logic entirely to infrastructure adapters.
2. Ensure strict `ADR-014` application in `interfaces` initialization logic.