---
id: prompt.audit.docs-cycle
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
  - docs/00-project/ai/prompts/library/audit/docs-content.md
  - docs/00-project/ai/prompts/library/audit/docs-pipeline.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/00-map.md
anti_patterns:
  - Counting Markdown files instead of verifying procedures
  - Mixing docs-pipeline build failures into content audit without INCLUDE_PIPELINE
  - Empty form cycles
  - Inventing commands not in manifests/CI
tags: [audit, docs, cycle, content, operator]
summary: Cyclic documentation audit — content drift, commands, links, fix, re-verify
max_body_lines: 160
---

# Cyclic documentation audit

N-итерационный **аудит документации**: content, IA, freshness, reproducibility
of procedures. Domain method: `prompt.audit.docs-content`. Loop shell:
`prompt.audit.orchestrator`.

Build/MkDocs/publish pipeline → `prompt.audit.docs-pipeline` (default via
`INCLUDE_PIPELINE=true`).

Default **`N=1`**, **`MODE=full`**, **`INCLUDE_PIPELINE=true`**, все **`ALLOW_*=true`**.

## Params

| Param | Default |
| --- | --- |
| `N` | `1` |
| `SCOPE` | `README.md docs/` (narrow by area) |
| `MODE` | `full` (also: `audit` \| `audit+issues`) |
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

- Map: `docs/00-project/00-map.md`
- Normative: `docs/00-project/NORMATIVE_SOURCES.md`, `RULES.md`
- AI docs are **mirrors** unless ownership policy says otherwise (`AGENTS.md`)
- Drift tooling when present: `python -m scripts.docs check-drift` / project docs scripts
- Never put secret values from `.env` into docs

## Preflight

1. `git status --porcelain`; SHA; branch.
2. Confirm SCOPE paths exist; empty SCOPE → STOP.
3. `run_id = <UTC>-docs-cycle-<shortsha>`
4. Artifacts: `reports/audit-runs/<run_id>/`

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Audit** | Run `prompt.audit.docs-content` on SCOPE. Verify purpose, bootstrap, install/test/run commands vs manifests/CI, env vars (names only), links, ADR/index freshness, contradictions. If `INCLUDE_PIPELINE=true`, also run `prompt.audit.docs-pipeline` and tag findings `pipeline` vs `content`. |
| **B Plan** | Cluster by surface (onboarding / API / ops / ADR / AI mirrors). Prefer fixes that restore SSOT links over rewriting prose. |
| **C Issues** | Dedupe (`docs`, `documentation`). Create only if ALLOW_ISSUE_WRITE + PROVEN. |
| **D Fix** | Minimal doc/code-comment fixes; regenerate only when project commands exist; no root scratch. |
| **E Validate** | Re-check changed claims; link/command sample; optional docs build if pipeline in scope. |
| **F Post** | Delta: resolved / unchanged / regressed / new. |

## Focus checklist (each cycle)

- [ ] README purpose + bootstrap path still accurate
- [ ] Commands match `pyproject.toml` / CI workflows
- [ ] Relative links resolve under SCOPE
- [ ] Security/ops runbooks without stale dangerous steps
- [ ] ADR/index entry points not orphaned
- [ ] AI mirrors do not redefine runtime (precedence to `.codex`/`.junie`)

## Stop

Secret in docs → P0 + stop leak. Empty SCOPE → STOP. Budget increases N/A but
do not invent SLA/coverage numbers.

## Success

- `findings.json` + `report.md` under `reports/audit-runs/<run_id>/`
- PROVEN command/link claims re-validated after fixes
- No new contradictory onboarding paths

## Related

- Domain: `prompt.audit.docs-content`, `prompt.audit.docs-pipeline`
- Planning: `prompt.docs.ai-audit-planning`
- Dual-agent: `prompt.audit.dual-agent-cycle` +
  `AUDIT_PROMPT_SOURCE=prompt.audit.docs-content`
- Closeout: `prompt.closeout.grok`
