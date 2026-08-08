# Devin CLI Optimization: Workflow Templates and Error Recovery

## Problem
Current Devin workflow system has usability issues:
- Full 8-step workflow is overkill for simple tasks (60% time waste)
- Profile selection requires reading ORCHESTRATION.md (~10 minutes)
- Error recovery between profiles is complex without clear guidance
- No simplified workflow templates for common scenarios
- No interactive profile selection helper

This creates unnecessary complexity and reduces productivity for routine tasks.

## Proposed Solution
Implement workflow optimization improvements to reduce complexity and improve error handling:

### 1. Simplified Workflow Templates
Create workflow templates for common scenarios in `.devin/workflows/`:

#### Quick-Fix Template (.devin/workflows/quick-fix.md)
```markdown
## Quick Fix Workflow
Для single-file bug fixes с низким риском:

**Когда использовать:** Ошибка в 1-2 файлах, очевидный fix, низкий риск

**Workflow (5 шагов vs 8):**
1. py-test-bot baseline (scope=1-2 files, foreground/background)
2. orchestrator fix (direct edits)
3. py-test-bot final (foreground/background)
4. py-doc-bot (docstring only, foreground)
5. py-audit-bot targeted (audit_type=code, foreground)

**Пропущенные шаги:** py-audit-bot baseline, py-plan-bot, py-audit-bot final

**Экономия времени:** ~60% vs полный workflow

**Использование:**
```bash
make devin-fix-bug
```
```

#### Doc-Only Template (.devin/workflows/doc-only.md)
```markdown
## Doc-Only Workflow
Для чистых изменений в документации:

**Когда использовать:** Только docs/, без code changes

**Workflow (2 шага vs 8):**
1. py-doc-bot (создание/обновление, foreground)
2. py-audit-bot targeted (audit_type=docs, foreground)

**Пропущенные шаги:** py-audit-bot baseline, py-plan-bot, py-test-bot baseline/final, orchestrator code, py-config-bot, py-audit-bot final

**Экономия времени:** ~75% vs полный workflow

**Использование:**
```bash
make devin-update-docs
```
```

#### Config-Only Template (.devin/workflows/config-only.md)
```markdown
## Config-Only Workflow
Для изменений только в конфигурации:

**Когда использовать:** Только configs/, без code changes

**Workflow (4 шаги vs 8):**
1. py-audit-bot targeted (audit_type=config, foreground)
2. py-plan-bot (plan, foreground)
3. py-config-bot (изменение configs, foreground)
4. py-test-bot final (scope=config-related tests, foreground/background)
5. py-audit-bot final (foreground)

**Пропущенные шаги:** py-audit-bot baseline, orchestrator code, py-doc-bot

**Экономия времени:** ~50% vs полный workflow

**Использование:**
```bash
make devin-audit-config
```
```

**Expected impact:** 60-75% faster for simple tasks

### 2. Interactive Profile Selection Guide
Add interactive profile selector to Makefile:

```makefile
.PHONY: devin-select-profile

devin-select-profile:
	@echo "Select profile based on task type:"
	@echo "  1) Bug fix              → py-debug-bot"
	@echo "  2) Feature addition     → py-plan-bot → orchestrator"
	@echo "  3) Config change        → py-config-bot"
	@echo "  4) Documentation        → py-doc-bot"
	@echo "  5) Testing              → py-test-bot"
	@echo "  6) Audit                → py-audit-bot"
	@echo "  7) Architecture debt    → py-audit-bot (debt profile)"
	@read -p "Select profile (1-7): " profile; \
	case $$profile in \
		1) echo "Using py-debug-bot for bug fix";; \
		2) echo "Using py-plan-bot for feature planning";; \
		3) echo "Using py-config-bot for config change";; \
		4) echo "Using py-doc-bot for documentation";; \
		5) echo "Using py-test-bot for testing";; \
		6) echo "Using py-audit-bot for audit";; \
		7) echo "Using py-audit-bot (debt) for architecture debt";; \
		*) echo "Invalid selection"; exit 1;; \
	esac
```

**Expected impact:** 80% faster profile selection (10 → 2 minutes)

