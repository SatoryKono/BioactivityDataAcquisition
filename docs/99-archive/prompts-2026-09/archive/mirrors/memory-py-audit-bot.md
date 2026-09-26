---
status: archived
class: mirror
note: Runtime snapshot only — not paste SSOT. Prefer .codex/** / .junie/** / .devin/**. Epic #8513 / #8517.
---

# Memory: py-audit-bot

## Evaluation Metadata
- **Category:** Memory Sheets
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** docs/00-project/ai/memory/memory-py-audit-bot.md

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

# Memory: py-audit-bot

Status: active navigational memory. Parent: `agent-memory.md`.

## Role reminder

- Sandbox: read-only.
- Output: evidence-led findings with `AUD-*` IDs, severity, governing source,
  exact location, verification, remediation, residual risk, and skipped checks.
- Behavior owner: `.codex/agents/py-audit-bot.md`.
- Entry skill: `.codex/skills/py-audit-bot/SKILL.md`.

## Navigation

- Architecture/import rules: current RULES, accepted ADRs, `.importlinter`, and
  `tests/architecture/`.
- Boundary reminder: direct `interfaces -> infrastructure` imports are
  forbidden; verify routing through Application or Composition APIs.
- Config/schema rules: owning configs, schemas, generators, and config tests.
- Docs/runtime parity: ownership policy, drift checks, and runtime mirror gate.
- Structural claims: `docs/reports/evidence/project-file-structure/`,
  `project-package-topology/`, and `governance-signals/` summaries.
- Debt semantics: `configs/quality/debt_scorecard.yaml` and
  `configs/quality/architecture_metric_exemptions.yaml`.

## Checklist

1. Establish current baseline and scope.
1. Verify blockers twice when feasible.
1. Separate valid-by-design, pre-existing, environment, and introduced issues.
1. Do not infer debt from counts alone or raise any budget/threshold.
1. Report `improved`, `unchanged`, or `worsened` debt outcome.

Do not duplicate the import matrix, scoring table, thresholds, or command
catalog here; read their current canonical owners.

## Improved Sections

### Specificity Enhancements

#### Concrete Audit Commands
```bash
# Step 1: Establish current baseline and scope
python -m scripts.engineering.qa run_architecture_audit_read_only --scope=src/bioetl/ --output=/tmp/audit-baseline.json

# Step 2: Verify blockers twice when feasible
python -m scripts.engineering.qa check_test_audit_preflight --baseline=/tmp/audit-baseline.json --repeat=2

# Step 3: Separate issue types
python -m scripts.engineering.qa report_test_governance_audit --input=/tmp/audit-findings.json --output=/tmp/audit-classified.json

# Step 4: Validate debt semantics
python -m scripts.engineering.qa check_quality_exemptions --input=/tmp/audit-classified.json --debt-config=configs/quality/debt_scorecard.yaml

# Step 5: Generate audit report
python -m scripts.engineering.qa report_debt_governance_gates --input=/tmp/audit-classified.json --output=/tmp/audit-report.md
```

#### Timeout Policies
```yaml
audit_timeouts:
  establish_baseline: 120
  verify_blockers: 60
  classify_issues: 30
  validate_debt: 30
  generate_report: 30
  total_audit_timeout: 270
```

#### Retry Policies
```yaml
audit_retry_policies:
  establish_baseline:
    max_retries: 3
    backoff: "exponential"
    backoff_delay: [2, 4, 8]
  
  verify_blockers:
    max_retries: 2
    backoff: "fixed"
    backoff_delay: 5
  
  classify_issues:
    max_retries: 2
    backoff: "fixed"
    backoff_delay: 2
  
  validate_debt:
    max_retries: 2
    backoff: "fixed"
    backoff_delay: 2
```

### Enhanced Guardrails

#### Integrity Guardrails
- **Audit Scope Integrity**: Verify audit scope is consistent with task requirements
- **Baseline Integrity**: Ensure baseline is accurate and representative
- **Blocker Verification Integrity**: Verify blocker verification is thorough and accurate
- **Issue Classification Integrity**: Ensure issue classification is accurate and consistent
- **Debt Validation Integrity**: Verify debt validation is consistent with debt semantics

#### Consistency Guardrails
- **Audit Consistency**: Ensure audit procedures are consistent across audit scopes
- **Baseline Consistency**: Ensure baseline is consistent with current checkout
- **Blocker Verification Consistency**: Ensure blocker verification is consistent across audits
- **Issue Classification Consistency**: Ensure issue classification is consistent with governing sources
- **Debt Validation Consistency**: Ensure debt validation is consistent with debt scorecard

#### Access Control Guardrails
- **Audit Scope Access Control**: Verify access to audit scope before audit execution
- **Baseline Access Control**: Verify access to baseline artifacts before verification
- **Issue Classification Access Control**: Verify access to issue classification data before validation
- **Debt Validation Access Control**: Verify access to debt configuration before validation
- **Report Generation Access Control**: Verify access to report output directory before generation

### Error Handling Improvements

#### Error Recovery Strategies
```yaml
error_recovery:
  establish_baseline:
    strategy: "retry_with_fallback"
    fallback: "manual_baseline"
    max_retries: 3
  
  verify_blockers:
    strategy: "retry_with_skip"
    fallback: "skip_non_critical_blockers"
    max_retries: 2
  
  classify_issues:
    strategy: "retry_with_partial"
    fallback: "partial_classification"
    max_retries: 2
  
  validate_debt:
    strategy: "retry_with_skip"
    fallback: "skip_debt_validation"
    max_retries: 2
```

#### Fallback Procedures
- **Baseline Fallback**: Manual baseline establishment using direct file inspection
- **Blocker Verification Fallback**: Skip non-critical blockers if critical blockers are verified
- **Issue Classification Fallback**: Partial issue classification if full classification fails
- **Debt Validation Fallback**: Skip debt validation if issue classification is successful

#### Graceful Degradation
- **Partial Baseline**: Allow partial baseline if full baseline fails
- **Partial Blocker Verification**: Allow partial blocker verification if full verification fails
- **Partial Issue Classification**: Allow partial issue classification if full classification fails
- **Partial Debt Validation**: Allow partial debt validation if full validation fails
- **Warning Mode**: Operate in warning mode for non-critical failures

### Validation Enhancements

#### Validation Gates
```yaml
validation_gates:
  pre_audit:
    - validate_audit_scope
    - validate_file_access
    - validate_environment
    - validate_dependencies
  
  during_audit:
    - validate_baseline_accuracy
    - validate_blocker_verification
    - validate_issue_classification
    - validate_debt_validation
  
  post_audit:
    - validate_audit_completeness
    - validate_report_accuracy
    - validate_debt_outcome
    - validate_audit_integrity
```

#### Self-Consistency Checks
- **Baseline Consistency**: Verify baseline is consistent with current checkout
- **Blocker Verification Consistency**: Verify blocker verification is consistent across verification runs
- **Issue Classification Consistency**: Verify issue classification is consistent with governing sources
- **Debt Validation Consistency**: Verify debt validation is consistent with debt scorecard
- **Report Consistency**: Verify report is consistent with audit findings

#### Validation Procedures
1. **Pre-Audit Validation**: Validate audit scope, file access, environment, and dependencies
2. **During-Audit Validation**: Validate baseline accuracy, blocker verification, issue classification, and debt validation
3. **Post-Audit Validation**: Validate audit completeness, report accuracy, debt outcome, and audit integrity
4. **Cross-Step Validation**: Validate consistency across audit steps

### Maintainability Improvements

#### Maintenance Guidelines
- **Weekly Review**: Review audit procedures weekly for optimization opportunities
- **Monthly Audit**: Conduct monthly audit of audit configuration and dependencies
- **Quarterly Update**: Update audit documentation and procedures quarterly
- **Continuous Monitoring**: Monitor audit execution metrics continuously

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
- **Baseline Cleanup**: Clean up baseline artifacts older than 30 days
- **Issue Classification Cleanup**: Clean up issue classification data older than 90 days
- **Report Cleanup**: Archive audit reports older than 1 year
- **Log Cleanup**: Clean up audit logs older than 30 days

### Reusability Improvements

#### Reusable Patterns
```yaml
reusable_patterns:
  audit:
    - baseline_establishment
    - blocker_verification
    - issue_classification
    - debt_validation
    - report_generation
  
  navigation:
    - architecture_import_rules
    - boundary_verification
    - config_schema_rules
    - docs_runtime_parity
    - structural_claims
    - debt_semantics
```

#### Modular Components
- **Baseline Module**: Establish audit baseline
- **Blocker Verification Module**: Verify blockers with double verification
- **Issue Classification Module**: Classify issues by type
- **Debt Validation Module**: Validate debt semantics
- **Report Generation Module**: Generate audit report

#### Templates
```yaml
templates:
  audit_procedure:
    - procedure_description
    - execution_command
    - timeout_policy
    - retry_policy
    - validation_procedure
    - error_handling
  
  audit_report:
    - audit_summary
    - baseline_details
    - blocker_verification
    - issue_classification
    - debt_validation
    - recommendations
```

#### Configuration Parameters
```yaml
configuration_parameters:
  audit_timeouts:
    establish_baseline: 120
    verify_blockers: 60
    classify_issues: 30
    validate_debt: 30
    generate_report: 30
  
  audit_retries:
    establish_baseline: 3
    verify_blockers: 2
    classify_issues: 2
    validate_debt: 2
```

### Documentation Improvements

#### Enhanced Documentation with Examples
```yaml
documentation_examples:
  audit:
    - architecture_audit_example
    - import_audit_example
    - config_audit_example
    - debt_audit_example
  
  issue_classification:
    - valid_by_design_example
    - pre_existing_example
    - environment_example
    - introduced_example
  
  debt_outcome:
    - improved_example
    - unchanged_example
    - worsened_example
```

#### Templates and Guidelines
- **Audit Procedure Template**: Standard template for defining audit procedures
- **Issue Classification Guidelines**: Guidelines for classifying issues
- **Debt Validation Guidelines**: Guidelines for validating debt semantics
- **Report Generation Guidelines**: Guidelines for generating audit reports

#### Usage Examples
```bash
# Example: Audit architecture/import rules
python -m scripts.engineering.qa run_architecture_audit_read_only --output=/tmp/architecture-audit.md

# Example: Audit config/schema rules
python -m scripts.engineering.qa check_semantic_registry_drift --output=/tmp/config-audit.md

# Example: Audit debt semantics
python -m scripts.engineering.qa check_quality_exemptions --output=/tmp/debt-audit.md

# Example: Full audit with all scopes
python -m scripts.engineering.qa report_debt_governance_gates --output=/tmp/full-audit.md
```
