# Config-Only Workflow

## Purpose
Simplified workflow for configuration-only changes.

## When to Use
- Only configuration changes (configs/)
- No code changes in src/
- No documentation changes (except config-related)
- No behavioral changes to the system logic

## Workflow Steps (4 steps vs 8)

### 1. py-audit-bot targeted (audit_type=config)
```python
run_subagent(
    title="py-audit-bot targeted config audit",
    task="Follow .devin/agents/py-audit-bot/AGENT.md for targeted configuration audit (audit_type=config)",
    profile="py-audit-bot",
    is_background=False
)
```

### 2. py-plan-bot (plan)
```python
run_subagent(
    title="py-plan-bot config planning",
    task="Follow .devin/agents/py-plan-bot/AGENT.md for planning configuration changes",
    profile="py-plan-bot",
    is_background=False
)
```

### 3. py-config-bot (configuration change)
```python
run_subagent(
    title="py-config-bot configuration update",
    task="Follow .devin/agents/py-config-bot/AGENT.md for configuration changes in configs/",
    profile="py-config-bot",
    is_background=False
)
```

### 4. py-test-bot final (scope=config-related tests)
```python
run_subagent(
    title="py-test-bot final config tests",
    task="Follow .devin/agents/py-test-bot/AGENT.md for final tests on config-related scope",
    profile="py-test-bot",
    is_background=True
)
```

### 5. py-audit-bot final
```python
run_subagent(
    title="py-audit-bot final config audit",
    task="Follow .devin/agents/py-audit-bot/AGENT.md for final configuration audit",
    profile="py-audit-bot",
    is_background=False
)
```

## Skipped Steps
- py-audit-bot baseline (targeted audit sufficient)
- orchestrator code (no code changes)
- py-doc-bot (no doc changes except config-related)
- py-test-bot baseline (config changes don't need baseline)

## Time Savings
- **Full workflow:** ~30 minutes
- **Config-only workflow:** ~15 minutes
- **Savings:** ~50% faster

## Usage
```bash
make devin-audit-config
```

## Example Scenario
**Issue:** Update pipeline configuration for ChEMBL activity

**Config-Only Workflow:**
1. Run py-audit-bot targeted on configs/
2. Run py-plan-bot for config change planning
3. Run py-config-bot to update the configuration
4. Run py-test-bot final on config-related tests
5. Run py-audit-bot final for verification

## Exit Criteria
- Configuration updated correctly
- py-config-bot gap analysis shows 0 critical findings
- Config-related tests pass
- No MUST findings from py-audit-bot final
- Configuration follows project schema validation

## When NOT to Use
- Code changes in src/ included
- Documentation changes included (except config-related)
- Behavioral changes to system logic
- API changes that require code updates

## Alternative Workflows
- **Code + config changes:** Use full workflow from ORCHESTRATION.md
- **Doc + config changes:** Use full workflow
- **Complex config changes:** Use full workflow with py-plan-bot detailed planning
