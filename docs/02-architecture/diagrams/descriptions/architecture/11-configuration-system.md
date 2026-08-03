______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Configuration System

- Исходная диаграмма: `architecture/11-configuration-system.mmd`

## Описание

Диаграмма Configuration System показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 11-configuration-system. В исходном файле прямо зафиксирован контекст: Shows how YAML configs are loaded, validated, and used across the system.. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: YAML Config Files, Infrastructure Config Loaders, Infrastructure Schemas (Pydantic), Domain Configuration, Composite Domain Config. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: YAML Config Files, configs/base/*.yaml pipeline and quality defaults, configs/providers/*.yaml source plus provider defaults, configs/entities/*/*.yaml unified entity configs, configs/composites/\*.yaml composite configs. Диаграмма показывает актуальную unified topology: pipeline, DQ и filter settings разрешаются через base/provider/entity/composite hierarchy. В метаданных указана оценка плотности (@nodes=27), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
