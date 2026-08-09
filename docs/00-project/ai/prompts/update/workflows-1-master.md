# Master Workflow

## Evaluation Metadata
- **Category:** Workflows
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** .devin/workflows/master.md

## Evaluation Breakdown
- Clarity: 8/10 (weight: 0.15)
- Completeness: 8/10 (weight: 0.15)
- Specificity: 9/10 (weight: 0.12)
- Context: 8/10 (weight: 0.10)
- Guardrails: 9/10 (weight: 0.10)
- Maintainability: 9/10 (weight: 0.08)
- Reusability: 9/10 (weight: 0.08)
- Error Handling: 9/10 (weight: 0.08)
- Validation: 9/10 (weight: 0.07)
- Documentation: 8/10 (weight: 0.07)

## Original Content

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

## Improved Sections

### Specificity Enhancements

#### Concrete Execution Commands
```bash
# Trigger post-change workflow for code changes
bash .devin/workflows/post-change.md --scope=src/** --trigger=code-change

# Trigger review workflow (optional)
bash .devin/workflows/review.md --scope=src/** --trigger=user_request

# Trigger pre-commit workflow (git hook only)
bash .devin/workflows/pre-commit.md --scope=src/** --trigger=git_hook

# Trigger qodo-sync workflow (AI rules only)
bash .devin/workflows/qodo-sync.md --scope=configs/** --trigger=ai_rules_change
```

#### Timeout Policies
- **post-change.md**: 300 seconds timeout for validation checks
- **review.md**: 180 seconds timeout for code review analysis
- **pre-commit.md**: 60 seconds timeout for pre-commit validation
- **qodo-sync.md**: 120 seconds timeout for Qodo synchronization

#### Retry Policies
- **post-change.md**: 3 retries with exponential backoff (1s, 2s, 4s) for transient failures
- **review.md**: 2 retries with 1s delay for analysis failures
- **pre-commit.md**: No retries (blocking failure)
- **qodo-sync.md**: 3 retries with 2s delay for sync failures

### Enhanced Guardrails

#### Integrity Guardrails
- **Workflow State Validation**: Verify workflow execution state before and after each step
- **Dependency Integrity**: Ensure all workflow dependencies are satisfied before execution
- **State Consistency**: Maintain consistent state across workflow executions
- **Atomic Operations**: Use atomic operations for critical state changes

#### Consistency Guardrails
- **Execution Order Enforcement**: Strict enforcement of workflow execution order
- **Conditional Logic Validation**: Validate conditional execution logic before application
- **Reporting Consistency**: Ensure consistent reporting format across all workflows
- **Error Message Standardization**: Use standardized error message formats

#### Access Control Guardrails
- **Workflow Authorization**: Verify user authorization for workflow execution
- **Scope Validation**: Validate change scope before workflow selection
- **Resource Access Control**: Enforce resource access controls for workflow operations
- **Audit Trail**: Maintain audit trail for all workflow executions

### Error Handling Improvements

#### Error Recovery Strategies
```yaml
error_recovery:
  post-change:
    strategy: "retry_with_rollback"
    max_retries: 3
    backoff: "exponential"
    rollback_on_failure: true
  
  review:
    strategy: "continue_with_warning"
    max_retries: 2
    backoff: "fixed"
    rollback_on_failure: false
  
  pre-commit:
    strategy: "fail_fast"
    max_retries: 0
    backoff: "none"
    rollback_on_failure: false
  
  qodo-sync:
    strategy: "retry_with_logging"
    max_retries: 3
    backoff: "fixed"
    rollback_on_failure: false
```

#### Fallback Procedures
- **post-change.md**: Fallback to manual validation if automated checks fail
- **review.md**: Fallback to manual code review if automated review fails
- **pre-commit.md**: No fallback (blocking failure)
- **qodo-sync.md**: Fallback to manual Qodo sync if automated sync fails

#### Graceful Degradation
- **Partial Success**: Allow partial success for non-critical workflows
- **Warning Mode**: Operate in warning mode for non-blocking failures
- **Best Effort**: Use best-effort execution for optional workflows
- **Degraded Functionality**: Maintain degraded functionality during failures

### Validation Enhancements

#### Validation Gates
```yaml
validation_gates:
  pre_execution:
    - validate_workflow_state
    - validate_dependencies
    - validate_authorization
    - validate_scope
  
  during_execution:
    - validate_step_completion
    - validate_state_consistency
    - validate_resource_usage
  
  post_execution:
    - validate_results
    - validate_reporting
    - validate_audit_trail
```

