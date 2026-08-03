______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-08'

______________________________________________________________________

# Effective Config Artifact Domain Model

- Исходная диаграмма: `architecture/48-effective-config-artifact-domain-model.mmd`

## Описание

Диаграмма «Effective Config Artifact Domain Model» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате диаграмма классов (class diagram) и служит ориентиром на уровне детализации «Domain / Model». В комментариях исходника зафиксирован фокус диаграммы: {init: {'theme': 'neutral', 'themeVariables': {'fontFamily': 'Inter, system-ui', 'lineWidth': '2'}}}%%. Схема имеет плотность порядка 9 узлов и 8 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: EffectiveConfigArtifact, EffectiveConfigHashes, ConfigSourceRef, ResolvedConfigSnapshot, RuntimeOverrideSnapshot, ExecutionEnvironmentSnapshot.

## Метаданные

- Тип: `classDiagram`
- Уровень: `Domain / Model`
- Дата метаданных: `2026-05-12`
