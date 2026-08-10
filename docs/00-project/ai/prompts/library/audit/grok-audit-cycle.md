---
id: prompt.audit.grok-cycle
version: 2.2.0
status: active
class: operator-paste
owner: BioETL Team
runtimes: [grok, codex, any]
params: [REPO, BASE, WORK_BRANCH, SCOPE, MODE, CYCLE_COUNT, AUDIT_MODE, REQUIRE_GH_TRACKING, LANGUAGE]
includes:
  - fragments/read-order.md
  - fragments/git-safety.md
  - fragments/debt-budget-ban.md
  - fragments/env-guardrail.md
  - fragments/evidence-contract.md
  - fragments/language-ru.md
related_ssot:
  - AGENTS.md
  - docs/00-project/NORMATIVE_SOURCES.md
  - docs/00-project/ai/agents/guides/MEMORY_USAGE.md
  - docs/00-project/ai/agents/guides/grok-operator-runbook.md
  - docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md
anti_patterns:
  - Nine simultaneous Principal roles
  - Full RULES/ADR dump in the prompt
  - CYCLE_COUNT=5 with mandatory empty cycles
  - 24-section mandatory report outline every time
  - Closing issues without code/evidence on origin/main
tags: [audit, grok, operator]
summary: One-cycle audit paste with severity, stop conditions, Windows/memory gates
max_body_lines: 140
---

# BioETL audit cycle

Default **one** full cycle per session. Raise to 2 only if explicitly requested.
Do not run empty cycles "for form".

## Params

| Param | Default |
| --- | --- |
| `REPO` | `SatoryKono/BioactivityDataAcquisition` |
| `BASE` | `main` |
| `WORK_BRANCH` | `fix/<audit-slug>` (never main) |
| `SCOPE` | surface list or theme |
| `MODE` | `audit` |
| `CYCLE_COUNT` | `1` |
| `AUDIT_MODE` | `full` \| `differential` |
| `REQUIRE_GH_TRACKING` | `true` |
| `LANGUAGE` | `ru` (code/ids/paths original) |

## Runtime (Grok / Windows)

- Windows: only `.\.venv-win\Scripts\python.exe` (never Linux `.venv` from Win)
- Actor: `BIOETL_AI_RUNTIME=grok`, `BIOETL_AI_AGENT=<role>`; set `BIOETL_AI_MODEL` when known
- Memory: `python -m memory.tooling.workflow pre-task ...` before substantial work; `post-task` at end
- Root scratch ban: no `_tmp_*.py`, no `nul`/`NUL` at repo root
- Large SCOPE → plan mode first, then execute
- MCP slim preferred; if MCP down → repo search / `gh` / local scripts and mark `DEGRADED_MCP`
- Do not restate full RULES/ADR; link only

## Stage 0 — Scope lock

- `full`: inventory only paths that **exist** under SCOPE in this checkout
- `differential`: delta vs `origin/BASE` intersected with SCOPE
- Empty/invalid SCOPE → STOP and ask operator

## Stage 1 — Findings

Each finding **must** have:

| Field | Rule |
| --- | --- |
| severity | `Critical` \| `High` \| `Medium` \| `Low` |
| path | existing file |
| symbol / lines | symbol or line range |
| claim | one assertion |
| evidence | test / command / snippet |
| status | `PROVEN` \| `NOT_PROVEN` |

Severity: **Critical** data loss / secret / determinism / wrong medallion write;
**High** layer-boundary or silent contract break / false-green tests;
**Medium** maintainability / missing tests on changed surface;
**Low** docs/naming without runtime risk.

No file-level proof → `NOT_PROVEN` (no issue).

## Stage 2 — GitHub tracking

If `REQUIRE_GH_TRACKING=true`:

- Search open issues before create (dedupe)
- One root cause or path-cluster → one issue
- GitHub API fail → `BLOCKED_GH`; keep findings local

## Stage 3 — Remediation

- Fix PROVEN in-scope items only; leave blocked open with blocker
- Focused tests/checks for the surface
- Post-change: `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- If `.codex/**` or `.junie/**` changed → `bash scripts/ai/junie/check_junie_mirror.sh --check`
- PR for product/docs deltas only

## Stop conditions

- `NO_ACTIONABLE_FINDINGS` → stop (do not invent work)
- `CYCLE_COUNT` exhausted → stop + summary
- Secret or destructive risk without approval → stop + ask

## Cycle closeout

| Finding | Severity | Issue | State | Commit/PR | Verification |
| --- | --- | --- | --- | --- | --- |

States: `FIXED` | `OPEN` | `BLOCKED` | `VERIFIED_ALREADY_RESOLVED` | `NOT_PROVEN` | `WONT_FIX_OUT_OF_SCOPE`
