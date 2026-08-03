______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-08'

______________________________________________________________________

# Workflow Control Plane Manifest And Ledger Publication

- Исходная диаграмма: `architecture/31-workflow-control-plane-manifest-and-ledger-publication.mmd`

## Описание

Диаграмма «Workflow Control Plane Manifest And Ledger Publication» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Control Plane». В комментариях исходника зафиксирован фокус диаграммы: {init: {'theme': 'neutral', 'themeVariables': {'fontFamily': 'Inter, system-ui', 'lineWidth': '2'}}}%%. Схема имеет плотность порядка 9 узлов и 10 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: workflow CLI command, workflow execution state, WorkflowManifestStep, WorkflowManifest, WorkflowLedger, child run manifests.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Control Plane`
- Дата метаданных: `2026-05-12`
