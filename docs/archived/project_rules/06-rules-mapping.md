# Rules Mapping (RULES.md v5.10 → docs/*)

*Синхронизировано с RULES.md v5.10 (2026-01-06)*
*Обновлено: 2026-01-15 — удалены устаревшие ссылки после консолидации*

Этот документ фиксирует соответствие разделов RULES.md ключевым документам в `docs/` для прозрачности и будущих ревизий.

## Таблица соответствия

| RULES.md   | Содержание                                                 | Документы                                          |
|------------|------------------------------------------------------------|----------------------------------------------------|
| §1.1–1.1.1 | Слои, контракты (Ports & Adapters, Protocols, mypy strict) | `quick-reference/rules-summary.md` §1              |
| §2.1       | Medallion (Bronze/Silver/Gold)                             | `quick-reference/rules-summary.md` §2              |
| §2.1.1     | Delta Maintenance (VACUUM weekly, forensic retention)      | `quick-reference/rules-summary.md` §2              |
| §2.2       | Schema Drift Policy (Info/Warn/Critical, SLA 48h)          | `02-architecture/data-layers.md`                   |
| §2.4       | Backfill/Replay + Lock Enforcement                         | `quick-reference/rules-summary.md` §4              |
| §2.6       | NULL/Quarantine (Unified)                                  | `03-guides/troubleshooting.md`                     |
| §2.8       | Content Hash / Entity ID                                   | `02-architecture/data-layers.md`                   |
| §3.1       | Ошибки/Retry/Backoff                                       | `quick-reference/rules-summary.md` §3              |
| §3.1.4     | Circuit Breaker + метрики                                  | `quick-reference/rules-summary.md` §3              |
| §3.2       | Observability (Log Schema, dataset label)                  | `02-architecture/observability-layers.md`          |
| §3.3       | Конкурентность и блокировки (MemoryLock)                   | `quick-reference/rules-summary.md` §4              |
| §5.2       | Secrets Policy                                             | `quick-reference/rules-summary.md` §5              |
| §5.3       | Graceful Shutdown + Checkpoints                            | `quick-reference/rules-summary.md` §5              |
| §5.5       | DR (RPO/RTO, Runbook)                                      | `quick-reference/rules-summary.md` §5              |
| §7.1       | Data Contracts (Gold schemas, versions)                    | `03-data-contracts/gold-schemas.md`                |
| App A      | Источники/библиотеки/лимиты                                | `RULES.md` Приложение A                            |
| App C      | Error Recovery Playbook                                    | `05-operations/runbooks/`                          |
| App D      | Пример pipeline config                                     | `RULES.md` Приложение D                            |

## Политика обновления

- При изменении RULES.md: обновить «Синхронизировано с RULES.md vX.Y» в заголовках затронутых документов
- Любые расхождения фиксируются в PR как checklist-пункты
- Каноническая версия правил: `docs/RULES.md`
- Краткая версия: `docs/quick-reference/rules-summary.md`
