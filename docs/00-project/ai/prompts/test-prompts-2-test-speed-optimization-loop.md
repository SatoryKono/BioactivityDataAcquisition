# Test Speed Optimization Loop

## Evaluation Metadata
- **Category:** Test Prompts
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** docs/00-project/ai/prompts/test_speed_optimization_loop.md

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

# Test Speed Optimization Loop

*Статус: internal (working prompt artifact)*

> **Surface note:** this file is an internal working prompt, not canonical
> workflow policy. For active project rules use `docs/00-project/RULES.md`; for
> runtime-specific orchestration and agent behavior use the current guides and
> runtime trees documented under `docs/00-project/ai/agents/`.

Цель: ускорить запуск тестов в репозитории BioETL минимум на 30% без снижения
надежности проверок.

## Prompt

```text
Задача: ускорить запуск тестов в репозитории BioETL минимум на 30% без снижения надежности проверок.

Контекст проекта:
- Используй только штатные команды и правила проекта из `AGENTS.md` / `AGENT.md`.
- Для mixed Windows + WSL checkout в WSL используй `bash scripts/engineering/dev/run_pytest.sh`, для CI/single-OS допускается `uv run python -m pytest`.
- В проекте pytest уже настроен с `pytest-xdist`, `pytest-timeout`, маркерами `unit`, `integration`, `e2e`, `architecture`, `benchmark`, `serial`, `slow`.
- Бенчмарки (`-m benchmark`) и `slow` по умолчанию исключены. Не сравнивай несопоставимые наборы тестов.
- Любые изменения не должны нарушать архитектурные ограничения и не должны ухудшать достоверность тестов ради скорости.

Что нужно сделать:
1. Изучи текущий тестовый контур проекта:
- `pyproject.toml`
- `tests/`
- `tests/conftest.py`, локальные `conftest.py`
- `scripts/engineering/dev/run_pytest.sh`, `scripts/engineering/dev/run_pytest.ps1`, `scripts/engineering/ci/run_pytest_resilient.py`
- relevant CI workflows в `.github/workflows/`
- существующие архитектурные тесты, связанные с тестовой стратегией и pytest

2. Найди реальные возможности ускорения:
- узкие места в collection time
- тяжелые/глобальные fixtures
- лишние импорты и side effects при collection
- неправильная сегментация test suites
- serial tests, которые можно распараллелить
- неудачные pytest flags/defaults
- дублирующие или избыточные тестовые прогоны
- неоптимальные smoke/integration/e2e boundaries
- проблемы xdist, cache, import mode, timeout policy, VCR-heavy tests
- тесты или helper-код, которые делают лишний I/O или sleep

3. Сначала зафиксируй baseline:
- выбери 1-2 репрезентативных сценария запуска, которыми реально пользуются разработчики
- для каждого сценария сделай не менее 3 замеров
- за baseline считай median wall-clock time
- отдельно зафиксируй command line, test count, pass/fail, environment assumptions

4. Подготовь краткий план реализации:
- перечисли только изменения с наибольшим ожидаемым эффектом
- для каждого пункта укажи: гипотеза, ожидаемый выигрыш, риск, способ проверки
- начинай с наиболее дешевых и обратимых изменений

5. Реализуй план:
- вноси изменения небольшими, проверяемыми шагами
- после каждого значимого изменения прогоняй релевантные проверки
- если меняешь test infra, обнови docs/comments только там, где это действительно нужно

6. Проведи повторные замеры:
- используй те же сценарии, те же команды и ту же методику
- сравни median against baseline
- посчитай итоговое ускорение в процентах

7. Если итоговое ускорение меньше 30%:
- повтори цикл с шага 1
- используй новые гипотезы, а не повтор предыдущих
- явно зафиксируй, что уже пробовали и почему этого оказалось недостаточно

8. Остановись только когда:
- достигнуто ускорение >= 30%, или
- остались только high-risk/low-confidence изменения
- в этом случае дай честный отчет: что ускорили, что мешает добрать 30%, какие следующие шаги самые перспективные

Обязательные ограничения:
- не отключай тесты ради "ускорения", если это меняет смысл покрытия
- не снижай строгость проверок без явного обоснования
- не ломай CI parity без очень веской причины
- не нарушай архитектурные правила проекта
- любые claims о производительности подтверждай цифрами до/после

Формат результата:
- baseline
- найденные bottlenecks
- план
- реализованные изменения
- результаты замеров до/после
- итоговый процент ускорения
- residual risks / next steps
```

## Recommended Skills And Agents

Использовать в таком порядке:

1. `capability-discovery`
1. `py-test-bot`
1. `py-debug-bot` при неочевидных bottleneck'ах
1. `py-test-bot` если нужно распараллелить исследование по сегментам test suite
1. `verify-unit-tests` после изменений в unit/smoke helpers
1. `verify-integration-tests` после изменений в integration/e2e/VCR контуре
1. `verify-architecture` если меняются test orchestration scripts или guardrails
1. `verify-implementation` как финальная интегральная проверка

### Suggested Multi-Agent Flow

