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
  - fragments/orchestrator-guards.md
related_ssot:
  - docs/00-project/ai/prompts/README.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/prompts/library/audit/dual-agent-cycle.md
tags: [audit, cycle, pack, operator]
summary: Pack of cyclic domain audits — tests, docs, tech-debt, repo hygiene
max_body_lines: 120
---

# Cyclic audit pack (tests / docs / tech-debt / repo hygiene)

Четыре **готовых** циклических аудита. Каждая строка — отдельный paste card.

| # | Domain | Card | Domain method | Artifacts |
| --- | --- | --- | --- | --- |
| 1 | Тесты | `prompt.audit.tests-cycle` → [tests-cycle.md](tests-cycle.md) | `prompt.audit.tests-system` | `reports/audit-runs/<run_id>/` |
| 2 | Документация | `prompt.audit.docs-cycle` → [docs-cycle.md](docs-cycle.md) | `prompt.audit.docs-content` | same |
| 3 | Техдолг | `prompt.audit.tech-debt-cycle` → [tech-debt-cycle.md](tech-debt-cycle.md) | `prompt.audit.tech-debt` | same |
| 4 | Гигиена репо | `prompt.audit.repo-tree-cycle` → [repo-tree-cycle.md](repo-tree-cycle.md) | `prompt.audit.repo-tree` | same |
| 5 | Дашборды | `prompt.observability.dashboard-audit-cycle` → [../observability/dashboard-audit-cycle.md](../observability/dashboard-audit-cycle.md) | panel-audit + bi-acceptance | `reports/audit/dashboard-cycle/` |

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
    # or docs-content / tech-debt / repo-tree
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
    # or docs-content / tech-debt / repo-tree
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
| `prompt.audit.grok-cycle` | Generic one-cycle meta audit (any SCOPE) |
| `prompt.audit.orchestrator` | Generic N-loop shell (needs AUDIT_PROMPT_SOURCE) |

## Policy

- Tech-debt budgets: **only decrease or hold** (never raise).
- No admin merge bypass in audit prompts (use operator-owned process if needed).
- Artifacts under `reports/`, never repo-root `_audit*`.
