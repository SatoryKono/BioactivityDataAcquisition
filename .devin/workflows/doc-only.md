# Doc-Only Workflow

## Purpose
Simplified workflow for documentation-only changes.

## When to Use
- Only documentation changes (docs/, README.md, etc.)
- No code changes
- No configuration changes
- No behavioral changes to the system

## Workflow Steps (2 steps vs 8)

### 1. py-doc-bot (documentation update)
```python
run_subagent(
    title="py-doc-bot documentation update",
    task="Follow .devin/agents/py-doc-bot/AGENT.md for documentation updates in docs/",
    profile="py-doc-bot",
    is_background=False
)
```

### 2. py-audit-bot targeted (audit_type=docs)
```python
run_subagent(
    title="py-audit-bot targeted docs audit",
    task="Follow .devin/agents/py-audit-bot/AGENT.md for targeted documentation audit (audit_type=docs)",
    profile="py-audit-bot",
    is_background=False
)
```

## Skipped Steps
- py-audit-bot baseline (not needed for doc changes)
- py-plan-bot (obvious doc changes, no planning needed)
- py-test-bot baseline/final (no code changes to test)
- orchestrator code (no code changes)
- py-config-bot (no config changes)
- py-audit-bot final (targeted audit sufficient)

## Time Savings
- **Full workflow:** ~30 minutes
- **Doc-only workflow:** ~8 minutes
- **Savings:** ~75% faster

## Usage
```bash
make devin-update-docs
```

## Example Scenario
**Issue:** Update README.md with new installation instructions

**Doc-Only Workflow:**
1. Run py-doc-bot to update README.md
2. Run targeted py-audit-bot for documentation audit

## Exit Criteria
- Documentation updated correctly
- No MUST findings from py-audit-bot
- Links and references are valid
- Documentation follows project style guide

## When NOT to Use
- Code changes included
- Configuration changes included
- Behavioral changes to the system
- API changes that require code updates

## Alternative Workflows
- **Code + doc changes:** Use full workflow from ORCHESTRATION.md
- **Config + doc changes:** Use config-only workflow
- **API doc changes:** Use full workflow (requires code changes)