- `capability-discovery` для подтверждения test wrappers, quality commands и локальных путей.
- `py-test-bot` для распараллеленного поиска bottleneck'ов в `unit`,
  `integration`, `e2e`, `architecture`, CI wrappers.
- `py-test-bot` как основной исполнитель для изменений.
- `py-debug-bot` точечно для самых дорогих мест: collection, fixtures, import
  side effects, xdist behavior.
- `verify-unit-tests` и `verify-integration-tests` после правок.
- `verify-implementation` в финале.

## Notes

- Это рабочий prompt artifact, а не governance source of truth.
- При конфликте с `docs/00-project/RULES.md`, `AGENTS.md`, `AGENT.md` или
  runtime-агентными инструкциями приоритет у активных project docs.

## Improved Sections

### Specificity Enhancements

#### Concrete Benchmark Commands
```bash
# Step 1: Study current test infrastructure
cat pyproject.toml
ls -la tests/
cat tests/conftest.py
cat scripts/engineering/dev/run_pytest.sh
cat scripts/engineering/dev/run_pytest.ps1
cat scripts/engineering/ci/run_pytest_resilient.py
ls -la .github/workflows/

# Step 3: Capture baseline measurements
# Scenario 1: Unit tests
for i in {1..3}; do
  time bash scripts/engineering/dev/run_pytest.sh tests/bioetl/pipelines/ -m unit -q
done

# Scenario 2: Integration tests
for i in {1..3}; do
  time bash scripts/engineering/dev/run_pytest.sh tests/bioetl/pipelines/ -m integration -q
done

# Step 6: Repeat measurements after optimization
for i in {1..3}; do
  time bash scripts/engineering/dev/run_pytest.sh tests/bioetl/pipelines/ -m unit -q
done
```

#### Timeout Policies
```yaml
optimization_timeouts:
  study_infrastructure: 300
  find_bottlenecks: 600
  capture_baseline: 600
  prepare_plan: 300
  implement_changes: 1800
  repeat_measurements: 600
  total_optimization_timeout: 4200
```

#### Retry Policies
```yaml
optimization_retry_policies:
  study_infrastructure:
    max_retries: 3
    backoff: "fixed"
    backoff_delay: 5
  
  find_bottlenecks:
    max_retries: 2
    backoff: "fixed"
    backoff_delay: 10
  
  capture_baseline:
    max_retries: 3
    backoff: "exponential"
    backoff_delay: [2, 4, 8]
  
  implement_changes:
    max_retries: 2
    backoff: "fixed"
    backoff_delay: 15
```

#### Iteration Limits
```yaml
optimization_iteration_limits:
  optimization_cycles: 5
  baseline_measurements: 3
  post_optimization_measurements: 3
  bottleneck_investigation: 10
```

### Enhanced Guardrails

#### Integrity Guardrails
- **Baseline Integrity**: Verify baseline measurements are accurate and representative
- **Bottleneck Detection Integrity**: Ensure bottleneck detection is thorough and accurate
- **Optimization Integrity**: Verify optimizations do not reduce test reliability
- **Measurement Integrity**: Ensure measurements are consistent and reproducible

#### Consistency Guardrails
- **Measurement Consistency**: Ensure measurements are consistent across runs
- **Optimization Consistency**: Ensure optimizations are consistent with project patterns
- **Reporting Consistency**: Ensure reporting is consistent with optimization results
- **CI Consistency**: Ensure optimizations are consistent with CI requirements

#### Access Control Guardrails
- **Infrastructure Access Control**: Verify access to test infrastructure before analysis
- **Baseline Access Control**: Verify access to baseline artifacts before measurement
- **Optimization Access Control**: Verify access to test files before optimization
- **Report Access Control**: Verify access to report output directory before generation

### Error Handling Improvements

#### Error Recovery Strategies
```yaml
error_recovery:
  study_infrastructure:
    strategy: "retry_with_fallback"
    fallback: "manual_infrastructure_study"
    max_retries: 3
  
  find_bottlenecks:
    strategy: "retry_with_partial"
    fallback: "partial_bottleneck_detection"
    max_retries: 2
  
  capture_baseline:
    strategy: "retry_with_averaging"
    fallback: "manual_baseline_capture"
    max_retries: 3
  
  implement_changes:
    strategy: "retry_with_rollback"
    fallback: "manual_implementation"
    max_retries: 2
```

#### Fallback Procedures
- **Infrastructure Study Fallback**: Manual infrastructure study using direct file inspection
- **Bottleneck Detection Fallback**: Partial bottleneck detection using manual profiling
- **Baseline Capture Fallback**: Manual baseline capture using direct timing
- **Implementation Fallback**: Manual implementation using direct file editing

#### Graceful Degradation
- **Partial Bottleneck Detection**: Allow partial bottleneck detection if full detection fails
- **Partial Baseline**: Allow partial baseline if full baseline capture fails
- **Partial Optimization**: Allow partial optimization if full optimization fails
- **Warning Mode**: Operate in warning mode for non-critical failures

### Validation Enhancements

