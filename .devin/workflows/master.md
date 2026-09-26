---
auto_execution_mode: 0
description: Master workflow for coordinating all BioETL Devin workflows with conditional execution and dependency management
---

Canonical BioETL governance references:
- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## Purpose

Master workflow that coordinates all Devin workflows (review, post-change, pre-commit, qodo-sync) with conditional execution based on task type and scope.

## Workflow Triggers

### 1. Code Changes (src/, tests/)
**Primary workflow:** `post-change.md`
**Secondary workflows:** `review.md` (if requested), `pre-commit.md` (if git hook)

**Execution order:**
1. `post-change.md` - mandatory validation
2. `review.md` - conditional (if user requests code review)
3. `pre-commit.md` - conditional (if running as git hook)

### 2. Documentation Changes (docs/)
**Primary workflow:** `post-change.md`
**Secondary workflows:** `review.md` (if requested)

**Execution order:**
1. `post-change.md` - mandatory validation
2. `review.md` - conditional (if user requests doc review)

### 3. Configuration Changes (configs/)
**Primary workflow:** `post-change.md`
**Secondary workflows:** `qodo-sync.md` (if AI rules affected)

**Execution order:**
1. `post-change.md` - mandatory validation
2. `qodo-sync.md` - conditional (if AI rules changed)

### 4. Runtime Changes (.devin/, .codex/)
**Primary workflow:** `post-change.md`
**Secondary workflows:** None

**Execution order:**
1. `post-change.md` - mandatory validation

## Conditional Execution Matrix

| Change Scope | post-change | review | pre-commit | qodo-sync |
|-------------|-------------|--------|------------|-----------|
| src/**       | ✅ Mandatory | ⚪ Optional | ⚪ Git hook only | ❌ Skip |
| tests/**     | ✅ Mandatory | ⚪ Optional | ⚪ Git hook only | ❌ Skip |
| docs/**      | ✅ Mandatory | ⚪ Optional | ❌ Skip | ❌ Skip |
| configs/**   | ✅ Mandatory | ❌ Skip | ❌ Skip | ⚪ If AI rules |
| .devin/**    | ✅ Mandatory | ❌ Skip | ❌ Skip | ❌ Skip |
| .codex/**    | ✅ Mandatory | ❌ Skip | ❌ Skip | ❌ Skip |

## Dependency Graph

```
master.md
├── post-change.md (always runs first)
│   ├── module-coverage-inventory.json refresh (if src/** changed)
│   ├── cursor/windsurf sync (if AI rules changed)
│   └── targeted validation (lint, tests, architecture)
├── review.md (conditional, parallel to post-change)
│   └── code review analysis
├── pre-commit.md (conditional, git hook only)
│   └── pre-commit validation
└── qodo-sync.md (conditional, if AI rules changed)
    └── Qodo rules synchronization
```

## Integration with Skills

### Skill → Workflow Routing

| Skill | Primary Workflow | Secondary Workflow |
|-------|-----------------|-------------------|
| py-audit-bot | review.md | post-change.md |
| py-debug-bot | post-change.md | review.md |
| py-config-bot | post-change.md | qodo-sync.md |
| py-doc-bot | post-change.md | review.md |
| py-test-bot | post-change.md | pre-commit.md |
| py-plan-bot | review.md | post-change.md |

## Error Handling

### Workflow Failure Strategy

1. **post-change.md failure:** BLOCKER - stop all workflows
2. **review.md failure:** WARNING - continue with other workflows
3. **pre-commit.md failure:** BLOCKER - stop git commit
4. **qodo-sync.md failure:** WARNING - log but continue

### Rollback Strategy

- If `post-change.md` fails, revert changes if possible
- If `review.md` fails, provide specific feedback for fixes
- If `pre-commit.md` fails, block commit with clear error message
- If `qodo-sync.md` fails, log warning and continue

## Monitoring and Reporting

### Success Criteria

- All mandatory workflows complete successfully
- Conditional workflows execute only when triggered
- No silent failures or skipped validations
- Clear reporting of workflow execution status

### Reporting Format

```yaml
workflow_execution:
  timestamp: "YYYY-MM-DD HH:MM"
  trigger: "code-change|doc-change|config-change|runtime-change"
  scope: "src/**|docs/**|configs/**|.devin/**|.codex/**"
  
  workflows:
    - name: "post-change"
      status: "success|failure|skipped"
      duration_ms: 1234
      checks_run: 5
      checks_passed: 5
      
    - name: "review"
      status: "success|failure|skipped"
      triggered_by: "user_request|auto"
      duration_ms: 567
      
    - name: "pre-commit"
      status: "success|failure|skipped"
      triggered_by: "git_hook"
      duration_ms: 890
      
    - name: "qodo-sync"
      status: "success|failure|skipped"
      triggered_by: "ai_rules_change"
      duration_ms: 234
      
  overall_status: "success|failure|partial_success"
  total_duration_ms: 2925
```

## Guardrails

- Never increase technical-debt budgets or widen linter/Sonar exclusions
- Never edit `.env` files without explicit per-task user approval
- Never expose secrets in code, docs, configs, tests, or logs
- Tracked `configs/**` YAML: placeholders / env refs only
- Always run `post-change.md` before any other workflow
- Respect workflow dependencies and execution order
- Provide clear error messages and actionable feedback

## Maintenance

### When to Update This Workflow

- Adding new workflows to the Devin configuration
- Changing workflow dependencies or execution order
- Modifying conditional execution logic
- Updating error handling strategies

### Version History

- v2.0 (2026-08-07): Initial master workflow with conditional execution
- Separated concerns: post-change (mandatory), review (optional), pre-commit (git hook), qodo-sync (AI rules)