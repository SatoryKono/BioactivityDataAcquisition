# LF1-07: Зафиксировать целевые колонки DQ 9403

## 1. Зафиксированные исходные данные (bioetl-dq-v2/9403)

- **Endpoint:** `/ops/observability/processed-records?pipeline=${selected_pipeline}&run_type=${run_type:csv}&run_id=${selected_run_id}`
- **Target A:** Запрос к `/ops/observability/processed-records` (возвращает JSON в виде таблицы с ключом `rows`). Возвращает `parameter`, `value` (count out), `percentage`, `row_status`.
- **StageInput:** Запрос к `/ops/observability/selected-run-status?pipeline=${selected_pipeline}&run_id=${selected_run_id}`. Парсит `quality_evidence.funnel` и формирует пары `parameter` и `count in` для каждого этапа.
- **Join / Transformations:**
  - `joinByField`: Outer join по `parameter`.
  - `filterByValue`: Исключает строки "05 silver_skipped_records" и "10 gold_skipped_records".
  - `organize`:
    - Исключает: `row_status`, `Time`.
    - Переименовывает: `value` -> `count out`, `count in StageInput` -> `count in`.
    - Порядок колонок: `parameter`, `count in`, `count out`, `percentage`.

## 2. Сопоставление с response schema и F-09

В ответе endpoint'а `processed-records` присутствуют следующие поля для каждой строки (согласно контракту `bioetl_processed_records_table`):
- `parameter`: Название этапа, string, никогда не пустое.
- `value`: Значение счетчика, string (отформатированное число или `"UNKNOWN"`), Null policy: если нет данных или `None`, то возвращается `"UNKNOWN"`.
- `percentage`: Процентное соотношение, string (отформатированное с `%` или `"UNKNOWN"`), Null policy: если нет данных или `None`, то возвращается `"UNKNOWN"`.
- `row_status`: Статус (дефицит), string (например, `"silver_deficit"`, `"gold_deficit"` или `""`), Null policy: `""` при отсутствии дефицита.

В объединенной таблице панели 9403 (после transform) колонки:

| Имя | Тип | Единицы | Порядок | Null policy |
|---|---|---|---|---|
| `parameter` | string | N/A | 1 | Не пустой |
| `count in` | string/integer | N/A (записи) | 2 | Если значение равно null или отсутствует (из-за отсутствия данных в `selected-run-status`), отображается `N/A` (через Grafana value mappings: special null -> UNKNOWN -> N/A, No data -> N/A). |
| `count out` | string | N/A (записи) | 3 | Если значение от бэкенда пришло `"UNKNOWN"`, Grafana map-ит его в `N/A`. Реальный ноль отображается как `0`. |
| `percentage` | string | % (проценты) | 4 | Если значение от бэкенда пришло `"UNKNOWN"`, Grafana map-ит его в `N/A`. Реальный ноль отображается как `0.0%`. |

## 3. Фильтрация skipped-строк и процентное форматирование

- **Фильтрация:** В трансформациях Grafana (`filterByValue`) явно исключаются значения параметра "05 silver_skipped_records" и "10 gold_skipped_records". Это соответствует закрытым задачам #11770/#11569 по сокрытию skipped-строк из визуализации.
- **Процентное форматирование:** Бэкенд форматирует проценты в `format_percentage` (`_processed_records_table_support.py`). Правила:
  - Если знаменатель `constant_100` -> возвращает `100.0%` (для `bronze_records`).
  - Если числитель или знаменатель отсутствует либо знаменатель равен 0, возвращается `"UNKNOWN"`. Нулевой числитель при положительном знаменателе даёт `"0.0%"`.
  - Значение форматируется до 3 знаков после запятой, отбрасывая лишние нули (`0.0%`, `12.5%`, `99.999%`).

## 4. Семантика значений

- **count (реальное значение):** Положительное целое число, полученное из Prometheus / Ledger.
- **percentage (реальное значение):** Форматированное строковое значение, рассчитанное относительно bronze (кроме 0).
- **Отсутствующее значение (No data / UNKNOWN):** Если данные отсутствуют (ни разу не записаны, метрика не инициализирована), бэкенд возвращает `"UNKNOWN"`. В Grafana value mappings `"UNKNOWN"`, `"No data"` и `null` преобразуются в отображаемое значение `N/A`.
- **Реальный ноль:** Бэкенд отдает `"0"` для `value` (count out). Для `percentage` при нулевом `value` и положительном `bronze_records` бэкенд возвращает `"0.0%"`. При отсутствующем значении, отсутствующем или нулевом знаменателе возвращается `"UNKNOWN"`, который Grafana отображает как `N/A`.
- **Источники полей:**
  - `parameter`: жестко задано в контракте `PROCESSED_RECORDS_ROW_SPECS` (бэкенд).
  - `count in`: извлечено через JSONata из поля `quality_evidence.funnel[].records_in` эндпоинта `selected-run-status`.
  - `count out`: поле `value` из эндпоинта `processed-records`.
  - `percentage`: поле `percentage` из эндпоинта `processed-records`.

## 5. Спецификация и примеры

### Спецификация колонок панели 9403:
- **`parameter`** (String): Имя этапа обработки (01 bronze_records ... 11 gold_deduplicated_records, без 05 и 10).
- **`count in`** (String/Int): Количество записей на входе этапа. Источник: `/ops/observability/selected-run-status`. Пустое -> N/A.
- **`count out`** (String): Количество обработанных записей. Источник: `/ops/observability/processed-records`. Пустое/UNKNOWN -> N/A.
- **`percentage`** (String): Процент `count out` от `bronze_records`. Источник: `/ops/observability/processed-records`. Пустое/UNKNOWN -> N/A.

### Пример результата (Теоретическая спецификация)
| parameter | count in | count out | percentage |
|---|---|---|---|
| 01 bronze_records | [count_in value] | [count_out value] | [percentage] |
| 02 silver_valid_records | [count_in value] | [count_out value] | [percentage] |

(строка `05 silver_skipped_records` исключается трансформацией).

## Decision & Evidence
**Source SHA:** `a474a4118bd19288c4315c98a0168a863e7b36ad`
**Deploy SHA:** `NOT_VERIFIABLE`
**Date (UTC):** `2026-11-07 22:30:26 UTC`
**Status:** BLOCKED / NOT_VERIFIABLE. Live observability stack unavailable. Connection refused on 3000 and 8000 ports in the sandbox environment. Original F-Audit records unavailable.
