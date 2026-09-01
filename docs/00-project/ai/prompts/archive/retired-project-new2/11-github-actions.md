---
id: prompt.audit.project.new2.github-actions
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
  - docs/01-requirements/REQUIREMENTS.md
  - docs/01-requirements/traceability/requirements-traceability-crosswalk.csv
  - .github/workflows
  - .github/dependabot.yml
  - docs/04-reference/github-actions-workflows.md
  - docs/00-project/ai/prompts/library/audit/github-actions.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Broad write permissions for convenience
  - Unpinned third-party actions
  - Treating untrusted PR code as safe under privileged triggers
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Raising debt budgets
tags: [audit, ci, github-actions, supply-chain, cycle, operator]
summary: Cyclic GitHub Actions supply-chain audit — pins, permissions, trust model, ALLOW_* true, early-stop
max_body_lines: 220
---

# Cyclic GitHub Actions audit

Циклическая оболочка над method `prompt.audit.github-actions` (nine-kit).
Loop: `prompt.audit.orchestrator`. Library defaults: **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `.github/workflows .github/dependabot.yml` |
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
| `WORK_BRANCH` | `fix/gha-cycle-new2-<shortsha>` |

## Anchors

- Catalog: `docs/04-reference/github-actions-workflows.md`
- Order: trust model → correctness → reproducibility → cache → artifacts
- Pin actions; least privilege; no secrets in logs
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA. Чужой dirty → worktree.
2. `run_id = <UTC>-gha-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
3. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Trust** | Events, `pull_request_target`, tokens, third-party actions, runners. |
| **B Pins** | Unpinned tags vs SHA. Dependabot coverage. |
| **C Correctness** | Workflow catalog vs files; required checks vs docs. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[gha][<REQ-id>][P#]`. |
| **E Fix** | Pin/permissions/docs. No admin bypass. |
| **F Validate** | Workflow YAML validity. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.

## Success

- Trust + pin findings with path evidence
- Catalog not silently drifted
