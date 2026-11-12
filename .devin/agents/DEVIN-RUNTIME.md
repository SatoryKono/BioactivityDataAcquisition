# DEVIN-RUNTIME.md — Runtime Map For BioETL Agents (Devin CLI)

## Canonical Sources

Available sources; load by **Context tiers** below, not as an always-on dump:

- `AGENTS.md`
- `.devin/agents/DEVIN-RUNTIME.md`
- `.codex/agents/CODEX-RUNTIME.md` (reference for logical profile definitions)
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

Map logical BioETL `py-*` profiles onto the Devin CLI runtime roles using custom subagent profiles. This document provides the Devin-specific adaptation of the Codex runtime mapping.

## Canonical Launch

Hook discovery: `python scripts/ai/codex/doctor.py hooks --no-write --json`.
Exit 2 means installed capability is NOT_PROVEN. Discovery never runs hooks or
runtime commands. See `docs/05-operations/runbooks/ai-hook-compatibility.md` for
platform observations and vendor contracts; documentation alone cannot enable
a native adapter.

Run Devin from the repository root. These are declared sources, not proof
that every file is loaded at startup: `AGENTS.md`, `.devin/config.json`,
`.devin/mcp_config.json`, `.devin/agents/**`, and `.devin/skills/**`.
Verify resolver/discovery separately with `devin rules list`,
`devin rules show AGENTS` and `devin skills list --json`. These commands do
not prove model execution or child-process permission enforcement.
`make devin-check` is not a no-write loader probe: its prerequisite writes a
local MCP overlay. Follow `docs/05-operations/runbooks/ai-rules-loading.md`.
For the established launch workflow:

```bash
make devin-check
make devin
```

Start the daily shared MCP plane explicitly when the task needs MCP tools:

```bash
make devin-mcp-start
```

The default launch never starts Docker or optional monitoring. `make devin`
materializes only the gitignored `.devin/mcp_config.local.json` daily overlay
and then invokes the installed `devin` CLI.

Tracked `.devin/mcp_config.json` remains the **full** portable inventory (do
not slim that file without a `setup_mcp.py` review). The daily overlay
`.devin/mcp_config.local.json` is machine-local and **must** be the slim/stable
profile: no Grafana/Prometheus/neo4j in the default Devin day, and no MCP
`github` on `py-*` children. Do not commit `.devin/mcp_config.local.json`.

The logical `py-test-bot` tests-only write scope (including VCR cassettes)
is carried out by the authorized parent while native delegation is blocked.
Existing `src/**`, `configs/**`, `docs/**`, and Exec `gh` denials remain.

## Response Language

- By default, answer the user in Russian when the user writes in Russian.
- The GitHub review body and all inline review comments produced through
  `gh pr review` or an equivalent GitHub API **MUST** be written in Russian,
  regardless of the surrounding conversation language.
- Keep code, commands, file paths, identifiers, API field names, and other technical literals in their valid original form.

## Technical Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- This includes scorecard budgets, exemption limits, hotspot thresholds, hotspot family caps, and equivalent budget surfaces.

## Environment Configuration

Devin CLI and its MCP servers use tokens and parameters from the repository root `.env` file.
The `.env` file is machine-local and secret-bearing:

### MCP Server Configuration

MCP servers defined in `.devin/mcp_config.json` use environment variable expansion for secrets:

- `DEEPWIKI_API_KEY` / `DEEPWIKI_ORGANISATION_ID` - DeepWiki MCP server authentication
- `CONTEXT7_API_KEY` - Context7 MCP server
- `NEEDLE_API_KEY` - Needle MCP server
- `REF_TOOL_API_KEY` - Ref Tool MCP server
- Other MCP server tokens as configured in `.devin/mcp_config.json`

### Common Environment Variables

