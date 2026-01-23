# Consistency Check Guide (RULES.md v5.11)

*Синхронизировано с RULES.md v5.11 (2026-01-06)*
*Обновлено: 2026-01-15 — обновлены пути после консолидации документации*

Цель: описать автоматическую проверку согласованности документов `docs/*` с RULES.md v5.11.

## Проверяемые инварианты

- Наличие в ключевых документах обязательных формулировок:
    - Medallion уровни и запрет Raw Parquet в Silver
    - Bronze lifecycle (версии пути)
    - Delta `VACUUM` еженедельно `retention_period=7 days`
    - Forensic retention (7d по умолчанию; 30d для Critical)
    - Schema Drift policy (Info/Warn/Critical + SLA 48h)
    - Locking: MemoryLock (Local-Only); Max 4h; safety guard
    - Circuit Breaker: trigger=5, open=5m, half-open probe; метрики `circuit_breaker_state`, `trips_total`
    - DQ thresholds: 5%/20%; аномалии: 2x/5x baseline; cold start
    - Secrets policy; PII salted; Graceful Shutdown; DR RPO/RTO

## Файлы-мишени

- `docs/quick-reference/rules-summary.md` — краткая справка
- `docs/templates/pipeline-review-checklist.md` — чек-лист для PR
- `docs/02-architecture/data-layers.md` — описание слоёв данных

## Pseudo-steps для CI (read-only checks)

```bash
# 1) Проверка версии RULES в ключевых документах
grep -l "RULES.md v5.11" docs/quick-reference/rules-summary.md

# 2) Ключевые формулировки
grep -R "Raw Parquet" docs/quick-reference/rules-summary.md
grep -R "VACUUM" docs/quick-reference/
grep -R "MemoryLock" docs/quick-reference/
grep -R "5%.*20%" docs/quick-reference/

# 3) Checklist наличие ключевых пунктов
grep -R "VACUUM" docs/templates/pipeline-review-checklist.md
grep -R "dataset" docs/templates/pipeline-review-checklist.md
```

## Критерии фейла

- Отсутствует хотя бы один ключевой пункт из списка инвариантов в целевых документах
- В чек-листе отсутствуют пункты по `VACUUM` и/или `dataset` в Log Schema
- Файлы документации нарушают kebab-case (обнаружены подчёркивания)

## Политика обновлений

При выпуске новой версии RULES.md обновить версию в шапках документов и перечень проверяемых инвариантов.
