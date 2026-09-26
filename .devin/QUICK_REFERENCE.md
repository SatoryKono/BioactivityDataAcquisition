# Devin Quick Reference

## Common Tasks

### Bug Fix
```bash
make devin-fix-bug
```
**Workflow:** 5 steps vs 8 (60% faster)
- py-test-bot baseline (1-2 files)
- orchestrator fix
- py-test-bot final
- py-doc-bot (docstring only)
- py-audit-bot targeted

### Feature Addition
```bash
make devin-add-feature
```
**Workflow:** Full feature workflow
- py-plan-bot
- orchestrator implementation
- py-test-bot baseline+final
- py-doc-bot
- py-audit-bot final

### Documentation Update
```bash
make devin-update-docs
```
**Workflow:** 2 steps vs 8 (75% faster)
- py-doc-bot
- py-audit-bot targeted docs audit

### Config Audit
```bash
make devin-audit-config
```
**Workflow:** Config-focused audit
- py-audit-bot targeted on configs/
- py-config-bot gap analysis if needed

## Profile Selection

| Task Type | Profile | Description |
|-----------|---------|-------------|
| Bug fix | py-debug-bot | Debugging and fixing errors |
| Feature addition | py-plan-bot → orchestrator | Planning and implementation |
| Config change | py-config-bot | Configuration modifications |
| Documentation | py-doc-bot | Documentation updates |
| Testing | py-test-bot | Test execution and coverage |
| Audit | py-audit-bot | Code review and architecture checks |
| Architecture debt | py-audit-bot (debt profile) | Architecture debt reduction |

## Workflows

### Quick-Fix Workflow
**When:** Single-file bug fixes, low risk
**Steps:** 5 (vs 8 full workflow)
**Time savings:** ~60%
**Command:** `make devin-fix-bug`

### Doc-Only Workflow
**When:** Documentation-only changes
**Steps:** 2 (vs 8 full workflow)
**Time savings:** ~75%
**Command:** `make devin-update-docs`

### Config-Only Workflow
**When:** Configuration-only changes
**Steps:** 4 (vs 8 full workflow)
**Time savings:** ~50%
**Command:** `make devin-audit-config`

### Full Workflow
**When:** Complex changes requiring full validation
**Steps:** 8
**Command:** Follow ORCHESTRATION.md standard workflow

## Available Workflows

```bash
make devin-workflows
```

- `audit-documents` - Document audit workflow
- `deepwiki-regeneration` - DeepWiki update workflow
- `master` - Master workflow
- `post-change` - Post-change validation
- `pre-commit` - Pre-commit checks
- `qodo-sync` - Qodo sync workflow
- `review` - Code review workflow
- `shared-validation` - Shared validation workflow

## MCP Startup Profiles

### Minimal MCP Plane
```bash
make devin-mcp-start-minimal
```
**Servers:** memory, filesystem, fetch
**Startup time:** ~30 seconds
**Use for:** Simple tasks, local development

### Standard MCP Plane
```bash
make devin-mcp-start-standard
```
**Servers:** minimal + github, docker, brave-search
**Startup time:** ~1 minute
**Use for:** Standard development tasks

### Full MCP Plane
```bash
make devin-mcp-start-full
```
**Servers:** All 18 servers
**Startup time:** ~2 minutes
**Use for:** Complex tasks requiring all capabilities

## Basic Commands

```bash
# Start Devin with BioETL runtime
make devin

# Validate Devin configuration
make devin-check

# Start MCP servers (standard profile)
make devin-mcp-start

# List available workflows
make devin-workflows
```

## Error Recovery

### Test Failures
```bash
# Check test output
cat reports/pytest/latest.log

# Debug with py-debug-bot
run_subagent(title="debug FAIL-XXX", task="Follow .devin/agents/py-debug-bot/AGENT.md for FAIL-XXX", profile="py-debug-bot", is_background=False)
```

### Audit Findings
```bash
# Review findings
cat reports/*/review_py-audit-bot_*.md

# Address in priority: MUST → SHOULD → MAY
```

### Permission Issues
```bash
# Use smart permission mode
make devin DEVIN_ARGS='--permission-mode smart'
```

### MCP Server Issues
```bash
# Check MCP status
make devin-mcp-start

# Use minimal MCP plane
make devin-mcp-start-minimal
```

## Performance Tips

1. **Use minimal MCP plane** for simple tasks (75% faster startup)
2. **Use quick-fix shortcuts** for routine bug fixes (60% faster)
3. **Use workflow discovery** to find appropriate workflows (80% faster discovery)
4. **Profile selection guide** for choosing the right profile (80% faster selection)

## Documentation

- `.devin/agents/DEVIN-SETUP-GUIDE.md` - Setup and configuration
- `.devin/agents/ORCHESTRATION.md` - Workflow orchestration
- `.devin/agents/DEVIN-RUNTIME.md` - Runtime mapping
- `.devin/workflows/*.md` - Specific workflow documentation
- `.devin/troubleshooting.md` - Error recovery guide

## Getting Help

```bash
# Show all available commands
make help

# Check Devin status
make devin-check

# List workflows
make devin-workflows
```

## Memory Workflow

Before starting tasks, use the canonical memory workflow:

```bash
# Pre-task
python -m memory.tooling.workflow pre-task --task-id <id> --title "<task>"

# Post-task
python -m memory.tooling.workflow post-task --task-id <id> --title "<task>" --summary "<result>"
```

## Technical Debt Guardrails

**IMPORTANT:** All BioETL profiles enforce the technical debt guardrail:
- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.**
- Budgets may only shrink or stay unchanged
- Any attempt to increase limits is marked as a blocker
