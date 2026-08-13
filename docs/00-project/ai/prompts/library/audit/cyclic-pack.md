---
id: prompt.audit.cyclic-pack
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [any]
params: [N, MODE, LANGUAGE]
includes:
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/git-safety.md
  - fragments/orchestrator-guards.md
related_ssot:
  - docs/00-project/ai/prompts/README.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/prompts/library/audit/dual-agent-cycle.md
<<<<<<< Updated upstream
||||||| Stash base
  - docs/00-project/ai/prompts/library/audit/coderabbit-project-cycle.md
=======
  - docs/00-project/ai/prompts/library/audit/coderabbit-project-cycle.md
  - docs/00-project/ai/prompts/library/audit/cycle/README.md
>>>>>>> Stashed changes
tags: [audit, cycle, pack, operator]
<<<<<<< Updated upstream
summary: Pack of cyclic domain audits — tests, docs, tech-debt, repo hygiene
max_body_lines: 120
||||||| Stash base
summary: Pack of cyclic domain audits — tests, docs, debt, hygiene, dashboards, architecture, CodeRabbit
max_body_lines: 130
=======
summary: Pack of cyclic domain audits — 10-domain prompt.audit.cycle.* program
max_body_lines: 160
>>>>>>> Stashed changes
---

# Cyclic audit pack (tests / docs / tech-debt / repo hygiene)

<<<<<<< Updated upstream
Четыре **готовых** циклических аудита. Каждая строка — отдельный paste card.
||||||| Stash base
**Семь** готовых циклических аудитов (включая architecture и CodeRabbit project).
Каждая строка — отдельный paste card.
=======
**Десять** канонических циклических аудитов живут в
[cycle/](cycle/README.md) (`prompt.audit.cycle.*`). Старые циклы
(`docs-cycle`, `tests-cycle`, …) остаются совместимыми one-family cards.
>>>>>>> Stashed changes

| # | Domain | Card | Domain method | Artifacts |
| --- | --- | --- | --- | --- |
<<<<<<< Updated upstream
| 1 | Тесты | `prompt.audit.tests-cycle` → [tests-cycle.md](tests-cycle.md) | `prompt.audit.tests-system` | `reports/audit-runs/<run_id>/` |
| 2 | Документация | `prompt.audit.docs-cycle` → [docs-cycle.md](docs-cycle.md) | `prompt.audit.docs-content` | same |
| 3 | Техдолг | `prompt.audit.tech-debt-cycle` → [tech-debt-cycle.md](tech-debt-cycle.md) | `prompt.audit.tech-debt` | same |
| 4 | Гигиена репо | `prompt.audit.repo-tree-cycle` → [repo-tree-cycle.md](repo-tree-cycle.md) | `prompt.audit.repo-tree` | same |
| 5 | Дашборды | `prompt.observability.dashboard-audit-cycle` → [../observability/dashboard-audit-cycle.md](../observability/dashboard-audit-cycle.md) | panel-audit + bi-acceptance | `reports/audit/dashboard-cycle/` |
| 6 | Архитектура | `prompt.architecture.cycle` → [../architecture/architecture-cycle.md](../architecture/architecture-cycle.md) | `prompt.architecture.review` | `reports/audit-runs/` + `reports/audit/architecture/` |
||||||| Stash base
| 1 | Тесты | `prompt.audit.tests-cycle` → [tests-cycle.md](tests-cycle.md) | `prompt.audit.tests-system` | `reports/audit-runs/<run_id>/` |
| 2 | Документация | `prompt.audit.docs-cycle` → [docs-cycle.md](docs-cycle.md) | `prompt.audit.docs-content` | same |
| 3 | Техдолг | `prompt.audit.tech-debt-cycle` → [tech-debt-cycle.md](tech-debt-cycle.md) | `prompt.audit.tech-debt` | same |
| 4 | Гигиена репо | `prompt.audit.repo-tree-cycle` → [repo-tree-cycle.md](repo-tree-cycle.md) | `prompt.audit.repo-tree` | same |
| 5 | Дашборды | `prompt.observability.dashboard-audit-cycle` → [../observability/dashboard-audit-cycle.md](../observability/dashboard-audit-cycle.md) | panel-audit + bi-acceptance | `reports/audit/dashboard-cycle/` |
| 6 | Архитектура | `prompt.architecture.cycle` → [../architecture/architecture-cycle.md](../architecture/architecture-cycle.md) | `prompt.architecture.review` + 10-category scorecard → plan → implement | `reports/audit-runs/` + `reports/audit/architecture/` |
| 7 | Проект + CodeRabbit | `prompt.audit.coderabbit-project-cycle` → [coderabbit-project-cycle.md](coderabbit-project-cycle.md) | multi-domain matrix + CR dual-pass → plan → fix → re-CR | `reports/audit-runs/` + `reports/audit/coderabbit-project/` |
=======
| 1 | Документация + `scripts/docs` | `prompt.audit.cycle.docs` → [cycle/docs.md](cycle/docs.md) | `docs-content` + `docs-pipeline` | `reports/audit-runs/<run_id>/` |
| 2 | Диаграммы + `scripts/diagrams` | `prompt.audit.cycle.diagrams` → [cycle/diagrams.md](cycle/diagrams.md) | `prompt.audit.diagrams` | same |
| 3 | Агенты + память | `prompt.audit.cycle.agents-memory` → [cycle/agents-memory.md](cycle/agents-memory.md) | `agents-runtime` + memory workflow | same |
| 4 | Конфиги | `prompt.audit.cycle.configs` → [cycle/configs.md](cycle/configs.md) | py-config-bot hierarchy | same |
| 5 | Тестовый слой | `prompt.audit.cycle.tests` → [cycle/tests.md](cycle/tests.md) | `prompt.audit.tests-system` | same |
| 6 | Техдолг | `prompt.audit.cycle.tech-debt` → [cycle/tech-debt.md](cycle/tech-debt.md) | `prompt.audit.tech-debt` | same |
| 7 | Архитектура | `prompt.audit.cycle.architecture` → [cycle/architecture.md](cycle/architecture.md) | 10-category scorecard | same |
| 8 | Наблюдаемость / feed | `prompt.audit.cycle.telemetry` → [cycle/telemetry.md](cycle/telemetry.md) | metrics + recording rules | same |
| 9 | Рендер / дизайн панелей | `prompt.audit.cycle.dashboards` → [cycle/dashboards.md](cycle/dashboards.md) | panel-audit + BI-acceptance | `reports/audit/dashboard-cycle/` |
| 10 | Проект + CodeRabbit | `prompt.audit.cycle.coderabbit` → [cycle/coderabbit.md](cycle/coderabbit.md) | multi-domain + CR dual-pass | `reports/audit/coderabbit-project/` |
>>>>>>> Stashed changes

