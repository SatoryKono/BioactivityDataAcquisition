---
id: prompt.audit.project.new2.http-clients
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params:
  - N
  - SCOPE
  - MODE
  - LANGUAGE
  - AUDIT_MODE
  - ALLOW_ISSUE_WRITE
  - ALLOW_PUSH
  - ALLOW_MERGE
  - ALLOW_CLOSE
  - MAX_ISSUES_PER_ITERATION
  - BASE_BRANCH
  - REPO
  - WORK_BRANCH
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/project-requirements-audit.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/RULES.md
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - docs/02-architecture/decisions/ADR-032-unified-http-client.md
  - src/bioetl/infrastructure/adapters/http/client.py
  - src/bioetl/infrastructure/adapters/http/_client_retry_flow.py
  - src/bioetl/infrastructure/adapters/http/rate_limiter.py
  - src/bioetl/infrastructure/adapters/http/pagination.py
  - src/bioetl/infrastructure/adapters/http/circuit_breaker.py
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Hardcoded secrets or tokens in adapters
  - Unbounded retries without backoff/QPS
  - Missing User-Agent / timeout
  - Pagination that drops pages on partial failure
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Raising debt budgets
tags: [audit, http, retry, rate-limit, adapters, cycle, operator]
summary: Cyclic HTTP-client audit — timeout, retry, QPS, pagination, circuit breaker, ALLOW_* true, early-stop
max_body_lines: 230
---

# Cyclic HTTP client / adapter audit

RULES §4.1.1, ADR-032. Не visual telemetry и не VCR (см.
`prompt.audit.project.new2.vcr-http`). Loop: `prompt.audit.orchestrator`.
Library defaults: **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `src/bioetl/infrastructure/adapters/` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/http-clients-cycle-new2-<shortsha>` |

## Anchors

- Unified client: `adapters/http/client.py` + retry/rate_limiter/pagination/CB
- Timeouts, backoff, QPS, User-Agent, no secrets in code
- Partial failure / pagination completeness
- PROVEN finding MUST have `requirement_id`
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. SCOPE exists; empty → STOP.
3. `run_id = <UTC>-http-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | Shared HTTP stack vs provider-specific adapters. Duplicate retry stacks. |
| **B Contract** | Timeout, retry/backoff, QPS, UA, CB. Secrets/env names only. |
| **C Pagination** | Page completeness; no silent drop. Health-check paths. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[http][<REQ-id>][P#]`. |
| **E Fix** | Minimal adapter change. No live hammering of third-party APIs. |
| **F Validate** | Unit/contract tests in SCOPE. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 → STOP.

## Success

- HTTP contract evidence (timeouts/retry/QPS) for in-scope adapters
- No token literals; no unbounded retry
