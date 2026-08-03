______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-08'

______________________________________________________________________

# Filter Config Resolution And Column Filter Evaluation

- Исходная диаграмма: `architecture/46-filter-config-resolution-and-column-filter-evaluation.mmd`

## Описание

Диаграмма «Filter Config Resolution And Column Filter Evaluation» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Configuration / Component». В комментариях исходника зафиксирован фокус диаграммы: {init: {'theme': 'neutral', 'themeVariables': {'fontFamily': 'Inter, system-ui', 'lineWidth': '2'}}}%%. Схема имеет плотность порядка 9 узлов и 11 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: filter YAML, filter_config_loader.py, input_config.py, silver_config.py, gold_config.py, column_filter.py.

## Метаданные

- Тип: `flowchart`
- Уровень: `Configuration / Component`
- Дата метаданных: `2026-05-12`
