______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# PubMed Medallion Layer Flow

- Исходная диаграмма: `providers/pubmed/03-medallion-layer-flow.mmd`

## Описание

Диаграмма PubMed Medallion Layer Flow показывает поток данных через слои Medallion архитектуры (Bronze, Silver, Gold) для PubMed на уровне System и использует нотацию flowchart. Материал помогает понять deterministic writes, DQ gates, quarantine routing и strict validation в рамках сценария PubMed medallion layer implementation. В исходном файле прямо зафиксирован контекст: Medallion Bronze/Silver/Gold flow for PubMed. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Bronze Layer, Silver Layer, Gold Layer, DQ Gates, Quarantine. Именно через эти блоки визуализированы слои Medallion архитектуры и маршруты передачи данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Provider API, Bronze JSONL+zstd append-only, Transform + normalize, DQ / schema gates, Silver Delta merge sort_by, Gold strict contract when enabled, Consumers / exports. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `system`
- Дата метаданных: `2026-07-28`

## ADR References

- ADR-014: Deterministic Writes
- ADR-018: Gold Strict Validation
- ADR-040: Diagram Governance

## Компоненты

### Bronze Layer
- Provider API → Bronze JSONL+zstd append-only
- Deterministic writes согласно ADR-014
- Append-only запись в Bronze Delta Lake

### Silver Layer
- Transform + normalize
- DQ / schema gates
- Silver Delta merge sort_by при прохождении DQ gates
- Quarantine routing при провале DQ gates

### Gold Layer
- Gold strict contract when enabled (ADR-018)
- Строгая валидация для Gold слоя
- Consumers / exports как выходной поток