______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Bootstrap / DI Container (Composition Root)

- Исходная диаграмма: `architecture/12-bootstrap-di-container.mmd`

## Описание

Диаграмма Bootstrap / DI Container (Composition Root) показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять, какие composition seams реально центральны сегодня: sanctioned public `composition.entrypoints`, lower-level `composition.bootstrap`, runtime path через `bootstrap_pipeline_runner -> build_pipeline_runner`, а также factory-level seams `ProviderRegistry`, `PipelineRegistry`, `DataSourceFactory`, `GenericPipelineFactory / RunnerFactory` и `StorageFactory`.

Ключевые контейнеры здесь: Public composition seams, Internal composition modules, Registries + factories, Runtime bootstrap, CLI/bootstrap services, Created collaborators. По схеме удобно валидировать, что главным public входом остаётся `composition.entrypoints`, а helper-объекты вроде `RunnerFactoryBuilderService` живут уже как composite runtime helpers, а не как центральный bootstrap-образ. В метаданных указана плотность `@nodes=20`, что сохраняет схему в читаемом диапазоне без дополнительной декомпозиции.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-03-24`
