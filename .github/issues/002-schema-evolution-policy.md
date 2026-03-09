---
title: "Schema Evolution Policy — автоматизация backward-compatibility checks для Gold-схемы"
labels:
  - schema-evolution
  - breaking-changes
  - developer-experience
  - priority:high
milestone: "Data Governance v2"
---

## Problem

ADR-036 определяет политику версионирования Gold-контрактов, но проверка обратной совместимости при изменении схемы выполняется вручную и не интегрирована в CI/CD. Изменения Gold-схемы (добавление обязательного поля, переименование колонки, смена типа) ломают downstream consumers — notebooks, dashboards, scheduled reports, API-эндпоинты.

Типичный инцидент: разработчик меняет `confidence_score` с `DOUBLE` на `DECIMAL(10,4)`. Проходит ревью, деплоится, через часы ломается Spark-job аналитиков. Обнаруживается только при ручном запуске notebook. Время реагирования — часы до дней.

В контексте композитных пайплайнов проблема каскадирует: изменение схемы в одной ветке DAG может затронуть consumers, которые зависят от downstream-таблиц через несколько уровней трансформаций.

## Proposed Solution

### 1. Schema Registry

Delta-таблица `schema_registry`: `table_name`, `version`, `schema_json`, `timestamp`, `author`, `change_type` (`BACKWARD_COMPATIBLE` / `BREAKING`), `migration_notes`. Новая версия регистрируется автоматически при изменении Gold-схемы.

### 2. CI compatibility checks

При каждом PR, затрагивающем Gold-схему, автоматическое сравнение с production-версией. Классификация:

| Изменение | Классификация |
|-----------|---------------|
| Добавление nullable колонки | Compatible |
| Удаление колонки | Breaking |
| INT → BIGINT (расширение) | Compatible |
| DOUBLE → INT (сужение) | Breaking |
| Переименование колонки | Breaking |
| Изменение nullable → NOT NULL | Breaking |

Breaking changes блокируют merge без override от data steward.

### 3. Consumer registry & notification

Таблица `consumer_registry` — каждый notebook/dashboard/сервис регистрирует зависимость от Gold-таблиц и колонок. При breaking change в CI определяется список затронутых consumers, владельцы получают: GitHub mention в PR, Slack notification, описание изменения и рекомендации по миграции.

### 4. Deprecation workflow

Breaking changes требуют deprecation period (по умолчанию 4 недели). Старая и новая колонка сосуществуют, deprecated-поля помечены в metadata и продолжают заполняться. Warning при обращении. Удаление — только после подтверждения миграции всех consumers через registry.

### 5. Schema diff в PR

Автоматический human-readable комментарий в PR: added/removed/modified columns, классификация совместимости, затронутые consumers, required actions.

## Integration with Composite Pipelines

Schema check работает на двух уровнях:

**CI/CD (pre-deploy):** diff новой схемы vs production → блок или pass.

**Runtime (defensive assertion):** в каждой стадии pipeline — защита от drift, который CI не поймал (например, upstream провайдер изменил типы):

```python
@asset
def gold_table(context, silver_data):
    expected = load_from_registry("gold_compounds", version="current")
    result = transform_to_gold(silver_data)

    if not schema_compatible(result.schema, expected):
        raise SchemaBreakingChange(diff(result.schema, expected))
    return result
```

Через lineage graph (Issue #1) schema change автоматически показывает полный blast radius по DAG пайплайна.

## Acceptance Criteria

- [ ] `schema_registry` создан и заполнен для всех существующих Gold-таблиц
- [ ] CI pipeline включает автоматическую проверку backward compatibility
- [ ] Breaking changes блокируют merge без override от data steward
- [ ] `consumer_registry` реализован с API для регистрации зависимостей
- [ ] Notification pipeline нотифицирует владельцев затронутых consumers
- [ ] Deprecation workflow документирован и интегрирован
- [ ] Schema diff автоматически публикуется как комментарий к PR
- [ ] Интеграционные тесты покрывают все типы schema changes
- [ ] ADR-036 обновлён с описанием автоматизированного процесса
