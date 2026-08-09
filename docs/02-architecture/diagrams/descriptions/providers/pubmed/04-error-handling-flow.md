______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# PubMed Error Handling Flow

- Исходная диаграмма: `providers/pubmed/04-error-handling-flow.mmd`

## Описание

Диаграмма PubMed Error Handling Flow показывает стратегию обработки ошибок для PubMed extract/transform paths на уровне System и использует нотацию flowchart. Материал помогает понять классификацию ошибок, retry логику, quarantine routing и cleanup operations в рамках сценария PubMed error handling. В исходном файле прямо зафиксирован контекст: Error handling for PubMed extract/transform paths. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Error Classification, Transient HTTP Error Handling, Permanent HTTP Error Handling, Schema/DQ Error Handling, Config Error Handling, Retry Logic, Cleanup Operations. Именно через эти блоки визуализированы этапы обработки ошибок и маршруты передачи управления. Примеры узлов, отражающих доменную модель и инфраструктуру: Error observed, Retry / rate limit / CB, Fail batch / surface error, Quarantine + metrics, Fail fast config error, Retry attempt, Operator inspect / replay, Release lock / cleanup ADR-015. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `system`
- Дата метаданных: `2026-07-28`

## ADR References

- ADR-032: Unified HTTP Client
- ADR-040: Diagram Governance

## Компоненты

### Error Classification
- Error observed → Class determination
- Классы: Transient HTTP, Permanent HTTP, Schema/DQ, Config

### Transient HTTP Error Handling
- Retry / rate limit / CB (Circuit Breaker)
- Retry logic с проверкой exhausted retries
- Retry attempt при наличии попыток

### Permanent HTTP Error Handling
- Fail batch / surface error
- Release lock / cleanup ADR-015

### Schema/DQ Error Handling
- Quarantine + metrics
- Operator inspect / replay для manual investigation

### Config Error Handling
- Fail fast config error
- Немедленный провал при ошибках конфигурации

### Cleanup Operations
- Release lock / cleanup ADR-015
- Cleanup ресурсов при фатальных ошибках