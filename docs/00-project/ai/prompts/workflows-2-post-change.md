# Post-Change Workflow

## Evaluation Metadata
- **Category:** Workflows
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** .devin/workflows/post-change.md

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
description: Run BioETL post-change validation checklist after code edits (coordinated by master.md)
---

Canonical BioETL governance references:
- `AGENTS.md`
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/`
- `.devin/workflows/master.md` (coordinator)

Follow `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`.

## Master Workflow Integration

This workflow is coordinated by `master.md` which provides:
- Conditional execution based on change scope
- Dependency management between workflows
- Error handling and rollback strategy
- Centralized reporting

## Steps

1. **Determine change scope** (coordinated by master.md):
   - Detect changed files: `src/**`, `tests/**`, `docs/**`, `configs/**`, `.devin/**`, `.codex/**`
   - Apply conditional execution matrix from master.md

2. Re-scan impacted code, configs, docs, and tests

3. If `src/bioetl/**/*.py` changed: refresh `reports/quality/module-coverage-inventory.json` (`source_tree_sha256` MUST change)

4. If AI guidance rules changed under `docs/00-project/ai/rules/cursor/`:
   ```bash
   uv run python -m scripts.ai.sync.cursor --deploy
   uv run python -m scripts.ai.sync.windsurf
   ```

5. Keep Devin workflows in `.devin/workflows/` aligned with Windsurf Cascade workflows when review/post-change/pre-commit/qodo-sync guidance changes

6. **Run shared validation** (from `shared-validation.md`):
   - Architecture validation
   - Code quality validation
   - Secrets validation
   - Technical debt validation

7. Run targeted checks:
   - `make lint`
   - `make test-architecture` (when architecture boundaries touched)
   - relevant unit/integration tests for changed modules

8. Report: checks run, checks skipped, mirror-sync status (Cursor / Windsurf / Devin workflows)

9. Confirm no silent breaking changes to CLI/API/schema contracts

10. **Report to master.md** with execution status and results

## Conditional Execution

This workflow executes as MANDATORY for all change scopes per master.md matrix:
- `src/**`: ✅ Mandatory
- `tests/**`: ✅ Mandatory  
- `docs/**`: ✅ Mandatory
- `configs/**`: ✅ Mandatory
- `.devin/**`: ✅ Mandatory
- `.codex/**`: ✅ Mandatory

## Error Handling

- **BLOCKER failure**: Stop all workflows, report to master.md
- **Rollback**: Revert changes if possible
- **Reporting**: Provide clear error messages and actionable feedback

## Guardrails

- Never increase technical-debt budgets or widen linter/Sonar exclusions
- Never edit `.env` files without explicit per-task user approval
- Never expose secrets in code, docs, configs, tests, or logs
- Tracked `configs/**` YAML: placeholders / env refs only
- Always report execution status to master.md for coordination

## Improved Sections

### Specificity Enhancements

#### Concrete Execution Commands
```bash
# Step 1: Detect changed files
git diff --name-only HEAD~1 HEAD | grep -E '^(src|tests|docs|configs|\.devin|\.codex)/'

# Step 3: Refresh module coverage inventory (if src/bioetl/**/*.py changed)
python _refresh_module_coverage_inventory.py

# Step 4: Sync AI guidance rules (if docs/00-project/ai/rules/cursor/ changed)
uv run python -m scripts.ai.sync.cursor --deploy
uv run python -m scripts.ai.sync.windsurf

# Step 6: Run shared validation
bash .devin/workflows/shared-validation.md

# Step 7: Run targeted checks
make lint
make test-architecture
pytest tests/bioetl/pipelines/ -v

# Step 10: Report to master.md
echo "workflow_execution_status: success" | tee -a /tmp/post-change-report.log
```

#### Timeout Policies
```yaml
timeouts:
  step_1_scope_detection: 30
  step_2_rescan: 60
  step_3_module_coverage: 120
  step_4_ai_sync: 180
  step_5_workflow_alignment: 60
  step_6_shared_validation: 300
  step_7_targeted_checks: 240
  step_8_reporting: 30
  step_9_contract_validation: 60
  step_10_master_report: 30
  total_timeout: 1110
