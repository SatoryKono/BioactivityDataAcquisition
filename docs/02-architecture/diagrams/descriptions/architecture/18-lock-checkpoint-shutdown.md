______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Locking, Checkpoint, and Graceful Shutdown

- Исходная диаграмма: `architecture/18-lock-checkpoint-shutdown.mmd`

## Описание

Диаграмма Locking, Checkpoint, and Graceful Shutdown показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 18-lock-checkpoint-shutdown. В исходном файле зафиксирован контекст runtime lock safety mechanisms для Local-Only профиля. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Domain Ports, Domain Lock Types, Application: LockRuntimeService, Application: CheckpointRuntimeService, Application: Shutdown. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Domain Ports, LockPort (Protocol) ━━━━━━━━━━━━━━━━━ + acquire(key, owner, ttl) + release(key, owner) + heartbeat(key, owner) + validate_owner(key, owner) + validate_fencing_token(token), CheckpointPort (Protocol) ━━━━━━━━━━━━━━━━━ + save(key, data) + load(key) → dict | None + list_all() → list + delete(key), ShutdownPort (Protocol), Domain Lock Types, FencingToken (frozen dataclass) ━━━━━━━━━━━━━━━━━ sequence: int key: str owner_id: RunID issued_at: float. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=22), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
