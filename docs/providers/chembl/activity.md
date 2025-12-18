# Пайплайн: ChEMBL Activity

**Имя пайплайна:** `chembl_activity`
**Провайдер:** `chembl`
**Сущность:** `activity`

## 1. Описание

Этот пайплайн извлекает данные о биологической активности (`activity`) из API ChEMBL.

## 2. Конфигурация

**Источник конфигурации:** `configs/pipelines/chembl/activity.yaml`

| Параметр | Значение | Описание |
|---|---|---|
| `pipeline_name` | `chembl_activity` | Уникальное имя пайплайна. |
| `provider` | `chembl` | Имя провайдера данных. |
| `entity_type` | `activity` | Тип извлекаемой сущности. |
| `primary_keys` | `["activity_id"]` | Ключи для слияния в Silver-слое. |

## 3. Процесс (ETL)

### 3.1. Extract

- **Источник:** ChEMBL API.
- **Стратегия:** Определяется в `configs/sources/chembl.yaml`.

### 3.2. Transform

- Нормализация значений.
- Добавление метаданных о запуске.
- Расчет `content_hash` для дедупликации.

### 3.3. Load

| Слой | Формат | Стратегия | Путь |
|---|---|---|---|
| **Bronze** | `jsonl` | Append-only | `data/output/bronze` |
| **Silver** | `delta` | Merge (по `activity_id`) | `data/output/silver` |
| **Gold** | `delta` | Overwrite | `data/output/gold` |

## 4. Качество Данных (DQ)

- **Soft Fail Threshold:** `5%` — при превышении этого порога ошибок в батче будет выведено предупреждение.
- **Hard Fail Threshold:** `20%` — при превышении этого порога батч будет помечен как сбойный.
