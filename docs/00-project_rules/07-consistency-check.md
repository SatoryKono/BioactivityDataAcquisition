# Consistency Check Guide (RULES.md v5.9)

*Синхронизировано с RULES.md v5.9 (2026-01-01)*

Цель: описать автоматическую проверку согласованности документов `docs/*` с RULES.md v5.9 без реализации кода.

## Проверяемые инварианты

- Наличие в ключевых документах обязательных формулировок:
    - Medallion уровни и запрет Raw Parquet в Silver.
    - Bronze lifecycle (версии пути).
    - Delta `VACUUM` еженедельно `retention_period=7 days`.
    - Forensic retention (7d по умолчанию; 30d для Critical).
    - Schema Drift policy (Info/Warn/Critical + SLA 48h).
    - Locking: MemoryLock (Local-Only); Max 4h; safety guard.
    - Circuit Breaker: trigger=5, open=5m, half-open probe; метрики `circuit_breaker_state`, `trips_total`.
    - DQ thresholds: 5%/20%; аномалии: 2x/5x baseline; cold start.
    - Secrets policy; PII salted; Graceful Shutdown; DR RPO/RTO.

## Файлы-мишени

- `docs/00-project_rules/00-rules-summary.md`
- `docs/00-project_rules/02-user-rules.md`
- `docs/templates/pipeline-review-checklist.md`

## Pseudo-steps для CI (read-only checks)

```bash
# 1) Проверка шапок документов на версию RULES
grep -R "Синхронизировано с RULES.md v5.9" docs/00-project_rules/ | wc -l

# 2) Ключевые формулировки (примерный набор)
grep -R "Raw Parquet" docs/00-project_rules/00-rules-summary.md
grep -R "VACUUM" docs/00-project_rules/
grep -R "MemoryLock" -n docs/00-project_rules/
grep -R "Trigger | 5" -n docs/00-project_rules/00-rules-summary.md
grep -R "5%.*20%" -n docs/00-project_rules/
grep -R "forensic_retention" -n docs/

# 3) Именование документации (kebab-case, NN-)
# (эвристика: отсутствие подчёркиваний в именах, H1=Title Case вручную проверяется ревью)
find docs -name "*.md" | grep -v "_"

# 4) Checklist наличие ключевых пунктов
grep -R "VACUUM" docs/templates/pipeline-review-checklist.md
grep -R "dataset" docs/templates/pipeline-review-checklist.md
```

## Критерии фейла

- Отсутствует хотя бы один ключевой пункт из списка инвариантов в целевых документах.
- В чек-листе отсутствуют пункты по `VACUUM` и/или `dataset` в Log Schema.
- Файлы документации нарушают kebab-case (обнаружены подчёркивания).

## Политика обновлений

- При выпуске новой версии RULES.md обновить версию в шапках документов и перечень проверяемых инвариантов.
