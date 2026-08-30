---
id: prompt.audit.project.new2.qa-gates
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
  - scripts/engineering/qa/README.md
  - reports/quality/architecture-quality-scorecard.json
  - reports/quality/debt-governance-gates.json
  - .codex/skills/verify-architecture/SKILL.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Raising scorecard/coverage/hotspot budgets
  - Hand-editing generated quality JSON
  - Stale source_tree_sha256 after src/bioetl changes
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
tags: [audit, quality, scorecard, gates, cycle, operator]
summary: Cyclic QA-gates audit — quality scripts, scorecard freshness, no budget growth, ALLOW_* true, early-stop
max_body_lines: 220
---

# Cyclic quality-gates / scorecard freshness audit

Генераторы `scripts/engineering/qa`, committed `reports/quality/*`.
Не 10-category architecture scoring as product (см.
`prompt.audit.project.new.architecture`) — здесь **свежесть артефактов и
запрет роста бюджетов**. Skill: **verify-architecture**. Loop:
`prompt.audit.orchestrator`. Library defaults: **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `scripts/engineering/qa/ reports/quality/` |
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
| `WORK_BRANCH` | `fix/qa-gates-cycle-new2-<shortsha>` |

## Anchors

- `python -m scripts.engineering.qa --help` / README
- Scorecard JSON, debt-governance-gates, module-coverage inventory
- Refresh hashes only via canonical commands
- **УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО**
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA. Snapshot budget fields (read-only).
2. `run_id = <UTC>-qa-new2-<shortsha>`. Marker: `Cycle-run: <run_id>`.
3. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | QA entrypoints vs README vs CI wiring. |
| **B Freshness** | Committed JSON vs generators. Hand-edits. |
| **C Budgets** | Any cap increase vs snapshot → `REJECTED_POLICY`. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[qa][<REQ-id>][P#]`. |
| **E Fix** | Re-run owner command; no cap raises. |
| **F Validate** | Architecture-quick / documented qa check. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.

## Success

- Freshness/budget delta table
- No raised caps
