# Dashboard Design System (BioETL)

Дата актуализации: **2026-05-03**
Источник истины: `grafana/dashboards/*.json`

## 1) Единая семантическая палитра статусов (обязательно)

Для status-панелей (`stat`/`gauge`) применяется фиксированная палитра:

- **OK** → `green`
- **DEGRADED** → `orange`
- **BROKEN** → `red`
- **UNKNOWN** → `gray`

`UNKNOWN` обязателен как явное отображение no-data/null через mapping:
- `null` → текст `UNKNOWN` + цвет `gray`.

## 2) Единые threshold ranges (обязательно)

### 2.1 Stat/Gauge

Для всех status-панелей:

- `fieldConfig.defaults.color.mode = thresholds`
- `fieldConfig.defaults.thresholds.mode = absolute`
- `fieldConfig.defaults.thresholds.steps`:
  1. `{ "color": "green", "value": null }`
  2. `{ "color": "orange", "value": 1 }`
  3. `{ "color": "red", "value": 2 }`

Нормативная интерпретация:

- `0` → OK
- `1` → DEGRADED
- `>=2` → BROKEN
- `null` → UNKNOWN

### 2.2 Time-series

Для time-series, визуализирующих те же статусы, диапазоны MUST совпадать семантически:

- OK: `< 1`
- DEGRADED: `>= 1 and < 2`
- BROKEN: `>= 2`
- UNKNOWN: отсутствие данных/NaN/null отображается как unknown-состояние, а не как OK.

## 3) Единый стиль заголовков и описаний панелей (обязательно)

### 3.1 Заголовок

Шаблон:

`<Субсистема>: <Метрика/Сигнал> [<Окно>]`

Примеры:
- `Runtime: Failure Rate [24h]`
- `Provider Health: Retry Saturation [1h]`

### 3.2 Description

Шаблон:

1. Что измеряется (1 предложение)
2. Как интерпретировать `OK/DEGRADED/BROKEN/UNKNOWN`
3. Если применимо — ссылка на runbook/drilldown

Пример структуры:

- `Measures ...`
- `Status mapping: 0=OK, 1=DEGRADED, >=2=BROKEN, null=UNKNOWN.`
- `Use <dashboard/link> for drilldown.`

## 4) Правило no-data/unknown (обязательно)

- Нельзя молча трактовать no-data как OK для status-панелей.
- Если no-data действительно эквивалентно нулевому событию, это должно быть отражено в query явно (`... or vector(0)`) и подтверждено в description.
- Во всех остальных случаях no-data должен остаться `UNKNOWN`.

## 5) QA Gate

Базовая автоматическая проверка:

```bash
uv run python -m scripts.engineering.qa check-dashboard-visual-semantics
```

Проверка валидирует:

- color mode = `thresholds`
- стандартизованные threshold steps
- обязательный `UNKNOWN` mapping для `null`
