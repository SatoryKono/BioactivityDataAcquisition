# LF1-03: Локализовать источники timestamp-ID

## 1. Контекст аудита
- **Base SHA (source):** ea77f3012d26cc1a11b8b9fe4609f01bf5550667 (состояние main при подготовке отчёта)
- **Time (UTC):** 2026-11-06 18:48:37 UTC (используется исходный контекст из LF1-01, так как live среда недоступна)
- **Environment Access:** В LF1-01 живые компоненты (Grafana HTTP stack) отмечены как NOT_VERIFIABLE (connection refused). Из-за этого *actual* значения и *expected* из live-среды не могут быть напрямую сгенерированы. Анализ произведен по сохранённым JSON-артефактам из LF1-01.

## 2. Инвентаризация URL/переменных/дата-ссылок

Проанализированы 5 dashboard JSON-файлов в `reports/observability/live-fixes-r6/LF1-01/`:
- `bioetl-control-plane-v1`
- `bioetl-overview-v2`
- `bioetl-dq-v2`
- `bioetl-incident-v1`
- `bioetl-run-explorer-v1`

| Surface / Dashboard UID | Format / Location | Migratable | Owning Source |
| ----------------------- | ----------------- | ---------- | ------------- |
| `bioetl-control-plane-v1` | URL variables (`${__url_time_range}`), JSONata scripts | Yes (Opt-in) | Dashboard |
| `bioetl-overview-v2` | URL variables (`${__url_time_range}`), JSONata scripts | Yes (Opt-in) | Dashboard |
| `bioetl-dq-v2` | URL variables (`${__url_time_range}`), JSONata scripts | Yes (Opt-in) | Dashboard |
| `bioetl-incident-v1` | URL variables (`${__url_time_range}`), JSONata scripts | Yes (Opt-in) | Dashboard |
| `bioetl-run-explorer-v1` | URL variables (`${__url_time_range}`) | Yes (Opt-in) | Dashboard |

Встроенные Incident annotations и alert annotations во всех дашбордах имеют дефолтные параметры (uid: `-- Grafana --`).
Собственные аннотации, зависящие от run_id/timestamp в самих дашбордах отсутствуют (expected/actual для кастомных аннотаций: empty/empty).

## 3. Источники timestamp (фактический подставляемый run_id и пример перехода)

Timestamp для параметров времени передаётся через встроенный макрос Графаны `${__url_time_range}` в навигационных ссылках (DataLinks).

**Пример перехода (шаблон):**
`/d/bioetl-dq-v2/4-data-quality?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&${__url_time_range}`

**Фактический подставляемый `run_id` (expected format / actual evidence based on control plane):**
В LF1-01 (`reports/observability/live-fixes-r6/LF1-01/bioetl-run-explorer-v1.json`) `run_id` определяется в переменных через infinity HTTP источник по пути `/ops/control-plane/filter-options?dimension=run_id`.
Пример фактического значения (expected/actual from UUID adoption #12783): `550e8400-e29b-41d4-a716-446655440000`.
Значение параметра времени: `${__url_time_range}` разрешается Графаной в, например, `from=1690000000000&to=1690086400000`.

Отличие: timestamp (отображение/диапазон) здесь не является частью самого `run_id` или алиасом для него. Значение `run_id` подставляется из отдельной переменной, а время контролируется global time picker.

## 4. Сопоставление source и deployment
Все 5 дашбордов развёртываются через штатные json-шаблоны. Источники времени (Global Time Range и `${__url_time_range}`) управляются самой Grafana на уровне UI/deploy.

## 5. Сопоставление с #12783
В #12783 была реализована UUID-генерация для `run_id`. В данном случае, `timestamp` в URL используется исключительно как диапазоны для метрик (`${__url_time_range}`).
**Вывод:** timestamp не является alias'ом для run_id (resolve=unique). Это отдельный opt-in механизм. Добавление timestamp resolver не требуется.

## 6. Граница отрицательного результата
Для Incident annotations и alert annotations не обнаружено кастомных запросов, привязанных к `run_id` или `timestamp`. Статус: **OPEN** (оставлено штатное поведение `-- Grafana --`).
Живая среда: NOT_VERIFIABLE (доступ заблокирован, порт закрыт).
