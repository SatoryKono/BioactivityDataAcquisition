______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-08'

______________________________________________________________________

# Reproducible Run Contract Across Manifest Ledger And Output Metadata

- Исходная диаграмма: `architecture/26-reproducible-run-contract-across-manifest-ledger-and-output-metadata.mmd`

## Описание

Диаграмма «Reproducible Run Contract Across Manifest Ledger And Output Metadata» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Control Plane». В комментариях исходника зафиксирован фокус диаграммы: {init: {'theme': 'neutral', 'themeVariables': {'fontFamily': 'Inter, system-ui', 'lineWidth': '2'}}}%%. Схема имеет плотность порядка 11 узлов и 16 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Показательные узлы для быстрого чтения: RunManifest, RunLedgerEntry, EffectiveConfigArtifact, run_id / manifest_id / batch_id, bronze metadata yaml, silver metadata yaml.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Control Plane`
- Дата метаданных: `2026-05-12`
