# Consolidated Review — S1: Domain
**Date**: 2026-04-07
**Sub-reviews**: 21 agents
**Status**: WARN
**Consolidated Score**: 9.79

## Sub-review Summary

| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S1.1 — Subzone aggregates | 18 | 10.00 | PASS | 0 | 0 |
| S1.2 — Subzone composite | 24 | 10.00 | PASS | 0 | 0 |
| S1.3 — Subzone config | 9 | 10.00 | PASS | 0 | 0 |
| S1.4 — Subzone contracts | 20 | 10.00 | PASS | 0 | 0 |
| S1.5 — Subzone control_plane | 10 | 10.00 | PASS | 0 | 0 |
| S1.6 — Subzone entities | 26 | 10.00 | PASS | 0 | 0 |
| S1.7 — Subzone exceptions | 21 | 6.80 | WARN | 6 | 1 |
| S1.8 — Subzone filtering | 12 | 10.00 | PASS | 0 | 0 |
| S1.9 — Subzone lineage | 5 | 10.00 | PASS | 0 | 0 |
| S1.10 — Subzone mapping | 10 | 10.00 | PASS | 0 | 0 |
| S1.11 — Subzone models | 7 | 10.00 | PASS | 0 | 0 |
| S1.12 — Subzone normalization | 8 | 10.00 | PASS | 0 | 0 |
| S1.13 — Subzone ports | 63 | 10.00 | PASS | 0 | 0 |
| S1.14 — Subzone registry | 5 | 10.00 | PASS | 0 | 0 |
| S1.15 — Subzone root | 20 | 10.00 | PASS | 0 | 0 |
| S1.16 — Subzone schemas | 43 | 10.00 | PASS | 0 | 0 |
| S1.17 — Subzone services | 48 | 9.80 | PASS | 0 | 1 |
| S1.18 — Subzone transformations | 5 | 10.00 | PASS | 0 | 0 |
| S1.19 — Subzone types | 15 | 10.00 | PASS | 0 | 0 |
| S1.20 — Subzone validation | 4 | 10.00 | PASS | 0 | 0 |
| S1.21 — Subzone value_objects | 39 | 9.80 | PASS | 0 | 1 |

## Aggregated Issues

### Critical (MUST fix)
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/domain/exceptions/__init__.py:61`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/domain/exceptions/bounded_context.py:13`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/domain/exceptions/infrastructure/__init__.py:5`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/domain/exceptions/infrastructure/__init__.py:6`
- **ISSUE-3**: Domain imports higher layer in `src/bioetl/domain/exceptions/infrastructure/__init__.py:15`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/domain/exceptions/infrastructure/_delta.py:7`

### High
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/domain/exceptions/network/service.py:190`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/domain/services/phased_migration_support.py:40`
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/domain/value_objects/compound_ids.py:235`

## Cross-subzone Observations
- Standard module boundaries are observed.

## Top 5 Recommendations
1. Adhere to dependency injection guidelines to prevent tight coupling.
