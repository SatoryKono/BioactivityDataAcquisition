# Test Fix/Re-test Loop

## Evaluation Metadata
- **Category:** Test Prompts
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** docs/00-project/ai/prompts/test_fix_retest_loop.md

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

# Test Fix/Re-test Loop

*Статус: internal (working prompt artifact)*

> **Surface note:** Это рабочий промт, не каноническая политика проекта.
> Для реальных правил пользуйтесь `docs/00-project/RULES.md` и runtime
> guides under `docs/00-project/ai/agents/`.

## Prompt

```text
Цель: отлаживать и исправлять задачу до зелёного состояния тестов по циклу «run → fix → run».

## 1) Запусти тесты (целево, минимально)
- Если есть известная ошибка (failure) — прогоняю только затронутые тесты.
- Если падений нет, запускаю минимальный релевантный scope для текущей задачи.
- Запускаю подходящую команду для окружения:
  - Linux/WSL: `bash scripts/engineering/dev/run_pytest.sh <scope> --maxfail=1 -q`
  - Windows: `.\scripts\engineering\dev\run_pytest.ps1 <scope> --maxfail=1 -q`
  - fallback: `python -m pytest <scope> -q`
- В каждом прогоне фиксирую: команду, scope, статус, количество падений, первые ошибки.

## 2) Если ошибок нет — заверши
- Если все тесты пройдены (`exit code == 0`): зафиксируй результат и заверши задачу.
- Отчёт по шагу 2:
  - что именно тестировал;
  - итоговый статус;
  - фактический scope и команда.

## 3) Если есть ошибки — фиксишь и возвращаешься к шагу 1
- Разбираю root cause по первому приоритетному фейлу.
- Вношу минимально достаточное исправление (без расширения scope без нужды).
- Снова запускаю **тот же scope**.
- Повторяю цикл, пока:
  - получен green;
  - либо обнаружен блокер non-actionable (инфраструктурный/внешний фактор) с явной фиксацией,
    почему он не может быть исправлен в текущем контуре,
  - либо исчерпан лимит итераций (по умолчанию 5).

## 4) Условия остановки
- Завершай только когда:
  - все тесты зелёные; или
  - лимит итераций исчерпан с явной фиксацией блокеров и следующими шагами.
- В финале всегда указывай:
  - число итераций;
  - какие ошибки были и как исправлялись;
  - текущее состояние (`green / partially green / blocked`);
  - следующий шаг для ручного/внешнего блокера.
```

## Improved Sections

### Specificity Enhancements

#### Concrete Test Execution Commands
```bash
# Step 1: Run tests (targeted, minimal)
# Linux/WSL
bash scripts/engineering/dev/run_pytest.sh tests/bioetl/pipelines/chembl/test_activity.py::test_activity_transform --maxfail=1 -q

# Windows
.\scripts\engineering\dev\run_pytest.ps1 tests/bioetl/pipelines/chembl/test_activity.py::test_activity_transform --maxfail=1 -q

# Fallback
python -m pytest tests/bioetl/pipelines/chembl/test_activity.py::test_activity_transform --maxfail=1 -q

# With timeout
python -m pytest tests/bioetl/pipelines/chembl/test_activity.py::test_activity_transform --maxfail=1 -q --timeout=60
```

#### Timeout Policies
```yaml
test_execution_timeouts:
  unit_test: 60
  integration_test: 300
  e2e_test: 600
  architecture_test: 120
  default_timeout: 60
```

#### Retry Policies
```yaml
test_retry_policies:
  transient_failure:
    max_retries: 3
    backoff: "exponential"
    backoff_delay: [1, 2, 4]
  
  flaky_test:
    max_retries: 2
    backoff: "fixed"
    backoff_delay: 5
  
  infrastructure_failure:
    max_retries: 1
    backoff: "fixed"
    backoff_delay: 10
```

#### Iteration Limits
```yaml
iteration_limits:
  default: 5
  complex_fix: 10
  infrastructure_blocker: 3
  external_dependency: 2
```

### Enhanced Guardrails

#### Integrity Guardrails
- **Test Scope Integrity**: Verify test scope is consistent with task requirements
- **Test Execution Integrity**: Ensure test execution is deterministic and reproducible
- **Fix Integrity**: Verify fixes are minimal and sufficient
- **Root Cause Integrity**: Ensure root cause analysis is accurate and complete

#### Consistency Guardrails
- **Test Execution Consistency**: Ensure test execution is consistent across iterations
- **Fix Consistency**: Ensure fixes are consistent with codebase patterns
- **Reporting Consistency**: Ensure reporting is consistent across iterations
- **Iteration Consistency**: Ensure iteration limits are consistent with task complexity

#### Access Control Guardrails
- **Test Scope Access Control**: Verify access to test files before execution
- **Fix Access Control**: Verify access to source files before modification
- **Report Access Control**: Verify access to report output directory before generation
- **Log Access Control**: Verify access to log directory before logging

### Error Handling Improvements

#### Error Recovery Strategies
```yaml
error_recovery:
  test_execution:
    strategy: "retry_with_fallback"
    fallback: "manual_test_execution"
    max_retries: 3
  
  fix_application:
    strategy: "retry_with_rollback"
    fallback: "manual_fix"
    max_retries: 2
  
  root_cause_analysis:
    strategy: "retry_with_alternative"
    fallback: "manual_analysis"
    max_retries: 2
```

