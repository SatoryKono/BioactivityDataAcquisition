______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-08'

______________________________________________________________________

# Control Plane Artifact Publication Pipeline

- Исходная диаграмма: `architecture/24-control-plane-artifact-publication-pipeline.mmd`

## Описание

Диаграмма «Control Plane Artifact Publication Pipeline» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Control Plane». В комментариях исходника зафиксирован фокус диаграммы: {init: {'theme': 'neutral', 'themeVariables': {'fontFamily': 'Inter, system-ui', 'lineWidth': '2'}}}%%. Схема имеет плотность порядка 16 узлов и 18 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: CLI run / workflow commands, composition.bootstrap.runtime.assembly, PipelineRunner, build_postrun_service, control plane writers, RunManifest.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Control Plane`
- Дата метаданных: `2026-05-12`
