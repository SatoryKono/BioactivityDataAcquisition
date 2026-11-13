# JUNIE-RUNTIME.md — Runtime Map For BioETL Agents (JetBrains Junie)

This file is the JetBrains Junie equivalent of `.codex/agents/CODEX-RUNTIME.md`.
Junie and Codex are equal-peer tracked AI runtime trees for BioETL; runtime
behavior changes MUST be synchronized via
`scripts/ai/junie/check_junie_mirror.sh`.

## Canonical Sources

Available sources; load by **Context tiers** below, not as an always-on dump:

- `AGENTS.md`
- `.junie/guidelines.md`
- `.codex/agents/CODEX-RUNTIME.md` (equal-peer Codex runtime map)
- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## Repository authority

`AGENTS.md` owns precedence and permanent guardrails. This runtime adapter
and its profiles/skills cannot weaken them. Refer to the root Instruction
Scope matrix rather than maintaining a parallel priority list. Delegated
post-change policy and this runtime's Proof-or-Stop requirements both apply;
reference documents and native configuration presence cannot override them.

## Context tiers

The `AGENTS.md` Required AI Context table is the single task-class matrix.
Apply its source-reuse and memory-write rules before loading a role or wrapper;
this map does not define a second bootstrap table. V3/V4 retain the full package
and required pre-task. Hash-only work uses `BIOETL_AI_MEMORY_MODE=off`.

## Purpose

Map logical BioETL `py-*` profiles onto the native JetBrains Junie runtime
roles used in this repository. `scripts/ai/junie/check_junie_mirror.sh --check`
enforces `scripts/ai/junie/junie-mirror-contract.json`: py-\* profile SHA-256,
shared agent docs, and the skills tree. `JUNIE-RUNTIME.md` and
`CODEX-RUNTIME.md` are runtime-only maps and are **not** byte-compared; they
MUST keep identical logical profile mappings. Runtime-specific labels (Codex
`default`/`worker` vs Junie-native roles) MAY differ as declared in the
contract.

## Response Language

- By default, answer the user in Russian when the user writes in Russian.
- The GitHub review body and all inline review comments produced through
  `gh pr review` or an equivalent GitHub API **MUST** be written in Russian,
  regardless of the surrounding conversation language.
- Keep code, commands, file paths, identifiers, API field names, and other
  technical literals in their valid original form.

## Technical Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- This includes scorecard budgets, exemption limits, hotspot thresholds, hotspot family caps, and equivalent budget surfaces.

## Memory Provenance

Before invoking `python -m memory.tooling.workflow pre-task` or `post-task`,
identify the active runtime explicitly:

```bash
BIOETL_AI_RUNTIME=junie \
BIOETL_AI_AGENT=<active-profile-or-junie> \
BIOETL_AI_MODEL=<model-id-if-known> \
python -m memory.tooling.workflow <pre-task-or-post-task> ...
```

`BIOETL_AI_RUNTIME` and `BIOETL_AI_AGENT` MUST be non-empty. Set
`BIOETL_AI_MODEL` when the runtime exposes a stable model identifier; otherwise
omit it rather than guessing. Generated episodic records bind this actor
identity to repository, commit, branch, worktree, task, and source references.

## Governed Profiles

Hook discovery: `python scripts/ai/codex/doctor.py hooks --no-write --json`.
Exit 2 means installed capability is NOT_PROVEN. Discovery never runs hooks or
runtime commands. See `docs/05-operations/runbooks/ai-hook-compatibility.md` for
platform observations and vendor contracts; documentation alone cannot enable
a native adapter.

The table is a logical responsibility map, not a native registration receipt.
The byte-parity profile Markdown files do not declare vendor YAML metadata;
native custom-agent registration is NOT_PROVEN for the installed build. Until
qualified, the parent reads a selected guide and performs its responsibilities
directly without claiming a native agent was loaded. Keep the governed mirrors.
See `docs/05-operations/runbooks/ai-rules-loading.md` for version-bound evidence.
The logical profile set
MUST match the tracked `.codex/agents/py-*.md` and `.junie/agents/py-*.md`
inventories.

| Logical profile | Parent responsibility (not a native role name) | Default authority |
| --------------- | ---------------------------------------------- | ----------------- |
| `py-audit-bot`  | audit                                          | read-only         |
| `py-config-bot` | config remediation                             | workspace write   |
| `py-debug-bot`  | diagnosis                                      | read-only         |
| `py-doc-bot`    | documentation                                  | workspace write   |
| `py-plan-bot`   | planning                                       | read-only         |
| `py-test-bot`   | tests                                          | workspace write   |

