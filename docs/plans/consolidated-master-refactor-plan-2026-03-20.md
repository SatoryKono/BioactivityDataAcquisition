# Consolidated Master Refactor Plan

Дата: 2026-03-20
Статус: active master plan, Wave 0 reconciled
Язык: русский

## Назначение

Этот документ консолидирует актуальные предложения по рефакторингу из:
- `docs/plans/`
- `docs/reports/evidence/`

Цель документа — заменить набор пересекающихся execution plans, roadmap-ов,
backlog-ов и evidence-derived proposals одной общей программой работ, пригодной
для дальнейшего исполнения волнами.

## Результат Wave 0

Wave 0 в рамках этого master plan теперь считается выполненной как
reconciliation pass. Это означает не то, что все исторические refactor-темы
одновременно закрыты кодом, а то, что их статусная модель и иерархия больше не
конфликтуют между собой.

После reconciliation действуют следующие правила:

- этот документ является главным execution/backlog документом для общей
  программы рефакторинга;
- [consolidated-master-refactor-plan-expanded-waves-2026-03-20.md](consolidated-master-refactor-plan-expanded-waves-2026-03-20.md)
  является его развёрнутым companion-документом по волнам;
- `rf-fs-*`, `rf-04`, `rf-06`, `rf-07` и evidence roadmaps больше не
  трактуются как конкурирующие master programs;
- документы типа `ledger`, `seam map`, `decision summary` и calibration
  summaries считаются supporting context или constraints, а не самостоятельными
  очередями исполнения.

Wave 0 также снимает несколько старых противоречий:

- `RF-FS-004` больше не нужно трактовать как исходный широкий structural
  backlog item; его уже выполненные локальные slices и ownership decisions
  должны читаться как implemented context и remaining config-seam constraints;
- `RF-06` больше не читается как активная кодовая migration wave, а как
  docs/governance watchpoint;
- `RF-07D` остаётся deferred runtime watchpoint и не должен неявно
  перетаскиваться в следующую активную implementation wave;
- provider-assembly simplification остаётся допустимым следующим execution
  направлением, но только вне explicit runtime instance-threading campaign.

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

Статус после reconciliation: `completed`

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
- один главный master plan и один развёрнутый companion document;
- явное отделение active execution plans от context-only inputs.

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

Локальный статус на текущий момент:
- canonical helper path уже зафиксирован для `ProviderAssemblySupport`
  resolution, support-aware data-source creator binding, HTTP-oriented
  `ProviderConfig` assembly и non-HTTP data-source config assembly;
- remaining runtime `ProviderRegistry` ownership intentionally stays deferred.

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

Локальный статус на текущий момент:
- `registration_biblio.py` и `pipeline_builder.py` уже прошли intended
  decomposition path;
- `composite_support_service_builders.py` сейчас лучше трактовать как
  guarded facade-only seam, а не как кандидат на ещё один forced split.
- `pipeline_builder.py` тоже лучше удерживать как guarded service-factory
  facade, а не как новый decomposition target.

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

Локальный статус на текущий момент:
- первым bounded cluster для этой волны выбран `crossref/batch.py` family;
- cluster start зафиксирован в
  `wave-3-crossref-batch-cluster-plan-2026-03-20.md`;
- preflight inventory для cluster start уже завершён:
  прямых `src`-импортёров у `crossref.batch` сейчас нет, а внешний контракт
  удерживается в основном tests/architecture touchpoints;
- следующий implementation step для `Wave 3` сужен до internal workflow split
  with compatibility seam, а не к broad adapter rewrite.

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

Практическая иерархия после Wave 0 выглядит так:

1. master execution:
   - `consolidated-master-refactor-plan-2026-03-20.md`
   - `consolidated-master-refactor-plan-expanded-waves-2026-03-20.md`
2. active targeted plans:
   - `rf-04-composition-hotspots-execution-plan-2026-03-20.md`
   - `rf-07-provider-registry-migration-plan-2026-03-20.md`
   - `rf-06-domain-facade-hygiene-plan-2026-03-20.md`
3. reconciled context / closeout inputs:
   - `rf-fs-remaining-backlog-execution-plan-2026-03-20.md`
   - `rf-fs-004-execution-plan-2026-03-20.md`
   - `refactor-proposals-consolidation-input-2026-03-20.md`
4. evidence constraints:
   - decision summaries and calibration/synthesis artifacts under
     `docs/reports/evidence/`

## Рекомендуемый immediate next step

После закрытия Wave 0 дальнейшие действия нужно читать в двух разных режимах,
чтобы не смешивать structural closeout и next debt program:

1. для legacy structural closeout:
   - держать `RF-06` как docs/governance watchpoint;
   - держать `RF-07D` как deferred runtime watchpoint;
   - использовать remaining `rf-fs-*` документы только как subordinate inputs,
     а не как самостоятельный execution queue.
2. для следующей активной debt-oriented волны:
   - открыть Wave 1 как provider-assembly simplification;
   - ограничить её composition/provider assembly scope;
   - не расширять её до explicit runtime `ProviderRegistry` threading без новых
     reopen criteria.
