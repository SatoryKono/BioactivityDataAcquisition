# Devin Runtime Setup Guide for BioETL

## Overview

This guide explains how to use Devin CLI with the BioETL custom subagent profiles, which provide the same logical workflow as Codex runtime but adapted for Devin's architecture.

## Quick Start

Use Devin CLI `v3000.3` or newer. From the repository root:

```bash
# One-time/current-session verification
make devin-check

# Optional: start the daily shared MCP plane before MCP-heavy work
make devin-mcp-start

# Start the interactive client
make devin
```

Pass CLI arguments through `DEVIN_ARGS`, for example:

```bash
make devin DEVIN_ARGS='--permission-mode smart'
```

`make devin` does not start Docker, monitoring, or the shared MCP plane. It
only refreshes the gitignored daily MCP override and starts `devin` from the
repository root, where the CLI discovers `AGENTS.md` and `.devin/**`.

## Key Differences from Codex

| Aspect | Codex | Devin |
|--------|-------|-------|
| **Agent Spawning** | `spawn_agent(agent_type, message)` | `run_subagent(title, task, profile, is_background)` |
| **Built-in Profiles** | `default`, `explorer`, `worker` | `subagent_explore`, `subagent_general` |
| **Custom Profiles** | Native agent roles | Custom subagent profiles in `.devin/agents/*/AGENT.md` |
| **Model Assignment** | Fixed per profile (opus/sonnet) | Inherits parent model or explicit `model:` field |
| **Execution Modes** | Sequential/parallel | Foreground/background with permissions |

## Custom Subagent Profiles

BioETL provides 9 custom subagent profiles in `.devin/agents/`:

| Profile | Model | Role | Execution Mode |
|---------|-------|------|----------------|
| `py-audit-bot` | parent | Baseline/final audit, code review, architecture guardian | Foreground |
| `py-audit-bot` | parent | Architecture-debt reduction workflow | Foreground |
| `py-plan-bot` | parent | Task planning, RF-* decomposition | Foreground |
| `py-test-bot` | swe-1.6 | Tests (baseline/final/retest), coverage | Foreground/background |
| `py-config-bot` | swe-1.6 | YAML configs (pipeline/DQ/filter/composite) | Foreground |
| `py-debug-bot` | parent | RCA, bug fixes, regression debugging | Foreground |
| `py-doc-bot` | swe-1.6 | Docs, ADR, CHANGELOG, Mermaid diagrams | Foreground |
| `py-test-bot` | parent | Hierarchical testing (L1→L2→L3) | Background |
| `py-audit-bot` | parent | Hierarchical code review (S1–S8) | Background |

## Usage Examples

### Starting a Task with py-audit-bot

```python
run_subagent(
    title="py-audit-bot baseline audit",
    task="Follow .devin/agents/py-audit-bot/AGENT.md for task_id=AUD-001, phase=baseline, scope=src/bioetl/application/.",
    profile="py-audit-bot",
    is_background=False,
)
```

### Running Tests in Background

```python
run_subagent(
    title="py-test-bot final tests",
    task="Follow .devin/agents/py-test-bot/AGENT.md for task_id=TEST-001, phase=final, scope=src/bioetl/domain/.",
    profile="py-test-bot",
    is_background=True,
)
```

### Planning with py-plan-bot

```python
run_subagent(
    title="py-plan-bot task planning",
    task="Follow .devin/agents/py-plan-bot/AGENT.md for task_id=PLAN-001, task_description='Implement new transformer for ChEMBL data'.",
    profile="py-plan-bot",
    is_background=False,
)
```

## Standard Workflow

The standard BioETL workflow in Devin follows this pattern:

1. **Baseline Audit** → `py-audit-bot` (foreground)
2. **Planning** → `py-plan-bot` (foreground)
3. **Baseline Tests** → `py-test-bot` (foreground/background)
4. **Implementation** → orchestrator (direct edits)
5. **Config Changes** → `py-config-bot` (foreground) if needed
6. **Final Tests** → `py-test-bot` (foreground/background)
7. **Documentation** → `py-doc-bot` (foreground)
8. **Final Audit** → `py-audit-bot` (foreground)

## Foreground vs Background

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

## File Structure

