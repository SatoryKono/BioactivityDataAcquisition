## История Изменений (Changelog)

- **5.0.0** (2025-12-16): Актуализация версий и документации. Версия проекта синхронизирована с RULES.md v5.0.
  Обновлены pyproject.toml и __init__.py. Актуализированы документы: CHANGELOG.md, IMPLEMENTATION_ROADMAP.md,
  AUDIT_REPORT.md, README.md, docs/00-map.md для отражения реального прогресса разработки (Фазы 0-4 завершены).
- **5.0-implementation-phase4** (2025-12-15): Завершена Phase 4 (Application Layer). Реализованы BasePipeline,
  ChEMBLActivityPipeline, CLI (bioetl run/quarantine/checkpoint). Добавлена поддержка incremental/backfill/rebuild
  режимов с graceful shutdown и checkpoint recovery. ~990 строк кода.
- **5.0-implementation-phase3** (2025-12-15): Завершена Phase 3 (Provider Adapters). Реализованы адаптеры для
  ChEMBL, PubChem, UniProt с rate limiting, circuit breaker, health checks. HTTP infrastructure с async httpx,
  TokenBucket, exponential backoff. ~1,300 строк кода.
- **5.0-implementation-phase2** (2025-12-15): Завершена Phase 2 (Infrastructure Adapters). Реализованы BronzeWriter
  (JSONL+zstd), DeltaWriter (merge/upsert), GoldWriter (SCD Type 2), S3CheckpointAdapter, UnifiedQuarantine.
  Redis distributed locking с heartbeat и fencing tokens. ~2,110 строк кода.
- **5.0-docs-sync** (2025-12-15): Синхронизация документации с RULES.md v5.0: обновлены `00-rules-summary.md`,
  `02-user-rules.md`, чек‑лист пайплайнов; добавлены документы `06-rules-mapping.md` и `07-consistency-check.md`;
  уточнены Bronze lifecycle, еженедельный Delta VACUUM (7d), Forensic retention, стратегия партиционирования,
  Observability и Lock invariants.
- **5.0** (2025-12-15): Production Ready. Final Governance Polish, Circuit Breaker half-open observability, Backfill
  lock timeouts, Generic Health Probes, Deprecation clarification.
- **4.6** (2025-12-15): Governance & Stability. RFC 2119, Entity ID vs Content Hash, Bronze Lifecycle, Hard Limits,
  Threat Model. Added Log Schema, Provider Health Matrix, Circuit Breaker details, Backfill Locking, and Deprecation
  workflows.
- **4.5** (2025-05-20): Final Polish & Governance. Medallion Paths, DQ Levels, Observability, Fencing Tokens, Security
  IAM.
- **4.4** (2025-05-20): Resilience & Operations. Circuit Breaker, DR Runbooks, Quarantine Ops, Env Isolation, Salt
  Rotation.
- **4.3** (2025-05-20): Security & DR. Salted Hashes, RPO/RTO, Heartbeat Locks, Environments, Delta Infrastructure.
- **4.2** (2025-05-20): Delta Lake Strategy, Unified Quarantine Schema, Threshold adjustments.
- **4.1** (2025-05-20): [DEPRECATED] Storage Fixes. (Заменено версией 4.2).
- **4.0** (2025-05-20): Data Contracts, Partitioning, Null Policy, Recovery Playbook.
- **3.0** (2025-05-20): Lineage, Backfill, Concurrency, Graceful Shutdown, Dev Experience.
- **2.0** (2025-05-20): Классификация ошибок, Medallion, Rate limiting, Перевод на русский.
- **1.0** (2025-04-01): Черновик.
