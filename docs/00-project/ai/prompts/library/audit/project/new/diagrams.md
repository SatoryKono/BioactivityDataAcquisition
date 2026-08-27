---
id: prompt.audit.project.new.diagrams
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
  - docs/02-architecture
  - scripts/diagrams
  - .codex/skills/technical-designer-mermaid/SKILL.md
  - docs/00-project/ai/prompts/library/audit/diagrams.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Preferring pretty PNG over accurate text-as-code
  - Unpinned npx -y in production CI
  - Huge code-level diagrams of the entire monorepo
  - Empty form cycles
  - ALLOW_* true by library default
  - Committing binary render churn without policy
  - Closing issues against unmerged PR heads as if they were origin/main
tags: [audit, diagrams, mermaid, cycle, scripts, operator]
summary: Improved cyclic diagrams audit — ADR-040 Mermaid skill, pinned render, fail-closed ALLOW, early-stop
max_body_lines: 220
---

# Improved cyclic diagrams audit

Улучшает `prompt.audit.cycle.diagrams` + method `prompt.audit.diagrams`.
Skill: **technical-designer-mermaid** (BioETL mode, ADR-040). Loop:
`prompt.audit.orchestrator`.

Library defaults: **`ALLOW_*=false`**. Пустые циклы запрещены.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `docs/02-architecture/diagrams scripts/diagrams` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `ALLOW_PUSH` | `false` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `false` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/diagrams-cycle-new-<shortsha>` |

## Anchors

- Canonical source = text-as-code (`.mmd`), not a lone PNG
- Renderer/version pinned; no bare `npx -y` in production CI
- C4 container ≠ Docker (ADR-010)
- PROVEN finding MUST have `requirement_id`
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA; branch. Чужой dirty → worktree.
2. SCOPE exists; empty → STOP.
3. `run_id = <UTC>-diagrams-new-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | List `.mmd` / policy SVG; map claim → live path or mark stale. |
| **B Lint/render** | Follow mermaid skill + `scripts/diagrams` owners. Record pinned toolchain evidence. |
| **C Drift** | Diagram vs ADR/code. No whole-repo code-level dump. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[diagrams][<REQ-id>][P#]`. `Cycle-run`. |
| **E Fix** | Minimal source-first edit; regenerate only via canonical script. |
| **F Validate** | Re-lint touched diagrams. Close only on `origin/main` evidence if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 и без regression → STOP.

## Success

- Canonical `.mmd` remains SoT; CI renderer pinned
- Lint/budget/artifact evidence in the run dir
- No secret or unpublished endpoint on published diagrams
