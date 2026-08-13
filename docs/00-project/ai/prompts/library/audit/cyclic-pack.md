---
id: prompt.audit.cyclic-pack
version: 1.1.0
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
  - docs/00-project/ai/prompts/library/audit/coderabbit-project-cycle.md
  - docs/00-project/ai/prompts/library/audit/cycle/README.md
tags: [audit, cycle, pack, operator]
summary: Pack of cyclic domain audits — 10-domain prompt.audit.cycle.* program
max_body_lines: 160
---

# Cyclic audit pack (tests / docs / tech-debt / repo hygiene / …)

**Десять** канонических циклических аудитов живут в
[cycle/](cycle/README.md) (`prompt.audit.cycle.*`). Старые циклы
(`docs-cycle`, `tests-cycle`, …) остаются совместимыми one-family cards.

| # | Domain | Card | Domain method | Artifacts |
| --- | --- | --- | --- | --- |
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

Library cards may default `ALLOW_*=false` (fail-closed). Operator full-run paste
above **explicitly** enables mutations. `INCLUDE_PIPELINE` applies to **docs-cycle**
(and orchestrator docs runs). Tests/tech-debt cards ignore it if unused.

## How to run

### A. Single-agent cyclic (default)

1. Open the domain card (tests-cycle / docs-cycle / tech-debt-cycle / …).
2. Paste into agent with params filled (for mutations set ALLOW_* true).
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
  SCOPE=<paths>
  MODE=full
  INCLUDE_PIPELINE=true
  CODERABBIT=required-then-agent
  ALLOW_ISSUE_WRITE=true
  ALLOW_PUSH=true
  ALLOW_MERGE=true
  ALLOW_CLOSE=true
```

### D. Exhaustive project + CodeRabbit

```text
Use prompt.audit.coderabbit-project-cycle with:
  N=10
  MODE=full
  CODERABBIT=required-then-agent
  INCLUDE_DOMAINS=all
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
| `prompt.architecture.cycle` | **Cyclic** architecture audit (v1.1): 10 categories → plan → implement |
| `prompt.audit.coderabbit-project-cycle` | **Exhaustive** project cyclic audit + CodeRabbit dual-pass |
| `prompt.audit.grok-cycle` | Generic one-cycle meta audit (any SCOPE) |
| `prompt.audit.orchestrator` | Generic N-loop shell (needs AUDIT_PROMPT_SOURCE) |

## Policy

- Tech-debt budgets: **only decrease or hold** (never raise).
- No admin merge bypass in audit prompts (use operator-owned process if needed).
- Artifacts under `reports/`, never repo-root `_audit*`.