- `GITHUB_TOKEN` / `GITHUB_PERSONAL_ACCESS_TOKEN` - GitHub operations via MCP
- `OPENAI_API_KEY` - OpenAI API for LLM operations
- `BRAVE_API_KEY` - Brave Search API via MCP
- `DOCKER_API_KEY` / `DOCKER_USERNAME` - Docker Hub operations
- Provider API keys: `BIOETL_UNIPROT_API_KEY`, `BIOETL_OPENALEX_API_KEY`, etc.

### Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
- Если задача требует изменения `.env`, исполнитель должен остановиться и сначала запросить явное разрешение пользователя.

## Memory Provenance

Before invoking `python -m memory.tooling.workflow pre-task` or `post-task`,
identify the active runtime explicitly:

```bash
BIOETL_AI_RUNTIME=devin \
BIOETL_AI_AGENT=<active-profile-or-devin> \
BIOETL_AI_MODEL=<model-id-if-known> \
python -m memory.tooling.workflow <pre-task-or-post-task> ...
```

`BIOETL_AI_RUNTIME` and `BIOETL_AI_AGENT` MUST be non-empty. Set
`BIOETL_AI_MODEL` when Devin exposes a stable model identifier; otherwise omit
it rather than guessing. Generated episodic records bind this actor identity
to repository, commit, branch, worktree, task, and source references.

## Devin vs Codex Runtime Differences

| Aspect            | Codex Runtime                                      | Devin Runtime                                                                                                                                                                                                                                            |
| ----------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Agent spawning    | `spawn_agent(agent_type, message)`                 | `run_subagent(title, task, profile, is_background)`                                                                                                                                                                                                      |
| Built-in profiles | `default`, `explorer`, `worker`                    | `subagent_explore`, `subagent_general`                                                                                                                                                                                                                   |
| Custom profiles   | Native agent roles                                 | Custom subagent profiles in `.devin/agents/*/AGENT.md`                                                                                                                                                                                                   |
| Model assignment  | Inherit parent (no provider-specific model labels) | Inherits parent model or explicit `model:` field. Read-only profiles use `model: parent`; write profiles (`py-config-bot`, `py-doc-bot`, `py-test-bot`) may pin `model: swe-1.6` — the sanctioned Devin default subagent model. Other pins are forbidden |
| Execution modes   | Sequential/parallel                                | Foreground/background with permissions                                                                                                                                                                                                                   |
| Tool permissions  | Role-based                                         | Profile-based + session grants                                                                                                                                                                                                                           |

## Recommended Mapping

Logical `py-*` profiles → Devin custom subagent profiles:

| Logical Profile | Devin Profile   | Model                  | Tool Access                                                                                                                   | Execution Mode        |
| --------------- | --------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| `py-audit-bot`  | `py-audit-bot`  | Parent model           | Read/search declarations only (`read`, `grep`, `glob`); modes `baseline`/`final`/`targeted`/`review`/`debt`/`reproducibility` | Foreground            |
| `py-plan-bot`   | `py-plan-bot`   | Parent model           | Read-only                                                                                                                     | Foreground            |
| `py-debug-bot`  | `py-debug-bot`  | Parent model           | Read-only (reproduce/isolate/guidance; no `src/` or `tests/` writes)                                                          | Foreground            |
| `py-config-bot` | `py-config-bot` | Default subagent model | Read + write (`configs/`)                                                                                                     | Foreground            |
| `py-doc-bot`    | `py-doc-bot`    | Default subagent model | Read + write (`docs/`)                                                                                                        | Foreground            |
| `py-test-bot`   | `py-test-bot`   | Default subagent model | Read/search declarations only; parent executes tests and authorized `tests/**` writes                                         | Foreground/background |

## Permission boundary and qualification

Native delegation of restricted profiles is blocked until the selected
binary/version/platform demonstrates registration and effective tool limits.
This applies to `py-audit-bot`, `py-debug-bot`, `py-plan-bot`, and `py-test-bot`.
Until then, the authorized parent reads the matching Devin profile/skill and
performs scoped commands, test writes, and reports itself. Do not substitute
`subagent_general`, resume in foreground, or grant broader permissions as an
automatic fallback. Missing qualification is NOT_PROVEN, never sandbox PASS.

