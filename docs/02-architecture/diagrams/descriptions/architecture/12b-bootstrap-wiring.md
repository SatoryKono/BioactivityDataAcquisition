______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Bootstrap: Wiring Graph

- Исходная диаграмма: `architecture/12b-bootstrap-wiring.mmd`

## Описание

Диаграмма Bootstrap: Runtime and Admin Wiring показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Она описывает текущую wiring-модель: sanctioned public `composition.entrypoints` и lower-level `composition.bootstrap` выводят к `bootstrap_pipeline_runner`, `bootstrap_pipeline_runner_service`, `build_pipeline_runner`, `bootstrap.cli + bootstrap.assembly` и composite runtime helpers. Ниже уже видны созданные collaborator groups: provider adapter, `StorageContext / StorageAdapter`, observability bundle, locking/checkpoint ports, `PipelineRunner`, `PipelineRunnerService`, `CompositePipelineRunner` и admin services.

Этот view полезен для проверки того, что runtime wiring больше не выглядит как абстрактные `RunnerBootstrap / StorageBootstrap` блоки, а выражен через реальные bootstrap functions и assembly leaves, которые сегодня владеют DI-путём.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-03-24`
