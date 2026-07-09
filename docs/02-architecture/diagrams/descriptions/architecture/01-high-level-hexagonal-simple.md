______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-08'

______________________________________________________________________

# Simplified High-Level Hexagonal Architecture

- Исходная диаграмма: `architecture/01-high-level-hexagonal-simple.mmd`

## Описание

Диаграмма «Simplified High-Level Hexagonal Architecture» из architecture-набора детализирует конкретный архитектурный компонент или подсистему BioETL. Она представлена в формате блок-схема потоков (flowchart) и служит ориентиром на уровне детализации «System / Component». В комментариях исходника зафиксирован фокус диаграммы: Simplified overview of Ports & Adapters pattern with essential layers only.. Схема имеет плотность порядка 13 узлов и 15 связей; её удобно использовать как обзорный архитектурный срез для проверки влияния изменений, согласования интерфейсов и подготовки рефакторинга, но не как исчерпывающий каталог текущей кодовой поверхности. Ключевые блоки/подграфы: External Systems, Interfaces Layer, Composition Layer, Application Layer, Domain Layer, Infrastructure Layer. Показательные узлы для быстрого чтения: External APIs (ChEMBL, PubMed, UniProt, etc.), File System (Delta Lake / Parquet), Observability (Prometheus, OpenTelemetry), CLI Commands, Bootstrap / Assembly, Core Pipeline (Executor, Transformer, Writer). Примечание: Simplified version of 01-high-level-hexagonal.mmd (46 nodes → 13 nodes).

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-07-03`
- Узлы: `13`
