# 00 Activity Chembl Overview

## Pipeline
**ChemblActivityPipeline** наследует ChemblCommonPipeline и добавляет специфичную трансформацию активности.

## Компоненты
- **ActivityExtractor** — получает батчи активности из ChemblClient по дескриптору релиза/фильтров.
- **ActivityTransformer** — нормализует числовые показатели, единицы, связывает с Assay/Target/TestItem.
- **ActivityNormalizer** — вычисляет бизнес-ключ, `hash_business_key`, `hash_row`, приводит колонки к порядку схемы.
- **ActivitySchema** — Pandera-схема с типами полей, ключами и порядком колонок.
- **ActivityWriter** — записывает таблицы активности и QC-отчёты.
- **ActivityParser** — парсит ответы API в сырой формат для трансформации.

## Особенности
- Поддержка работы с релизами ChEMBL и батчевой пагинацией.
- Генерация QC-артефактов на основе ValidationResult.
- Использование общих дескрипторов ChemblDescriptorFactory для параметров выборки.

## Зависимости
Опирается на базовые компоненты: UnifiedAPIClient, SchemaRegistry, ValidationService, UnifiedOutputWriter. Схемы и контракты описаны в `docs/reference/core/*` и `docs/reference/schemas/00-schemas-overview.md`.
