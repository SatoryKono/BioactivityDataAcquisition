# Политика файлов и директорий

*Синхронизировано с RULES.md v5.20 | Последнее обновление: 2026-01-14*

---

## Обзор

Данный документ описывает политику организации файлов и директорий проекта BioETL,
включая иерархию конфигураций и структуру выходных данных. Правила именования
классов и переменных вынесены в [02-naming-policy.md](02-naming-policy.md).

---

## 1. Структура Конфигураций Pipeline

### 1.1. Иерархия файлов

```
configs/
├── pipelines/
│   ├── _base.yaml            # Унифицированная базовая схема (v2.0.0)
│   ├── _schema.json         # JSON Schema для валидации конфигов
│   ├── _providers/          # Документация провайдеров
│   │   ├── chembl.yaml
│   │   ├── pubchem.yaml
│   │   └── ...
│   └── <provider>/          # Entity-специфичные конфиги
│       └── <entity>.yaml
└── sources/
    └── <provider>.yaml      # Настройки API провайдера
```

### 1.2. Цепочка наследования

```
_base.yaml (базовые значения) → <provider>/<entity>.yaml (переопределения)
```

**Примечание**: `_base.yaml` является каноническим файлом для всех базовых настроек
пайплайнов (v2.0.0).

### 1.3. Обязательные поля entity config

Каждый entity config (`<provider>/<entity>.yaml`) **MUST** содержать:

| Поле | Описание | Пример |
|------|----------|--------|
| `pipeline_name` | Уникальный идентификатор `{provider}_{entity}` | `chembl_activity` |
| `provider` | Имя провайдера | `chembl` |
| `entity_type` | Тип сущности | `activity` |
| `version` | Семантическая версия | `"1.1.0"` |
| `primary_keys` | Первичный ключ | `["activity_id"]` |
| `silver_table` | Имя Silver-таблицы | `chembl_activity` |
| `gold_table` | Имя Gold-таблицы | `chembl_activity` |
| `sink` | Пути к слоям с `sort_by` | См. ниже |

### 1.4. Валидация конфигураций

Все entity configs валидируются через `_schema.json`:

```bash
# Pre-commit hook автоматически проверяет конфиги
# Ручная валидация:
python -c "import json, yaml, jsonschema; \
  schema = json.load(open('configs/pipelines/_schema.json')); \
  config = yaml.safe_load(open('configs/pipelines/chembl/activity.yaml')); \
  jsonschema.validate(config, schema)"
```

---

## 2. Иерархия путей для данных

### 2.1. Паттерн путей

Все выходные данные следуют иерархической структуре:

```
data/output/{layer}/{provider}/{entity}/
```

| Слой | Паттерн пути | Пример |
|------|--------------|--------|
| **Bronze** | `data/output/bronze/{provider}/{entity}/` | `data/output/bronze/chembl/activity/` |
| **Silver** | `data/output/silver/{provider}/{entity}/` | `data/output/silver/chembl/activity/` |
| **Gold** | `data/output/gold/{provider}/{entity}/` | `data/output/gold/chembl/activity/` |
| **CSV (Silver)** | `data/output/csv/silver/{provider}/{entity}/` | `data/output/csv/silver/chembl/activity/` |
| **CSV (Gold)** | `data/output/csv/gold/{provider}/{entity}/` | `data/output/csv/gold/chembl/activity/` |

### 2.2. Пример конфигурации sink

```yaml
sink:
  bronze:
    path: "data/output/bronze/chembl/activity"
  silver:
    path: "data/output/silver/chembl/activity"
    primary_key: ["activity_id"]
    partition_by: []
    sort_by:
      columns: ["activity_id"]
      ascending: true
    csv_export:
      path: "data/output/csv/silver/chembl/activity"
  gold:
    path: "data/output/gold/chembl/activity"
    sort_by:
      columns: ["activity_id"]
      ascending: true
    csv_export:
      path: "data/output/csv/gold/chembl/activity"
```

### 2.3. Обязательность sort_by (ADR-014)

**MUST**: Все entity configs должны содержать `sort_by` для Silver и Gold слоёв.

Это требование обеспечивает:
- Детерминизм выходных данных
- Воспроизводимость при повторных запусках
- Стабильность diff-сравнений

См. [ADR-014: Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md).

---

## 3. Соглашения об именовании

### 3.1. Pipeline идентификаторы

| Паттерн | Описание | Пример |
|---------|----------|--------|
| `{provider}_{entity}` | Стандартный формат | `chembl_activity` |
| `{provider}_{entity}_{variant}` | С вариантом | `chembl_publication_term` |

**НЕ используется**: `{entity}_{provider}` (например, `activity_chembl`)

### 3.2. Имена таблиц

Silver и Gold таблицы используют тот же паттерн:

```yaml
silver_table: "chembl_activity"
gold_table: "chembl_activity"
```

---

## 4. Файлы источников (sources)

### 4.1. Структура

```
configs/sources/<provider>.yaml
```

Содержит настройки API провайдера:
- `base_url` — базовый URL API
- `rate_limit` — лимиты запросов
- `timeout` — таймауты
- `retry` — настройки повторов
- `circuit_breaker` — настройки Circuit Breaker

### 4.2. Ссылка из entity config

```yaml
source_file: ../../sources/chembl.yaml
```

---

## 5. Политика очистки

| Слой | Retention | Примечание |
|------|-----------|------------|
| Bronze | 90 дней | Автоматическая архивация |
| Silver | Постоянно | Delta Lake VACUUM (7 дней) |
| Gold | Постоянно | Delta Lake VACUUM (7 дней) |

См. [RULES.md §2.1.1](../RULES.md) для деталей политики retention.

---

## 6. Миграция и обратная совместимость

### 6.1. История изменений

| Версия | Дата | Изменение |
|--------|------|-----------|
| 2.0.0 | 2026-01-14 | Унификация `_defaults.yaml`, удаление `_base.yaml` |
| 2.0.0 | 2026-01-14 | Иерархические пути `{layer}/{provider}/{entity}` |
| 2.0.0 | 2026-01-14 | Обязательный `sort_by` во всех entity configs |
| 2.0.0 | 2026-01-14 | JSON Schema валидация через `_schema.json` |

### 6.2. Проверка соответствия

```bash
# Проверить все конфиги
make validate-configs

# Или вручную через pre-commit
pre-commit run validate-pipeline-configs --all-files
```

---

## Связанные документы

- [RULES.md](../RULES.md) — Конституция проекта
- [ADR-014: Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-025: Pipeline Config Unification](../02-architecture/decisions/ADR-025-pipeline-config-unification.md)
- [04-extending-bioetl.md](04-extending-bioetl.md) — Добавление новых pipeline

---

*Последнее обновление: 2026-01-14*
