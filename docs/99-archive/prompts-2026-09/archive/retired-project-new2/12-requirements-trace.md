---
id: prompt.audit.project.new2.requirements-trace
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
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Counting files as coverage of a requirement
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Raising debt budgets
tags: [audit, requirements, traceability, cycle, operator]
summary: Cyclic REQ-* traceability audit — requirements vs tests/code, ALLOW_* true, early-stop
max_body_lines: 210
---

# Cyclic requirements traceability audit

REQ-* in `REQUIREMENTS.md` + crosswalk CSV. Fragment
`project-requirements-audit` is inlined via includes — this card **owns**
coverage gaps. Loop: `prompt.audit.orchestrator`.
Library defaults: **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `docs/01-requirements/ tests/` |
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
| `WORK_BRANCH` | `fix/req-trace-cycle-new2-<shortsha>` |

## Anchors

- IDs only from REQUIREMENTS.md / traceability CSV
- Each PROVEN finding already requires `requirement_id`; here the object is
  **orphan REQ** and **untraced tests**
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA.
2. `run_id = <UTC>-req-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
3. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | REQ ids in markdown vs CSV. Duplicates/missing rows. |
| **B Trace** | Sample REQ → test/code path. Gaps = NOT_PROVEN until evidenced. |
| **C Drift** | Tests citing invented REQ. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[req][<REQ-id>][P#]`. |
| **E Fix** | Crosswalk/test names/docs. Do not invent IDs. |
| **F Validate** | Re-read CSV+REQUIREMENTS. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.

## Success

- Orphan/untraced REQ table
- No invented REQ-* in findings
