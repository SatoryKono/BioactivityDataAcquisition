# #10246 — семантика empty-state для Provider Health (блокирующее решение stream 1)

Date: 2026-09-09
Branch: `codex/grafana-10258-remediation`
Issue: https://github.com/SatoryKono/BioactivityDataAcquisition/issues/10246
Нормативная база: `DASH-STATE-001`, `DASH-STATE-003`, `DASH-STATE-004`,
`DASH-ZERO-001` (`docs/01-requirements/DASHBOARD_REQUIREMENTS.md`).

Этот memo — единственный источник истины по empty-state семантике для
дочерних задач #10251 (runtime) и #10253 (DQ). Решение зафиксировано, его
**нельзя** пересматривать в дочерних задачах.

## 0. Базовый инвариант

Панель рендерит **ровно одно подтверждённое состояние на один просмотр**.
Формулировки вида «UNKNOWN … или VALID EMPTY, если …» запрещены во всех
операторских текстах (`noValue`, `description`, HTML-copy). Если два состояния
неразличимы по доступным панели доказательствам — состояние **UNKNOWN**.

Таксономия состояний: `POPULATED` · `VALID EMPTY` · `UNKNOWN`
(подкласс `TELEMETRY MISSING`) · `QUERY ERROR` · `SELECT RUN` · `N/A`.

## 1. Когда разрешено VALID EMPTY

`VALID EMPTY` разрешено **только** если панель сама доказывает покрытие
телеметрии. Требуются одновременно все условия:

1. требуемый series/семейство метрик **присутствует** для селектора панели
 (наличие доказано в самом запросе, а не предполагается);
1. записанный статус — OK/complete для **всех** сущностей в области панели
 (для fleet-панелей: ни один provider не выше OK и ни один не в состоянии
 `3 = UNKNOWN`);
1. **нет** активной строки-причины (`cause`, blocker, reason);
1. для `noValue`-копии дополнительно: нулевое число фреймов физически
 **не может** означать «телеметрии нет» (в запросе встроено доказательство
 присутствия). Иначе `VALID EMPTY` в `noValue` запрещено.

Отсутствующий, устаревший или частично покрытый series **никогда** не
`VALID EMPTY`. `VALID EMPTY` — не зелёный «здоровый ноль», а подтверждённое
«доказано пусто».

## 2. Когда обязателен UNKNOWN

`UNKNOWN` — состояние fail-closed по умолчанию. Обязательно, когда:

