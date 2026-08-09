# CODEX-RUNTIME.md — Runtime Map For BioETL Agents

## Canonical Sources

- Runtime contract and precedence: `AGENTS.md`
- Project rules: `docs/00-project/RULES.md`
- Requirements: `docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `docs/02-architecture/decisions`
- Normative source index: `docs/00-project/NORMATIVE_SOURCES.md`
- Memory policy: `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

Load only the role- and risk-relevant sources selected by those contracts.

## Purpose

Map logical BioETL `py-*` profiles onto the native Codex runtime roles used in this repository.

## Response Language

- By default, answer the user in Russian when the user writes in Russian.
- Keep code, commands, file paths, identifiers, API field names, and other technical literals in their valid original form.

## Technical Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- This includes scorecard budgets, exemption limits, hotspot thresholds, hotspot family caps, and equivalent budget surfaces.

## Memory Provenance

Before invoking `python -m memory.tooling.workflow pre-task` or `post-task`,
identify the active runtime explicitly:

```bash
BIOETL_AI_RUNTIME=codex \
BIOETL_AI_AGENT=<active-profile-or-codex> \
BIOETL_AI_MODEL=<model-id-if-known> \
python -m memory.tooling.workflow <pre-task-or-post-task> ...
```

`BIOETL_AI_RUNTIME` and `BIOETL_AI_AGENT` MUST be non-empty. Set
`BIOETL_AI_MODEL` when the runtime exposes a stable model identifier; otherwise
omit it rather than guessing. Generated episodic records bind this actor
identity to repository, commit, branch, worktree, task, and source references.

## Native Project Discovery

- `.codex/config.toml` contains portable trusted-project settings only.
- `.codex/agents/py-*.toml` exposes the six governed profiles to native Codex
  custom-agent discovery. Each thin descriptor routes to its matching Markdown
  profile, skill, and memory sheet; the parent model is inherited.
- `.codex/skills/**` is the sole project-local skill discovery and behavioral
  source.
- Validate these surfaces with
  `python3 scripts/ai/codex/doctor.py static --no-write`.

## Common Task Routing

Use the smallest existing skill that matches the request:

| Request template | Mutation default | Route | Minimum validation |
| --- | --- | --- | --- |
| Diagnose without fixing | read-only | `py-debug-bot` | reproduction and evidence only |
| Implement a focused fix | write in requested scope | direct implementation; `py-config-bot` when configs change | targeted lint/tests |
| Review the current diff | read-only | `py-audit-bot` (`review`) | diff inspection; no external writes |
| Diagnose CI failure | read-only | `py-debug-bot` | reproduction, root cause, remediation guidance |
| Implement diagnosed CI remediation | write in requested scope | direct parent implementation | failed check plus targeted regression |
| Prepare a PR | branch/commit/push authorized by request | direct parent workflow | repository quality gates for touched scope |
| Audit architecture debt | read-only | `py-audit-bot` (`debt`) | architecture/debt gates; budgets MUST NOT increase |

Templates do not broaden user authority. Diagnosis and review stay read-only
unless the user also asks for implementation. Load the selected skill and
relevant sources/tests; do not load every ADR or the whole repository by
default.

## Risk-Based Validation

| Tier | Typical scope | Minimum checks |
| --- | --- | --- |
| V1 | docs-only | targeted links/drift and mirror sync |
| V2 | focused Python/tooling | targeted Ruff plus related unit tests |
| V3 | config/runtime contract | schema/contract checks plus related tests |
| V4 | architecture or broad change | architecture gates, lint/type checks, and relevant broad tests |

Every closeout reports checks run, skipped checks with exact reasons/follow-up,
runtime/docs mirror status, and debt outcome (`improved`, `unchanged`, or
`worsened`). A lower tier cannot bypass an applicable architecture,
determinism, security, or technical-debt gate. `worsened` cannot be hidden by
raising a budget or exemption limit.

## Proof-or-Stop Closeout

Agent prose is a claim, not lifecycle state. For write-capable tasks, create a
source-bound closeout plan and, after the existing validation commands finish,
assemble and verify their normalized receipts:

```bash
<python> -m scripts.engineering.qa proof-or-stop plan \
  --task-id <task-id> --claim done --run-id <run-id>
<python> -m scripts.engineering.qa proof-or-stop assemble \
  --task-id <task-id> --claim done --run-id <run-id> \
  --actor <agent> --runtime <runtime> --trust-tier local_single_host \
  --receipt <receipt.json>
<python> -m scripts.engineering.qa proof-or-stop verify \
  --bundle reports/quality/proof-or-stop/<run-id>/bundle.json
```

Use `.venv-win/Scripts/python.exe` on native Windows and
`.venv/bin/python` in WSL/Linux. `ADMIT` is the only outcome that can qualify a
lifecycle transition at the policy-required trust tier. `DEGRADED` and `STOP`
must be reported with reasons and follow-up; unavailable evidence is never
pass. Optional vendor evaluators may add receipts but cannot override the core
verifier. EvidenceStore ingestion is a separate explicit operation and never
creates a waiver or `DecisionRecord`.

## Related Runtime Surfaces

- `.codex/agents/ORCHESTRATION.md`
- `.codex/agents/README.md`
- `.codex/config.toml`
- `.codex/agents/py-*.toml`
- `.codex/skills/`

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
