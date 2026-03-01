# План улучшения диаграмм views (полный охват)

- Дата аудита: 2026-03-01
- Охват: `156` диаграмм из `docs/02-architecture/mmd-diagrams/views/*.mermaid`
- Источники: `scripts/diagrams/lint_diagrams.py`, `scripts/diagrams/check_diagram_quality_gates.py`
- Текущее состояние: `lint issues = 0`; quality warnings = 0.
- В этом цикле: выровнена семантика связей в flowchart, сокращены перегруженные подписи, удалены избыточные `<br/>`.

## Таблица по каждой диаграмме

| # | Диаграмма | Тип | Найдено проблем | План улучшения | Статус |
|---:|---|---|---|---|---|
| 1 | `00-legend.mermaid` | `flowchart` | — | плановых правок нет; периодический lint/render/smoke-контроль | без правок в этом цикле |
| 2 | `01-full-system-component-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 3 | `01-full-system-component-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 4 | `01-full-system-component-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 5 | `01-full-system-component-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 6 | `01-full-system-component-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 7 | `01-high-level-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 8 | `01-high-level-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 9 | `01-high-level-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 10 | `01-high-level-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 11 | `01-high-level-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 12 | `02-medallion-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 13 | `02-medallion-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 14 | `02-medallion-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 15 | `02-medallion-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 16 | `02-medallion-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 17 | `04-domain-layer-class-diagram-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 18 | `04-domain-layer-class-diagram-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 19 | `04-domain-layer-class-diagram-full.mermaid` | `classDiagram` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 20 | `04-domain-layer-class-diagram-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 21 | `04-domain-layer-class-diagram-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 22 | `05-layers-interaction-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 23 | `05-layers-interaction-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 24 | `05-layers-interaction-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 25 | `05-layers-interaction-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 26 | `05-layers-interaction-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 27 | `05-pipeline-lifecycle-states-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 28 | `05-pipeline-lifecycle-states-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 29 | `05-pipeline-lifecycle-states-full.mermaid` | `stateDiagram` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 30 | `05-pipeline-lifecycle-states-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 31 | `05-pipeline-lifecycle-states-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 32 | `06-application-layer-class-diagram-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 33 | `06-application-layer-class-diagram-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 34 | `06-application-layer-class-diagram-full.mermaid` | `classDiagram` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 35 | `06-application-layer-class-diagram-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 36 | `06-application-layer-class-diagram-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 37 | `07-circuit-breaker-states-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 38 | `07-circuit-breaker-states-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 39 | `07-circuit-breaker-states-full.mermaid` | `stateDiagram` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 40 | `07-circuit-breaker-states-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 41 | `07-circuit-breaker-states-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 42 | `08-complete-etl-workflow-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 43 | `08-complete-etl-workflow-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 44 | `08-complete-etl-workflow-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 45 | `08-complete-etl-workflow-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 46 | `08-complete-etl-workflow-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 47 | `08-domain-ddd-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 48 | `08-domain-ddd-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 49 | `08-domain-ddd-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | обновлено в этом цикле |
| 50 | `08-domain-ddd-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 51 | `08-domain-ddd-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 52 | `10-infrastructure-layer-class-diagram-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 53 | `10-infrastructure-layer-class-diagram-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 54 | `10-infrastructure-layer-class-diagram-full.mermaid` | `classDiagram` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 55 | `10-infrastructure-layer-class-diagram-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 56 | `10-infrastructure-layer-class-diagram-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 57 | `12-local-deployment-architecture-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 58 | `12-local-deployment-architecture-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 59 | `12-local-deployment-architecture-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 60 | `12-local-deployment-architecture-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 61 | `12-local-deployment-architecture-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 62 | `14-provider-health-states-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 63 | `14-provider-health-states-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 64 | `14-provider-health-states-full.mermaid` | `stateDiagram` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 65 | `14-provider-health-states-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 66 | `14-provider-health-states-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 67 | `15-dq-check-workflow-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 68 | `15-dq-check-workflow-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 69 | `15-dq-check-workflow-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 70 | `15-dq-check-workflow-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 71 | `15-dq-check-workflow-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 72 | `21-activity-entity-data-flow-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 73 | `21-activity-entity-data-flow-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 74 | `21-activity-entity-data-flow-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 75 | `21-activity-entity-data-flow-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 76 | `21-activity-entity-data-flow-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 77 | `26-hexagonal-ports-adapters-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 78 | `26-hexagonal-ports-adapters-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 79 | `26-hexagonal-ports-adapters-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 80 | `26-hexagonal-ports-adapters-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 81 | `26-hexagonal-ports-adapters-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 82 | `28-composition-root-di-graph-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 83 | `28-composition-root-di-graph-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 84 | `28-composition-root-di-graph-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 85 | `28-composition-root-di-graph-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 86 | `28-composition-root-di-graph-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 87 | `29-composite-pipeline-workflow-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 88 | `29-composite-pipeline-workflow-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 89 | `29-composite-pipeline-workflow-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 90 | `29-composite-pipeline-workflow-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 91 | `29-composite-pipeline-workflow-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 92 | `30-port-adapter-mapping-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 93 | `30-port-adapter-mapping-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 94 | `30-port-adapter-mapping-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 95 | `30-port-adapter-mapping-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 96 | `30-port-adapter-mapping-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 97 | `31-pipeline-run-lifecycle-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 98 | `31-pipeline-run-lifecycle-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 99 | `31-pipeline-run-lifecycle-full.mermaid` | `stateDiagram` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 100 | `31-pipeline-run-lifecycle-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 101 | `31-pipeline-run-lifecycle-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 102 | `32-single-record-journey-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 103 | `32-single-record-journey-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 104 | `32-single-record-journey-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | обновлено в этом цикле |
| 105 | `32-single-record-journey-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 106 | `32-single-record-journey-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 107 | `33-cli-run-interaction-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 108 | `33-cli-run-interaction-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 109 | `33-cli-run-interaction-full.mermaid` | `sequenceDiagram` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 110 | `33-cli-run-interaction-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 111 | `33-cli-run-interaction-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 112 | `34-batch-processing-flow-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 113 | `34-batch-processing-flow-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 114 | `34-batch-processing-flow-full.mermaid` | `sequenceDiagram` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 115 | `34-batch-processing-flow-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 116 | `34-batch-processing-flow-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 117 | `35-bootstrap-sequence-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 118 | `35-bootstrap-sequence-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 119 | `35-bootstrap-sequence-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 120 | `35-bootstrap-sequence-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 121 | `35-bootstrap-sequence-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 122 | `36-architecture-principles-mindmap-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 123 | `36-architecture-principles-mindmap-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 124 | `36-architecture-principles-mindmap-full.mermaid` | `mindmap` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 125 | `36-architecture-principles-mindmap-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 126 | `36-architecture-principles-mindmap-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 127 | `39-medallion-invariants-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 128 | `39-medallion-invariants-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 129 | `39-medallion-invariants-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | обновлено в этом цикле |
| 130 | `39-medallion-invariants-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 131 | `39-medallion-invariants-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 132 | `41-error-classification-tree-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 133 | `41-error-classification-tree-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 134 | `41-error-classification-tree-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 135 | `41-error-classification-tree-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 136 | `41-error-classification-tree-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 137 | `44-cross-provider-enrichment-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 138 | `44-cross-provider-enrichment-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 139 | `44-cross-provider-enrichment-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | обновлено в этом цикле |
| 140 | `44-cross-provider-enrichment-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 141 | `44-cross-provider-enrichment-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 142 | `46-yaml-config-resolution-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 143 | `46-yaml-config-resolution-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 144 | `46-yaml-config-resolution-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 145 | `46-yaml-config-resolution-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 146 | `46-yaml-config-resolution-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 147 | `48-composite-phase-lifecycle-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 148 | `48-composite-phase-lifecycle-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 149 | `48-composite-phase-lifecycle-full.mermaid` | `stateDiagram` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 150 | `48-composite-phase-lifecycle-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 151 | `48-composite-phase-lifecycle-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
| 152 | `50-exception-hierarchy-dataflow.mermaid` | `flowchart` | — | поддерживать явный путь данных Bronze→Silver→Gold и маркировать ветки ошибок | без правок в этом цикле |
| 153 | `50-exception-hierarchy-domain.mermaid` | `flowchart` | — | поддерживать доменную фокусировку: исключать инфраструктурные детали и служебные узлы | без правок в этом цикле |
| 154 | `50-exception-hierarchy-full.mermaid` | `flowchart` | — | сохранять полноту, но выносить перегруженные детали в декомпозированные view | без правок в этом цикле |
| 155 | `50-exception-hierarchy-infra.mermaid` | `flowchart` | — | поддерживать инфраструктурный фокус: показывать адаптеры/хранилища и точки интеграции | без правок в этом цикле |
| 156 | `50-exception-hierarchy-overview.mermaid` | `flowchart` | — | держать L1-вид в пределах 5-9 блоков и проверять пересечения при добавлении узлов | без правок в этом цикле |
