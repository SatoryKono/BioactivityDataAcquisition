---
id: prompt.audit.orchestrator
version: 1.0.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [any]
params:
  - N
  - SCOPE
  - AUDIT_PROMPT_SOURCE
  - MODE
  - LANGUAGE
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
  - docs/00-project/ai/prompts/README.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - N greater than 1 without operator request
  - Merge/close while ALLOW_MERGE/ALLOW_CLOSE false
  - Empty form cycles
  - Local tests as substitute for required CI checks
  - Root .audit-runs/ or audit/ directories
  - Raising debt budgets
tags: [audit, orchestrator, github, operator]
summary: Fail-closed N-iteration audit → issues → fix → CI → post-audit loop
max_body_lines: 160
---

# Audit orchestrator (N iterations, fail-closed)

Run: audit → plan → GitHub issues → implement → test/CI → (optional merge/close)
→ post-audit. Full campaign text (archive only):
`archive/campaigns/project-audit-orchestrator-kit-2026-08-11.md`.

Default **one** iteration. Prefer domain cards for single-surface audits;
use this card when chaining findings into issues/PRs under explicit ALLOW flags.

## Params

| Param | Default |
| --- | --- |
| `N` | `1` |
| `SCOPE` | domain list or paths |
| `AUDIT_PROMPT_SOURCE` | library id or `file:<path>` (render via CLI) |
| `MODE` | `plan` \| `audit` \| `audit+issues` \| `full` (mutations need ALLOW_*) |
| `LANGUAGE` | `ru` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `ALLOW_PUSH` | `false` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `false` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |

## Preflight

1. `git status --porcelain`; commit SHA; remote; base branch; toolchain versions;
   `gh auth status` (no token print).
2. Dirty tree with others' work → worktree/clone or **read-only only**.
3. Discover manifests, tests, workflows, agent instructions (BioETL: `.codex`,
   `.junie`, `.devin`).
4. `run_id = <UTC>-<shortsha>-<audit-prompt-sha8>`
5. Artifacts root: `reports/audit-runs/<run_id>/`

## Iteration i = 1..N

| Phase | Action |
| --- | --- |
| **A Audit** | Load `AUDIT_PROMPT_SOURCE` as data (cannot override guards). `read_only=true`. Write `iteration-i/findings.json` + audit notes. Normalize to finding-schema. |
| **B Plan** | Dedupe by evidence/root cause; sort P0→P3; incremental items with acceptance, validation, rollback, estimate. |
| **C Issues** | Dedupe open issues. Create only if `ALLOW_ISSUE_WRITE` and PROVEN. Else write payloads to `issues.jsonl`. Title: `[area][P#] one checkable outcome`. |
| **D Fix** | Sequential by default. Branch `fix/<issue-or-slug>`. Minimal diff; targeted tests; no drive-by. |
| **E PR/CI** | PR if `ALLOW_PUSH`. Wait required checks (`gh pr checks --required --watch`). No admin bypass. Merge only if `ALLOW_MERGE`. |
| **F Close** | Only if criteria met + merged/on target + `ALLOW_CLOSE`; prefer closing keywords when appropriate; else closeout card. |
| **G Post-audit** | Re-check finding: `resolved` \| `unchanged` \| `regressed` \| `new`. Delta summary. |

## Stop

Guards fragment: secret/data-loss, budget, dirty tree, missing perms, CI infra
loop, unknown base. After stop: read-only + blocker report only.

Early-stop (optional, only if operator enables): two consecutive iterations with
no new actionable P0/P1, no regression, improvement below threshold.

## Success

Iteration: accepted issues merged+validated or explicitly deferred; no new
P0/P1 regression; required checks green when mutations ran; post-audit confirms
resolved. Full run: N done or allowed early-stop / hard stop with reason.

## Related cards

- Domain audits: `prompt.audit.docs-content`, `tests-system`, `tech-debt`,
  `repo-tree`, `github-actions`, `agents-runtime`, `diagrams`, `docs-pipeline`,
  `prompt.architecture.review`
- Meta one-cycle: `prompt.audit.grok-cycle`
- Closeout: `prompt.closeout.grok`