```
.devin/
├── agents/
│   ├── DEVIN-RUNTIME.md          # Runtime mapping documentation
│   ├── ORCHESTRATION.md           # Workflow orchestration guide
│   ├── README.md                  # Agent catalog
│   ├── py-audit-bot/
│   │   └── AGENT.md              # Audit profile
│   ├── py-audit-bot/
│   │   └── AGENT.md              # Architecture debt profile
│   ├── py-plan-bot/
│   │   └── AGENT.md              # Planning profile
│   ├── py-test-bot/
│   │   └── AGENT.md              # Testing profile
│   ├── py-config-bot/
│   │   └── AGENT.md              # Configuration profile
│   ├── py-debug-bot/
│   │   └── AGENT.md              # Debugging profile
│   ├── py-doc-bot/
│   │   └── AGENT.md              # Documentation profile
│   ├── py-test-bot/
│   │   └── AGENT.md              # Hierarchical testing profile
│   └── py-audit-bot/
│       └── AGENT.md              # Code review orchestration profile
├── skills/
│   └── [BioETL skills catalog]
├── config.json                   # Tracked project settings
├── mcp_config.json               # Tracked shared MCP inventory
└── mcp_config.local.json         # Generated daily override (gitignored)
```

## Migration from Codex

If you're familiar with Codex runtime, here are the key changes:

1. **Invocation**: Replace `spawn_agent()` with `run_subagent()`
2. **Profiles**: Use custom profile names instead of agent types
3. **Models**: `parent` model inherits from parent agent, `swe-1.6` for cost-effective tasks
4. **Permissions**: Configure in AGENT.md frontmatter instead of role-based
5. **Execution**: Explicitly specify foreground/background mode

## Technical Debt Guardrail

**IMPORTANT**: All BioETL profiles enforce the technical debt guardrail:
- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- Budgets may only shrink or stay unchanged
- Any attempt to increase limits is marked as a blocker

## Configuration

Devin CLI `v3000.3+` splits project settings from MCP servers:

- `.devin/config.json` contains supported project settings (`permissions`,
  `read_config_from`, and optional hooks).
- `.devin/mcp_config.json` contains the tracked full shared HTTP inventory.
- `.devin/mcp_config.local.json` is generated by `make devin-setup`; it keeps
  daily servers available and marks optional servers disabled without changing
  the tracked inventory.

Secrets are never committed. Token-bearing HTTP headers use Devin's
`${env:VAR}` expansion and must be supplied through the environment or Devin
Secrets. The repository `.env` guardrail remains in force: Devin asks before
reading or writing any `.env*` file.

## Troubleshooting

### Profile Not Found
If a custom profile is not available, fall back to built-in profiles:
- Use `subagent_explore` for read-only tasks
- Use `subagent_general` for general code changes

### CLI or Configuration Not Found

Run `make devin-check`. Devin discovers the project root by walking up from the
current directory to `.git`; do not pass a repository config path manually.
If the CLI is missing or older than `v3000.3`, install or update it before using
the split `config.json` / `mcp_config.json` layout.

### Permission Denied
Background subagents cannot request new permissions. If a background subagent fails due to permissions:
1. Resume it in foreground mode
2. Grant the necessary permissions
3. Continue execution

### Model Selection
- `parent` model uses the same model as the parent agent
- `swe-1.6` is the default subagent model (cost-effective)
- Explicit model names can be set in AGENT.md frontmatter

### `No allowed model available`

First run:

```bash
devin auth status
devin models list
```

If both commands succeed but starting a session still reports
`No allowed model available`, project discovery is already complete and the
failure is in the Devin account/team model entitlement returned to the ACP
backend. Refresh the Devin login or correct the team's allowed/default model in
Devin, then retry `make devin`. Do not work around this by committing a personal
model or credential to repository config.

## Related Documentation

- `.devin/agents/DEVIN-RUNTIME.md` - Detailed runtime mapping
- `.devin/agents/ORCHESTRATION.md` - Workflow orchestration
- `.devin/agents/README.md` - Agent catalog
- `.codex/agents/CODEX-RUNTIME.md` - Codex reference (for comparison)
- `.codex/agents/ORCHESTRATION.md` - Codex workflow reference

## Support

For issues or questions:
1. Check the relevant AGENT.md file for profile-specific guidance
2. Consult ORCHESTRATION.md for workflow questions
3. Review DEVIN-RUNTIME.md for runtime mapping details
4. Refer to Codex documentation for logical profile definitions