## Shared defaults (operator full-run)

```text
N=10
MODE=full
LANGUAGE=ru
INCLUDE_PIPELINE=true
ALLOW_ISSUE_WRITE=true
ALLOW_PUSH=true
ALLOW_MERGE=true
ALLOW_CLOSE=true
BASE_BRANCH=main
REPO=SatoryKono/BioactivityDataAcquisition
```

`INCLUDE_PIPELINE` applies to **docs-cycle** (and orchestrator docs runs).  
Tests/tech-debt cards ignore it if unused. Override ALLOW_* only to *restrict*.

## How to run

### A. Single-agent cyclic (default)

1. Open the domain card (tests-cycle / docs-cycle / tech-debt-cycle).
2. Paste into agent with params filled (defaults already MODE=full + ALLOW_* true).
3. Agent may open issues, push PRs, merge, and close when acceptance is met.

### B. Orchestrator + domain method

```text
Use prompt.audit.orchestrator with:
  N=10
  AUDIT_PROMPT_SOURCE=prompt.audit.tests-system
    # or docs-content / tech-debt / repo-tree / architecture.review
  SCOPE=<paths>
  MODE=full
  INCLUDE_PIPELINE=true
  ALLOW_ISSUE_WRITE=true
  ALLOW_PUSH=true
  ALLOW_MERGE=true
  ALLOW_CLOSE=true
```

### C. Dual-agent (A/B + CodeRabbit + peer review)

```text
Use prompt.audit.dual-agent-cycle with:
  OUTER_CYCLES=10
  AUDIT_PROMPT_SOURCE=prompt.audit.tests-system
    # or docs-content / tech-debt / repo-tree / architecture.review
  SCOPE=<paths>
  MODE=full
  INCLUDE_PIPELINE=true
  CODERABBIT=required-then-agent
  ALLOW_ISSUE_WRITE=true
  ALLOW_PUSH=true
  ALLOW_MERGE=true
  ALLOW_CLOSE=true
```

## Do not confuse

| Card | Purpose |
| --- | --- |
| `prompt.tests.cycle` | **Run** pytest loop (baseline → fix → retest) |
| `prompt.audit.tests-cycle` | **Audit** the test *system* (lanes, flaky, gates) |
| `prompt.audit.repo-tree` | One-shot root/tree hygiene audit |
| `prompt.audit.repo-tree-cycle` | **Cyclic** root/tree hygiene (N loops + fix/PR) |
| `prompt.architecture.review` | One-shot architecture review (hexagonal/C4) |
| `prompt.architecture.cycle` | **Cyclic** project architecture audit (N loops + fix/PR) |
| `prompt.audit.grok-cycle` | Generic one-cycle meta audit (any SCOPE) |
| `prompt.audit.orchestrator` | Generic N-loop shell (needs AUDIT_PROMPT_SOURCE) |

## Policy

- Tech-debt budgets: **only decrease or hold** (never raise).
- No admin merge bypass in audit prompts (use operator-owned process if needed).
- Artifacts under `reports/`, never repo-root `_audit*`.
