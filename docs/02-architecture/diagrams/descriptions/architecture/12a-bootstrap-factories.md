______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Bootstrap: Factories and Registries

- Исходная диаграмма: `architecture/12a-bootstrap-factories.mmd`

## Описание

Диаграмма Bootstrap: Factories and Registries показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Она концентрируется на актуальных public and factory seams composition-слоя: `composition.entrypoints`, `composition.bootstrap`, `ProviderRegistry`, `PipelineRegistry`, `DataSourceFactory`, `GenericPipelineFactory / RunnerFactory`, `StorageFactory` и composite-specific helper seam, где остаются `RunnerFactoryBuilderService + CompositeSupportServicesFactory`.

Этот срез нужен для быстрого чтения factory topology без лишней runtime-детализации. По нему удобно видеть, что provider/data source и pipeline/storage creation теперь читаются через канонические registry/factory seams, а legacy-looking helper names сохранены только там, где они действительно обслуживают composite runtime path.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-03-24`
