Этап 1
Изучи правила работы с Grafana dashboards в этом репозитории и проведи исчерпывающий аудит дашборда
Silver Reject Explorer, Explore Logs и Explore Traces,.

  Перед аудитом:
  1. Выполни обязательный runtime-контекст из AGENTS.md: прочитай memory/docs policy и запусти pre-task workflow.
  2. Используй профиль/skill для Grafana dashboards, а при проверке PromQL также Prometheus metric/rule/query skills.
  3. Найди точный JSON-файл дашборда по title/uid, не предполагая путь заранее.

  Цель аудита: ничего не исправлять автоматически, а выявить ошибки, риски и подготовить детальный план корректировки.

  Проверь:

  1. Дизайн и удобство работы
  - Логика первого экрана: видно ли текущее состояние без прокрутки.
  - Action-first названия панелей.
  - Группировка рядов и секций.
  - Единообразие units, thresholds, colors, legends, descriptions.
  - Понятность OK/WARN/CRIT/UNKNOWN состояний.
  - Наличие drilldowns, dataLinks, runbook links для проблемных панелей.
  - Поведение при No data/null/0.
  - Удобство фильтров dashboard variables.
  - Риск перегрузки пользователя, дублирования или скрытых critical signals.

  2. Соответствие требованиям проекта
  - Проверь соответствие AGENTS.md, RULES.md, REQUIREMENTS.md, ADRs и dashboard docs.
  - Проверь локальный-only guardrail: не должно появляться требований к внешней оркестрации без необходимости.
  - Проверь соответствие dashboard conventions проекта: naming, current-status vs historical-range semantics, GLOBAL panel labeling, docs mirror sync.
  - Проверь соответствие observability/monitoring документации и существующим тестам.
  - Найди связанные docs/tests/contracts/configs, которые должны быть обновлены при исправлениях.

  3. Корректность каждой панели
  Для каждой панели проверь:
  - Panel ID, title, type, datasource.
  - PromQL выражения: синтаксис, корректность label filters, `$pipeline`, `$run_type`, `$__range`, recording rules, aggregation semantics.
  - Соответствие query смыслу панели и description.
  - Единицы измерения, thresholds, value mappings, reducer/calculation.
  - Legend/labels: не теряются ли важные измерения.
  - Scope: pipeline-scoped или GLOBAL, явно ли это указано.
  - Точность интерпретации 0/null/No data.
  - Наличие устаревших метрик, отсутствующих recording rules или несогласованных labels.
  - Возможные false OK / false CRIT сценарии.

  Проверки:
  - Валидируй JSON dashboard.
  - Если есть Prometheus rules, проверь их через promtool.
  - Проверь dashboard inventory/parity инструменты проекта.
  - Проверь релевантные тесты Grafana/Prometheus.
  - Если live Prometheus/Grafana доступны локально, проверь фактическое наличие метрик/rules через API. Если недоступны, явно отметь это как ограничение и выполни статический аудит.

  Формат результата:

  1. Краткий вывод
  - Общая оценка состояния dashboard.
  - Главные риски для операторов.
  - Можно ли доверять dashboard для runtime incident triage.

  2. Findings
  Выведи ошибки по severity: CRITICAL, HIGH, MEDIUM, LOW.
  Для каждого finding укажи:
  - Severity.
  - Файл и строку, если возможно.
  - Panel ID и title.
  - Что не так.
  - Почему это риск.
  - Как исправить.
  - Какие проверки подтвердят исправление.

  3. Аудит панелей
  Дай таблицу по всем панелям:
  - Panel ID.
  - Title.
  - Status: OK / Needs Fix / Needs Review.
  - Основная проблема или подтверждение корректности.

  4. План корректировки
  Сформируй phased remediation plan:
  - Phase 1: critical correctness fixes.
  - Phase 2: usability/design fixes.
  - Phase 3: docs/tests/mirror sync.
  - Phase 4: final validation.
  Для каждой задачи укажи файл, конкретное изменение, риск и проверку.

  5. Проверки и ограничения
  - Перечисли команды, которые были запущены.
  - Отдельно укажи проверки, которые не удалось выполнить, и почему.
  - Укажи pre-existing проблемы вне dashboard, если они мешают полной валидации.

 Этап 2.
 1. Если по результатом проверок найдены палени в которых не видно  полное название или
 не все данные или есть проктутка -- предложи и реализуй исправления.
 2. Если в одной или более строке панелей есть  свободное пространство в строке -- предложи и реализуй исправления.


 Этап 3
 1. Если были внесены правки переходи к этапу 1
 2. Если по результатом проверок не было внесено исправлений -- выведи отчет о работе и завершай.
