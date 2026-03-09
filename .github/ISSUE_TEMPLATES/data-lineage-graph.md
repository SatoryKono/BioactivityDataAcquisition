## Problem

Отсутствует формализованный механизм отслеживания происхождения данных от Gold-слоя до исходного API-ответа. Исследователь, использующий запись из Gold-таблицы в публикации, не может программно восстановить полную цепочку трансформаций и подтвердить, из какого API-вызова, в какой момент и через какие этапы обработки запись получена. Это критический пробел для воспроизводимости научных исследований — рецензенты и регуляторы всё чаще требуют полную провенанс-информацию.

При обнаружении ошибки в Gold-данных невозможно быстро выполнить root cause analysis: неясно, была ли ошибка в исходных данных провайдера, возникла при трансформации Bronze→Silver / Silver→Gold, или является артефактом конкретной версии pipeline.

В контексте композитных пайплайнов проблема усугубляется: один API-ответ может порождать записи в нескольких Silver/Gold-таблицах через ветвление DAG, и lineage превращается в граф, а не линейную цепочку.

## Proposed Solution

### 1. Lineage ID propagation
Сквозной `lineage_id` (UUID v4) генерируется при ingestion в Bronze и пропагируется через все трансформации. В Bronze `lineage_id` привязан к API request/response (endpoint URL, parameters, HTTP status, timestamp). В композитном пайплайне каждая стадия передаёт `lineage_id` как first-class column.

### 2. Delta Lake metadata enrichment
`userMetadata` в Delta commit log обогащается на каждой стадии: source table, transformation name, pipeline version (git SHA), input/output row counts, schema version. Автоматически через wrapper над Delta write operations.

### 3. Lineage graph store
Delta-таблица `lineage_graph`: `source_entity`, `target_entity`, `transformation`, `pipeline_version`, `run_id`, `timestamp`, `row_count_in`, `row_count_out`. Строится post-factum из Delta transaction logs scheduled job-ом (не замедляет основной pipeline). Поддерживает запросы: «для данной Gold-записи покажи все upstream-зависимости до Raw».

### 4. Python API
Функция `trace_lineage(gold_table, record_id) -> LineageChain` возвращает структурированную цепочку. Для визуализации — интеграция с DataHub/OpenLineage или минимальный UI.

### 5. Immutable Raw storage
Оригинальные API-ответы хранятся с HTTP-заголовками и метаданными запроса, retention ≥ 2 года. Данные старше 6 мес. — на S3 Glacier/IA.

## Integration with Composite Pipelines

Lineage аккумулируется как побочный эффект каждой стадии pipeline:

```python
@asset
def silver_compounds(context, bronze_compounds):
    result = transform(bronze_compounds)
    result["lineage_id"] = bronze_compounds["lineage_id"]  # propagate

    context.delta_write(result, user_metadata={
        "source": "bronze_compounds",
        "transform": "silver_compounds",
        "git_sha": GIT_SHA,
        "pipeline_run_id": context.run_id,
    })
```

При ветвлении (один Bronze → несколько Silver) lineage graph автоматически отражает DAG-структуру pipeline.

## Acceptance Criteria

- [ ] `lineage_id` генерируется при ingestion и пропагируется через Bronze → Silver → Gold
- [ ] Delta commit logs обогащены lineage-метаданными (source, transformation, git SHA)
- [ ] Создана и заполняется таблица `lineage_graph`
- [ ] Реализована и покрыта тестами функция `trace_lineage()`
- [ ] Raw API-ответы хранятся immutably с retention ≥ 2 года
- [ ] Валидация: для 100% записей Gold lineage восстанавливается до Raw
- [ ] Совместимость со стандартом OpenLineage
- [ ] Документация с архитектурной диаграммой lineage flow
