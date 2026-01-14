# ADR-025: Pipeline Configuration Unification

**Status**: Accepted
**Date**: 2026-01-14 (Updated)
**Authors**: Claude Code
**Reviewers**: -

## Context

Pipeline configs имели следующие проблемы:
1. Дублирование между `_base.yaml` и `_defaults.yaml`
2. Плоские пути без иерархии `{provider}/{entity}`
3. Отсутствие `sort_by` у 78% entity configs (нарушение ADR-014)
4. Нестандартные `batch_size` без документации
5. Отсутствие автоматической валидации конфигов

## Decision

### 1. Унифицированный _defaults.yaml (v2.0.0)

Файл `_base.yaml` удалён, его содержимое объединено с `_defaults.yaml`:

```
configs/
├── pipelines/
│   ├── _defaults.yaml       # Unified Base Schema v2.0.0 (единый источник)
│   ├── _schema.json         # JSON Schema для валидации (NEW)
│   ├── _providers/          # Provider documentation
│   │   ├── chembl.yaml
│   │   ├── pubchem.yaml
│   │   └── ...
│   └── <provider>/
│       └── <entity>.yaml    # Entity-specific configs
└── sources/
    └── <provider>.yaml      # Provider-level API settings
```

**Rationale**: Единый источник defaults устраняет рассинхронизацию.

### 2. Иерархические пути для данных

Введён стандартный паттерн путей:

```
data/output/{layer}/{provider}/{entity}/
```

| Слой | Паттерн | Пример |
|------|---------|--------|
| Bronze | `data/output/bronze/{provider}/{entity}/` | `data/output/bronze/chembl/activity/` |
| Silver | `data/output/silver/{provider}/{entity}/` | `data/output/silver/chembl/activity/` |
| Gold | `data/output/gold/{provider}/{entity}/` | `data/output/gold/chembl/activity/` |
| CSV | `data/output/csv/{layer}/{provider}/{entity}/` | `data/output/csv/silver/chembl/activity/` |

**Rationale**: Консистентная структура упрощает навигацию и автоматизацию.

### 3. Обязательный sort_by (ADR-014 compliance)

**MUST**: Все entity configs содержат `sort_by` для Silver и Gold слоёв:

```yaml
sink:
  silver:
    sort_by:
      columns: ["primary_key_column"]
      ascending: true
  gold:
    sort_by:
      columns: ["primary_key_column"]
      ascending: true
```

**Rationale**: Детерминизм выходных данных, воспроизводимость результатов.

### 4. JSON Schema валидация

Добавлен `_schema.json` для автоматической валидации:

```bash
# Pre-commit hook
python scripts/validate_pipeline_configs.py

# Ручная проверка
make validate-configs
```

Schema проверяет:
- Наличие обязательных полей (`pipeline_name`, `provider`, `sink`, etc.)
- Формат `pipeline_name` (`^[a-z]+_[a-z_]+$`)
- Допустимые значения `provider` (enum)
- Структуру `sink` с `sort_by`

### 5. Flat Naming Convention: `<provider>_<entity>`

Сохранён существующий паттерн именования:

**Rationale**:
- Консистентность по всем 20 конфигам
- Группировка по провайдеру в листингах
- Соответствует структуре `configs/pipelines/{provider}/`

## Consequences

### Positive

1. **Единый источник defaults**: `_defaults.yaml` v2.0.0 — нет дублирования
2. **Детерминизм выходных данных**: `sort_by` во всех entity configs (ADR-014)
3. **Автоматическая валидация**: JSON Schema + pre-commit предотвращает регрессии
4. **Консистентные пути**: `{layer}/{provider}/{entity}` упрощает навигацию
5. **Provider knowledge captured**: API limits, auth requirements documented

### Negative

1. **Breaking change для путей**: Существующие данные требуют миграции
   - Mitigated: Скрипт миграции `scripts/migrate_data_paths.py`

### Neutral

1. **20 entity configs обновлены**: Все содержат `sort_by` и иерархические пути

## Alternatives Considered

### A. Сохранить два файла defaults

Оставить `_base.yaml` и `_defaults.yaml` раздельно.

**Rejected**: Дублирование и риск рассинхронизации.

### B. YAML Anchors for Inheritance

Use YAML anchors/aliases for config inheritance:
```yaml
<<: *defaults
pipeline_name: chembl_activity
```

**Rejected**: Requires config loader changes. Current file-based inheritance works.

### C. Плоские пути без иерархии

Оставить пути вида `data/output/bronze/` без `{provider}/{entity}`.

**Rejected**: Сложно навигировать при 20+ pipelines.

## Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| `sink.silver.format: delta` | PASS | All configs inherit from defaults |
| `sink.silver.primary_key` | PASS | All entity configs specify |
| `dq_rules` thresholds | PASS | 0.05/0.20 in defaults |
| `circuit_breaker` settings | PASS | 5/300 in defaults |
| `rate_limit` per provider | PASS | In source configs |
| No hardcoded secrets | PASS | Uses `${ENV_VAR}` syntax |

## References

- [RULES.md v5.10, Appendix D](../../../RULES.md) - Reference schema
- [ADR-014: Deterministic Writes](ADR-014-deterministic-writes.md) - sort_by requirement
- [03-file-policy.md](../../00-project_rules/03-file-policy.md) - File structure documentation
- [04-extending-bioetl.md](../../00-project_rules/04-extending-bioetl.md) - Entity config template
- [configs/pipelines/_schema.json](../../../configs/pipelines/_schema.json) - JSON Schema
- [configs/pipelines/_defaults.yaml](../../../configs/pipelines/_defaults.yaml) - Unified defaults v2.0.0

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-01-13 | Claude Code | Initial version |
| 2026-01-14 | Claude Code | Updated: _base.yaml merged into _defaults.yaml v2.0.0 |
| 2026-01-14 | Claude Code | Added: Hierarchical paths `{layer}/{provider}/{entity}` |
| 2026-01-14 | Claude Code | Added: Mandatory `sort_by` for ADR-014 compliance |
| 2026-01-14 | Claude Code | Added: JSON Schema validation via `_schema.json` |
