# Consolidated Review — S1: Domain
**Date**: 2026-04-03
**Sub-reviews**: 5 agents
**Status**: PASS
**Consolidated Score**: 9.6

## Sub-review Summary

| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S1.1 — Ports+Contracts | 83 | 10.0 | PASS | 0 | 0 |
| S1.2 — Entities+VO | 65 | 10.0 | PASS | 0 | 0 |
| S1.3 — Schemas | 43 | 10.0 | PASS | 0 | 0 |
| S1.4 — Services | 70 | 10.0 | PASS | 0 | 0 |
| S1.5 — Other | 84 | 8.2 | PASS | 0 | 6 |

## Aggregated Issues
### Critical (MUST fix)

### High
- ARCH-002: Domain purity violation in `src/bioetl/domain/exceptions/__init__.py:61`
- ARCH-002: Domain purity violation in `src/bioetl/domain/exceptions/bounded_context.py:13`
- ARCH-002: Domain purity violation in `src/bioetl/domain/exceptions/infrastructure/_delta.py:7`
- ARCH-002: Domain purity violation in `src/bioetl/domain/exceptions/infrastructure/__init__.py:5`
- ARCH-002: Domain purity violation in `src/bioetl/domain/exceptions/infrastructure/__init__.py:6`
- ARCH-002: Domain purity violation in `src/bioetl/domain/exceptions/infrastructure/__init__.py:15`

## Cross-subzone Observations
- Multiple modules exhibit missing return type annotations on public functions.
