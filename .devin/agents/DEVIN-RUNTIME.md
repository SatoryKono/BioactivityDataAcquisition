# DEVIN-RUNTIME.md — Runtime Map For BioETL Agents (Devin CLI)

## Canonical Sources

Read before planning or editing:

- `docs/00-project/NORMATIVE_SOURCES.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`
- `AGENTS.md`
- `.codex/agents/CODEX-RUNTIME.md` (reference for logical profile definitions)

## Purpose

Map logical BioETL `py-*` profiles onto the Devin CLI runtime roles using custom subagent profiles. This document provides the Devin-specific adaptation of the Codex runtime mapping.

## Response Language

- By default, answer the user in Russian when the user writes in Russian.
- Keep code, commands, file paths, identifiers, API field names, and other technical literals in their valid original form.

## Technical Debt Guardrail

- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- This includes scorecard budgets, exemption limits, hotspot thresholds, hotspot family caps, and equivalent budget surfaces.

## Devin vs Codex Runtime Differences

| Aspect | Codex Runtime | Devin Runtime |
| ------ | ------------- | ------------- |
| Agent spawning | `spawn_agent(agent_type, message)` | `run_subagent(title, task, profile, is_background)` |
| Built-in profiles | `default`, `explorer`, `worker` | `subagent_explore`, `subagent_general` |
| Custom profiles | Native agent roles | Custom subagent profiles in `.devin/agents/*/AGENT.md` |
| Model assignment | Fixed per profile (opus/sonnet) | Inherits parent model or explicit `model:` field |
| Execution modes | Sequential/parallel | Foreground/background with permissions |
| Tool permissions | Role-based | Profile-based + session grants |

## Recommended Mapping

Logical `py-*` profiles → Devin custom subagent profiles:

| Logical Profile | Devin Profile | Model | Tool Access | Execution Mode |
| --------------- | ------------- | ----- | ----------- | -------------- |
| `py-audit-bot` | `py-audit-bot` | Parent model | Read-only (read, grep, glob, exec) | Foreground |
| `py-architecture-debt-bot` | `py-architecture-debt-bot` | Parent model | Read + limited write (reports/) | Foreground |
| `py-plan-bot` | `py-plan-bot` | Parent model | Read-only | Foreground |
| `py-test-bot` | `py-test-bot` | Default subagent model | Read + exec (tests) | Foreground/background |
| `py-config-bot` | `py-config-bot` | Default subagent model | Read + write (configs/) | Foreground |
| `py-debug-bot` | `py-debug-bot` | Parent model | Read + write (src/, tests/) | Foreground |
| `py-doc-bot` | `py-doc-bot` | Default subagent model | Read + write (docs/) | Foreground |
| `py-test-swarm` | `py-test-swarm` | Parent model | Read + exec + write (reports/) | Background |
| `py-review-orchestrator` | `py-review-orchestrator` | Parent model | Read-only | Background |

## Devin Subagent Invocation

### Standard Pattern

```python
run_subagent(
    title="py-audit-bot baseline audit",
    task="Follow .devin/agents/py-audit-bot/AGENT.md for task_id=AUD-001, phase=baseline, scope=src/bioetl/application/.",
    profile="py-audit-bot",
    is_background=False
)
```

### Built-in Profile Fallback

When custom profiles are not available, use built-in profiles:

```python
# For read-only exploration
run_subagent(
    title="Codebase exploration",
    task="Explore the architecture of X",
    profile="subagent_explore",
    is_background=True
)

# For general code changes
run_subagent(
    title="Implementation",
    task="Implement feature X",
    profile="subagent_general",
    is_background=False
)
```

## Common Task Routing

Use the smallest existing skill that matches the request:

| Request template | Mutation default | Route | Minimum validation |
| --- | --- | --- | --- |
| Diagnose without fixing | read-only | `py-debug-bot` (foreground) | reproduction and evidence only |
| Implement a focused fix | write in requested scope | direct implementation; `py-config-bot` when configs change | targeted lint/tests |
| Review the current diff | read-only | `py-review-orchestrator` (background) or `code-review` skill | diff inspection; no external writes |
| Investigate and fix CI | write only after root cause | GitHub CI workflow / `py-debug-bot` | failed checks plus targeted regression |
| Prepare a PR | branch/commit/push authorized by request | `create-pr` skill | repository quality gates for touched scope |
| Audit architecture debt | read-only | `py-architecture-debt-bot` (foreground) | architecture/debt gates; budgets MUST NOT increase |

Templates do not broaden user authority. Diagnosis and review stay read-only unless the user also asks for implementation. Load the selected skill and relevant sources/tests; do not load every ADR or the whole repository by default.

## Risk-Based Validation

| Tier | Typical scope | Minimum checks |
| --- | --- | --- |
| V1 | docs-only | targeted links/drift and mirror sync |
| V2 | focused Python/tooling | targeted Ruff plus related unit tests |
| V3 | config/runtime contract | schema/contract checks plus related tests |
| V4 | architecture or broad change | architecture gates, lint/type checks, and relevant broad tests |

Every closeout reports checks run, skipped checks with exact reasons/follow-up, runtime/docs mirror status, and debt outcome (`improved`, `unchanged`, or `worsened`). A lower tier cannot bypass an applicable architecture, determinism, security, or technical-debt gate. `worsened` cannot be hidden by raising a budget or exemption limit.

## Foreground vs Background Strategy

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
- Hierarchical orchestration (py-test-swarm, py-review-orchestrator)

**Note:** Background subagents inherit already-granted permissions; unapproved tools are auto-denied.

## Related Runtime Surfaces

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
model: parent  # or specific model like "claude-opus-4"
allowed-tools:
  - read
  - grep
  - glob
  - exec
permissions:
  allow:
    - Read(**)
    - Exec(git)
  deny:
    - write
    - edit
---

[Profile-specific system prompt and instructions]
```

## Env File Guardrail

- Любой `.env` файл (`.env`, `.env.*`) считается secret-bearing или machine-local surface.
- Agents and contributors **MUST NOT** create, edit, rename, move, overwrite, or delete any `.env` file without explicit per-task user approval.
