---
id: prompt.session.grok-bootstrap
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes:
- grok
- any
params:
- TASK
- MODE
- SCOPE
- WORK_BRANCH
- LANGUAGE
includes:
- fragments/git-safety.md
- fragments/debt-budget-ban.md
- fragments/env-guardrail.md
- fragments/evidence-contract-v3.md
- fragments/language-ru.md
related_ssot:
- AGENTS.md
- docs/00-project/NORMATIVE_SOURCES.md
- docs/00-project/ai/agents/guides/MEMORY_USAGE.md
- docs/00-project/ai/agents/guides/grok-operator-runbook.md
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
- Full RULES/ADR dump in the paste
- Starting implement mode without SCOPE
- Skipping post-change validation after writes
tags:
- session
- grok
- bootstrap
- operator
summary: Short daily-work bootstrap for Grok sessions on BioETL
max_body_lines: 100
---
# BioETL — Grok session bootstrap

Short start card for everyday work. Not a substitute for audit/closeout cards.

## Params

| Param | Default |
| --- | --- |
| `TASK` | one-paragraph goal + Definition of Done |
| `MODE` | `implement` \| `audit` \| `closeout` \| `plan-only` |
| `SCOPE` | paths / issue ids / theme |
| `WORK_BRANCH` | `fix/<slug>` (never main) |
| `LANGUAGE` | `ru` (code/ids/paths original) |

## Mode routing

| MODE | Next action |
| --- | --- |
| `plan-only` | Explore + plan; no writes unless operator upgrades |
| `implement` | Plan if SCOPE is large/cross-layer, then edit + tests |
| `audit` | Prefer `prompt.audit.cycle` render |
| `closeout` | Prefer `prompt.closeout.grok` render |

## Runtime

- Windows: `.\.venv-win\Scripts\python.exe` only
- Actor: `BIOETL_AI_RUNTIME=grok`, `BIOETL_AI_AGENT=<role>` when recording memory
- Substantial work → memory `pre-task` / `post-task`
- MCP slim; degrade gracefully if MCP down (`DEGRADED_MCP`)
- Root scratch ban; no tech-debt budget growth; no `.env` mutation without approval

## Execution

1. Lock SCOPE and MODE; stop if SCOPE empty
2. Read only sources needed for SCOPE (do not restate RULES)
3. Prefer worktree when main is dirty
4. Implement or report with file-level evidence
5. Focused tests/checks for touched surface
6. Post-change validation; mirror parity if `.codex/**` / `.junie/**` changed.
   Markdown link or `Owner:` / `Status:` / `Class:` header changes require
   `python -m scripts.docs generate-cleanup-inventory --update` in the same
   changeset (`--check` reads the working tree, not HEAD).

## Done when

- [ ] DoD met with evidence (paths/commands)
- [ ] Focused tests green **or** `BLOCKED` with reason
- [ ] Post-change obligations for touched surfaces reported
