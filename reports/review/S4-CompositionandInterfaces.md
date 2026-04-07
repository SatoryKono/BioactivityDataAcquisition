# Consolidated Review — S4: Composition and Interfaces
**Date**: 2026-04-07
**Sub-reviews**: 10 agents
**Status**: WARN
**Consolidated Score**: 8.99

## Sub-review Summary

| Sub-sector | Files | Score | Status | CRIT | HIGH |
|------------|-------|-------|--------|------|------|
| S4.1 — Subzone bootstrap | 46 | 10.00 | PASS | 0 | 0 |
| S4.2 — Subzone factories | 71 | 9.80 | PASS | 0 | 1 |
| S4.3 — Subzone providers | 18 | 10.00 | PASS | 0 | 0 |
| S4.4 — Subzone root | 18 | 9.55 | PASS | 0 | 2 |
| S4.5 — Subzone runtime_builders | 10 | 10.00 | PASS | 0 | 0 |
| S4.6 — Subzone services | 3 | 10.00 | PASS | 0 | 0 |
| S4.7 — Subzone cli | 78 | 7.00 | WARN | 34 | 0 |
| S4.8 — Subzone http | 6 | 10.00 | PASS | 0 | 0 |
| S4.9 — Subzone orchestration | 1 | 10.00 | PASS | 0 | 0 |
| S4.10 — Subzone root | 2 | 10.00 | PASS | 0 | 0 |

## Aggregated Issues

### Critical (MUST fix)
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/command.py:13`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/command.py:52`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/execution.py:8`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/execution.py:21`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/runtime.py:5`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/composite/support.py:9`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/health/command.py:31`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/health/command.py:32`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/maintenance/archive.py:24`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/maintenance/plan.py:24`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/maintenance/vacuum.py:29`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/maintenance/vacuum.py:32`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command.py:70`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command.py:71`
- **ISSUE-3**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command.py:74`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py:10`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py:32`
- **ISSUE-3**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/command_policy.py:35`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/result_flow.py:7`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/result_flow.py:10`
- **ISSUE-3**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/result_flow.py:18`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/result_presenter.py:5`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/runtime_helpers.py:8`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/runtime_helpers.py:11`
- **ISSUE-3**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/runtime_helpers.py:25`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/service_access.py:8`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/service_access.py:19`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run/support.py:42`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run_all/command.py:10`
- **ISSUE-2**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run_all/command.py:73`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run_all/command_policy.py:9`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run_all/execution.py:10`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/run_all/support.py:12`
- **ISSUE-1**: Domain imports higher layer in `src/bioetl/interfaces/cli/commands/domains/shared/execution_policy.py:16`

### High
- **ISSUE-1**: Hardcoded constructor dependency in `src/bioetl/composition/factories/pipeline/assembler.py:97`
- **ISSUE-1**: Direct structlog import outside infrastructure in `src/bioetl/composition/bootstrap_logger.py:25`
- **ISSUE-2**: Hardcoded constructor dependency in `src/bioetl/composition/bootstrap_logger.py:99`

## Cross-subzone Observations
- Standard module boundaries are observed.

## Top 5 Recommendations
1. Adhere to dependency injection guidelines to prevent tight coupling.
