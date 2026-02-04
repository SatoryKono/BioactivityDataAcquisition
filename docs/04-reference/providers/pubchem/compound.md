# Пайплайн: PubChem Compound

**Имя пайплайна:** `pubchem_compound`
**Провайдер:** `pubchem`
**Сущность:** `compound`

## 1. Описание

Этот пайплайн извлекает данные о химических соединениях (`compound`) из API PubChem.

## 2. Конфигурация

**Источник конфигурации:** `configs/pipelines/pubchem/compound.yaml`

| Параметр | Значение | Описание |
|---|---|---|
| `pipeline_name` | `pubchem_compound` | Уникальное имя пайплайна. |
| `provider` | `pubchem` | Имя провайдера данных. |
| `entity_type` | `compound` | Тип извлекаемой сущности. |
| `primary_keys` | `["cid"]` | Ключи для слияния в Silver-слое. |

## 3. Процесс (ETL)

### 3.1. Extract

- **Источник:** PubChem PUG REST API.
- **Стратегия:** `incremental` по `cid`.
- **Rate Limit:** 5 запросов в секунду.

### 3.2. Transform

- Дедупликация записей.
- Валидация схемы.

### 3.3. Load

| Слой | Формат | Стратегия | Таблица/Путь |
|---|---|---|---|
| **Bronze** | `jsonl` (сжатый `zstd`) | Append-only | `bronze/pubchem/compound/...` |
| **Silver** | `delta` | Merge (по `cid`) | `pubchem_compound` |
| **Gold** | `delta` | - | `dim_compound` |

## 4. Качество Данных (DQ)

- **Strict Mode:** `false` — ошибки валидации не приведут к падению пайплайна, а будут отправлены в карантин.

## 5. См. также

- [Running Pipelines](../../03-guides/running-pipelines.md) - Запуск пайплайнов
- [ChEMBL Activity](../chembl/activity.md) - Детальная документация (пример)
- [Project Rules](../../RULES.md) - Правила обработки данных