For the observed Devin `3000.11.3 (9c803229faa4)`, root resolution and skill
discovery were observed in the loading runbook; native custom-profile merge
and child-process enforcement were not. The current vendor permission contract
uses command prefixes for `Exec(...)`, file-tool scopes for `Write(...)`, and
restrictive profile `allowed-tools`. Skill `allowed-tools` has a different
auto-approval role; do not transfer that meaning to profiles. Legacy profile
`permissions` metadata is retained without claiming its interpretation.
The static checker accepts the governed block-list spelling and rejects
duplicate/ambiguous frontmatter keys; it does not emulate arbitrary YAML or
replace native permission qualification.

Project `.devin/config.json` keeps protected reads in `ask` only and denies
root/nested `.env*` file-tool writes. The root permits reading but this adapter
retains the additional prompt. There are no automatic Exec/Write grants;
ordinary commands and writes ask. These declarations cannot constrain arbitrary
shell children or guarantee absolute-path glob matching on every platform.
An approval for a command is not per-task approval to mutate `.env`.

Vendor config precedence is organization, session, project-local, project, user;
lists are combined and same-layer deny wins. File-path ask has no narrower-allow
exception; command/MCP specificity has its own rules. This vendor configuration
model is distinct from root repository instruction precedence. Active higher
layers and native enforcement must be inspected before qualification; do not
infer profile/parent composition from project config alone.

Windows OS isolation is unsupported in the current vendor contract. Project
settings cannot enable a sandbox. Git/Python/make or nested processes can write
outside `tests`; a filesystem-tool deny does not prove isolation of Exec.
The shared `scripts/engineering/repo/operation_guards.py` evaluates structured
protected mutations without executing them; it does not intercept shell tools.
Synthetic boundary tests use ordinary files and no real `.env` fixtures.

