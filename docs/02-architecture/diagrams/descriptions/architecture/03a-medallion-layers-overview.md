______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Medallion Layers Overview

- Исходная диаграмма: `architecture/03a-medallion-layers-overview.mmd`

## Описание

Диаграмма Medallion Layers Overview показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 03a-medallion-layers-overview. В исходном файле прямо зафиксирован контекст: Compact decomposition view for 03-medallion-data-flow.mmd (layer-level semantics). Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Ingestion, Processing, Serving. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Ingestion, Provider APIs, Bronze Layer\\nRaw JSON, Processing, Normalize + Validate, Silver Layer\\nDelta Tables. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=12), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
