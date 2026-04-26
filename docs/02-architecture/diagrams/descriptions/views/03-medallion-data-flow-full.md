______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Medallion Data Flow Full

- Исходная диаграмма: `views/03-medallion-data-flow-full.mermaid`

## Описание

Эта views-диаграмма Medallion Data Flow Full представляет срез типа full для родительской схемы 03-medallion-data-flow.mmd и использует нотацию flowchart. Она сохраняет полный reference-view после декомпозиции родительской architecture-диаграммы и нужна как компактная публикационная копия для визуального ревью, smoke-check рендера и сверки базового Bronze → Silver → Gold маршрута. В метке view зафиксировано назначение: Full. Показательные узлы в диаграмме: External APIs, Ingestion, Bronze, Transform, Silver, Gold. По ним можно быстро проверить корректность имен medallion layers, quarantine path и места подключения DQ analyzers без возврата к более плотной родительской схеме.

## Метаданные

- Тип: `flowchart`
- View: `Full`
- Parent: `03-medallion-data-flow.mmd`
