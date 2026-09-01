---
id: prompt.audit.project.new2.ops-runbooks
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
  - MONITORING
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
  - docs/02-architecture/decisions/ADR-010-local-only-deployment.md
  - docs/05-operations/runbooks/index.md
  - docs/03-guides/workflows.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Starting docker-compose.monitoring.yml without MONITORING=true
  - Requiring Redis/Docker for local default
  - Runbook commands that do not exist in CLI/docs
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Raising debt budgets
tags: [audit, ops, runbooks, dr, cycle, operator]
summary: Cyclic ops/runbook audit — DR, rollback, Game Day, ADR-010, ALLOW_* true, early-stop
max_body_lines: 220
---

# Cyclic operations / runbook audit

RULES §5, `docs/05-operations/`. ADR-010 local-only default.
`MONITORING=false` unless operator approved. Loop: `prompt.audit.orchestrator`.
Library defaults: **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `docs/05-operations/ docs/03-guides/workflows.md` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `MONITORING` | `false` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/ops-cycle-new2-<shortsha>` |

## Anchors

- Runbook index: `docs/05-operations/runbooks/index.md`
- Workflow CLI: `docs/03-guides/workflows.md`
- Do not start optional monitoring/Docker without approval
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA.
2. Do **not** start `docker-compose.monitoring.yml` unless MONITORING=true.
3. `run_id = <UTC>-ops-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | Runbooks: DR, rollback, shutdown, Game Day, control-plane triage. |
| **B Commands** | Each procedure vs CLI/docs/scripts that exist. |
| **C ADR-010** | Hidden Redis/Docker/orchestration requirements. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[ops][<REQ-id>][P#]`. |
| **E Fix** | Runbook/CLI docs. No live prod actions. |
| **F Validate** | Re-read changed procedures. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.

## Success

- Broken-command list with evidence
- Monitoring stack not started unless authorized