## Common Task Routing

Use the smallest existing skill that matches the request:

| Request template                            | Mutation default                         | Route                                                      | Minimum validation                                 |
| ------------------------------------------- | ---------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------- |
| Diagnose without fixing                     | read-only                                | `py-debug-bot`                                             | reproduction and evidence only                     |
| Implement a focused fix                     | write in requested scope                 | direct implementation; `py-config-bot` when configs change | targeted lint/tests                                |
| Review the current diff                     | read-only                                | `py-audit-bot` (`review`)                                  | diff inspection; no external writes                |
| Diagnose CI failure                         | read-only                                | `py-debug-bot`                                             | reproduction, root cause, remediation guidance     |
| Implement diagnosed CI remediation          | write in requested scope                 | direct parent implementation                               | failed check plus targeted regression              |
| Hash-only / date-stamp / remote-main rebind | write generated artifacts only           | parent in the existing worktree; no extra `implementer`    | matching `--check` after `--update`                |
| Prepare a PR                                | branch/commit/push authorized by request | direct parent workflow                                     | repository quality gates for touched scope         |
| Audit architecture debt                     | read-only                                | `py-audit-bot` (`debt`)                                    | architecture/debt gates; budgets MUST NOT increase |

Templates do not broaden user authority. Diagnosis and review stay read-only
unless the user also asks for implementation. Load the selected skill and
relevant sources/tests; do not load every ADR or the whole repository by
default.

## Risk-Based Validation

| Tier | Typical scope                | Minimum checks                                                     |
| ---- | ---------------------------- | ------------------------------------------------------------------ |
| V1   | docs-only                    | targeted links/drift, cleanup-inventory `--check`, and mirror sync |
| V2   | focused Python/tooling       | targeted Ruff plus related unit tests                              |
| V3   | config/runtime contract      | schema/contract checks plus related tests                          |
| V4   | architecture or broad change | architecture gates, lint/type checks, and relevant broad tests     |

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

Use `.venv-win/Scripts/python.exe` on native Windows. In WSL/Linux prefer the
canonical dev interpreter `${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python`
(matching `scripts/engineering/dev/run_pytest.sh` / `run_mypy.sh`) and fall back
to `.venv/bin/python` only when that venv is absent. `ADMIT` is the only outcome that can qualify a
lifecycle transition at the policy-required trust tier. `DEGRADED` and `STOP`
must be reported with reasons and follow-up; unavailable evidence is never
pass. Optional vendor evaluators may add receipts but cannot override the core
verifier. EvidenceStore ingestion is a separate explicit operation and never
creates a waiver or `DecisionRecord`.

### Explicit local closeout fallback

When a native lifecycle adapter has not been qualified, use the existing
repository facade after assembling the canonical receipts:

```bash
<python> -B -m scripts.engineering.repo closeout \
  --runtime junie --task-id <task-id> --claim done \
  --bundle reports/quality/proof-or-stop/<run-id>/bundle.json
```

This explicit command is not native hook registration or proof of client
loading. It calls the canonical verifier with current-source checks, binds the
expected task/runtime/claim and local state, and caps local qualification at
`DEGRADED` (exit 3), even when bundle fields declare CI/independent trust.
Caller labels do not authenticate execution transport. `STOP`/`ERROR` exit 2;
an actual parent interruption is `USER_STOP`/130, never a done claim. A worker
exit 130 alone does not prove user interruption. Missing evidence, crashes,
timeouts and duplicate events cannot qualify completion.

Native adapters and OpenCode write paths remain disabled/unqualified. The
command runs no producers, agents, services or EvidenceStore ingestion and
does not promote the staged CI enforcement policy. Real CI acceptance remains
separate. See the [explicit closeout runbook](../../docs/05-operations/runbooks/ai-closeout-wrapper.md)
for supported arguments, limitations and rollback.

## Related Runtime Surfaces

- `.junie/guidelines.md` (root Junie contract)
- `.junie/agents/ORCHESTRATION.md`
- `.junie/agents/README.md`
- `.junie/skills/`
- `.codex/agents/CODEX-RUNTIME.md` (equal-peer Codex runtime map)
- `.codex/agents/ORCHESTRATION.md`
- `.codex/agents/README.md`
- `.codex/skills/`
- `scripts/ai/junie/check_junie_mirror.sh` (parity enforcement)
- `scripts/ai/junie/junie-mirror-contract.json` (parity contract)

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
