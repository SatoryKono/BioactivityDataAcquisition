# Bootstrap: Factories and Registries

- Исходная диаграмма: `architecture/12a-bootstrap-factories.mmd`

## Описание
Диаграмма Bootstrap: Factories and Registries показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 12a-bootstrap-factories. В исходном файле прямо зафиксирован контекст: Covers composition root factories, provider registry, and builder assembly.. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Interfaces Layer, Composition Layer. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Interfaces Layer, CLI Commands (Click), HTTP Interface, Composition Layer, ProviderRegistry, DataSourceFactory. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=8), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-25`
