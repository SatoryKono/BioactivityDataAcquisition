# Devin Runtime Setup Guide for BioETL

## Overview

This guide explains how to use Devin CLI with the BioETL custom subagent profiles, which provide the same logical workflow as Codex runtime but adapted for Devin's architecture.

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
| `py-architecture-debt-bot` | parent | Architecture-debt reduction workflow | Foreground |
| `py-plan-bot` | parent | Task planning, RF-* decomposition | Foreground |
| `py-test-bot` | swe-1.6 | Tests (baseline/final/retest), coverage | Foreground/background |
| `py-config-bot` | swe-1.6 | YAML configs (pipeline/DQ/filter/composite) | Foreground |
| `py-debug-bot` | parent | RCA, bug fixes, regression debugging | Foreground |
| `py-doc-bot` | swe-1.6 | Docs, ADR, CHANGELOG, Mermaid diagrams | Foreground |
| `py-test-swarm` | parent | Hierarchical testing (L1→L2→L3) | Background |
| `py-review-orchestrator` | parent | Hierarchical code review (S1–S8) | Background |

## Usage Examples

### Starting a Task with py-audit-bot

```python
run_subagent(
    title="py-audit-bot baseline audit",
    task="Follow .devin/agents/py-audit-bot/AGENT.md for task_id=AUD-001, phase=baseline, scope=src/bioetl/application/.",
    profile="py-audit-bot",
    is_background=False
)
```

### Running Tests in Background

```python
run_subagent(
    title="py-test-bot final tests",
    task="Follow .devin/agents/py-test-bot/AGENT.md for task_id=TEST-001, phase=final, scope=src/bioetl/domain/.",
    profile="py-test-bot",
    is_background=True
)
```

### Planning with py-plan-bot

```python
run_subagent(
    title="py-plan-bot task planning",
    task="Follow .devin/agents/py-plan-bot/AGENT.md for task_id=PLAN-001, task_description='Implement new transformer for ChEMBL data'.",
    profile="py-plan-bot",
    is_background=False
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
- Hierarchical orchestration (py-test-swarm, py-review-orchestrator)

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
│   ├── py-architecture-debt-bot/
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
│   ├── py-test-swarm/
│   │   └── AGENT.md              # Hierarchical testing profile
│   └── py-review-orchestrator/
│       └── AGENT.md              # Code review orchestration profile
├── skills/
│   └── [BioETL skills catalog]
└── config.json                   # Devin configuration
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

The `.devin/config.json` file includes:
- MCP servers for external tools
- Organization settings
- Shell integration
- Comments referencing custom subagent profiles

## Troubleshooting

### Profile Not Found
If a custom profile is not available, fall back to built-in profiles:
- Use `subagent_explore` for read-only tasks
- Use `subagent_general` for general code changes

### Permission Denied
Background subagents cannot request new permissions. If a background subagent fails due to permissions:
1. Resume it in foreground mode
2. Grant the necessary permissions
3. Continue execution

### Model Selection
- `parent` model uses the same model as the parent agent
- `swe-1.6` is the default subagent model (cost-effective)
- Explicit model names can be set in AGENT.md frontmatter

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