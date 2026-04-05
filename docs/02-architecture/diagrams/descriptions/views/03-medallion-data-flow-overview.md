______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Medallion Data Flow Overview

- Исходная диаграмма: `views/03-medallion-data-flow-overview.mermaid`

## Описание

Эта views-диаграмма Medallion Data Flow Overview представляет срез типа overview для родительской схемы 03-medallion-data-flow.mmd и использует нотацию flowchart. Она нужна для быстрого чтения основного medallion path без детализации по support-компонентам и служит удобной точкой входа для онбординга и архитектурного ревью. В метке view зафиксировано назначение: Overview. Показательные узлы в диаграмме: Source, Bronze, Silver, Gold, DQ, Quarantine. По ним можно сверить терминологию слоёв, базовые переходы между ними и место аналитического/защитного контура вокруг основного data flow.

## Метаданные

- Тип: `flowchart`
- View: `Overview`
- Parent: `03-medallion-data-flow.mmd`