#### Fallback Procedures
- **Test Execution Fallback**: Manual test execution using direct pytest invocation
- **Fix Application Fallback**: Manual fix application using direct file editing
- **Root Cause Analysis Fallback**: Manual root cause analysis using direct debugging

#### Graceful Degradation
- **Partial Test Execution**: Allow partial test execution if full execution fails
- **Partial Fix**: Allow partial fix if full fix is not possible
- **Partial Root Cause Analysis**: Allow partial root cause analysis if full analysis is not possible
- **Warning Mode**: Operate in warning mode for non-critical failures

### Validation Enhancements

#### Validation Gates
```yaml
validation_gates:
  pre_test_execution:
    - validate_test_scope
    - validate_file_access
    - validate_environment
    - validate_dependencies
  
  during_test_execution:
    - validate_test_execution
    - validate_test_results
    - validate_error_messages
  
  post_test_execution:
    - validate_test_completeness
    - validate_fix_effectiveness
    - validate_root_cause_accuracy
    - validate_iteration_consistency
```

#### Self-Consistency Checks
- **Test Execution Consistency**: Verify test execution is consistent across iterations
- **Fix Consistency**: Verify fixes are consistent with codebase patterns
- **Root Cause Consistency**: Verify root cause analysis is consistent with error messages
- **Iteration Consistency**: Verify iteration limits are consistent with task complexity

#### Validation Procedures
1. **Pre-Test Execution Validation**: Validate test scope, file access, environment, and dependencies
2. **During-Test Execution Validation**: Validate test execution, test results, and error messages
3. **Post-Test Execution Validation**: Validate test completeness, fix effectiveness, root cause accuracy, and iteration consistency
4. **Cross-Iteration Validation**: Validate consistency across iterations

### Maintainability Improvements

#### Maintenance Guidelines
- **Weekly Review**: Review test execution procedures weekly for optimization opportunities
- **Monthly Audit**: Conduct monthly audit of test configuration and dependencies
- **Quarterly Update**: Update test documentation and procedures quarterly
- **Continuous Monitoring**: Monitor test execution metrics continuously

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
- **Test Log Cleanup**: Clean up test logs older than 30 days
- **Test Report Cleanup**: Archive test reports older than 1 year
- **Test Cache Cleanup**: Clean up test cache artifacts older than 7 days
- **Fix History Cleanup**: Archive fix history older than 1 year

### Reusability Improvements

#### Reusable Patterns
```yaml
reusable_patterns:
  test_execution:
    - targeted_test_execution
    - minimal_scope_selection
    - environment_detection
    - command_selection
  
  fix_application:
    - root_cause_analysis
    - minimal_fix_application
    - fix_validation
    - rollback_procedure
  
  iteration_management:
    - iteration_tracking
    - iteration_limit_enforcement
    - iteration_reporting
    - iteration_termination
```

#### Modular Components
- **Test Execution Module**: Execute tests with appropriate command and scope
- **Root Cause Analysis Module**: Analyze root cause of test failures
- **Fix Application Module**: Apply minimal and sufficient fixes
- **Iteration Management Module**: Manage iteration limits and reporting

#### Templates
```yaml
templates:
  test_execution:
    - test_scope
    - execution_command
    - timeout_policy
    - retry_policy
    - validation_procedure
  
  fix_application:
    - root_cause_analysis
    - fix_description
    - fix_validation
    - rollback_procedure
  
  iteration_report:
    - iteration_number
    - test_results
    - fix_applied
    - root_cause
    - next_steps
```

#### Configuration Parameters
```yaml
configuration_parameters:
  test_execution_timeouts:
    unit_test: 60
    integration_test: 300
    e2e_test: 600
    architecture_test: 120
  
  test_retry_policies:
    transient_failure: 3
    flaky_test: 2
    infrastructure_failure: 1
  
  iteration_limits:
    default: 5
    complex_fix: 10
    infrastructure_blocker: 3
    external_dependency: 2
```

### Documentation Improvements

#### Enhanced Documentation with Examples
```yaml
documentation_examples:
  test_execution:
    - unit_test_example
    - integration_test_example
    - e2e_test_example
    - architecture_test_example
  
  fix_application:
    - schema_fix_example
    - import_fix_example
    - logic_fix_example
    - infrastructure_fix_example
  
  iteration_management:
    - successful_iteration_example
    - blocked_iteration_example
    - exhausted_iteration_example
```

#### Templates and Guidelines
- **Test Execution Template**: Standard template for defining test execution procedures
- **Fix Application Guidelines**: Guidelines for applying minimal and sufficient fixes
- **Iteration Management Guidelines**: Guidelines for managing iteration limits and reporting
- **Reporting Guidelines**: Guidelines for generating iteration reports

#### Usage Examples
```bash
# Example: Execute unit test with fix/retest loop
bash scripts/engineering/dev/run_pytest.sh tests/bioetl/pipelines/chembl/test_activity.py::test_activity_transform --maxfail=1 -q --iterations=5

# Example: Execute integration test with fix/retest loop
bash scripts/engineering/dev/run_pytest.sh tests/bioetl/pipelines/chembl/test_activity.py -m integration --maxfail=1 -q --iterations=10

# Example: Execute architecture test with fix/retest loop
bash scripts/engineering/dev/run_pytest.sh tests/architecture/ --maxfail=1 -q --iterations=5
```
