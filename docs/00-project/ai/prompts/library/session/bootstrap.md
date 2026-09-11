---
id: prompt.session.grok-bootstrap
version: 1.2.0
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
- fragments/generated-artifact-ci.md
related_ssot:
- AGENTS.md
- docs/00-project/NORMATIVE_SOURCES.md
- docs/00-project/ai/agents/guides/MEMORY_USAGE.md
- docs/00-project/ai/agents/guides/grok-operator-runbook.md
- docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
- docs/05-operations/runbooks/generated-artifact-drift-workflow.md
anti_patterns:
- Full RULES/ADR dump in the paste
- Starting implement mode without SCOPE
- Skipping post-change validation after writes
- One SHA copied between telemetry and test-governance
- lowercase git-style `merge origin/main` (use `merge(main): include #<n> <topic>`)
- python -m scripts.engineering.qa.refresh_governance_artifacts for ci-rebind
- Extra worktree add for a branch already listed by `git worktree list`
tags:
- session
- grok
- bootstrap
- operator
summary: Short daily-work bootstrap for Grok sessions on BioETL (MODE includes ci-rebind)
max_body_lines: 160
---
# BioETL — Grok session bootstrap

Short start card for everyday work. Not a substitute for audit/closeout cards.

## Params

| Param | Default |
| --- | --- |
| `TASK` | one-paragraph goal + Definition of Done |
| `MODE` | `implement` \| `audit` \| `closeout` \| `plan-only` \| `ci-rebind` |
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
| `ci-rebind` | Hash-only generated-artifact families; steps below |

## Runtime

- Windows: `.\.venv-win\Scripts\python.exe` only
- Actor: `BIOETL_AI_RUNTIME=grok`, `BIOETL_AI_AGENT=<role>` when recording memory
- Substantial work → memory `pre-task` / `post-task`. Hash-only rebind,
  date-stamp, remote-main, and `ci-rebind`: `BIOETL_AI_MEMORY_MODE=off` (skip RAG).
- MCP slim; degrade gracefully if MCP down (`DEGRADED_MCP`)
- Root scratch ban; no tech-debt budget growth; no `.env` mutation without approval

## Execution

1. Lock SCOPE and MODE; stop if SCOPE empty
2. Read only sources needed for SCOPE (do not restate RULES). Hash-only /
   date-stamp / remote-main / `ci-rebind` → drift runbook + reporter, not full RULES/ADR.
3. One task = one branch. Run `git worktree list`; if `WORK_BRANCH` is already
   mounted, `cd` that path. `git worktree add` only when the branch is missing.
   Abort foreign `MERGE_HEAD` / `CHERRY_PICK_HEAD`. Prune only `prunable`
   after operator confirmation.
4. Generated CI: classify family via the included fragment; do not guess SHA
5. Focused tests/`--check` for the touched surface (not full architecture-fast)
6. Post-change validation; mirror parity if `.codex/**` / `.junie/**` changed.
   Markdown link or `Owner:` / `Status:` / `Class:` header changes require
   `python -m scripts.docs generate-cleanup-inventory --update` in the same
   changeset (`--check` reads the working tree, not HEAD).

## MODE `ci-rebind`

1. Reuse the existing worktree of `WORK_BRANCH`; do not add a second copy
2. `BIOETL_AI_MEMORY_MODE=off`
3. `git fetch origin main` (never `--depth=1` onto `origin/main`)
4. Coupled (does **not** call `_ratchet_family_budgets`):

```text
python -m scripts.engineering.qa refresh-ci-drift-families --update --test-gov --flaky-fingerprint --evidence --remote-main --dataflow
```

5. Telemetry only if the tests tree changed; hasher args from the included fragment.
   Do not copy `source_tree_sha256` between telemetry and test-gov.
6. Module-coverage **measurements** only from a green `coverage-verify` candidate
   of this SHA. Never `report-module-coverage --allow-missing-coverage-xml` as a
   substitute; never a partial local `coverage.xml`. Canon: drift runbook.
7. Ban `python -m scripts.engineering.qa.refresh_governance_artifacts` for this MODE.
8. Commit `fix(ci): ...` or `merge(main): include #<n> <topic>` — not lowercase
   `merge origin/main`.

## Done when

- [ ] DoD met with evidence (paths/commands)
- [ ] Focused tests green **or** `BLOCKED` with reason
- [ ] Post-change obligations for touched surfaces reported
