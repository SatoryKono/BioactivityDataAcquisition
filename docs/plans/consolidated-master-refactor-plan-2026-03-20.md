# Consolidated Master Refactor Plan

Дата: 2026-03-20
Статус: master draft
Язык: русский

## Назначение

Этот документ консолидирует актуальные предложения по рефакторингу из:
- `docs/plans/`
- `docs/reports/evidence/`

Цель документа — заменить набор пересекающихся execution plans, roadmap-ов,
backlog-ов и evidence-derived proposals одной общей программой работ, пригодной
для дальнейшего исполнения волнами.

## Что было включено

В качестве основных источников были использованы:
- `rf-fs-remaining-backlog-execution-plan-2026-03-20.md`
- `rf-fs-004-execution-plan-2026-03-20.md`
- `rf-04-composition-hotspots-execution-plan-2026-03-20.md`
- `rf-06-domain-facade-hygiene-plan-2026-03-20.md`
- `rf-07-provider-registry-migration-plan-2026-03-20.md`
- `rf-07d-runtime-deferred-wave-plan-2026-03-20.md`
- `TECHNICAL-DEBT-ROADMAP.md`
- `TECHNICAL-DEBT-EXECUTION-PLAN.md`
- `BACKLOG-dependency-hotspots-prioritized-2026-03-20.md`
- `BACKLOG-complexity-hotspots-implementation-2026-03-20.md`
- `naming-cleanup-refactor-plan-2026-03-20.md`

В качестве ограничений и supporting context учитывались:
- решения по `PipelineConfigLoader`
- решения по runtime ownership `ProviderRegistry`
- evidence по dependency hotspots, duplication/dead-code и
  ownership-compatibility seams

Не включались как самостоятельные future plans:
- уже реализованные wave-документы
- seam maps и ledgers без собственной программы исполнения
- decision summaries, которые сейчас работают скорее как ограничения

## Главный принцип консолидации

Консолидированный план строится не вокруг отдельных старых идентификаторов
документов, а вокруг пяти фактических потоков работы:

1. незавершённые structural RF-FS waves
2. provider-registry и composition seams
3. hotspot reduction в infrastructure/adapters и complexity clusters
4. ownership/facade/naming hygiene
5. conservative cleanup и residual test/CI debt

Это позволяет убрать дубли между `RF-FS`, `RF-04`, `RF-07` и
technical-debt roadmap, не потеряв важные предложения.

## Консолидированный порядок работ

### Wave 0. Закрытие уже начатых structural хвостов

Приоритет: `P0`

Сюда входят работы, которые уже запущены и не должны оставаться в подвешенном
состоянии:
- добивание `RF-FS-004` до полного wave-level closeout
- явное закрытие статусов по `RF-FS-006a/006b`
- синхронизация remaining structural backlog с фактическим кодом

Почему это первая волна:
- она уменьшает стратегическую неопределённость;
- без неё последующие планы рискуют опираться на уже устаревший backlog.

Основной результат:
- один актуальный structural backlog без “полузакрытых” пунктов.

### Wave 1. ProviderRegistry и provider-assembly cluster

Приоритет: `P1`

Это главный следующий refactor target по совокупному весу evidence.
В эту волну объединяются:
- `rf-07-provider-registry-migration-plan`
- `rf-07d-runtime-deferred-wave-plan`
- relevant части `rf-04-composition-hotspots-execution-plan`
- Wave 1 из technical-debt execution plan

Цели:
- сократить повторяющуюся provider-assembly scaffolding;
- сузить duplicated registry-resolution paths;
- удержать class-level/default-registry compatibility как явный, а не
  случайный seam;
- не пересечь слишком рано runtime/bootstrap safe boundary.

Основные модули:
- `src/bioetl/composition/providers/registration.py`
- `registration_bio.py`
- `registration_biblio.py`
- `_registration_contracts.py`
- смежные call sites и deferred runtime paths

Выход этой волны:
- canonical provider-resolution path;
- меньше repeated assembly;
- явная фиксация retained compatibility obligations;
- зелёные architecture guards по provider-registry decomposition.

### Wave 2. Composition hotspots и ownership-heavy seams

Приоритет: `P1`

Эта волна объединяет:
- незакрытые части `rf-04-composition-hotspots-execution-plan`
- ownership-driven work из technical-debt evidence
- оставшиеся composition-side hotspots, которые не были уже закрыты локально

Цели:
- сделать composition более “assembly-only”, где это уже подтверждено кодом и
  evidence;
- удержать отдельно canonical owners и compat shims;
- закрыть мягкие противоречия между tests, reports и реальным ownership.

Сюда же попадают:
- classification pass для retained seams (`retain`, `simplify-now`,
  `retire-later`);
- review незавершённых composition factory seams;
- alignment между provider-registry migration и broader composition topology.

