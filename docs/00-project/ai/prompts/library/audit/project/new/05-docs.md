---
id: prompt.audit.project.new.docs
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
  - INCLUDE_PIPELINE
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
  - docs/00-project/00-map.md
  - mkdocs.yml
  - scripts/docs
  - docs/00-project/ai/prompts/library/audit/docs-content.md
  - docs/00-project/ai/prompts/library/audit/docs-pipeline.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Counting Markdown files instead of verifying procedures
  - Treating generator exit 0 as semantic correctness
  - Empty form cycles
  - Mutations without PROVEN + requirement_id
  - Closing issues against unmerged PR heads as if they were origin/main
  - Publishing docs from MODE=audit
  - Returning retired top-level scripts/docs shims
tags: [audit, docs, cycle, content, pipeline, scripts, operator]
summary: Improved cyclic docs audit — content plus scripts/docs pipeline, ALLOW_* true, early-stop
max_body_lines: 220
---

# Improved cyclic documentation audit

Улучшает `prompt.audit.cycle.docs` + `prompt.audit.docs-cycle`. Не runtime SSOT.
Loop: `prompt.audit.orchestrator`. Два disjoint-контура: `content` /
`pipeline`.

Library defaults: **`ALLOW_*=true`**. Operator full-run: issue/push/merge/close включены по умолчанию. Пустые циклы запрещены.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `README.md docs/ mkdocs.yml scripts/docs/` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `INCLUDE_PIPELINE` | `true` |
| `ALLOW_ISSUE_WRITE` | `true` |
| `ALLOW_PUSH` | `true` |
| `ALLOW_MERGE` | `true` |
| `ALLOW_CLOSE` | `true` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/docs-cycle-new-<shortsha>` |

## Anchors

- `python -m scripts.docs` (`verify`, `check-drift`, `check-links`, `check-kpi`)
- AI docs = mirrors; `.codex/**` ≡ `.junie/**` win
- Windows: `.\.venv-win\Scripts\python.exe`
- PROVEN finding MUST have `requirement_id`

## Preflight

1. `git status --porcelain`; SHA; branch. Чужой dirty → worktree.
2. SCOPE paths exist; empty → STOP.
3. `run_id = <UTC>-docs-new-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Content** | Method `prompt.audit.docs-content`. Audience, SoT, owner, commands vs `pyproject.toml`/CI, links, contradictions. Tag `content`. |
| **B Pipeline** | If `INCLUDE_PIPELINE=true`: method `prompt.audit.docs-pipeline`. Run `verify` / `check-drift` / `check-links` as evidence. Exit 0 ≠ semantics. Tag `pipeline`. |
| **C Plan** | Cluster root-causes. Prefer restore-SSOT-link. |
| **D Issues** | Create only if ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[docs][<REQ-id>][P#]`. Cap MAX_ISSUES. Body: `Cycle-run: <run_id>`. |
| **E Fix** | Minimal doc/comment. Regenerations only via `python -m scripts.docs <cmd>`. Never `main`. |
| **F Validate** | Re-check claims; sample links. Close only if ALLOW_CLOSE and evidence on `origin/main` (or operator accepted PR-head). |

`MODE=audit` stops after C. `audit+issues` after D. `full` through F.

## Early-stop

После D посчитать `new_issues_i` и `open_cycle_issues` (`Cycle-run: <run_id>`).
**STOP**, если `new_issues_i == 0` **и** `open_cycle_issues == 0`.
Иначе два подряд цикла без новых PROVEN P0/P1 и без regression → STOP.
Не выдумывать пустые циклы до N.

## Success

- `findings.json` + `report.md` + per-iteration delta
- Pipeline contour has command evidence
- No new contradictory onboarding paths; `.env` secrets not in docs
