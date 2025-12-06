# 03 Data Flow

## Цепочка стадий
1. **extract** — Client получает страницы/батчи данных, оборачивает их в структуру, совместимую с трансформером.
2. **transform** — нормализатор приводит поля к целевым типам, добавляет хеши и business key, сортирует колонки.
3. **validate** — ValidationService применяет схемы из SchemaRegistry, собирает ValidationResult, метрики и QC-отчёты.
4. **write** — UnifiedOutputWriter атомарно записывает таблицы, `meta.yaml`, QC и контрольные суммы.

## Хуки и режимы
- `prepare_run` и `finalize_run` (PipelineHookABC) вызываются до и после основного цикла для инициализации ресурсов и сборки итоговых метрик.
- `dry-run` выполняет extract/transform/validate без записи, позволяя проверять конфиги и схемы.

## Управление ошибками и мониторинг
- ErrorPolicyABC определяет, когда остановить пайплайн или пропустить записи при валидации/IO.
- Логирование и метрики (UnifiedLogger, TracerABC, ProgressReporterABC) сопровождают каждую стадию, фиксируя контекст run_id/pipeline_name.

## End-to-end сценарий (ChEMBL)
1. CLI-команда `bioetl run --pipeline chembl_activity` создаёт контекст запуска и загружает конфиг.
2. ChemblClient извлекает данные по дескриптору (release, фильтры), пагинирует и передаёт батчи в ActivityTransformer.
3. Transformer нормализует значения, считает `hash_business_key` и `hash_row`, сопоставляет TestItem/Target идентификаторы.
4. ValidationService применяет ActivitySchema, формирует QC-отчёты и метрики валидации.
5. UnifiedOutputWriter записывает таблицы в `tables/`, создаёт `meta.yaml`, формирует `quality_report_table.csv` и `correlation_report_table.csv` атомарно и вычисляет контрольные суммы.
6. finalize_run закрывает ресурсы клиента и публикует финальное состояние RunResult.