Выход этой волны:
- composition меньше зависит от исторически накопленных compatibility-shaped
  seams;
- ownership state для ключевых узлов становится явно зафиксированным.

### Wave 3. Adapter и infrastructure hotspot reduction

Приоритет: `P1`

Это отдельная волна, потому что hotspot evidence ясно показывает:
основной pressure-tail сидит в `src/bioetl/infrastructure/adapters`, а не в
формальных нарушениях архитектуры.

Сюда объединяются:
- `BACKLOG-dependency-hotspots-prioritized`
- Wave 2 из technical-debt execution plan
- релевантные предложения из complexity backlog, если они касаются тех же
  hotspots

Цели:
- снижать pressure в densest allowed seams;
- работать bounded clusters, а не broad rewrite-ом;
- не смешивать hotspot reduction с произвольным поведением/feature churn.

Подход:
- hotspot ledger;
- выбор одного подкластера за раз;
- локальный refactor + локальный verify;
- ratchet against regressions after every slice.

Выход этой волны:
- уменьшение концентрации в adapter/infrastructure hotspot tails;
- сохранение зелёных drift, size и mypy gates.

### Wave 4. Complexity hotspot implementation

Приоритет: `P2`

Эта волна использует отдельный complexity backlog, но подчиняется уже
сконсолидированному порядку. Она не должна идти раньше structural/provider
волн, потому что complexity evidence хоть и сильный, но более локальный.

Основной кандидат сейчас:
- `crossref` batch hotspot family и связанные orchestration seams

Цели:
- разрезать большие complexity-heavy units на подответственности;
- удержать текущие governance budgets и exemption policy;
- не превращать complexity cleanup в новый слой compatibility debt.

Выход этой волны:
- меньше крупных complexity hotspots;
- меньше reliance на exemptions;
- чище bounded execution paths.

### Wave 5. Domain facade, naming и narrative hygiene

Приоритет: `P2`

Сюда объединяются:
- `rf-06-domain-facade-hygiene-plan`
- `naming-cleanup-refactor-plan`
- частично governance-signals roadmap там, где он ещё предлагает будущие
  calibration slices

Почему не раньше:
- это важные, но менее срочные улучшения по сравнению с provider/infrastructure
  pressure.

Цели:
- улучшить архитектурный narrative around `domain.ports` и facade policies;
- провести naming cleanup там, где он реально уменьшает когнитивную нагрузку;
- не запускать repo-wide rename wave.

Выход этой волны:
- понятнее фасады и naming semantics;
- меньше drift между “как называется” и “что реально является owner”.

### Wave 6. Conservative cleanup и residual debt follow-up

Приоритет: `P3`

Последняя волна объединяет:
- candidate-level dead code cleanup
- residual test/CI debt follow-up
- оставшиеся низкорисковые cleanup candidates

Ключевое правило:
- никакой broad delete campaign;
- только candidate-level evidence;
- sanctioned compatibility seams и aggregate seams исключаются по умолчанию.

Сюда же включается follow-up evidence по residual test-scope debt, если он
нужен для отдельной CI/test architecture программы.

## Общие guardrails

Во всех волнах действуют единые ограничения:
- не смешивать cleanup, hotspot reduction и ownership closure в один широкий
  batch;
- каждая волна должна резаться на sequential safe slices;
- каждый slice должен иметь свой verify set;
- class-level compatibility и retained shims нельзя убирать без явного
  migration rationale;
- решения из evidence/decision summaries трактуются как constraints, а не как
  повод к мгновенной широкой переделке.

## Единый verify-контур

Полный master plan не означает один гигантский test run после всех изменений.
Нужно применять layered verify:

1. локальные unit/integration suites для текущего slice
2. targeted architecture tests по затронутому seam
3. `mypy --strict --no-incremental` по затронутому дереву
4. wave-level gates после завершения группы slices
5. периодический global sanity run на переходах между крупными волнами

## Что считать актуальным результатом консолидации

После этой консолидации master plan должен использоваться как главный
execution документ, а старые планы — как:
- источники деталей;
- supporting ledgers;
- evidence-backed constraints.

Иными словами:
- `rf-fs-*`, `rf-04`, `rf-07` и technical-debt roadmap больше не должны
  восприниматься как конкурирующие программы;
- они становятся вложенными источниками для единой последовательности работ.

## Рекомендуемый immediate next step

Если переходить от master plan к исполнению прямо сейчас, лучший старт такой:

1. официально принять Wave 1 как текущую активную волну;
2. собрать provider-registry resolution ledger по:
   - `registration.py`
   - `registration_bio.py`
   - `registration_biblio.py`
3. выделить Slice 1A как первый implementation batch;
4. прогнать targeted provider-registry verify before moving дальше.
