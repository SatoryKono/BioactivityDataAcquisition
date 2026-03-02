# Bootstrap / DI Container (Composition Root)

- Исходная диаграмма: `mmd-diagrams/architecture/12-bootstrap-di-container.mmd`

## Описание
Диаграмма Bootstrap / DI Container (Composition Root) показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 12-bootstrap-di-container. В исходном файле прямо зафиксирован контекст: Shows how dependencies are assembled and wired together.. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Entry Points, composition layer, Bootstrap Assembly, Factories, Provider Registry. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Entry Points, CLI Commands (Click), HTTP Interface, composition layer, Bootstrap Assembly, RuntimeAssembly ━━━━━━━━━━━━━━━━━ Central DI wiring point. Creates all infrastructure and application components.. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=29), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные
- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
