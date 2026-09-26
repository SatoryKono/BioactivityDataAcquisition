______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# UniProt Data Transformation Flow

- Исходная диаграмма: `providers/uniprot/02-data-transformation-flow.mmd`

## Описание

Диаграмма UniProt Data Transformation Flow показывает процесс трансформации и нормализации данных UniProt на уровне System и использует нотацию flowchart. Материал помогает понять field mapping, domain normalization, identifier canonicalization, schema validation и quarantine routing в рамках сценария UniProt transformation/normalization. В исходном файле прямо зафиксирован контекст: Transformation/normalization flow for UniProt. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Field Mapping, Domain Normalization, Identifier Canonicalization, Schema Validation, Quarantine Routing. Именно через эти блоки визуализированы этапы трансформации и маршруты передачи данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Raw provider records, Field mapping FieldSpec/profile, Domain normalization profiles, Identifier family canonicalization, Pandera schema validation, Domain entity / row contract, Silver write input. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=46), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `system`
- Дата метаданных: `2026-07-28`

## ADR References

- ADR-040: Diagram Governance

## Компоненты

### Field Mapping
- Field mapping согласно FieldSpec/profile
- Преобразование сырых provider records в структурированный формат

### Domain Normalization
- Domain normalization profiles
- Применение профилей нормализации для доменных сущностей

### Identifier Canonicalization
- Identifier family canonicalization
- Стандартизация идентификаторов в каноническую форму

### Schema Validation
- Pandera schema validation
- Проверка валидности данных согласно схеме
- Обработка soft fail (Null/flag per policy) и hard fail path

### Quarantine Routing
- Quarantine routing для hard fail path
- Domain entity / row contract для валидных данных
- Silver write input как выходной поток