#### Self-Consistency Checks
- **Workflow State Consistency**: Verify workflow state is consistent across executions
- **Dependency Consistency**: Verify dependencies are consistent with workflow state
- **Reporting Consistency**: Verify reporting is consistent with execution results
- **Audit Trail Consistency**: Verify audit trail is consistent with execution history

#### Validation Procedures
1. **Pre-Execution Validation**: Validate workflow state, dependencies, authorization, and scope
2. **During-Execution Validation**: Validate step completion, state consistency, and resource usage
3. **Post-Execution Validation**: Validate results, reporting, and audit trail
4. **Cross-Workflow Validation**: Validate consistency across workflow executions

### Maintainability Improvements

#### Maintenance Guidelines
- **Monthly Review**: Review workflow execution logs monthly for optimization opportunities
- **Quarterly Audit**: Conduct quarterly audit of workflow configuration and dependencies
- **Annual Update**: Update workflow documentation and procedures annually
- **Continuous Monitoring**: Monitor workflow execution metrics continuously

#### Versioning Strategy
```yaml
versioning:
  format: "v{major}.{minor}.{patch}"
  major: "breaking changes"
  minor: "new features or significant improvements"
  patch: "bug fixes or minor improvements"
  
  current_version: "v2.0.0"
  release_schedule: "as_needed"
  backward_compatibility: "maintained_for_minor_and_patch"
```

#### Cleanup Procedures
- **Log Cleanup**: Clean up workflow execution logs older than 90 days
- **State Cleanup**: Clean up workflow state artifacts older than 30 days
- **Cache Cleanup**: Clean up workflow cache artifacts older than 7 days
- **Audit Trail Cleanup**: Archive audit trail records older than 1 year

### Reusability Improvements

#### Reusable Patterns
```yaml
reusable_patterns:
  workflow_execution:
    - trigger_detection
    - scope_validation
    - conditional_execution
    - error_handling
    - reporting
  
  workflow_coordination:
    - dependency_management
    - execution_order_enforcement
    - state_synchronization
    - conflict_resolution
```

#### Modular Components
- **Workflow Trigger Module**: Detect and validate workflow triggers
- **Scope Validation Module**: Validate change scope for workflow selection
- **Conditional Execution Module**: Execute workflows based on conditions
- **Error Handling Module**: Handle workflow errors with recovery strategies
- **Reporting Module**: Generate standardized workflow execution reports

#### Templates
```yaml
templates:
  workflow_definition:
    - metadata
    - triggers
    - execution_logic
    - error_handling
    - reporting
  
  workflow_report:
    - execution_summary
    - workflow_results
    - error_details
    - recommendations
```

#### Configuration Parameters
```yaml
configuration_parameters:
  timeouts:
    post-change: 300
    review: 180
    pre-commit: 60
    qodo-sync: 120
  
  retries:
    post-change: 3
    review: 2
    pre-commit: 0
    qodo-sync: 3
  
  backoff:
    post-change: "exponential"
    review: "fixed"
    pre-commit: "none"
    qodo-sync: "fixed"
```

### Documentation Improvements

#### Enhanced Documentation with Examples
```yaml
documentation_examples:
  workflow_execution:
    - code_change_example
    - doc_change_example
    - config_change_example
    - runtime_change_example
  
  error_handling:
    - post-change_failure_example
    - review_failure_example
    - pre-commit_failure_example
    - qodo-sync_failure_example
```

#### Templates and Guidelines
- **Workflow Definition Template**: Standard template for defining new workflows
- **Error Handling Guidelines**: Guidelines for implementing error handling
- **Reporting Guidelines**: Guidelines for generating workflow reports
- **Maintenance Guidelines**: Guidelines for maintaining workflows

#### Usage Examples
```bash
# Example: Execute post-change workflow for code changes
bash .devin/workflows/post-change.md \
  --scope=src/bioetl/pipelines/ \
  --trigger=code-change \
  --timeout=300 \
  --retries=3

# Example: Execute review workflow for code review
bash .devin/workflows/review.md \
  --scope=src/bioetl/pipelines/ \
  --trigger=user_request \
  --timeout=180 \
  --retries=2

# Example: Execute pre-commit workflow as git hook
bash .devin/workflows/pre-commit.md \
  --scope=src/bioetl/pipelines/ \
  --trigger=git_hook \
  --timeout=60 \
  --retries=0
```
