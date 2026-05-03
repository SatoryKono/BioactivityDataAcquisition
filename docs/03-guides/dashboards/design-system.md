# Dashboard Design System (BioETL)

Дата актуализации: **2026-05-03**
Источник истины: `grafana/dashboards/*.json`

## 1) Единая семантика статусов OK/WARN/CRIT/UNKNOWN (обязательно)

Для status-панелей (`stat`/`gauge`) применяется фиксированная палитра:

- **OK** → `green`
- **WARN** → `orange`
- **CRIT** → `red`
- **UNKNOWN** → `gray`

`UNKNOWN` обязателен как явное отображение no-data/null через mapping:
- `null` → текст `UNKNOWN` + цвет `gray`.

### 1.1 Canonical mapping: L0 vs diagnostic dashboards

| Dashboard surface | Numeric range | Canonical status term | Visualization color |
| --- | --- | --- | --- |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `0` | `OK` | `green` |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `1` | `WARN` | `orange` |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `>=2` | `CRIT` | `red` |
| **L0 operator dashboards** (`1. Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`) | `null` | `UNKNOWN` | `gray` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `<1` | `OK` *(alias `HEALTHY` optional)* | `green` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `>=1 and <2` | `WARN` *(alias `DEGRADED` optional)* | `orange` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `>=2` | `CRIT` *(alias `BROKEN` optional)* | `red` |
| **Diagnostic dashboards only** (drilldown / deep-dive) | `null` / no data | `UNKNOWN` | `gray` |

Норматив:
- В **L0 operator dashboards** MUST использоваться только термины `OK/WARN/CRIT/UNKNOWN`.
- Термины `DEGRADED/BROKEN/HEALTHY` допускаются только в диагностических deep-dive поверхностях и MUST быть явно привязаны к этой таблице.
- Если в диагностическом UI используются alias-термины, в description MUST присутствовать строка вида `Alias mapping: DEGRADED=WARN, BROKEN=CRIT`.

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
- `1` → WARN
- `>=2` → CRIT
- `null` → UNKNOWN

### 2.2 Time-series

Для time-series, визуализирующих те же статусы, диапазоны MUST совпадать семантически:

- OK: `< 1`
- DEGRADED: `>= 1 and < 2`
- BROKEN: `>= 2`
- UNKNOWN: отсутствие данных/NaN/null отображается как unknown-состояние, а не как OK.

## 3) Единый стиль заголовков и описаний панелей (обязательно)

### 3.1 Заголовок (action-first)

Шаблон:

`<Action Verb>: <Object/Signal> [<Window>]`

Примеры:
- `Monitor: Runtime Failure Rate [24h]`
- `Inspect: Provider Retry Saturation [1h]`
- `Track: Latest Successful Data Timestamp`

Требование: все новые панели MUST использовать action-first заголовки с глаголом в начале (`Monitor`, `Inspect`, `Track`, `Compare`, `Review`).

### 3.2 Description

Шаблон:

1. Что измеряется (1 предложение)
2. Как интерпретировать `OK/WARN/CRIT/UNKNOWN`
3. Если применимо — ссылка на runbook/drilldown

Пример структуры:

- `Measures ...`
- `Status mapping: 0=OK, 1=WARN, >=2=CRIT, null=UNKNOWN.`
- `Use <dashboard/link> for drilldown.`

## 4) Правило no-data/unknown (обязательно)

- Нельзя молча трактовать no-data как OK для status-панелей.
- Если no-data действительно эквивалентно нулевому событию, это должно быть отражено в query явно (`... or vector(0)`) и подтверждено в description.
- Во всех остальных случаях no-data должен остаться `UNKNOWN`.

## 5) Единый unit/decimals для схожих KPI (обязательно)

- Для счётчиков событий (`... Missing`, `... Incompatibilities`, `... Failures`) использовать `unit=short`, `decimals=0`.
- Для timestamp KPI (`Latest Successful Data Timestamp` и аналогичные) использовать `unit=dateTimeAsIso`, `decimals=0`.
- Для долей/процентов (`... Rate`, `... Ratio`) использовать единый unit внутри dashboard-семейства (`percentunit` или `percent`) и согласованный `decimals` (обычно `0` или `2`).
- Схожий KPI в разных dashboards MUST иметь одинаковую пару `unit/decimals`.

## 6) QA Gate

Базовая автоматическая проверка:

```bash
uv run python -m scripts.engineering.qa check-dashboard-visual-semantics
```

Проверка валидирует:

- color mode = `thresholds`
- стандартизованные threshold steps
- обязательный `UNKNOWN` mapping для `null`

## 7) UI-лексика навигации (обязательно)

Источник фиксированного словаря для `links[].title`: `docs/03-guides/dashboards/navigation-contract.md`.

Правила:
- Названия top-level ссылок MUST совпадать с каноническими строками из navigation contract (например: `Back to Overview`, `2. Runtime`, `3. Provider Health`, `4. Data Quality`, `5. Silver Reject Explorer`, `Control Plane v1`, `6. Workflow Overview`).
- Explore-ссылки MUST использовать полные названия: `Explore Logs (Loki, tracing profile)` и `Explore Traces (Tempo, tracing profile)`.
- Формулировки вида `Explore Logs`, `Explore Traces`, `Next Recommended Drilldown` считаются legacy-лексикой и не допускаются в shipped dashboards.

## 8) JSON invariant: timezone (обязательно)

Для всех shipped dashboards в `grafana/dashboards/*.json` применяется единый JSON-invariant:

- корневое поле `timezone` MUST быть `"browser"`.

Пример:

```json
{
  "timezone": "browser"
}
```
