______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-13'

______________________________________________________________________

# Dashboard Extension Guide (Human)

Дата сверки: **2026-07-13**
Источник истины: `grafana/dashboards/*.json`

Короткий guide для инженера, который вручную расширяет shipped Grafana dashboards
в BioETL.

## 1. Текущая карта дашбордов

- `0. Control Plane` (`bioetl-control-plane-v1`) — deep-dive по reproducibility/control-plane paths.
- `1. Overview` (`bioetl-overview-v2`) — L0 answer-first hub.
- `2. Runtime` (`bioetl-runtime`) — runtime triage surface.
- `3. Provider Health` (`bioetl-provider-health-v2`) — provider incident surface по health checks/retries.
- `4. Data Quality` (`bioetl-dq-v2`) — DQ surface.
- `5. Workflow` (`bioetl-workflow-overview`) — workflow run/step outcomes.

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

- Top-level шина: `0. Control Plane` / `1. Overview` / `2. Runtime` /
  `3. Provider Health` / `4. Data Quality` / `5. Workflow` /
  `6. Alerts & SLO`.
- На текущей странице текущий dashboard остаётся видимым в navigation panel
  `id=1000` как disabled theme-safe item; machine-readable `panel.links`
  по-прежнему не содержат self-link. Полная навигация читаема в dark/light
  themes и переносится без обрезки на viewport `1024px`.
- Любые дубли dashboard-to-dashboard links из одного dashboard в один target
  dashboard запрещены.
- Во всех восьми shipped navigation panels `id=1000` после bus `0..6`
  закреплены
  global adjunct links `Silver Reject Explorer`, `Explore Logs`,
  `Explore Traces`.
- Navigation panel links должны открываться в том же окне; не используйте
  `target="_blank"` в HTML top navigation.
- Иерархия layout следует design system tiers:
  `Tier 1` answer row,
  `Tier 2` current-context support,
  `Tier 3` selected-range evidence below fold,
  `Tier 4` diagnostic/detail rows below fold. Tier 4 row-группы шиппятся
  collapsed by default; полный render/audit явно раскрывает их, когда нужно
  проверить secondary/noisy detail.

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

- Базовый handoff должен быть contextual:

```text
queryType = traceqlSearch
query = { span."bioetl.pipeline" =~ "${pipeline:regex}" }
```

- Для provider-only surface используйте:

```text
query = { span."bioetl.provider" =~ "${provider:regex}" }
```

- Correlation по-прежнему идёт через `trace_id` / `span_id`, но shipped Explore handoff должен уже открываться в текущем dashboard scope, а не с пустым `{}`.

## 5. Минимальная проверка после изменений

```bash
uv run python -m json.tool grafana/dashboards/<dashboard>.json
uv run python -m pytest -q tests/integration/test_grafana_config.py
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

## 8. Visual consistency gates

Перед merge каждый изменённый dashboard MUST пройти чеклист:

- [ ] Для всех `stat`/`gauge` панелей используется единый `color.mode=thresholds`.
- [ ] Для всех `stat`/`gauge` панелей используется единый `thresholds.steps`: green/null, orange/1, red/2.
- [ ] Для всех status-панелей задано единое no-data поведение: `null -> UNKNOWN (gray)`.
- [ ] Для терминов статусов применяется единая таблица mapping из `docs/03-guides/dashboards/design-system.md` (раздел **1.1 Canonical mapping: L0 vs diagnostic dashboards**).
- [ ] В L0 dashboards используется только `OK/WARN/CRIT/UNKNOWN`; alias-термины (`DEGRADED/BROKEN/HEALTHY`) допустимы только в диагностических deep-dive поверхностях и с явным alias mapping в description.
- [ ] Для Prometheus current-status/current-cause panels не используется invalid `or vector(0)`; missing telemetry остаётся `UNKNOWN`.
- [ ] Для HTTP-backed forensic panels copy различает empty result, invalid filter chain и backend failure.
- [ ] Для схожих KPI в разных dashboards совпадают `unit` и `decimals` (например, event counts = `short/0`, timestamps = `dateTimeAsIso/0`).
- [ ] Заголовки новых/переименованных панелей соответствуют action-first шаблону (`Monitor/Inspect/Track/...: ...`).
- [ ] Заголовки и описания новых панелей соответствуют шаблонам из design system.
- [ ] Пройдена автоматическая проверка:

```bash
uv run python -m scripts.engineering.qa check-dashboard-visual-semantics
```
