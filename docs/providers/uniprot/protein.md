# Пайплайн: UniProt Protein

**Имя пайплайна:** `uniprot_protein`
**Провайдер:** `uniprot`
**Сущность:** `protein`

## 1. Описание

Этот пайплайн извлекает данные о белках (`protein`) из API UniProt.

## 2. Конфигурация

**Источник конфигурации:** `configs/pipelines/uniprot/protein.yaml`

| Параметр | Значение | Описание |
|---|---|---|
| `pipeline_name` | `uniprot_protein` | Уникальное имя пайплайна. |
| `provider` | `uniprot` | Имя провайдера данных. |
| `entity_type` | `protein` | Тип извлекаемой сущности. |
| `primary_keys` | `["accession"]` | Ключи для слияния в Silver-слое. |

## 3. Процесс (ETL)

### 3.1. Extract

- **Источник:** UniProt REST API.
- **Стратегия:** `incremental` по `accession`.
- **Rate Limit:** 10 запросов в секунду.

### 3.2. Transform

- Дедупликация записей.
- Валидация схемы.

### 3.3. Load

| Слой | Формат | Стратегия | Таблица/Путь |
|---|---|---|---|
| **Bronze** | `jsonl` (сжатый `zstd`) | Append-only | `bronze/uniprot/protein/...` |
| **Silver** | `delta` | Merge (по `accession`) | `uniprot_protein` |
| **Gold** | `delta` | - | `dim_target` |

## 4. Качество Данных (DQ)

- **Strict Mode:** `false` — ошибки валидации не приведут к падению пайплайна, а будут отправлены в карантин.
