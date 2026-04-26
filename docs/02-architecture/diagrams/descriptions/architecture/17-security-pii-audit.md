______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Security, PII Hashing, and Audit Trail

- Исходная диаграмма: `architecture/17-security-pii-audit.mmd`

## Описание

Диаграмма Security, PII Hashing, and Audit Trail показывает архитектурный срез BioETL на уровне System / Component и использует нотацию flowchart. Материал помогает понять границы ответственности модулей, точки интеграции и зависимости между компонентами в рамках сценария 17-security-pii-audit. В исходном файле прямо зафиксирован контекст: Shows how PII is handled and audit trail is maintained.. Это описание задает ожидаемую интерпретацию схемы при техническом ревью и синхронизации документации с кодовой базой. Ключевые контейнеры/подграфы включают: Domain Ports, Domain Types, PII Hashing Flow, Infrastructure: PII Hasher, Infrastructure: Audit. Именно через эти блоки визуализированы границы слоев и маршруты передачи управления или данных. Примеры узлов, отражающих доменную модель и инфраструктуру: Domain Ports, PiiHasherPort (Protocol) -------- + hash(value: str) -> str, AuditPort (Protocol) -------- + log_write(entry) + get_entries(filters), Domain Types, AuditEntry (frozen dataclass) -------- run_id, timestamp, layer table_name, operation records_count, metadata, AuditLayer -------- BRONZE / SILVER / GOLD. По этим сущностям можно проверить согласованность терминов, портов и адаптеров между диаграммой и реализацией. В метаданных указана оценка плотности (@nodes=16), что полезно для контроля читаемости, декомпозиции view-слоев и стабильного рендеринга в CI-пайплайне.

## Метаданные

- Тип: `flowchart`
- Уровень: `System / Component`
- Дата метаданных: `2026-02-24`
