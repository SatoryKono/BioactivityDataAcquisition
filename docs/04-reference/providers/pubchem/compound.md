# Пайплайн: PubChem Compound

**Имя пайплайна:** `pubchem-compound`
**Провайдер:** `pubchem`
**Сущность:** `compound`

## 1. Описание

Этот пайплайн извлекает данные о химических соединениях (`compound`) из API PubChem.

## 2. Конфигурация

**Источник конфигурации:** `configs/entities/pubchem/compound.yaml`

| Параметр | Значение | Описание |
|---|---|---|
| `pipeline-name` | `pubchem-compound` | Уникальное имя пайплайна. |
| `provider` | `pubchem` | Имя провайдера данных. |
| `entity-type` | `compound` | Тип извлекаемой сущности. |
| `primary-keys` | `["cid"]` | Ключи для слияния в Silver-слое. |

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
| **Silver** | `delta` | Merge (по `cid`) | `pubchem-compound` |
| **Gold** | `delta` | - | `dim-compound` |

## 4. Качество Данных (DQ)

- **Strict Mode:** `false` — ошибки валидации не приведут к падению пайплайна, а будут отправлены в карантин.

## 5. См. также

- [Running Pipelines](../../../03-guides/running-pipelines.md) - Запуск пайплайнов
- [ChEMBL Activity](../chembl/activity.md) - Детальная документация (пример)
- [Project Rules](../../../00-project/RULES.md) - Правила обработки данных
