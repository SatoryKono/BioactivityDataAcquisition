# BatchExecutor Internal Architecture

- Исходная диаграмма: `architecture/15-batch-executor-internals.mmd`

## Описание
Диаграмма BatchExecutor Internal Architecture показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 15-batch-executor-internals. В исходном файле прямо зафиксирован контекст: Shows the composition of BatchExecutor and its helper components.. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: BatchExecutor, Composed Helper Components, Data Flow Through Batch, TransformResult, Error Classification. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: BatchExecutor, BatchExecutor -------- services, context, config batch_size, checkpoint_interval + execute() + process(), Composed Helper Components, BatchMemoryManager -------- adaptive batch sizing + check_pressure() + maybe_recover(), BatchMetricsRecorder -------- batch and error metrics + track_batch_size() + track_error(), BatchTracingManager -------- execution spans + start_batch_span() + end_span(). По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=15), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