Sources: [permissions](https://docs.devin.ai/cli/reference/permissions),
[configuration precedence](https://docs.devin.ai/cli/reference/configuration/global-vs-local),
[subagent fields](https://docs.devin.ai/cli/subagents),
[sandbox](https://docs.devin.ai/cli/sandbox). These are current vendor contracts,
not a substitute for version-bound execution evidence. No adapter or service is
enabled by this change; the remaining native isolation result is NOT_PROVEN.

## Common Task Routing

Use the smallest existing skill that matches the request:

| Request template                   | Mutation default                         | Route                                                                  | Minimum validation                                 |
| ---------------------------------- | ---------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------- |
| Diagnose without fixing            | read-only                                | `py-debug-bot` (foreground)                                            | reproduction and evidence only                     |
| Implement a focused fix            | write in requested scope                 | direct implementation; `py-config-bot` when configs change             | targeted lint/tests                                |
| Review the current diff            | read-only                                | `py-audit-bot` (`review`; background when authorized)                  | diff inspection; no external writes                |
| Diagnose CI failure                | read-only                                | `py-debug-bot` (foreground)                                            | reproduction, root cause, remediation guidance     |
| Implement diagnosed CI remediation | write in requested scope                 | parent / orchestrator                                                  | failed checks plus targeted regression             |
| Prepare a PR                       | branch/commit/push authorized by request | parent PR workflow; optional external `create-pr` skill when installed | repository quality gates for touched scope         |
| Audit architecture debt            | read-only                                | `py-audit-bot` (foreground)                                            | architecture/debt gates; budgets MUST NOT increase |

`create-pr` is a user-installed capability, not a project-local skill. Discover
it before use; if unavailable, the authorized parent follows repository PR policy
directly. Review uses the project-local `py-audit-bot` route.

All restricted-profile routes in the table are logical parent-guide routes while the qualification block applies. Templates do not broaden user authority. Diagnosis and review stay read-only unless the user also asks for implementation. Load the selected skill and relevant sources/tests; do not load every ADR or the whole repository by default.

## Risk-Based Validation

| Tier | Typical scope                | Minimum checks                                                     |
| ---- | ---------------------------- | ------------------------------------------------------------------ |
| V1   | docs-only                    | targeted links/drift, cleanup-inventory `--check`, and mirror sync |
| V2   | focused Python/tooling       | targeted Ruff plus related unit tests                              |
| V3   | config/runtime contract      | schema/contract checks plus related tests                          |
| V4   | architecture or broad change | architecture gates, lint/type checks, and relevant broad tests     |

Every closeout reports checks run, skipped checks with exact reasons/follow-up, runtime/docs mirror status, and debt outcome (`improved`, `unchanged`, or `worsened`). A lower tier cannot bypass an applicable architecture, determinism, security, or technical-debt gate. `worsened` cannot be hidden by raising a budget or exemption limit.

## Proof-or-Stop Closeout

Agent prose is a claim, not lifecycle state. For every write-capable task, run
`python -m scripts.engineering.qa proof-or-stop plan` before closeout, capture
the existing validation reports as normalized receipts, then run
`proof-or-stop assemble` and `proof-or-stop verify`. Use
`.venv-win/Scripts/python.exe` on native Windows and `.venv/bin/python` in
WSL/Linux.

Only `ADMIT` at the policy-required trust tier can qualify `tested`, `reviewed`,
`done`, or `ready_to_merge`. `DEGRADED` and `STOP` remain non-qualified claims
and require explicit reasons/follow-up. Unavailable evidence is never pass.
Optional vendor evaluators can add evidence but cannot override the offline
core verifier. EvidenceStore ingestion is a separate, explicitly authorized
command and never creates a waiver or `DecisionRecord`.

### Explicit local closeout fallback

When a native lifecycle adapter has not been qualified, use the existing
repository facade after assembling the canonical receipts:

```bash
<python> -m scripts.engineering.repo closeout \
  --runtime devin --task-id <task-id> --claim done \
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

## Foreground vs Background Strategy

The qualification block above applies before choosing either mode. Neither
mode is an isolation mechanism or an automatic permission escalation route.

### Foreground Subagents

Use for:

- Tasks requiring user approval (file writes, config changes)
- Critical path work where parent needs immediate results
- Debugging sessions requiring interactive permission grants
- Architecture audits where findings need immediate review

### Background Subagents

Use for:

- Read-only research and exploration
- Long-running test suites
- Documentation generation
- Evidence collection campaigns
- Hierarchical orchestration (py-test-bot, py-audit-bot)

**Note:** Background subagents inherit already-granted permissions; unapproved tools are auto-denied.

## Related Runtime Surfaces

- `Makefile` (`devin`, `devin-check`, `devin-mcp-start` launch contracts)
- `.devin/config.json` (tracked project settings)
- `.devin/mcp_config.json` (tracked full shared MCP inventory)
- `.devin/agents/ORCHESTRATION.md` (Devin-specific orchestration workflow)
- `.devin/agents/README.md` (Devin agent catalog)
- `.codex/agents/CODEX-RUNTIME.md` (Codex reference mapping)
- `.codex/agents/ORCHESTRATION.md` (Codex orchestration reference)
- `.devin/skills/` (BioETL skills for Devin)

## Custom Subagent Profile Structure

Each custom subagent profile lives in `.devin/agents/<profile-name>/AGENT.md`:

```markdown
---
name: py-audit-bot
description: Baseline/final audit, code review, architecture guardian
model: parent  # inherit parent; do not pin a provider-specific model label
allowed-tools:
  - read
  - grep
  - glob
permissions:
  allow:
    - Read(**)
  deny:
    - write
    - edit
---

[Profile-specific system prompt and instructions]
```

Restricted profiles expose read/search declarations only. All command execution
(including Git, pytest, mypy, pdb and Python) and authorized test writes remain
with the parent until separately qualified. The legacy permission example
preserves denials; it is not proof of a supported profile merge mechanism.

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