```

#### Retry Policies
```yaml
retry_policies:
  step_1_scope_detection:
    max_retries: 3
    backoff: "exponential"
    backoff_delay: [1, 2, 4]
  
  step_3_module_coverage:
    max_retries: 2
    backoff: "fixed"
    backoff_delay: 2
  
  step_4_ai_sync:
    max_retries: 3
    backoff: "exponential"
    backoff_delay: [2, 4, 8]
  
  step_6_shared_validation:
    max_retries: 2
    backoff: "fixed"
    backoff_delay: 5
  
  step_7_targeted_checks:
    max_retries: 3
    backoff: "exponential"
    backoff_delay: [3, 6, 12]
```

### Enhanced Guardrails

#### Integrity Guardrails
- **Change Scope Integrity**: Verify change scope detection accuracy before execution
- **Module Coverage Integrity**: Ensure `source_tree_sha256` changes when source code changes
- **AI Sync Integrity**: Verify AI guidance rules synchronization completeness
- **Workflow Alignment Integrity**: Ensure Devin workflows align with Windsurf Cascade workflows

#### Consistency Guardrails
- **Validation Consistency**: Ensure validation checks are consistent across change scopes
- **Reporting Consistency**: Ensure reporting format is consistent with master.md expectations
- **Contract Validation Consistency**: Ensure contract validation is consistent across all changes
- **Mirror Sync Consistency**: Ensure mirror synchronization is consistent across all runtime surfaces

#### Access Control Guardrails
- **Change Scope Access Control**: Verify access to changed files before validation
- **Module Coverage Access Control**: Verify access to module coverage inventory before refresh
- **AI Sync Access Control**: Verify access to AI guidance rules before synchronization
- **Workflow Alignment Access Control**: Verify access to workflow files before alignment

### Error Handling Improvements

#### Error Recovery Strategies
```yaml
error_recovery:
  step_1_scope_detection:
    strategy: "retry_with_fallback"
    fallback: "manual_scope_detection"
    max_retries: 3
  
  step_3_module_coverage:
    strategy: "retry_with_rollback"
    fallback: "manual_refresh"
    max_retries: 2
  
  step_4_ai_sync:
    strategy: "retry_with_partial_sync"
    fallback: "manual_sync"
    max_retries: 3
  
  step_6_shared_validation:
    strategy: "retry_with_skip"
    fallback: "targeted_validation_only"
    max_retries: 2
  
  step_7_targeted_checks:
    strategy: "retry_with_essential_only"
    fallback: "essential_checks_only"
    max_retries: 3
```

#### Fallback Procedures
- **Step 1 Fallback**: Manual change scope detection using git diff and manual inspection
- **Step 3 Fallback**: Manual module coverage inventory refresh using direct file manipulation
- **Step 4 Fallback**: Manual AI guidance rules synchronization using manual file copy
- **Step 6 Fallback**: Targeted validation only (skip non-essential validations)
- **Step 7 Fallback**: Essential checks only (skip non-essential checks)

#### Graceful Degradation
- **Partial Validation**: Allow partial validation if full validation fails
- **Partial Sync**: Allow partial AI sync if full sync fails
- **Essential Checks Only**: Run essential checks only if full checks fail
- **Warning Mode**: Operate in warning mode for non-critical failures

### Validation Enhancements

#### Validation Gates
```yaml
validation_gates:
  pre_execution:
    - validate_change_scope
    - validate_file_access
    - validate_environment
    - validate_dependencies
  
  during_execution:
    - validate_step_completion
    - validate_intermediate_results
    - validate_resource_usage
    - validate_state_consistency
  
  post_execution:
    - validate_final_results
    - validate_module_coverage
    - validate_ai_sync
    - validate_workflow_alignment
    - validate_contract_compatibility
