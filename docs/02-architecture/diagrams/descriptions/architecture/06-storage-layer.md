______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Storage Layer Components

- Исходная диаграмма: `architecture/06-storage-layer.mmd`

## Описание

Диаграмма Storage Layer Components показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 06-storage-layer. В исходном файле прямо зафиксирован контекст: Shows Bronze/Silver/Gold writers, Delta Lake, metadata, and validation.. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Domain Port, Storage Writers, Bronze Storage, Silver Storage, Gold Storage. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Domain Port, StoragePort (Protocol), Storage Writers, Bronze Storage, BronzeWriter ━━━━━━━━━━━━━━━━━ base_path: Path logger: LoggerPort metrics: MetricsPort save_json: bool validate_json: bool ━━━━━━━━━━━━━━━━━ + write_bronze() + aclose(), AtomicWriteGroup ━━━━━━━━━━━━━━━━━ Atomic multi-file writes with rollback. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=21), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
