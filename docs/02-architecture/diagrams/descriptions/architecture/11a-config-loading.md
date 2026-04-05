______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Configuration: Loading Pipeline

- Исходная диаграмма: `architecture/11a-config-loading.mmd`

## Описание

Диаграмма Configuration: Loading Pipeline показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 11a-config-loading. В исходном файле прямо зафиксирован контекст: YAML files, config loaders, and infrastructure schemas (Pydantic validation).. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: YAML Config Files, Infrastructure Config Loaders, Infrastructure Schemas (Pydantic). Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: YAML Config Files, configs/base/*.yaml, configs/providers/*.yaml, configs/entities/*/*.yaml, configs/composites/\*.yaml. Диаграмма фиксирует актуальную unified topology: DQ и filters разрешаются из base/provider/entity hierarchy. В метаданных указана оценка плотности (@nodes=11), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-27`
