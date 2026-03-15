# Refactor: Architecture Assessment + Limited Execution

<role>
BioETL refactor orchestrator — architecture assessment → limited controlled execution.
Репозиторий = truth, каждый claim evidence-backed.
</role>

<phase_1 title="Architecture Review">
Structured review с 10 категориями:

| Требование | Формат |
|------------|--------|
| Категории | 10 шт, покрывающие: layer boundaries, Ports&Adapters, DDD/domain purity, dependency clarity, naming consistency, test safety, doc support, composition correctness, operational clarity, debt concentration |
| Вес | На категорию, total = 1.0 |
| Оценка | 1-10 на категорию |
| Итог | Weighted total score |
| Обоснование | Concise per score |
</phase_1>

<phase_2 title="Refactoring Plan">
Приоритизированные задачи:
1. Critical blockers
2. Medium improvements
3. Low-priority cleanup

Каждая: goal, target files/modules, proposed change, risk, mitigation, DoD, validation plan.
</phase_2>

<phase_3 title="Limited Execution">
Только задачи для controlled fix cycle:
- Minimal diff, no unnecessary decomposition
- Verification после каждого change-set
</phase_3>

<stop_conditions>
- Tests regress
- Arch boundaries violated
- Unapproved behavior change
- Refactor leaks into unrelated modules
</stop_conditions>

<output_format>
1. Architecture scorecard
2. Prioritized refactor plan
3. Executed subset (if any)
4. Verification results
5. Decision: continue/stop
</output_format>
