<!-- GENERATED full paste. Source id: prompt.audit.grok-cycle. Do not edit by hand. -->
<!-- Regenerate: python -m scripts.ai.prompts render prompt.audit.grok-cycle --param N=10 --param MODE=full --param LANGUAGE=ru -->

<!-- prompt-id: prompt.audit.grok-cycle version: 2.2.0 -->
<!-- included fragments -->
## Read (do not restate)

1. `AGENTS.md` (precedence, mirrors, env ban, debt budgets)
2. `docs/00-project/NORMATIVE_SOURCES.md`
3. Relevant accepted ADRs only as needed for SCOPE
4. `docs/00-project/ai/agents/guides/MEMORY_USAGE.md` when AI/memory surfaces are in SCOPE

## Git / safety

- Do not edit or delete others' uncommitted work
- No `reset --hard`, no force-push
- Never commit to `main`; use `fix/<slug>` (or worktree if main is dirty)
- Push feature branch only; open PR to `main`
- Prefer evidence-only close when product root cause is already fixed on origin/main

## Tech-debt budgets

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ** tech-debt / quality budgets, exemptions, hotspot
  thresholds, or family caps.
- Debt may only decrease or stay unchanged. Do not silence gates by raising limits.

## Env guardrail

- Do **not** create, edit, rename, move, overwrite, or delete any `.env` /
  `.env.*` file without **explicit per-task user approval**.
- Reading `.env` is permitted. Tokens and secrets must not appear in commits,
  reports, logs, or issue comments.

## Evidence contract

- Every claim needs file-level proof: path, symbol or line range, and
  command/snippet output when applicable.
- Mark `NOT_PROVEN` when evidence is missing; do not invent findings.
- Prefer current checkout + `origin/main` over memory or stale reports.

## Language

- Answer the operator in **Russian** by default when the session is in Russian.
- Keep code, commands, paths, identifiers, and API field names in their valid
  original form.

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

## Applied params

- ALLOW_CLOSE: true
- ALLOW_ISSUE_WRITE: true
- ALLOW_MERGE: false
- ALLOW_PUSH: true
- BASE_BRANCH: main
- DEPTH: full
- INCLUDE_PIPELINE: true
- LANGUAGE: ru
- MODE: full
- MONITORING: false
- N: 10
- REPO: SatoryKono/BioactivityDataAcquisition
- SCOPE: 
- WORK_BRANCH: fix/audit-project-<shortsha>