```

#### Self-Consistency Checks
- **Change Scope Consistency**: Verify change scope is consistent with git diff results
- **Module Coverage Consistency**: Verify module coverage is consistent with source code changes
- **AI Sync Consistency**: Verify AI sync is consistent with AI guidance rules changes
- **Workflow Alignment Consistency**: Verify workflow alignment is consistent with Windsurf Cascade workflows
- **Contract Validation Consistency**: Verify contract validation is consistent across all changes

#### Validation Procedures
1. **Pre-Execution Validation**: Validate change scope, file access, environment, and dependencies
2. **During-Execution Validation**: Validate step completion, intermediate results, resource usage, and state consistency
3. **Post-Execution Validation**: Validate final results, module coverage, AI sync, workflow alignment, and contract compatibility
4. **Cross-Step Validation**: Validate consistency across workflow steps

### Maintainability Improvements

#### Maintenance Guidelines
- **Weekly Review**: Review workflow execution logs weekly for optimization opportunities
- **Monthly Audit**: Conduct monthly audit of workflow configuration and dependencies
- **Quarterly Update**: Update workflow documentation and procedures quarterly
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
- **Report Cleanup**: Archive workflow reports older than 1 year

### Reusability Improvements

#### Reusable Patterns
```yaml
reusable_patterns:
  change_detection:
    - git_diff_detection
    - scope_validation
    - file_access_validation
  
  validation:
    - shared_validation
    - targeted_validation
    - contract_validation
  
  synchronization:
    - ai_sync
    - workflow_alignment
    - mirror_sync
```

#### Modular Components
- **Change Detection Module**: Detect and validate change scope
- **Module Coverage Module**: Refresh module coverage inventory
- **AI Sync Module**: Synchronize AI guidance rules
- **Workflow Alignment Module**: Align Devin workflows with Windsurf Cascade workflows
- **Validation Module**: Run shared and targeted validation
- **Reporting Module**: Generate standardized workflow execution reports

#### Templates
```yaml
templates:
  workflow_step:
    - step_description
    - execution_command
    - timeout_policy
    - retry_policy
    - error_handling
    - validation_procedure
  
  workflow_report:
    - execution_summary
    - step_results
    - validation_results
    - error_details
    - recommendations
```

#### Configuration Parameters
```yaml
configuration_parameters:
  timeouts:
    step_1_scope_detection: 30
    step_2_rescan: 60
    step_3_module_coverage: 120
    step_4_ai_sync: 180
    step_5_workflow_alignment: 60
    step_6_shared_validation: 300
    step_7_targeted_checks: 240
    step_8_reporting: 30
    step_9_contract_validation: 60
    step_10_master_report: 30
  
  retries:
    step_1_scope_detection: 3
    step_3_module_coverage: 2
    step_4_ai_sync: 3
    step_6_shared_validation: 2
    step_7_targeted_checks: 3
```

### Documentation Improvements

#### Enhanced Documentation with Examples
```yaml
documentation_examples:
  change_detection:
    - src_change_example
    - tests_change_example
    - docs_change_example
    - configs_change_example
    - runtime_change_example
  
  validation:
    - architecture_validation_example
    - code_quality_validation_example
    - secrets_validation_example
    - technical_debt_validation_example
  
  synchronization:
    - ai_sync_example
    - workflow_alignment_example
    - mirror_sync_example
```

#### Templates and Guidelines
- **Workflow Step Template**: Standard template for defining workflow steps
- **Validation Guidelines**: Guidelines for implementing validation procedures
- **Synchronization Guidelines**: Guidelines for implementing synchronization procedures
- **Reporting Guidelines**: Guidelines for generating workflow reports

#### Usage Examples
```bash
# Example: Execute post-change workflow for code changes
bash .devin/workflows/post-change.md \
  --scope=src/bioetl/pipelines/ \
  --trigger=code-change \
  --timeout=1110 \
  --retries=3

# Example: Execute post-change workflow for documentation changes
bash .devin/workflows/post-change.md \
  --scope=docs/00-project/ai/ \
  --trigger=doc-change \
  --timeout=1110 \
  --retries=3

# Example: Execute post-change workflow for configuration changes
bash .devin/workflows/post-change.md \
  --scope=configs/quality/ \
  --trigger=config-change \
  --timeout=1110 \
  --retries=3
```
