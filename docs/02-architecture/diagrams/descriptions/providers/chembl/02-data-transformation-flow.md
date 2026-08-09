______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# ChEMBL Data Transformation Flow

- Исходная диаграмма: `providers/chembl/02-data-transformation-flow.mmd`

## Описание

Диаграмма ChEMBL Data Transformation Flow показывает процесс трансформации данных из ChEMBL API в доменные сущности на уровне System и использует нотацию flowchart. Материал помогает понять обработку сырых API ответов, маппинг полей, нормализацию данных, валидацию и создание доменных сущностей в рамках сценария ChEMBL data transformation. В исходном файле прямо зафиксирован контекст: Data transformation flow diagram for ChEMBL provider showing raw API response processing, field mapping, data normalization, validation, and domain entity creation. Covers ChEMBL-specific data transformation patterns. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: JSON Parsing, Field Mapping, Data Normalization, Schema Validation, Domain Entity Creation. Именно через эти блоки визуализированы этапы трансформации и маршруты передачи данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Receive Raw API Response, Activity Records, Target Records, Compound Records, Activity Field Mapping, Standardize Activity Types, Schema Validation, Create Domain Entity. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `system`
- Дата метаданных: `2026-07-24`

## ADR References

- ADR-023: Entity Type Patterns
- ADR-034: Schema↔Domain Pairs
- ADR-040: Diagram Governance

## Компоненты

### JSON Parsing
- Парсинг JSON ответа от ChEMBL API
- Валидация формата JSON
- Извлечение записей

### Field Mapping
- Маппинг полей для разных типов данных (Activity, Target, Compound)
- Activity Field Mapping, Target Field Mapping, Compound Field Mapping

### Data Normalization
- Activity Normalization: стандартизация типов активностей, маппинг target proteins, стандартизация единиц
- Target Normalization: классификация targets, маппинг организмов, маппинг protein families
- Compound Normalization: стандартизация идентификаторов, стандартизация названий, парсинг структур

### Schema Validation
- Валидация данных согласно схеме
- Проверка соответствия ADR-034 Schema↔Domain Pairs
- Обработка ошибок валидации

### Domain Entity Creation
- Создание Activity Entity (Activity Domain Type)
- Создание Target Entity (Target Domain Type)
- Создание Compound Entity (Compound Domain Type)
- Создание доменных сущностей согласно ADR-023 Entity Type Patterns
