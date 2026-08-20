---
id: prompt.audit.cycle.diagrams
version: 1.1.0
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
  - docs/00-project/ai/prompts/library/audit/diagrams.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Preferring pretty PNG over accurate text-as-code
  - Unpinned npx -y in production CI
  - Huge code-level diagrams of the entire monorepo
  - Committing binary render churn without policy
  - Empty form cycles
tags: [audit, diagrams, mermaid, cycle, scripts, operator]
summary: Cyclic audit of version-controlled diagrams and render scripts
max_body_lines: 240
---

# Cyclic diagrams + diagram-scripts audit

N-итерационный аудит **диаграмм и вспомогательных скриптов** `scripts/diagrams`.
Диаграмма — engineering artifact: канонический text-as-code source,
воспроизводимый pinned render, соответствие коду/ADR.

Domain method: `prompt.audit.diagrams`. Loop shell: `prompt.audit.orchestrator`.
Default **`N=10`**, **`MODE=full`**, все **`ALLOW_*=true`**. Пустые циклы запрещены.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `docs/02-architecture/diagrams scripts/diagrams` |
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

## BioETL anchors

- Requirements: `docs/01-requirements/REQUIREMENTS.md` + traceability CSV; PROVEN findings need `requirement_id`
- Lint / governance: ADR-040; DOC-GOV-02 (`**/png/**` is a render artifact, not SSOT)
- Entry: `python -m scripts.diagrams` (`lint`, `lint-budget`, `checks`,
  `check-artifacts`, `check-visual-smoke`, `check-svg-text`)
- Layout: `scripts/diagrams/{lint,check,fix,render}/`
- Skill: `.codex/skills/technical-designer-mermaid/`
- Windows: `.\.venv-win\Scripts\python.exe -m scripts.diagrams …`
- C4 is zoom levels (context / container / component). Container ≠ Docker.

## Preflight

1. `git status --porcelain`; SHA; branch. Foreign dirty work → worktree.
2. Confirm SCOPE paths exist; empty SCOPE → STOP.
3. `run_id = <UTC>-diagrams-cycle-<shortsha>`
4. Artifacts: `reports/audit-runs/<run_id>/` + mirror `reports/audit/diagrams/`.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Inventory** | List `.mmd` / `.mermaid`, embedded Mermaid in md/mdx, tracked SVG/PNG. Per diagram: source, generated output, renderer/version, owner, last meaningful update, linked docs. Classify: context, container, component, sequence, deployment, data, state, CI flow. |
| **B Lint / budget** | Run `python -m scripts.diagrams lint` and `lint-budget`. Record gate result. Flag unpinned `npx -y` in CI/render scripts. |
| **C Render smoke** | Pinned project tooling only. `checks` / `check-artifacts` / `check-visual-smoke` as available. If generated images are tracked: clean render + `git diff` only when policy requires; else temp output. |
| **D Accuracy** | Each claim on a diagram → path in code/ADR/config. Orphan nodes, stale edges, secrets/internal endpoints that must not be published. A pretty but wrong diagram scores worse than a minimal accurate one. |
| **E Issues / Fix** | Dedupe. Create if ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[diagrams][<REQ-id>][P#]`. Fix `.mmd` / project fixers. No unpolicy binary churn. |
| **F Validate** | Re-lint / re-check-artifacts on touched set. Delta: resolved / unchanged / regressed / new. |

`MODE=audit` stops after D. `audit+issues` after issue payload. `full` through F.

## Focus checklist (each cycle)

- [ ] Canonical source is text-as-code (`.mmd`), not a lone PNG
- [ ] Renderer/version pinned; no bare `npx -y` in CI
- [ ] Quality budget not raised to pass lint
- [ ] C4 zoom appropriate; no whole-repo code-level dump
- [ ] Diagram claim maps to a live path or is marked stale
- [ ] Required SVG artifacts present when policy says so
- [ ] No secrets or unpublished internal endpoints on diagrams
- [ ] PNG/SVG churn justified or left uncommitted

## Stop

Full-repo code-level diagram → reject as out of method. Empty SCOPE → STOP.
Unpinned renderer in production CI → P1+. Secret on a published diagram → P0.
Do not commit binary render dumps without DOC-GOV-02 policy.

## Success

- `findings.json` + `report.md` under `reports/audit-runs/<run_id>/`
- Lint/budget/artifact evidence recorded
- Touched diagrams re-checked after fix
- `surface_score` 0–3 with PROVEN gaps only

## Related

- One-shot: `prompt.audit.diagrams`
- Dual-agent: `prompt.audit.dual-agent-cycle` +
  `AUDIT_PROMPT_SOURCE=prompt.audit.diagrams`
- Closeout: `prompt.closeout.grok`
- Previous: `prompt.audit.cycle.docs` · Next: `prompt.audit.cycle.agents-memory`
