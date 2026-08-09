______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# ChEMBL Medallion Layer Flow

- Исходная диаграмма: `providers/chembl/03-medallion-layer-flow.mmd`

## Описание

Диаграмма ChEMBL Medallion Layer Flow показывает процесс записи данных через слои Medallion архитектуры (Bronze, Silver, Gold) на уровне System и использует нотацию flowchart. Материал помогает понять поток данных от доменной сущности через Bronze write, Silver transformation, Gold enrichment до quarantine routing в рамках сценария ChEMBL medallion layer implementation. В исходном файле прямо зафиксирован контекст: Medallion layer flow diagram for ChEMBL provider showing Bronze write (JSONL), Silver transformation, Gold enrichment, and quarantine routing. Covers ChEMBL-specific medallion layer implementation. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Bronze Write, Silver Transformation, Gold Enrichment, Quarantine Handling. Именно через эти блоки визуализированы слои Medallion архитектуры и маршруты передачи данных. Примеры узлов, отражающих доменную модель и инфраструктуру: ChEMBL Domain Entity, Format as JSONL, Add Bronze Metadata, Write to Bronze Delta Lake, Apply Silver Transformations, Apply Silver DQ Rules, Apply Gold Transformations, Apply Strict Validation. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-002: Medallion Architecture
- ADR-018: Gold Strict Validation
- ADR-050: Silver Structural and Gold Semantic Filter Boundary
- ADR-040: Diagram Governance

## Компоненты

### Bronze Write
- Форматирование данных как JSONL
- Добавление Bronze metadata
- Запись в Bronze Delta Lake
- Обработка ошибок Bronze write

### Silver Transformation
- Применение Silver transformations
- Silver Data Type
- Data Normalization
- Enrichment
- Применение Silver DQ Rules
- Проверка Silver DQ
- Запись в Silver Delta Lake или routing в Silver Quarantine

### Gold Enrichment
- Применение Gold transformations
- Merge с другими источниками
- Final Gold Data
- Применение Strict Validation (ADR-018)
- Проверка Strict Validation
- Запись в Gold Delta Lake или routing в Gold Quarantine

### Quarantine Handling
- Обработка данных из Silver и Gold quarantine
- Эмитация Quarantine metrics
- Логирование ошибок всех слоев
- Эмитация error metrics