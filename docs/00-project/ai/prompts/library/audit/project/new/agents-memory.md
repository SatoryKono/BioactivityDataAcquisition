---
id: prompt.audit.project.new.agents-memory
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
  - CONTOURS
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
  - docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md
  - docs/00-project/ai/agents/guides/MEMORY_USAGE.md
  - src/memory/DAILY_WORKFLOW.md
  - .codex/agents
  - .junie/agents
  - docs/00-project/ai/prompts/library/audit/agents-runtime.md
  - docs/00-project/ai/prompts/library/audit/orchestrator.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Inventing REQ-* IDs not in REQUIREMENTS.md / the traceability CSV
  - Treating the Prompt Library as runtime SSOT
  - Ignoring .codex / .junie / .devin discovery
  - Fixing only a docs mirror without a runtime plan
  - Conversation dumps or secrets in memory handoffs
  - Empty form cycles
  - ALLOW_* true by library default
  - Auto-running destructive agent scripts
tags: [audit, agents, memory, runtime, scripts, cycle, operator]
summary: Improved cyclic agents/memory audit — runtime parity check, memory workflow, fail-closed ALLOW, early-stop
max_body_lines: 230
---

# Improved cyclic agents + memory audit

Улучшает `prompt.audit.cycle.agents-memory` + method
`prompt.audit.agents-runtime`. Runtime SSOT = `.codex/**` ≡ `.junie/**`
(+ `.devin/**` when present). Prompt Library — operator aid only.

Library defaults: **`ALLOW_*=false`**. Пустые циклы запрещены.

## Params

| Param | Default |
| --- | --- |
| `N` | `10` |
| `SCOPE` | `AGENTS.md .codex/ .junie/ .devin/ docs/00-project/ai/ scripts/ai/ src/memory/ scripts/memory/` |
| `MODE` | `full` (`audit` \| `audit+issues` \| `full`) |
| `LANGUAGE` | `ru` |
| `AUDIT_MODE` | `full` \| `differential` |
| `CONTOURS` | `runtime,scripts,memory` |
| `ALLOW_ISSUE_WRITE` | `false` |
| `ALLOW_PUSH` | `false` |
| `ALLOW_MERGE` | `false` |
| `ALLOW_CLOSE` | `false` |
| `MAX_ISSUES_PER_ITERATION` | `5` |
| `BASE_BRANCH` | `main` |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `WORK_BRANCH` | `fix/agents-memory-cycle-new-<shortsha>` |

## Anchors

- Parity: `bash scripts/ai/junie/check_junie_mirror.sh --check` (Windows: Git Bash / WSL)
- Memory: `python -m memory.tooling.workflow pre-task|post-task|smoke` (`PYTHONPATH=src`)
- Actor: `BIOETL_AI_RUNTIME`, `BIOETL_AI_AGENT` (optional `BIOETL_AI_MODEL`)
- PROVEN finding MUST have `requirement_id`
- Windows: `.\.venv-win\Scripts\python.exe`

## Preflight

1. `git status --porcelain`; SHA; branch. Чужой dirty → worktree.
2. SCOPE exists; empty → STOP.
3. `run_id = <UTC>-agents-new-<shortsha>`. Marker: `Cycle-run: <run_id>`.
4. Artifacts: `reports/audit-runs/<run_id>/`.

## Iteration i = 1..N

Run only contours in `CONTOURS`.

| Phase | Action |
| --- | --- |
| **A Runtime** | Inventory AGENTS.md, `.codex/agents|skills`, `.junie/**`, `.devin/**`, docs mirrors. Contradictions in commands/write vs read-only. **Must** record parity-check exit. |
| **B Scripts** | `scripts/ai/**`, `scripts/memory/**`: idempotency, dry-run for destructive ops, no `curl|bash`, no secrets on stdout. |
| **C Memory** | Catalog ↔ schema. Smoke workflow. No conversation dumps/secrets in notes. Vendor registry stays `NOT_PROVEN` without dated evidence. |
| **D Issues** | ALLOW_ISSUE_WRITE + PROVEN + `requirement_id`. Title `[agents][<REQ-id>][P#]`. Runtime-first; mirrors second. |
| **E Fix** | Edit runtime source first, then sync docs mirrors. Do not redefine runtime in `docs/00-project/ai/**`. |
| **F Validate** | Re-run parity check if `.codex`/`.junie` touched. Close only on `origin/main` if ALLOW_CLOSE. |

## Early-stop

`new_issues_i == 0` **и** `open_cycle_issues == 0` → STOP.
Два подряд цикла без новых PROVEN P0/P1 и без regression → STOP.

## Success

- Parity check recorded; Prompt Library not treated as SSOT
- Memory smoke/provenance evidence when memory contour is on
- No secrets in audit artifacts
