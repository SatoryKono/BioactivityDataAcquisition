______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-08'

______________________________________________________________________

# DQ Contract Config Loading And Policy Resolution

- Исходная диаграмма: `architecture/45-dq-contract-config-loading-and-policy-resolution.mmd`

## Описание

Диаграмма «DQ Contract Config Loading And Policy Resolution» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «Configuration / Component». В комментариях исходника зафиксирован фокус диаграммы: {init: {'theme': 'neutral', 'themeVariables': {'fontFamily': 'Inter, system-ui', 'lineWidth': '2'}}}%%. Схема имеет плотность порядка 8 узлов и 7 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: DQ YAML policies, dq_config_loader.py, _dq_config_normalization.py, _dq_config_validation_merge.py, DQPolicySnapshot, dq_policy_resolver.py.

## Метаданные

- Тип: `flowchart`
- Уровень: `Configuration / Component`
- Дата метаданных: `2026-05-12`
