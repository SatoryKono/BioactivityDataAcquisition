# Quick Fix Workflow

## Purpose
Simplified workflow for single-file bug fixes with low risk.

## When to Use
- Error in 1-2 files
- Obvious fix with clear root cause
- Low risk to existing functionality
- No architectural changes required

## Workflow Steps (5 steps vs 8)

### 1. py-test-bot baseline (scope=1-2 files)
```python
run_subagent(
    title="py-test-bot baseline for quick fix",
    task="Follow .devin/agents/py-test-bot/AGENT.md for baseline tests on current scope (1-2 files only)",
    profile="py-test-bot",
    is_background=True  # Can run in background for speed
)
```

### 2. orchestrator fix (direct edits)
```python
# Direct edits by orchestrator
# Fix the identified bug in the affected files
```

### 3. py-test-bot final
```python
run_subagent(
    title="py-test-bot final for quick fix",
    task="Follow .devin/agents/py-test-bot/AGENT.md for final tests on the fixed scope",
    profile="py-test-bot",
    is_background=True
)
```

### 4. py-doc-bot (docstring only)
```python
run_subagent(
    title="py-doc-bot docstring update",
    task="Follow .devin/agents/py-doc-bot/AGENT.md for docstring updates only on changed functions/classes",
    profile="py-doc-bot",
    is_background=False
)
```

### 5. py-audit-bot targeted (audit_type=code)
```python
run_subagent(
    title="py-audit-bot targeted code audit",
    task="Follow .devin/agents/py-audit-bot/AGENT.md for targeted code audit on the fixed scope",
    profile="py-audit-bot",
    is_background=False
)
```

## Skipped Steps
- py-audit-bot baseline (not needed for simple fixes)
- py-plan-bot (obvious fix, no planning needed)
- py-audit-bot final (targeted audit sufficient)

## Time Savings
- **Full workflow:** ~30 minutes
- **Quick fix workflow:** ~12 minutes
- **Savings:** ~60% faster

## Usage
```bash
make devin-fix-bug
```

## Example Scenario
**Issue:** Null pointer exception in `src/bioetl/application/pipelines/chembl_activity.py`

**Quick Fix Workflow:**
1. Run py-test-bot baseline on the specific file
2. Fix the null pointer in the orchestrator
3. Run py-test-bot final to verify fix
4. Update docstrings for the fixed function
5. Run targeted py-audit-bot on the changed file

## Exit Criteria
- All tests pass
- Docstrings updated
- No MUST findings from py-audit-bot
- Bug is fixed and verified

## When NOT to Use
- Architectural changes required
- Multiple files affected
- Root cause unclear
- High risk to existing functionality
- Configuration changes needed

## Alternative Workflows
- **Complex bug:** Use full workflow from ORCHESTRATION.md
- **Config-related bug:** Use config-only workflow
- **Architecture bug:** Use py-audit-bot (debt profile) workflow