1. покрытие не доказано из собственных доказательств панели;
1. «нет причин» и «нет телеметрии» неразличимы (главный случай #10246 H1);
1. часть области панели «тёмная» (например, хотя бы один provider в
 `bioetl_provider_current_status == 3`) — fleet-вердикт не может быть
 частично доказанным;
1. series присутствует, но устарел (stale) относительно окна свежести;
1. панель — verdict-карточка первого экрана (`stat` + `colorMode=background`):
 по `DASH-STATE-003` её `noValue` **обязан** быть строкой `UNKNOWN…`;
 контекстные `VALID EMPTY` / `SELECT RUN` там запрещены.

`UNKNOWN` всегда сопровождается: (a) указанием, что именно не доказано,
(b) следующим действием, (c) диагностической ссылкой на панель свежести или
покрытия. Цвет — gray, никогда green.

## 3. Когда обязателен TELEMETRY MISSING

`TELEMETRY MISSING` — **уточнение внутри класса UNKNOWN**, не отдельный
«здоровый» класс. Обязателен, когда отсутствие доказано на уровне series:
запрос панели — прямой selector/threshold по одному требуемому семейству
метрик, и ноль фреймов означает «семейство не эмитится для этого селектора»
(эталон: `9112 Inspect Full Non-OK Providers`).

Правила:

- `empty_state_class` остаётся `telemetry_missing`;
- цвет gray, fail-closed, никогда не ноль и никогда не `VALID EMPTY`;
- запрещён на verdict-карточках (`DASH-STATE-003` требует там литерал
 `UNKNOWN`);
- запрещено соединять с `VALID EMPTY` в одной строке.

`TELEMETRY MISSING` и `UNKNOWN` взаимозаменяемы на уровне класса
(оба fail-closed, `empty_state_class: telemetry_missing`); выбор — вопрос
точности диагностики, а не смены вердикта.

## 4. Когда обязателен QUERY ERROR

`QUERY ERROR` обязателен, когда запрос/датасорс **отказал**: HTTP не-2xx,
таймаут, ошибка парсинга PromQL, недоступный datasource, отказ Ops HTTP
backend.

- `QUERY ERROR` **никогда** не рендерится как пустой результат, как
 `VALID EMPTY` и как OK/зелёный;
- `noValue` **не может** объявлять `QUERY ERROR`: `noValue` срабатывает
 только на успешном пустом ответе. `QUERY ERROR` описывается в
 `description` как третий отдельный исход;
- по `DASH-STATE-004` отказ backend не превращается в «нулевое» значение и не
 переносится в `trust_status`/`processing_status`.

## 5. Правило `noValue`

1. `noValue` называет **ровно одно** состояние из
 {`VALID EMPTY`, `UNKNOWN`, `TELEMETRY MISSING`, `SELECT RUN`, `N/A`}.
1. Состояние-токен стоит **первым** в строке, далее — причина и следующее
 действие.
1. Запрещённые формулировки (hedge), проверяются автоматически в
 `scripts/engineering/qa/check_dashboard_visual_semantics.py`
 (`HEDGED_EMPTY_STATE_PATTERNS`, применяется к `noValue`, `description` и
 `noValue` внутри `fieldConfig.overrides`):
 - `or VALID EMPTY if …`, `or UNKNOWN if …`, `or TELEMETRY MISSING if …`;
 - `UNKNOWN … or VALID EMPTY` и `VALID EMPTY … or UNKNOWN` внутри одного
 предложения (до `.` или `;`);
 - `TELEMETRY MISSING … or VALID EMPTY` внутри одного предложения;
 - `UNKNOWN/VALID EMPTY` и `VALID EMPTY/UNKNOWN`.
1. Разрешено: перечисление-**отрицание**, обучающее таксономии, например
 `TELEMETRY MISSING is not a zero and not VALID EMPTY` — это не альтернатива
 для текущего рендера.
1. Регрессионный тест:
 `tests/integration/test_grafana_dashboard_metric_semantics.py::test_provider_health_no_value_copy_confirms_exactly_one_empty_state`
 и `::test_empty_state_hedge_invariant_rejects_the_10246_regression`.

## 6. Отображение в PromQL для 9103 (и unbounded-копии 9113)

Панели `9103 Inspect Top Provider Causes` и `9113 Inspect Full Provider Causes`
используют один и тот же запрос (9103 дополнительно ограничен `topk(4, …)`).

Структура запроса — три взаимоисключающие ветки:

1. **POPULATED** — реальные причины:
 `max by (provider, cause) (bioetl_provider_current_cause) > 0`
 (в 9103 обёрнуто в `topk(4, …)`).
1. **VALID EMPTY** — одна fleet-строка, только при доказанном покрытии
 (`COVERAGE_GUARD`):

 ```promql
 (count(max by (provider) (bioetl_provider_current_status)) > bool 0)
 * (count(max by (provider) (bioetl_provider_current_cause)) > bool 0)
 * absent(max by (provider) (bioetl_provider_current_status) != 0)
 * absent(max by (provider) (bioetl_provider_current_status) unless on(provider) max by (provider) (bioetl_provider_health_status))
 * absent(max by (provider, cause) (bioetl_provider_current_cause) > 0)
 ```

 Метка: `label_replace(COVERAGE_GUARD, "cause", "VALID EMPTY - FLEET coverage proven, no active provider causes", "", "")`.
1. **UNKNOWN** — одна fleet-строка, когда причин нет, а покрытие не доказано:
 `absent(max by (provider, cause) (bioetl_provider_current_cause) > 0) unless (COVERAGE_GUARD)`
 с меткой `"UNKNOWN - FLEET cause coverage unproven, restore provider telemetry"`.

Почему это корректно:

- каждый множитель `COVERAGE_GUARD` пустой ⇒ вся ветка `VALID EMPTY` пустая:
 нет статуса, нет cause-семейства, есть provider выше OK или в состоянии `3`,
 либо есть активная причина;
- `bioetl_provider_current_status == 0` по recording rule возможен только при
 наличии `bioetl_provider_health_status` (fallback даёт `3`), поэтому
 `absent(status != 0)` — и есть доказательство полного покрытия health-телеметрии;
 явный множитель с `unless on(provider) … health_status` оставлен как
 самодокументируемая проверка;
- ветка `UNKNOWN` вычитает `COVERAGE_GUARD` через `unless`, поэтому две
 fleet-строки **никогда** не появляются вместе;
- при наличии активных причин `absent(cause > 0)` пуст ⇒ обе fleet-ветки пусты,
 таблица показывает только реальные причины;
- ноль фреймов вообще (datasource молчит) ⇒ `noValue`
 `UNKNOWN — cause evidence unavailable. Verify the Prometheus datasource, then Monitor Telemetry Presence.`;
- fleet-строка **не подставляет** синтетическую метку `provider`: колонка
 Provider остаётся пустой, чтобы не создавать несуществующую provider-identity
 и не ломать drilldown-ссылку. Область указана внутри текста причины (`FLEET`);
- синтетические нули не вводятся (`or vector(0)` отсутствует), значение
 fleet-строки — результат `absent()`/`bool`, а колонка `Value` исключена
 трансформацией.

Контракт `docs/03-guides/dashboards/contracts/panel-content-contract.yaml`,
`bioetl-provider-health-v2`:

| panel | state_model | empty_state_class |
| --- | --- | --- |
| `9103` | `VALID_EMPTY`, `UNKNOWN`, `ERROR`, `TELEMETRY_ABSENT` | `telemetry_missing` |
| `9113` | `VALID_EMPTY`, `UNKNOWN`, `ERROR`, `TELEMETRY_ABSENT` | `telemetry_missing` |
| `9102` | `UNKNOWN`, `ERROR`, `TELEMETRY_ABSENT` | `telemetry_missing` |
| `9107` | `UNKNOWN`, `ERROR`, `TELEMETRY_ABSENT` | `telemetry_missing` |

`9102` и `9107` потеряли `VALID_EMPTY`, потому что их запросы
(`status >= 1`, `current_status_info`) не могут доказать пустоту: ноль строк
одинаково означает «все OK» и «series нет».

## 7. Как это обязаны применить #10251 и #10253

Оба follow-up применяют правила §1–§5 **без повторного решения**.

### #10251 — `grafana/dashboards/bioetl-runtime.json` (Stage column, Stage Expectedness)

1. **Stage column `VALID EMPTY`** допустим только при доказанном покрытии по
 §1: series стадий присутствует для выбранного pipeline/run scope,
 записанный статус — терминальный/OK, и нет активных blocker-строк. Если
 присутствие стадийного series не доказано в самом запросе — состояние
 `UNKNOWN`, а не «этап пуст».
1. **Stage Expectedness = N/A** разрешено только как `N/A` из таксономии §0,
 то есть когда «ожидаемость стадии» **неприменима по конструкции** (стадия
 отсутствует в контракте pipeline). Если ожидаемость неизвестна из-за
 отсутствия/устаревания телеметрии — это `UNKNOWN`, **не** `N/A`.
 `N/A` никогда не смешивается с `VALID EMPTY` в одной строке.
1. **Обязательно исправить hedge-копии** в `bioetl-runtime.json`:
 - `SELECT RUN — no exact Run ID selected. Choose a run first. VALID EMPTY if the selected run has no identity.`
 - `SELECT RUN — no exact Run ID selected. Choose a run first. VALID EMPTY if the selected run has no report.`
 - `SELECT RUN — no exact Run ID selected. Choose a run in Inspect Recent Runs. UNKNOWN/QUERY ERROR if a selected run has no accounting.`

 Каждая строка обязана называть **одно** состояние. Для HTTP-backed
 selected-run панелей ведущее состояние — `SELECT RUN` (пока run не выбран);
 условные хвосты `VALID EMPTY if …` / `UNKNOWN/QUERY ERROR if …` удаляются.
 После выбора run пустой ответ — `UNKNOWN`/`TELEMETRY MISSING` по §2–§3,
 отказ backend — `QUERY ERROR` по §4.
1. Паттерн для класса `SELECT RUN … VALID EMPTY if …` добавляется в
 `HEDGED_EMPTY_STATE_PATTERNS` только после того, как все семь дашбордов
 очищены. Сейчас паттерн намеренно узкий, чтобы гейт оставался зелёным на
 файлах, которых #10246 не касается.
1. Контракт: для тронутых runtime-панелей выровнять `state_model` по факту —
 добавить `UNKNOWN`, убрать `VALID_EMPTY` там, где пустота недоказуема, и
 сохранить `empty_state_class` (`select_run` для ops_http, `telemetry_missing`
 для Prometheus).

### #10253 — `grafana/dashboards/bioetl-dq-v2.json` (DQ empty copy)

1. DQ reasons/threshold панели: `VALID EMPTY` только при доказанном покрытии
 по §1 — присутствует `bioetl_dq_current_*` для выбранного scope, статус
 записан как OK/complete, активных reason-строк нет. Иначе `UNKNOWN`.
1. Панель `9102 Inspect Current DQ Reasons` (роль `causes_table`, tier 2) —
 прямой аналог provider-health `9103`. Если решено показывать
 подтверждённую пустоту, использовать **тот же** трёхветочный шаблон §6:
 `POPULATED` → `VALID EMPTY` с coverage-guard → `UNKNOWN` через `unless`.
 Одна строка-вердикт на просмотр, `provider`/`pipeline` метки не
 подставляются синтетически.
1. **Обязательно исправить hedge-копии** в `bioetl-dq-v2.json`:
 - `SELECT RUN — no exact Run ID selected. Choose a run first. VALID EMPTY if the selected run has no report.`
 - `SELECT RUN — no exact Run ID selected. Choose a run first. VALID EMPTY if the selected run has no identity.`
 - `SELECT RUN — no exact Run ID selected. Choose a run in Inspect Recent Runs. UNKNOWN/QUERY ERROR if a selected run has no accounting.`
1. Двойные 100% DQ-скоры при `UNKNOWN` покрытии (см. `dux4` заметки) — это
 `UNKNOWN`, а не «идеальное качество»: нулевой знаменатель по §1 не даёт
 права на `VALID EMPTY` и тем более на зелёный.
1. Контракт: выровнять `state_model`/`fixture_cases` тронутых DQ-панелей так
 же, как §6 (добавить `UNKNOWN`; `VALID_EMPTY` оставлять только там, где
 покрытие доказуемо запросом).

## 8. Сделанные изменения в рамках #10246

- `grafana/dashboards/bioetl-provider-health-v2.json`
 - `9103` — новый трёхветочный запрос, non-hedging `noValue`, расширенное
 `description`, добавлена диагностическая ссылка
 `Diagnose provider telemetry coverage` → `viewPanel=9104`;
 - `9113` — тот же запрос без `topk`, синхронизированное `description`;
 - `9102`, `9107` — `noValue` переведены на одно состояние `UNKNOWN`.
 - геометрия не менялась: `9103` остаётся `y=19` (ниже `first_window_y=18`).
- `docs/03-guides/dashboards/contracts/panel-content-contract.yaml` —
 `state_model`/`fixture_cases` для `9102`, `9103`, `9107`, `9113`.
- `scripts/engineering/qa/check_dashboard_visual_semantics.py` — инвариант
 `HEDGED_EMPTY_STATE_PATTERNS`.
- `tests/integration/test_grafana_dashboard_metric_semantics.py` — пять новых
 тестов (см. §5, §6).

## 9. Остаточный риск

1. PromQL нового запроса проверен статически (баланс скобок, precedence,
 семантика `absent()`/`unless` на label-less векторах). `promtool`/живой
 Prometheus в этом чекауте недоступны — требуется render/live-проверка перед
 релизом.
1. Fleet-строка вердикта оставляет колонки `Provider` и `Severity` пустыми.
 Это осознанный выбор (никакой синтетической provider-identity), но требует
 визуальной проверки на первом рендере.
1. `9112 Inspect Full Non-OK Providers` сохраняет `VALID_EMPTY` в
 `state_model` при `noValue = TELEMETRY MISSING …`. Строка не hedging, гейт
 зелёный, но запись контракта неточна — отдельный follow-up вне #10246.
1. Anti-hedge инвариант намеренно узкий: класс
 `SELECT RUN … VALID EMPTY if …` (control-plane, runtime, dq, overview,
 run-explorer) пока не покрыт гейтом. Ужесточение — после #10251/#10253.
1. Рабочее дерево во время работы над #10246 многократно сбрасывалось,
 коммитилось и переключалось между ветками параллельными агентами stream 1.
 Патч #10246 воспроизводим идемпотентным скриптом
 `reports/observability/remediation/10258/apply_10246.py`; если правки снова
 окажутся затёрты, восстановление — один запуск этого скрипта.

## 10. Доказательства валидации

Required-набор на стабильном снимке дерева — 83 passed, 0 failed:

```
tests/integration/test_grafana_dashboard_metric_semantics.py
tests/integration/test_dashboard_operator_readability.py
tests/integration/test_dashboard_first_window_noscroll.py
tests/integration/test_dashboard_qa_check_gates.py
```

Промежуточные прогоны содержали до 36 посторонних падений из файлов других
агентов (в один момент `grafana/dashboards/bioetl-dq-v2.json` был невалидным
JSON). Для чистой атрибуции использован
`reports/observability/remediation/10258/attribute_10246.py`: он дважды подряд
гоняет required-набор на одном дереве — с патчем #10246 и с четырьмя своими
файлами, восстановленными из `HEAD` (без обращения к git index). Результат:

```
failures attributable to #10246: 0
failures only without the patch: 0
pre-existing/concurrent failures: 36
```

Дополнительные зелёные гейты: `check-dashboard-visual-semantics`,
`validate_dashboard_content_contract`,
`generate_dashboard_content_contract --check`,
`report-dashboard-query-duplicates --check`,
`report-dashboard-promql-scope --check`,
`check-dashboard-performance-budgets`.
`max_first_screen_expr_chars` для provider-health остался `188`: `9103` живёт в
свёрнутом ряду `9106` и не входит в first-load-окно, поэтому удлинение запроса
не тратит бюджет.
