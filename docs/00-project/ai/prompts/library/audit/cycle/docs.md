---
id: prompt.audit.cycle.docs
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
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
  - fragments/audit-scale.md
  - fragments/finding-schema.md
  - fragments/unknown-params.md
  - fragments/reports-output.md
  - fragments/shell-portability.md
  - fragments/orchestrator-guards.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/RULES.md
  - docs/00-project/00-map.md
  - mkdocs.yml
  - scripts/docs
  - docs/00-project/ai/prompts/library/audit/docs-content.md
  - docs/00-project/ai/prompts/library/audit/docs-pipeline.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
anti_patterns:
  - Counting Markdown files instead of verifying procedures
  - Treating generator exit 0 as semantic correctness
  - Inventing commands not in manifests or CI
  - Empty form cycles
  - Publishing docs from audit mode
  - Returning retired top-level scripts/docs shims
tags: [audit, docs, cycle, content, pipeline, scripts, operator]
summary: Cyclic audit of documentation content and docs helper scripts
max_body_lines: 240
---

# Cyclic documentation + docs-scripts audit

N-итерационный аудит **документации и вспомогательных скриптов** `scripts/docs`.
Два disjoint-контура в одном цикле:

| Contour | Method | Что проверять |
| --- | --- | --- |
| `content` | `prompt.audit.docs-content` | purpose, IA, freshness, команды, ссылки, противоречия |
| `pipeline` | `prompt.audit.docs-pipeline` | generate → validate → artifact → publish |

Loop shell: `prompt.audit.orchestrator`. Default **`N=10`**, **`MODE=full`**,
**`INCLUDE_PIPELINE=true`**, все **`ALLOW_*=true`**. Пустые циклы запрещены.

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

## BioETL anchors

- Map / ownership: `docs/00-project/00-map.md`, DOC-GOV-09 in `NORMATIVE_SOURCES.md`
- Entry: `python -m scripts.docs` (`verify`, `check-drift`, `check-links`,
  `check-kpi`, `build-site`, `check-docstrings`)
- Layout: `scripts/docs/{checks,build,fixers,matrix,passports}/`
- KPI: `python -m scripts.docs check-kpi`; weekly `docs-kpi-weekly.yml`
- AI docs under `docs/00-project/ai/**` are **mirrors**, not runtime SSOT
- Windows: `.\.venv-win\Scripts\python.exe -m scripts.docs …`
- Never put secret values from `.env` into docs or generated pages

## Preflight

1. `git status --porcelain`; SHA; branch. Foreign dirty work → worktree.
2. Confirm SCOPE paths exist; empty SCOPE → STOP.
3. `run_id = <UTC>-docs-cycle-<shortsha>`
4. Artifacts: `reports/audit-runs/<run_id>/` + mirror `reports/audit/docs-content/`
   and `reports/audit/docs-pipeline/` when pipeline is in scope.

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Content** | Inventory README*, `docs/**`, CONTRIBUTING*, ADR, runbooks, onboarding. Per doc: audience, SoT, owner, last meaningful change. Verify bootstrap/install/test/run/lint commands against `pyproject.toml` and CI. Resolve relative links. Flag contradictory instructions. Tag findings `content`. |
| **B Pipeline** | If `INCLUDE_PIPELINE=true`: map `python -m scripts.docs` entrypoints, MkDocs, CI docs jobs. Prove SoT → generator → validation → artifact. Run `verify` / `check-drift` / `check-links` as evidence. Exit 0 ≠ semantic correctness. Tag findings `pipeline`. |
| **C Plan** | Cluster: onboarding / API / ops / ADR / AI mirrors / generator / CI. Prefer restore-SSOT-link over rewriting prose. One root-cause per issue. |
| **D Issues** | Dedupe (`docs`, `documentation`). Create only if ALLOW_ISSUE_WRITE + PROVEN. Cap MAX_ISSUES_PER_ITERATION. |
| **E Fix** | Minimal doc/comment fixes. Regenerations only via `python -m scripts.docs <cmd>`. Do not reintroduce retired top-level `scripts/docs/*.py` shims. No root scratch. |
| **F Validate** | Re-check changed claims; sample links/commands; optional `build-site` if pipeline in scope. Delta: resolved / unchanged / regressed / new. |

`MODE=audit` stops after C. `audit+issues` after D. `full` through F.

## Focus checklist (each cycle)

- [ ] README purpose + bootstrap path still accurate
- [ ] Commands match `pyproject.toml` / CI workflows
- [ ] Relative links resolve under SCOPE
- [ ] Env vars documented by **name only** (no secret values)
- [ ] ADR/index entry points not orphaned
- [ ] AI mirrors do not redefine runtime (`.codex` / `.junie` win)
- [ ] `python -m scripts.docs verify` evidence recorded when pipeline in scope
- [ ] Generated tracked artifacts have no random timestamps
- [ ] Findings tagged `content` vs `pipeline`

## Stop

Secret in docs or generated output → P0 + stop leak. Empty SCOPE → STOP.
Do not publish or push docs from `MODE=audit`. Do not invent SLA/coverage
numbers. Orchestrator hard-stop applies.

## Success

- `findings.json` + `report.md` under `reports/audit-runs/<run_id>/`
- PROVEN command/link claims re-validated after fixes
- No new contradictory onboarding paths
- Pipeline contour has evidence commands, not “exit 0 therefore correct”

## Related

- One-shot: `prompt.audit.docs-content`, `prompt.audit.docs-pipeline`
- Planning: `prompt.docs.ai-audit-planning`
- Dual-agent: `prompt.audit.dual-agent-cycle` +
  `AUDIT_PROMPT_SOURCE=prompt.audit.docs-content`
- Closeout: `prompt.closeout.grok`
- Next in pack: `prompt.audit.cycle.diagrams`
