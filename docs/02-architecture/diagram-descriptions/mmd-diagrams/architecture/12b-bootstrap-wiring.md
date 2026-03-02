# Bootstrap: Wiring Graph

- Исходная диаграмма: `mmd-diagrams/architecture/12b-bootstrap-wiring.mmd`

## Описание
Диаграмма Bootstrap: Wiring Graph показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 12b-bootstrap-wiring. В исходном файле прямо зафиксирован контекст: Covers runtime assembly sequence and main dependency injection graph.. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Composition Layer, Infrastructure Layer, Application Layer. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Composition Layer, bootstrap_pipeline_runner, RunnerBootstrap, StorageBootstrap, CheckpointBootstrap, LockBootstrap. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=15), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