#### Validation Gates
```yaml
validation_gates:
  pre_optimization:
    - validate_infrastructure_access
    - validate_environment
    - validate_dependencies
    - validate_baseline_stability
  
  during_optimization:
    - validate_bottleneck_detection
    - validate_optimization_safety
    - validate_test_reliability
    - validate_measurement_consistency
  
  post_optimization:
    - validate_optimization_effectiveness
    - validate_test_reliability
    - validate_ci_compatibility
    - validate_architecture_compliance
```

#### Self-Consistency Checks
- **Baseline Consistency**: Verify baseline measurements are consistent across runs
- **Bottleneck Consistency**: Verify bottleneck detection is consistent across analyses
- **Optimization Consistency**: Verify optimizations are consistent with project patterns
- **Measurement Consistency**: Verify measurements are consistent across optimization cycles

#### Validation Procedures
1. **Pre-Optimization Validation**: Validate infrastructure access, environment, dependencies, and baseline stability
2. **During-Optimization Validation**: Validate bottleneck detection, optimization safety, test reliability, and measurement consistency
3. **Post-Optimization Validation**: Validate optimization effectiveness, test reliability, CI compatibility, and architecture compliance
4. **Cross-Cycle Validation**: Validate consistency across optimization cycles

### Maintainability Improvements

#### Maintenance Guidelines
- **Weekly Review**: Review optimization procedures weekly for optimization opportunities
- **Monthly Audit**: Conduct monthly audit of optimization configuration and dependencies
- **Quarterly Update**: Update optimization documentation and procedures quarterly
- **Continuous Monitoring**: Monitor optimization metrics continuously

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
- **Baseline Cleanup**: Clean up baseline artifacts older than 90 days
- **Measurement Cleanup**: Clean up measurement data older than 30 days
- **Report Cleanup**: Archive optimization reports older than 1 year
- **Log Cleanup**: Clean up optimization logs older than 30 days

### Reusability Improvements

#### Reusable Patterns
```yaml
reusable_patterns:
  optimization:
    - infrastructure_study
    - bottleneck_detection
    - baseline_capture
    - optimization_implementation
    - measurement_validation
  
  bottleneck_detection:
    - collection_time_analysis
    - fixture_analysis
    - import_analysis
    - segmentation_analysis
    - parallelization_analysis
```

#### Modular Components
- **Infrastructure Study Module**: Study current test infrastructure
- **Bottleneck Detection Module**: Detect test bottlenecks
- **Baseline Capture Module**: Capture baseline measurements
- **Optimization Implementation Module**: Implement optimizations
- **Measurement Validation Module**: Validate optimization measurements

#### Templates
```yaml
templates:
  optimization_plan:
    - bottleneck_description
    - optimization_hypothesis
    - expected_improvement
    - risk_assessment
    - validation_method
  
  optimization_report:
    - baseline_summary
    - bottleneck_summary
    - optimization_summary
    - measurement_results
    - performance_improvement
    - residual_risks
    - next_steps
```

#### Configuration Parameters
```yaml
configuration_parameters:
  optimization_timeouts:
    study_infrastructure: 300
    find_bottlenecks: 600
    capture_baseline: 600
    prepare_plan: 300
    implement_changes: 1800
    repeat_measurements: 600
  
  optimization_retries:
    study_infrastructure: 3
    find_bottlenecks: 2
    capture_baseline: 3
    implement_changes: 2
  
  optimization_iteration_limits:
    optimization_cycles: 5
    baseline_measurements: 3
    post_optimization_measurements: 3
    bottleneck_investigation: 10
```

### Documentation Improvements

#### Enhanced Documentation with Examples
```yaml
documentation_examples:
  bottleneck_detection:
    - collection_time_bottleneck_example
    - fixture_bottleneck_example
    - import_bottleneck_example
    - segmentation_bottleneck_example
    - parallelization_bottleneck_example
  
  optimization:
    - fixture_optimization_example
    - import_optimization_example
    - segmentation_optimization_example
    - parallelization_optimization_example
    - xdist_optimization_example
  
  measurement:
    - baseline_measurement_example
    - post_optimization_measurement_example
    - performance_improvement_example
```

#### Templates and Guidelines
- **Optimization Plan Template**: Standard template for defining optimization plans
- **Bottleneck Detection Guidelines**: Guidelines for detecting test bottlenecks
- **Optimization Implementation Guidelines**: Guidelines for implementing optimizations
- **Measurement Validation Guidelines**: Guidelines for validating optimization measurements

#### Usage Examples
```bash
# Example: Optimize unit tests
python -m scripts.ai.optimize.test-speed --scope=unit --target=30 --iterations=5

# Example: Optimize integration tests
python -m scripts.ai.optimize.test-speed --scope=integration --target=30 --iterations=5

# Example: Optimize all tests
python -m scripts.ai.optimize.test-speed --scope=all --target=30 --iterations=5

# Example: Capture baseline for unit tests
python -m scripts.ai.optimize.baseline --scope=unit --measurements=3

# Example: Validate optimization effectiveness
python -m scripts.ai.optimize.validate --scope=unit --baseline=/tmp/baseline.json --optimized=/tmp/optimized.json
```
