______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Transformer Hierarchy

- Исходная диаграмма: `architecture/16-transformer-hierarchy.mmd`

## Описание

Диаграмма Transformer Hierarchy показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 16-transformer-hierarchy. В исходном файле прямо зафиксирован контекст: Shows the Template Method pattern and all provider-specific transformers.. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Template Method Pattern, ChEMBL Transformers, Publication Transformers, UniProt Transformers, Other Transformers. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Template Method Pattern, BaseTransformer (ABC) ━━━━━━━━━━━━━━━━━ provider: str entity_type: str \_tracer: TracingPort \_metrics: MetricsPort \_identity: IdentityService \_pii_hasher: PiiHasherPort \_data_normalizer: DataNormalizationPort ━━━━━━━━━━━━━━━━━ + transform(ctx, record, idx) → SilverRecord ├ \_transform_impl() ← ABSTRACT HOOK ├ compute_entity_id() ├ compute_content_hash() └ should_write_silver/gold() + transform_for_gold(ctx, silver) → dict + entity_to_silver_record(entity) → dict + hash_pii_value() / hash_pii_list() + validate_value_object(), ChEMBL Transformers, BaseChemblTransformer ━━━━━━━━━━━━━━━━━ entity_class: type primary_id_field: str ━━━━━━━━━━━━━━━━━ + \_extract_business_data(), ActivityTransformer, Publication Transformers. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=35), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
