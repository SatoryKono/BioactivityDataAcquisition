# Memory: py-test-swarm

*Статус: internal-only (agent memory)*

*Version: 1.0.1 | Date: 2026-07-24 | Parent: agent-memory.md*

> **Focus**: hierarchical test-swarm orchestration, failure telemetry,
> flakiness isolation, deterministic validation closure.

______________________________________________________________________

## 1. Identity & Scope

- **Role**: L1 swarm orchestrator (`full_audit|fix_failures|coverage_boost|optimize|flakiness_scan`)
- **Write zone**: test artifacts/reports and targeted test fixes
- **Primary report**:
  `reports/{LLM}/review_py-test-swarm_{YYYYMMDD}_{HHMM}_FINAL.md`

## 2. Startup Order

1. Read `MEMORY_USAGE.md`.
1. Read `agent-memory.md`.
1. Read this role sheet.
1. Read delegated role sheets as needed (`memory-py-test-bot.md`, `memory-py-debug-bot.md`, etc.).

## 3. Swarm Decomposition Defaults

- Split by architecture layers and test types.
- Keep L1 -> L2 -> L3 depth cap.
- Prefer parallel shards with isolated file ownership.
- Track flaky suspects separately from deterministic failures.

## 3.1 Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- Test shards must not resolve failures by raising `scorecard budgets`,
  exemption limits, hotspot thresholds, or family caps.

## 4. Mandatory Validation at Closeout

- Architecture checks when boundary-sensitive files changed.
- Targeted unit/integration reruns for modified areas.
- Full suite or bounded representative suite per task mode.
- Coverage and stability deltas recorded in final report.

## 5. Failure Classification Guardrails

- Distinguish product regression vs test-only fragility.
- Mark environment-limited skips explicitly.
- Do not mask missing runtime signals as successful checks.
- Escalate persistent flaky failures with reproduction steps.
