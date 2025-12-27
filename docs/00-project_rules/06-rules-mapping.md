# Rules Mapping (RULES.md v5.6 → docs/*)

*Синхронизировано с RULES.md v5.6 (2025-12-27)*

Этот документ фиксирует соответствие разделов RULES.md ключевым документам в `docs/` для прозрачности и будущих ревизий.

## Таблица соответствия

| RULES.md   | Содержание                                                 | Документы                                                                       
|------------|------------------------------------------------------------|---------------------------------------------------------------------------------
| §1.1–1.1.1 | Слои, контракты (Ports & Adapters, Protocols, mypy strict) | `01-project-rules.md` §1; `00-rules-summary.md` §1                              
| §2.1       | Medallion (Bronze/Silver/Gold)                             | `01-project-rules.md` §3.1; `00-rules-summary.md` §3.1                          
| §2.1.1     | Delta Maintenance (VACUUM weekly, forensic retention)      | `01-project-rules.md` §3.2; `00-rules-summary.md` §3.6; checklist §11           
| §2.2       | Schema Drift Policy (Info/Warn/Critical, SLA 48h)          | `01-project-rules.md` §3.3; `00-rules-summary.md` §3.2; `02-user-rules.md` §2.3 
| §2.3       | Data Lineage                                               | `01-project-rules.md` §3.4; `00-rules-summary.md` §3.4                          
| §2.4       | Backfill/Replay + Lock Enforcement                         | `01-project-rules.md` §3.5; `00-rules-summary.md` §4.3; checklist §9            
| §2.5       | Партиционирование (Soft/Hard limits)                       | `01-project-rules.md` §3.6; `00-rules-summary.md` §3.7                          
| §2.6       | NULL/Quarantine (Unified)                                  | `01-project-rules.md` §3.7; `00-rules-summary.md` §3.3                          
| §2.8       | Content Hash / Entity ID                                   | `01-project-rules.md` §3.8; `00-rules-summary.md` §3.5; checklist §6            
| §3.1       | Ошибки/Retry/Backoff                                       | `01-project-rules.md` §4.1–4.2; `00-rules-summary.md` §4.1–4.2                  
| §3.1.4     | Circuit Breaker + метрики                                  | `01-project-rules.md` §4.4; `00-rules-summary.md` §4.4; checklist §7–§10        
| §3.2       | Observability (Log Schema, dataset label)                  | `01-project-rules.md` §4.5; `00-rules-summary.md` §4.5; checklist §10           
| §3.3       | Конкурентность и блокировки (Redis)                        | `01-project-rules.md` §4.6; `00-rules-summary.md` §4.3; checklist §9            
| §3.4       | DQ Metrics & Аномалии                                      | `01-project-rules.md` §4.7; `00-rules-summary.md` §4.5                          
| §3.5       | Provider Health Monitoring                                 | `01-project-rules.md` §4.8; `00-rules-summary.md` §4.6                          
| §5.2       | Secrets Policy                                             | `01-project-rules.md` §5.2; `00-rules-summary.md` §5.1; checklist §12           
| §5.3       | Graceful Shutdown + Checkpoints                            | `01-project-rules.md` §5.3; `00-rules-summary.md` §5.4; checklist §13           
| §5.4       | Sensitive Data Policy                                      | `01-project-rules.md` §5.4; `00-rules-summary.md` §5.5; checklist §12           
| §5.5       | DR (RPO/RTO, Runbook)                                      | `01-project-rules.md` §5.5; `00-rules-summary.md` §5.2                          
| §5.6.1     | Environment Isolation                                      | `01-project-rules.md` §5.6; `00-rules-summary.md` §5.3                          
| §7.1       | Data Contracts (Gold schemas, versions)                    | `01-project-rules.md` §6.1; `00-rules-summary.md` §6                            
| §7.2       | Rollback Strategy                                          | `01-project-rules.md` §6.3; `00-rules-summary.md` §6.3                          
| App A      | Источники/библиотеки/лимиты                                | `01-project-rules.md` Приложение A                                              
| App C      | Error Recovery Playbook                                    | `01-project-rules.md` Приложение C                                              
| App D      | Пример pipeline config                                     | `01-project-rules.md` Приложение D                                              
| App E      | Schema Evolution примеры                                   | `01-project-rules.md` Приложение E                                              

## Политика обновления

- При изменении RULES.md: обновить «Синхронизировано с RULES.md vX.Y» в заголовках затронутых документов и пересобрать
  данную таблицу.
- Любые расхождения фиксируются в PR как checklist-пункты.