### 3. Error Recovery Guide
Create comprehensive error recovery guide in `.devin/troubleshooting.md`:

```markdown
# .devin/troubleshooting.md
## Common Error Scenarios and Recovery

### py-test-bot fails
**Symptoms:** Test failures in reports/pytest/
**Recovery:**
1. Check test output: `cat reports/pytest/latest.log`
2. Identify FAIL-XXX reference
3. Run py-debug-bot with FAIL-XXX reference
4. Fix and retest

### py-audit-bot reports MUST findings
**Symptoms:** MUST findings in review_py-audit-bot_*.md
**Recovery:**
1. Review findings in review file
2. Address in priority order: MUST → SHOULD → MAY
3. Re-run py-audit-bot for verification

### Permission denied
**Symptoms:** "Permission denied" errors
**Recovery:**
1. Check .devin/config.json permissions
2. Use smart permission mode: `make devin DEVIN_ARGS='--permission-mode smart'`
3. Grant specific permissions as needed
4. Re-run task

### MCP server not available
**Symptoms:** "MCP server not available" errors
**Recovery:**
1. Check MCP status: `make devin-mcp-start`
2. Use minimal MCP plane: `make devin-mcp-start-minimal`
3. Restart specific server if needed
4. Re-run task

### Memory workflow fails
**Symptoms:** Memory workflow errors
**Recovery:**
1. Check memory status: `python -m memory.tooling.workflow status`
2. Re-run pre-task: `python -m memory.tooling.workflow pre-task --task-id <id> --title "<task>"`
3. Continue with task
4. Re-run post-task: `python -m memory.tooling.workflow post-task --task-id <id> --title "<task>" --summary "<result>"`
```

**Expected impact:** 67% faster error recovery (15 → 5 minutes)

### 4. Interactive Tutorial
Create interactive tutorial for new users:

```makefile
.PHONY: devin-tutorial

devin-tutorial:
	@echo "Devin Interactive Tutorial"
	@echo "Step 1: Run baseline audit"
	@read -p "Press Enter to continue..."
	@$(DEVIN) --prompt "Run py-audit-bot baseline on src/bioetl/application/"
	@echo "Step 2: Plan a simple change"
	@read -p "Press Enter to continue..."
	@$(DEVIN) --prompt "Run py-plan-bot for adding a new field to Activity schema"
	@echo "Step 3: Implement the change"
	@read -p "Press Enter to continue..."
	@$(DEVIN) --prompt "Implement the planned change using orchestrator"
	@echo "Step 4: Test the change"
	@read -p "Press Enter to continue..."
	@$(DEVIN) --prompt "Run py-test-bot final on the changed scope"
	@echo "Tutorial complete!"
```

**Expected impact:** 70% easier new user onboarding

## Scope
CLI / UX

## Alternatives considered
1. **Full workflow automation engine** - Higher effort, more complex implementation
2. **AI-powered profile recommendation** - Requires additional AI integration
3. **Web-based tutorial** - Outside current scope, requires infrastructure

## Implementation plan
- [ ] Create simplified workflow templates (quick-fix.md, doc-only.md, config-only.md)
- [ ] Add interactive profile selection guide to Makefile
- [ ] Create comprehensive error recovery guide
- [ ] Create interactive tutorial for new users
- [ ] Update DEVIN-SETUP-GUIDE.md with new workflows
- [ ] Test all workflow templates
- [ ] Test error recovery scenarios

## Expected outcomes
- **60-75% faster** simple tasks (workflow templates)
- **80% faster** profile selection (interactive guide)
- **67% faster** error recovery (troubleshooting guide)
- **70% easier** new user onboarding (interactive tutorial)

## Risk assessment
**Low to medium risk** - Workflow templates are guidance-only (not mandatory), error recovery guide is documentation-only. Interactive commands are additive without changing existing behavior.

## Related files
- `.devin/workflows/quick-fix.md` (new)
- `.devin/workflows/doc-only.md` (new)
- `.devin/workflows/config-only.md` (new)
- `.devin/troubleshooting.md` (new)
- `Makefile`
- `.devin/agents/ORCHESTRATION.md`
- `.devin/agents/DEVIN-SETUP-GUIDE.md`
