# Dashboard Extension Guide (Human)

Дата сверки: **2026-03-29**  
Источник истины: `grafana/dashboards/*.json`

Короткий guide для инженера, который вручную расширяет shipped Grafana dashboards
в BioETL.

## 1. Текущая карта дашбордов

- `1. Overview` (`bioetl-overview-v2`) — главный hub. Держит ссылки на `2. Runtime`, `3. Provider Health`, `4. Data Quality`, а также `Explore Logs (Loki)` и `Explore Traces (Tempo)`.
- `2. Runtime` (`bioetl-runtime`) — runtime triage surface. Держит `Back to Overview` и Explore links.
- `3. Provider Health` (`bioetl-provider-health-v2`) — health-check surface по провайдерам. Держит `Back to Overview` и Explore links.
- `4. Data Quality` (`bioetl-dq-v2`) — DQ surface. Держит `Back to Overview` и Explore links.

## 2. Когда расширять существующий дашборд, а когда создавать новый

- Расширяйте существующий dashboard, если новая панель логически продолжает его текущую роль.
- Создавайте новый dashboard только если появляется отдельный operator workflow, который плохо помещается в `Overview` / `Runtime` / `Provider Health` / `Data Quality`.
- Не используйте docs как источник истины для panel IDs, links и query. Сначала откройте сам JSON.

## 3. Что менять безопасно

1. Откройте целевой JSON в `grafana/dashboards/`.
1. Сохраните `uid`, `templating`, `refresh`, `time` и общую роль dashboard, если изменение не требует отдельного migration decision.
1. Добавляйте панели с низкой кардинальностью.
1. Для event-driven stat panels используйте явный zero-fallback, если отсутствие серии означает “0”, а не “ошибка данных”.
1. Для Loki/Tempo drilldown сохраняйте общие shipped conventions.

## 4. Рабочие конвенции

### Навигация

- `1. Overview`: `2. Runtime` → `3. Provider Health` → `4. Data Quality`
- Остальные shipped dashboards: `Back to Overview`
- Explore links не заменяют dashboard links, а дополняют их

### Prometheus

- Если пустая серия означает отсутствие события, а не деградацию источника, используйте:

```promql
sum(increase(metric_name[24h])) or vector(0)
```

- Не добавляйте high-cardinality labels в summary/stat panels без необходимости.

### Loki

- Базовый handoff:

```logql
{job="bioetl"}
```

- Не полагайтесь на encoded interpolation `$pipeline/$provider` внутри `left=...`.

### Tempo

- Базовый handoff:

```text
queryType = traceqlSearch
query = {}
```

- Correlation идёт через `trace_id` / `span_id`, а не через Prometheus labels.

## 5. Минимальная проверка после изменений

```bash
./.venv/Scripts/python.exe -m json.tool grafana/dashboards/<dashboard>.json
./.venv/Scripts/python.exe -m pytest -q tests/integration/test_grafana_config.py
```

Если менялись названия, порядок дашбордов, links, time ranges или operator flow,
обновите минимум:

- `docs/03-guides/dashboards/README.md`
- `docs/03-guides/dashboards/monitoring-index.md`
- `docs/03-guides/dashboards/dashboard-v2-usage.md`
- `docs/05-operations/01-monitoring-guide.md`
- `grafana/README.md`

## 6. Definition of Done

- JSON валиден.
- Навигация соответствует текущему shipped flow.
- Панели не вводят оператора в заблуждение `No data`, если корректное состояние — `0`.
- `tests/integration/test_grafana_config.py` проходит.
- Документация синхронизирована, если operator surface изменился.
