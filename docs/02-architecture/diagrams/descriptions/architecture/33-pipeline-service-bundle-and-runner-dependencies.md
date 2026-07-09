______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-08'

______________________________________________________________________

# Pipeline Service Bundle And Runner Dependencies

- Исходная диаграмма: `architecture/33-pipeline-service-bundle-and-runner-dependencies.mmd`

## Описание

Диаграмма «Pipeline Service Bundle And Runner Dependencies» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Application / Component». В комментариях исходника зафиксирован фокус диаграммы: {init: {'theme': 'neutral', 'themeVariables': {'fontFamily': 'Inter, system-ui', 'lineWidth': '2'}}}%%. Схема имеет плотность порядка 9 узлов и 9 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: PipelineRunner, PipelineService, PipelineStorageProtocol, BatchExecutor, RecordProcessor, BatchWriter.

## Метаданные

- Тип: `classDiagram`
- Уровень: `Application / Component`
- Дата метаданных: `2026-05-12`
