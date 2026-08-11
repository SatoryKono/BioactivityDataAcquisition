---
id: prompt.campaign.bi-dashboard-audit-kit
version: 1.0.0
status: archived
class: campaign
owner: BioETL Team
runtimes: [any]
tags: [observability, dashboard, bi, accessibility, campaign, archive]
summary: BI dashboard acceptance kit — visual/layout/data contours (2026-08-11); not default paste
related_ssot:
  - AGENTS.md
  - docs/00-project/ai/prompts/README.md
  - grafana/dashboards
anti_patterns:
  - Using this megaprompt as default operator paste
  - Requiring Tableau/Power BI/Looker on BioETL default path
  - Data FAIL from screenshot alone
  - Starting monitoring without operator approval
---

# BI dashboard audit kit (archive)

**Status:** archived campaign. Prefer:

- `library/observability/bi-dashboard-acceptance.md` (`prompt.observability.bi-dashboard-acceptance`)
- Grafana engineering loop: `library/observability/dashboard-panel-audit.md`

**Intake:** 2026-08-11. UI chrome stripped; «Промпт» normalized; table headers partially restored.

**BioETL overlay:** default platform Grafana (`grafana/dashboards`); monitoring only with approval;
artifacts under `reports/audit/bi-dashboard/`; map `score_1_5` and high/medium/low priority via
library fragments; do not invent dbt/GX/Soda/Playwright unless present in checkout.

**Sources:** `bi-dashboard-audit-kit-2026-08-11-SOURCES.md`.

---

11.08.2026 07:57 — DD — Аудит BI-дашбордов

Набор промтов, вопросов и автоматических тестов для аудита BI-дашбордов
Executive summary
TL;DR. Для приемочного и регулярного аудита дашбордов целесообразно разделить контроль на три независимых контура: визуальная доступность и типографика, компоновка и состав панелей, корректность данных. Каждый контур следует прогонять на трех уровнях глубины: быстрая проверка человеком, детальный аудит с измеримыми доказательствами и автоматизированные проверки через DOM/API/metadata/SQL.

Для веб- и embedded-дашбордов базой визуальной доступности разумно принять WCAG 2.2: контраст обычного текста не ниже 4.5:1, крупного текста — 3:1, значимых нетекстовых графических/UI-компонентов — 3:1; цвет не должен быть единственным способом передачи информации; увеличение текста до 200% не должно приводить к потере содержания или функциональности. WCAG не устанавливает универсального минимального кегля для всего текста, поэтому размер необходимо оценивать вместе с фактической читаемостью, контрастом и масштабированием; как консервативную практическую базу для основного веб-текста USWDS рекомендует эффективный размер около 16 px и выше. [1][2][3][4][5] 

Ключевая организационная идея: аудитор не должен отвечать «нравится/не нравится». Каждый дефект должен иметь измеримое доказательство: ratio контраста, координаты/размеры элемента, число дублирующих панелей, фактический SQL-result, delta между источником и BI, возраст данных, список пропущенных периодов и т. п. Tableau прямо рекомендует строить дашборд под ясную цель и аудиторию и отдавать наиболее заметное место ключевому представлению; Grafana формулирует сходный принцип как «дашборд должен рассказывать историю или отвечать на вопрос» и снижать когнитивную нагрузку. Microsoft рекомендует минимизировать визуальный шум, поддерживать единообразие оформления и не прятать ключевую информацию исключительно в интерактивности. [6][7][8] 

Для автоматизации следует соединить два уровня. Первый — audit-as-code дашборда: metadata/API/JSON + visual regression через Playwright. Второй — data-quality tests: not_null, unique, relationships, freshness, reconciliation, schema drift и бизнес-инварианты через SQL/dbt/Great Expectations/Soda. Playwright умеет сравнивать screenshot с baseline; dbt имеет встроенные проверки unique, not_null, accepted_values, relationships; Great Expectations и Soda поддерживают freshness, schema, integrity и другие классы проверок. [9][10][11][12] 

Рекомендуемый release gate: любой FAIL высокого приоритета по правильности KPI, периоду/фильтрам, актуальности, единицам измерения, row-level security либо доступности ключевого содержимого блокирует приемку; средние нарушения могут уходить в backlog только при явно зафиксированном риске.

Модель аудита и единый формат ответа
Для универсальности относительно Tableau, Power BI, Looker, Grafana и кастомных приложений лучше отделять промт-аудитор от конкретного набора проверок. Tableau, Microsoft и Grafana в собственных руководствах также подчеркивают необходимость единообразия, ясной цели, документирования и последовательной структуры, что позволяет формализовать проверку в общий набор правил. [6][7][13] 

Базовый системный промт для аудитора или LLM-инструмента

text

Роль:
Ты — независимый аудитор BI-дашбордов. Оценивай не эстетические предпочтения,
а риск неправильного чтения данных, ошибочного решения, снижения доступности
или невозможности проверить вывод.

Поддерживаемые среды:
Tableau, Power BI/Fabric, Looker, Grafana, кастомные web-дашборды.

Входные данные:
- dashboard_id / page_id;
- screenshot или URL;
- viewport и zoom;
- metadata / JSON / XML дашборда, если доступны;
- список панелей, запросов и фильтров;
- user_role = analyst | manager | executive;
- словарь KPI и бизнес-правил, если доступен;
- результаты контрольных SQL/API-запросов, если доступны.

Обязательные правила:
1. Разделяй:
   FACT — непосредственно наблюдаемый/измеренный факт;
   INFERENCE — вывод из фактов;
   ASSUMPTION — предположение при недостатке данных.
2. Не объявляй число неверным только по скриншоту.
   Для data correctness используй SQL/API/semantic-layer evidence.
3. Для каждого FAIL/WARN дай измеримое доказательство.
4. Если правило неприменимо, используй N/A.
5. Не считай эстетическое предпочтение дефектом без связи
   с читаемостью, пользовательской задачей, стандартом или риском ошибки.
6. Проверяй влияние отдельно на analyst, manager и executive.
7. Не скрывай неопределенность.

Выход для каждого check:
{
  "check_id": "...",
  "status": "pass|warn|fail|na",
  "score_1_5": 1,
  "priority": "high|medium|low",
  "fact": "...",
  "evidence": ["..."],
  "measured_value": "...",
  "threshold_or_rule": "...",
  "affected_users": ["analyst","manager","executive"],
  "impact": "...",
  "recommendation": "...",
  "confidence": 0.00
}
Единая шкала

Балл	Интерпретация	Приемочное решение
5	Проверка пройдена, существенных замечаний нет	PASS
4	Незначительный дефект без риска неверного вывода	PASS / low backlog
3	Заметное ухудшение использования, но основная задача выполняется	WARN
2	Существенная вероятность неверного чтения или затруднения работы	FAIL
1	Критический риск неправильного решения или невозможность использования	FAIL

Приоритет лучше назначать независимо от балла. Например, контраст малозначимого footer может иметь низкий/средний приоритет, тогда как неправильный denominator KPI — высокий даже при визуально безупречном дашборде.

Минимально достаточное доказательство

text

Плохо:
"График плохо читается."

Хорошо:
"FAIL. Подписи оси Y имеют computed font-size 10 px;
контраст #999999 на #FFFFFF = 2.85:1.
Порог WCAG AA для обычного текста — 4.5:1.
При viewport 1366×768 подписи являются ключевыми для чтения значений.
Affected users: analyst, manager, executive.
Confidence: 0.99."
Для крупного текста WCAG допускает 3:1; под крупным в соответствующей технике понимается приблизительно 18 pt обычного или 14 pt жирного текста, что соответствует примерно 24 px и 18.5 px соответственно. [2] 

Аудит палитры, читаемости и типографики
Этот блок специально не оценивает расположение панелей. Его объект — цвет, контраст, семантика цвета, шрифты, подписи, форматирование чисел и способность визуальной системы сохранять читаемость. Tableau рекомендует ограничивать количество цветов, выстраивать явную типографическую иерархию и выбирать хорошо читаемые экранные шрифты; Power BI рекомендует единообразные размеры/стили однотипных элементов, минимум 4.5:1 для текста и отказ от цвета как единственного способа кодирования информации. [14][15] 

Быстрая проверка

ID	Готовый промт / вопрос	Ответ	Приоритет	Пример корректного ответа	Пример некорректного ответа
VQ-01	Есть ли ключевой текст с недостаточным контрастом? Перечисли элементы и ratio.	Да/Нет + текст	высокий	«Да. KPI Margin: 2.8:1 < 4.5:1»	«Цвет бледный»
VQ-02	Используется ли цвет как единственный способ различить статус, серию или отклонение?	Да/Нет	высокий	«Да: red/green без подписи/формы/иконки»	«Не люблю красный»
VQ-03	Существует ли четкая типографическая иерархия title → KPI → chart title → label → service text?	1–5 + текст	средний	«3/5: семь размеров, KPI и page title конкурируют»	«3/5»
VQ-04	Читаемы ли оси, легенды, подписи и фильтры при штатном viewport без ручного zoom?	Да/Нет + текст	высокий	«Нет: 10 px, три подписи обрезаны»	«Мелковато»
VQ-05	Последовательна ли семантика цветов между страницами?	1–5 + текст	средний	«2/5: синий означает Actual на стр.1 и Plan на стр.3»	«Разные цвета»
VQ-06	Можно ли интерпретировать отрицательное/положительное состояние без знания корпоративной палитры?	Да/Нет + текст	средний	«Нет: статус передается только оттенком fill»	«Неочевидно»

Детальный аудит

ID	Готовый промт / вопрос	Ответ	Приоритет	Корректный ответ	Некорректный ответ
VD-01	Измерь контраст всех текстовых ролей. Для каждой зафиксируй foreground, background, font-size, weight, ratio, pass/fail.	текст	высокий	«Axis: 4.8:1 PASS; caption: 3.2:1 FAIL»	«В основном нормально»
VD-02	Измерь контраст значимых иконок, границ controls, selected states и линий, необходимых для понимания.	текст	высокий	«Active filter outline = 2.1:1 < 3:1»	«Кнопка видна»
VD-03	Проверь визуализацию при моделировании основных дефицитов цветового зрения. Теряется ли различимость серий?	Да/Нет + текст	высокий	«Да: Series A/B становятся неразличимы; нужны маркеры»	«Красный/зеленый плохие»
VD-04	Проверь, что одинаковые понятия имеют одинаковое цветовое кодирование между страницами.	1–5 + текст	средний	«2/5: четыре конфликта семантики цвета»	«Палитры не совпадают»
VD-05	Проверь zoom/увеличение текста до 200%: clipping, overlap, исчезновение labels/controls.	Да/Нет + текст	высокий	«FAIL: при 200% Period filter обрезан»	«При зуме тесно»
VD-06	Проверь числовое форматирование: decimal places, thousands separator, %, currency, negative values, K/M/B.	1–5 + текст	высокий	«3/5: два KPI не показывают валюту; 1.5 означает млн только по tooltip»	«Числа разные»
VD-07	Составь inventory font-family/font-size/font-weight по ролям и найди выбросы.	текст	средний	«3 families, 11 sizes; policy разрешает 2/6»	«Много шрифтов»
VD-08	Проверь, что gridlines, borders и background имеют меньший визуальный вес, чем данные.	1–5 + текст	низкий/средний	«2/5: gridline визуально темнее data line»	«Сетка мешает»
VD-09	Проверить читаемость длинных подписей: нет ли неоднозначного truncation вроде North Amer....	Да/Нет + текст	средний	«FAIL: три категории после truncation неразличимы»	«Есть троеточия»
VD-10	Проверь tooltip: важные данные должны быть доступны без hover; tooltip — только дополнительный контекст.	Да/Нет	высокий	«FAIL: точное значение SLA доступно только через hover»	«Tooltip полезен»

Ключевая информация не должна зависеть только от tooltip: Power BI отдельно предупреждает не помещать туда информацию, критичную для пользователей, которые не могут ее получить через мышь или screen reader. [15] 

Автоматическая проверка

ID	Что передать автоматическому инструменту	Ответ	Приоритет	Корректный результат	Некорректный результат
VA-01	Извлеки DOM computed color, background-color, font-size, font-weight; рассчитай WCAG ratio.	Да/Нет + JSON	высокий	{"fail":3,"min_ratio":2.61}	{"looks_ok":true}
VA-02	Сравни screenshot с baseline, исключив timestamps/анимацию. Выведи diff ratio и bounding boxes.	1–5 + текст	средний	«1.2% changed; KPI/header only»	«Screenshots differ»
VA-03	Проанализируй theme/style definition и найди неожиданные font/color tokens.	Да/Нет + текст	средний	«4 font families > policy=2»	«Theme invalid»
VA-04	Для status/series elements проверь наличие второго кода: label/icon/shape/pattern.	Да/Нет	высокий	«FAIL: 6 categories differ only by fillColor»	«Есть красный»
VA-05	На viewport 1920, 1366, 1024 и zoom 200% проверь пересечения bounding boxes и clipping.	Да/Нет + JSON	высокий	«4 overlaps at 200%»	«Responsive failed»
VA-06	Найди тексты меньше проектного soft-limit и отсортируй по значимости.	текст	средний	«8 labels < 12px; 3 are axis labels»	«8 small fonts»

Здесь важно не превращать произвольный 12px или 14px в «требование WCAG»: WCAG ориентируется на контраст и возможность изменения размера, а не задает универсальный минимальный размер обычного текста. Для проектного style guide можно принять собственные пороги; USWDS, например, рекомендует для большинства обычного текста эффективный размер от 16 px. [4][5] 

Аудит расположения и состава панелей
Этот контур отвечает на другой вопрос: правильно ли организовано пространство дашборда и присутствует ли только тот состав визуализаций, который нужен пользователю для решения задачи. Tableau рекомендует начинать с цели и аудитории, размещать ключевое представление в наиболее заметной зоне; Grafana рекомендует логическую прогрессию «общее → конкретное» и снижение когнитивной нагрузки; Power BI — минимизировать число визуальных объектов и сохранять расположение повторяющихся элементов, включая slicers. [6][7][15] 

Быстрая проверка

ID	Промпт / вопрос	Ответ	Приоритет	Корректный ответ	Некорректный ответ
LQ-01	Можно ли за 5–10 секунд сформулировать главный вопрос страницы?	Да/Нет + текст	высокий	«Да: выполнение плана и причина отклонения»	«Да»
LQ-02	Находятся ли главный KPI и основное объясняющее представление в первом экране?	Да/Нет	высокий	«Нет: SLA KPI ниже fold»	«Почти»
LQ-03	Есть ли панели, дублирующие одну информацию без новой аналитической функции?	Да/Нет + текст	средний	«Card Revenue и gauge Revenue идентичны»	«Похожие графики»
LQ-04	Не перегружена ли страница фильтрами и controls?	1–5 + текст	средний	«2/5: 14 filters, 9 не нужны менеджеру»	«Фильтров много»
LQ-05	Понятен ли маршрут «обзор → причина → детализация»?	Да/Нет + текст	высокий	«Нет: из KPI нет перехода к драйверам»	«Не очень»
LQ-06	Существуют ли пустые/неиспользуемые области или элементы, мешающие основному потоку чтения?	Да/Нет	низкий/средний	«Да: 22% canvas занимает декоративный banner»	«Много пустоты»

Детальный аудит

ID	Промпт / вопрос	Ответ	Приоритет	Корректный ответ	Некорректный ответ
LD-01	Построй карту цель → KPI → trend → drivers → detail. Укажи отсутствующие звенья.	текст	высокий	«Есть KPI и raw table, но отсутствует объяснение trend/drivers»	«Добавить график»
LD-02	Для каждой панели укажи вопрос пользователя и решение, которое она поддерживает. Панели без функции пометь delete/rework.	текст	высокий	«Panel 7 не поддерживает ни одного решения»	«Panel 7 не нравится»
LD-03	Оцени соответствие chart type задаче: trend/comparison/distribution/composition/relation/exact values.	1–5 + текст	средний	«2/5: pie 17 категорий используется для точного сравнения»	«Pie плохой»
LD-04	Проверь alignment/grid/grouping и наличие одного очевидного визуального центра.	1–5 + текст	средний	«3/5: KPI-row разорван двумя filters»	«Криво»
LD-05	Проверь одинаковость расположения повторяющейся navigation/filter system между страницами.	Да/Нет + текст	средний	«Period: top-left на 4/5 страниц, bottom-right на одной»	«Разные layouts»
LD-06	Оцени dashboard для каждой persona. Что убрать/добавить для analyst, manager, executive?	текст	высокий	«Executive: убрать raw table; analyst: добавить drill/detail»	«Подходит всем»
LD-07	Есть ли ключевой вывод, доступный только через tooltip, drill или hidden tab?	Да/Нет	высокий	«Да: root cause только в drill-through»	«Drill удобен»
LD-08	Согласован ли refresh interval с фактической частотой ETL/source update?	текст	средний	«Dashboard refresh 30 s, ETL hourly — избыточно»	«Часто обновляется»
LD-09	Оцени количество query-backed panels и сложность загрузки. Какие элементы объединить/разделить?	текст	средний	«29 tiles; overview и diagnostics следует разделить»	«Медленно»
LD-10	Проверить, не вынуждает ли страница пользователя горизонтально/вертикально скроллить для ответа на основной вопрос.	Да/Нет + текст	средний	«Executive summary требует 2.3 viewport heights»	«Нужно прокручивать»
LD-11	Проверить, нет ли одновременно нескольких conflicting legends/scales для одного понятия.	Да/Нет	высокий	«Да: две legend используют одинаковые цвета для разных dimensions»	«Легенд много»
LD-12	Проверить видимость текущего filter context рядом с результатами.	1–5 + текст	высокий	«2/5: active region hidden в collapsed filter panel»	«Фильтр можно открыть»

Microsoft прямо советует минимизировать число визуализаций и ненужное дублирование; Google для Looker отдельно предупреждает о большом числе элементов и рекомендует избегать дашбордов с 25+ запросами как общего performance-антипаттерна, хотя это не универсальный жесткий лимит. [15][16] 

Автоматическая проверка

ID	Проверка	Ответ	Приоритет
LA-01	Из metadata/JSON посчитать panels, filters, charts, tables, text blocks и query-backed elements.	JSON + thresholds	средний
LA-02	Проверить overlap, выход за canvas, zero/near-zero dimensions, collision и чрезмерные gaps.	Да/Нет + bounds	высокий
LA-03	Сравнить coordinates/ID общих filters/navigation между страницами.	Да/Нет + delta	средний
LA-04	Сверить панели с required_panels шаблона конкретной persona.	Да/Нет + missing/excess	высокий
LA-05	Visual-regression на desktop/laptop/tablet viewport.	1–5 + screenshots	высокий
LA-06	Проверить названия панелей: пустые, дублированные, generic Panel 1, слишком длинные.	Да/Нет + list	средний
LA-07	Сопоставить dashboard refresh interval с source/ETL freshness metadata.	Да/Нет + duration	средний
LA-08	Найти идентичные query signatures, питающие разные визуально дублирующие tiles.	text/JSON	средний

Для Grafana такую проверку удобно строить непосредственно по dashboard JSON: модель содержит panels, variables и gridPos, где x/y/w/h задают положение и размер на 24-колоночной сетке. [17] 

Визуальный пример корректной иерархии

Основная идея — привести пользователя от сводки к диагностике, а не давать всем визуализациям одинаковый визуальный приоритет. Это соответствует рекомендациям Tableau и Grafana о ясной цели, логической последовательности и визуальной иерархии. [6][7] 

Пример проблемной структуры

Проблема здесь не в самом количестве прямоугольников, а в отсутствии приоритетов, дублировании функций, конкурирующих controls и невозможности быстро определить основной аналитический маршрут.

Аудит корректности данных в панелях
Этот блок должен разделять три разных класса ошибок:

Source quality — данные уже некорректны или неполны на уровне таблиц.
Semantic/business logic — исходные данные корректны, но неверны aggregation, join, definition, filter, time zone или denominator.
Presentation — semantic result корректен, но dashboard отображает другой period/unit/value либо маскирует NULL.

Для регрессионного контроля dbt предоставляет типовые unique, not_null, accepted_values, relationships; Great Expectations поддерживает проверки freshness, integrity, schema и distribution; Soda — missing, duplicate, freshness, schema и row-count checks. [10][11][12] 

Быстрая проверка

ID	Промпт / вопрос	Ответ	Приоритет	Корректный ответ	Некорректный ответ
DQ-01	Отображены ли data period и timestamp последнего фактического обновления?	Да/Нет	высокий	«Нет — freshness невозможно оценить»	«Наверное свежие»
DQ-02	Совпадают ли unit/currency/scale/period между KPI и связанными графиками?	Да/Нет + текст	высокий	«Нет: card Monthly, trend YTD»	«Цифры отличаются»
DQ-03	Совпадает ли значение панели с контрольным query при идентичных filters?	Да/Нет + delta	высокий	«Нет: +1.83%, tolerance 0.10%»	«Похоже»
DQ-04	Есть ли NULL/NaN/∞, отображенные как обычный 0 или скрытые?	Да/Нет + counts	высокий	«37 NULL rendered as 0»	«Есть нули»
DQ-05	Понятно ли определение KPI пользователю?	Да/Нет	высокий	«Нет: “Conversion” без denominator»	«Метрика стандартная»
DQ-06	Меняются ли связанные панели согласованно при изменении filter?	Да/Нет + evidence	высокий	«Нет: KPI не реагирует на Region»	«Один график остался»

Детальный аудит

ID	Промпт / вопрос	Ответ	Приоритет	Корректный ответ	Некорректный ответ
DD-01	Для каждого KPI зафиксируй formula, grain, filters, time zone, currency, denominator и exclusions; сравни с metric contract.	текст	высокий	«Dashboard включает cancelled, contract — paid only»	«Формула другая»
DD-02	Проверь duplicate inflation после joins через count(*) и count(distinct business_key).	текст	высокий	«Join увеличивает строки x1.18»	«Join подозрительный»
DD-03	Проверь completeness временного ряда: missing intervals, duplicate periods, late-arriving rows.	текст	высокий	«Missing 2026-07-14; duplicate 2026-07-21»	«Есть дырки»
DD-04	Проверь referential integrity, mandatory fields, accepted values, physical ranges.	текст	высокий	«0.7% orphan customer_id»	«Есть ошибки»
DD-05	Сверь totals/subtotals после фильтрации и drill. Учти non-additive metrics.	текст	высокий	«Regions sum ≠ total из-за distinct customers; UI это не поясняет»	«Итоги не сходятся»
DD-06	Проверь rates: denominator, zero denominator, weighted vs simple mean.	текст	высокий	«Среднее филиальных % вместо weighted conversion»	«Процент неверен»
DD-07	Проверь timezone/DST и границы < period_end вместо неоднозначного <= 23:59:59.	текст	высокий	«Dashboard группирует UTC, contract — Europe/London»	«Дата сдвинута»
DD-08	Сопоставь source freshness → semantic model/extract → dashboard cache.	текст	высокий	«Source 07:00; model/dashboard 05:00; SLA=2h — FAIL»	«Старые данные»
DD-09	Протестируй row-level security несколькими контрольными ролями и totals.	Да/Нет + text	высокий	«Region user видит company total через KPI — FAIL»	«RLS включен»
DD-10	Сопоставь visual value, tooltip, Show Data/export и API/query result.	текст	высокий	«Card=1245, export/API=1214»	«Экспорт другой»
DD-11	Проверь default filters и hidden filters: совпадает ли начальный контекст с документацией?	Да/Нет	высокий	«Hidden status excludes refunds без указания пользователю»	«Есть hidden filter»
DD-12	Проверь handling deleted/cancelled/backfilled records.	текст	высокий	«Backfill попадает только в source, extract не перезагружен»	«История меняется»
DD-13	Проверь currency conversion и дату FX-rate.	текст	высокий	«2026 sales пересчитываются current FX вместо transaction-date FX»	«Валюта не совпала»
DD-14	Проверить округление: сумма округленных частей vs округление итоговой суммы.	текст	средний	«UI subtotal differs 0.04 из-за pre-aggregation rounding»	«Есть копейки»

Автоматическая проверка

ID	Тест	Рекомендуемый выход	Приоритет
DA-01	NOT NULL для business-critical полей	count + samples	высокий
DA-02	UNIQUE primary/business keys	duplicates + keys	высокий
DA-03	REFERENTIAL INTEGRITY	orphan count + keys	высокий
DA-04	ACCEPTED VALUES	unexpected values	высокий
DA-05	Freshness	data_age, SLA, status	высокий
DA-06	Dashboard/source reconciliation	source, BI value, abs/rel delta	высокий
DA-07	Expected date/partition completeness	missing intervals	высокий
DA-08	Join inflation	row multiplier/key multiplier	высокий
DA-09	Schema drift	added/removed/type-changed	высокий
DA-10	Volume anomaly	current vs rolling baseline	средний
DA-11	Distribution/business bounds	min/max/quantiles/outliers	средний
DA-12	Cross-panel consistency	conflicting totals by filter context	высокий

SQL: обязательный минимум

sql

-- NULL + uniqueness
SELECT
    COUNT(*) AS rows_total,
    SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) AS null_ids,
    COUNT(*) - COUNT(DISTINCT order_id) AS duplicate_rows
FROM fact_orders;
sql

-- Referential integrity
SELECT COUNT(*) AS orphan_rows
FROM fact_orders AS f
LEFT JOIN dim_customer AS d
       ON d.customer_id = f.customer_id
WHERE f.customer_id IS NOT NULL
  AND d.customer_id IS NULL;
sql

-- Freshness
SELECT
    MAX(updated_at) AS latest_row,
    CURRENT_TIMESTAMP AS checked_at,
    CURRENT_TIMESTAMP - MAX(updated_at) AS data_age
FROM fact_orders;
sql

-- Reconciliation dashboard ↔ source
WITH source_value AS (
    SELECT SUM(net_amount) AS v
    FROM fact_orders
    WHERE status = 'paid'
      AND order_ts >= :period_start
      AND order_ts <  :period_end
),
dashboard_value AS (
    SELECT CAST(:value_from_bi AS DECIMAL(38, 6)) AS v
)
SELECT
    s.v AS source_value,
    d.v AS dashboard_value,
    ABS(d.v - s.v) AS abs_delta,
    CASE
        WHEN s.v = 0 THEN NULL
        ELSE ABS(d.v - s.v) / ABS(s.v)
    END AS rel_delta
FROM source_value AS s
CROSS JOIN dashboard_value AS d;
Для production-gate нужен явный tolerance, например:

text

PASS: rel_delta <= metric_tolerance
FAIL: rel_delta > metric_tolerance
Tolerance нельзя задавать одним универсальным процентом. Для денежных totals он может быть практически нулевым, а для probabilistic/approximate metrics или различающихся latency windows — выше; это должно быть свойством metric contract, а не решением аудитора на месте.

sql

-- Missing dates, PostgreSQL
WITH calendar AS (
    SELECT d::date AS dt
    FROM generate_series(
        :date_from::date,
        :date_to::date,
        interval '1 day'
    ) AS d
),
actual AS (
    SELECT DISTINCT order_ts::date AS dt
    FROM fact_orders
)
SELECT c.dt
FROM calendar AS c
LEFT JOIN actual AS a USING (dt)
WHERE a.dt IS NULL
ORDER BY c.dt;
sql

-- Join inflation
WITH before_join AS (
    SELECT
        COUNT(*) AS n,
        COUNT(DISTINCT order_id) AS business_keys
    FROM fact_orders
),
after_join AS (
    SELECT
        COUNT(*) AS n,
        COUNT(DISTINCT f.order_id) AS business_keys
    FROM fact_orders AS f
    LEFT JOIN bridge_order_tag AS b
           ON b.order_id = f.order_id
)
SELECT
    b.n AS rows_before,
    a.n AS rows_after,
    1.0 * a.n / NULLIF(b.n, 0) AS row_multiplier,
    b.business_keys AS keys_before,
    a.business_keys AS keys_after
FROM before_join AS b
CROSS JOIN after_join AS a;
sql

-- Weighted rate vs erroneous simple average
SELECT
    SUM(success_count) * 1.0 / NULLIF(SUM(total_count), 0) AS weighted_rate,
    AVG(success_count * 1.0 / NULLIF(total_count, 0))      AS simple_avg_rate
FROM daily_channel_metrics
WHERE metric_date >= :date_from
  AND metric_date <  :date_to;
Регулярные выражения

Использовать regex следует только там, где формат действительно является частью contract; проверка бизнес-смысла одной регуляркой невозможна.

regex

# ISO-like date YYYY-MM-DD
^\d{4}-(0[1-9]|1[0-2])-([0-2]\d|3[01])$
regex

# Процент: optional minus, до двух decimals
^-?(?:0|[1-9]\d{0,2})(?:[.,]\d{1,2})?%$
regex

# Валюта: pragmatic UI-format check
^-?\d{1,3}(?:[ \u00A0,]\d{3})*(?:[.,]\d{2})?\s?(?:USD|EUR|GBP|RUB|₽|\$|€|£)$
regex

# Email: pragmatic UI validation, не полный RFC-parser
^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$
Автоматизация и инструменты
Платформы предоставляют достаточно API/metadata для построения значительной части audit-as-code, хотя объем доступной информации различается. Вывод о необходимости комбинировать metadata/API с screenshot/DOM-проверкой является инженерной экстраполяцией: BI API хорошо раскрывают структуру, queries и content metadata, но не дают единого кроссплатформенного интерфейса для всех фактических пиксельных свойств отрендеренного UI. 

Среда	Что автоматизировать	API / CLI / механизм
Tableau	workbook/view inventory; metadata/lineage; CSV результата; screenshot/image; refresh	REST API, Metadata API, tabcmd [18][19]
Power BI / Fabric	workspace/semantic-model inventory; scanner metadata; DAX reconciliation; CI/CD	Power BI REST, Scanner APIs, Execute Queries, Fabric CLI fab [20][21]
Looker	dashboard/query metadata; broken content; LookML validation; query reconciliation	Looker API 4.0, official SDK, Content Validator [22]
Grafana	dashboard JSON; grid/layout; variables; datasource query; provisioning	HTTP API, /api/ds/query, gcx, Foundation SDK [23]
Custom web	DOM computed style; accessibility; screenshot regression; responsive tests	Playwright [9]
Data layer	null, unique, RI, freshness, schema, anomaly, metric rules	dbt / GX / Soda [10][11][12]

Tableau REST API может программно получать workbooks/views и возвращать view data в CSV, изображения и другие representations; Metadata API предназначен для каталога и lineage. Tableau также предоставляет tabcmd для командной автоматизации. [18][19] 

Для Power BI полезна связка Scanner APIs + Execute Queries: scanner metadata может включать schema, columns, measures и expressions при соответствующей tenant-конфигурации; Execute Queries позволяет выполнять DAX против semantic model. В Microsoft Fabric существует официальный CLI fab для автоматизации Fabric-операций. [20][21] 

В Looker API есть endpoint Content Validation, который валидирует Looks и dashboards и возвращает обнаруженные ошибки; API также позволяет запускать сохраненные и inline queries. Официальные SDK доступны в нескольких языках. [22] 

В Grafana dashboard JSON содержит структуру и координаты панелей; HTTP API позволяет управлять dashboards и делать datasource queries, а актуальная документация рекомендует gcx как CLI-направление для программного взаимодействия с Grafana. [23] 

Пример регулярного visual-regression теста

ts

import { test, expect } from "@playwright/test";

test("executive dashboard visual baseline", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto(process.env.DASHBOARD_URL!);

  // Авторизация/ожидание загрузки должны быть реализованы
  // в fixture конкретного проекта.
  await page.waitForLoadState("networkidle");

  await expect(page).toHaveScreenshot("executive-dashboard.webp", {
    fullPage: true,
    maxDiffPixelRatio: 0.005,
  });
});
Playwright прямо поддерживает toHaveScreenshot() для baseline comparison и предупреждает, что для стабильных результатов baseline и проверку следует запускать в одинаковом окружении, поскольку rendering зависит от ОС, браузера и других условий. [9] 

Приоритет внедрения автоматизации

Стадия	Что запускать	Когда
PR/CI	metadata lint, schema tests, metric SQL, dashboard-as-code validation	каждое изменение
Deploy	API/content validation, screenshots основных viewport	перед production
Hourly/daily	freshness, row count, RI, KPI reconciliation	по SLA данных
Weekly	visual regression полного набора страниц	регулярно
Monthly/quarterly	human detailed audit и проверка usefulness/composition	governance review

dbt рекомендует запускать data tests не только во время разработки, но и вместе с production transformations; source freshness позволяет отдельно контролировать актуальность источников. [10] 

Практический automated-auditor prompt

text

Получив:
1. dashboard metadata;
2. screenshot на утвержденном viewport;
3. baseline screenshot;
4. список ожидаемых KPI;
5. результаты SQL data tests;

выполни:
A. structural audit;
B. visual audit;
C. data reconciliation.

Запрещено:
- считать pixel diff бизнес-дефектом без классификации измененной области;
- считать любое изменение числа ошибкой без source-of-truth query;
- автоматически "исправлять" business definitions;
- считать N/A успешной проверкой.

Верни:
{
  "release_decision": "pass|conditional|block",
  "high_failures": 0,
  "medium_failures": 0,
  "visual_score": 1-5,
  "layout_score": 1-5,
  "data_score": 1-5,
  "checks": [...],
  "evidence_artifacts": [...]
}
Печатный чек-лист, визуальный процесс и CSV
Чек-лист для ручной приемки

✓	ID	Контроль	Приоритет	Результат / evidence
[ ]	V-01	Контраст ключевого текста соответствует порогу	высокий	
[ ]	V-02	Значимые UI/graphic elements различимы	высокий	
[ ]	V-03	Цвет не является единственным кодом	высокий	
[ ]	V-04	При zoom нет clipping/overlap	высокий	
[ ]	V-05	Типографическая иерархия едина	средний	
[ ]	V-06	Units/currency/percent visually explicit	высокий	
[ ]	L-01	Цель страницы понятна за 5–10 секунд	высокий	
[ ]	L-02	Главные KPI находятся в первом экране	высокий	
[ ]	L-03	Дублирующие панели отсутствуют	средний	
[ ]	L-04	Filters соответствуют persona	средний	
[ ]	L-05	Navigation и filters расположены последовательно	средний	
[ ]	L-06	Ключевой вывод не спрятан в hover/drill	высокий	
[ ]	L-07	Видим текущий filter context	высокий	
[ ]	D-01	Видимы period и data freshness	высокий	
[ ]	D-02	KPI сверены с source-of-truth	высокий	
[ ]	D-03	Единицы, валюты и периоды согласованы	высокий	
[ ]	D-04	NULL/NaN не маскируются под 0	высокий	
[ ]	D-05	Join не создает duplicate inflation	высокий	
[ ]	D-06	Rates используют правильный denominator	высокий	
[ ]	D-07	Time zone/DST обработаны корректно	высокий	
[ ]	D-08	Freshness соответствует SLA	высокий	
[ ]	D-09	RLS проверен контрольными ролями	высокий	
[ ]	D-10	Visual/export/API totals согласованы	высокий	

Mermaid-схема процесса аудита

Да

Нет

Инвентаризация dashboard / pages / personas

Baseline: screenshot + metadata + filters + KPI contracts

Три независимых контура

Палитра и типографика

Layout и состав панелей

Корректность данных

Score + evidence

Есть high-priority FAIL?

BLOCK: исправление

PASS / backlog

Retest

Новый утвержденный baseline

CI/CD visual + metadata tests

Scheduled data-quality tests

Monitoring / alerts




CSV UTF-8 для Excel

csv

check_id;block;check;priority;format;status;evidence
V-01;visual;Контраст ключевого текста;high;yes/no+text;;
V-02;visual;Цвет не единственный носитель смысла;high;yes/no;;
V-03;visual;Типографическая иерархия;medium;1-5+text;;
V-04;visual;Нет clipping/overlap при zoom;high;yes/no+text;;
V-05;visual;Units и числовые форматы однозначны;high;1-5+text;;
L-01;layout;Цель страницы понятна;high;yes/no+text;;
L-02;layout;Главные KPI в первом экране;high;yes/no;;
L-03;layout;Нет дублирующих панелей;medium;yes/no+text;;
L-04;layout;Filters соответствуют persona;medium;1-5+text;;
L-05;layout;Ключевой вывод не спрятан в hover/drill;high;yes/no;;
D-01;data;Период и актуальность видимы;high;yes/no;;
D-02;data;KPI сверяется с источником;high;yes/no+delta;;
D-03;data;Единицы валюты и периоды согласованы;high;yes/no+text;;
D-04;data;NULL/NaN не маскируются;high;yes/no+counts;;
D-05;data;Нет duplicate inflation;high;yes/no+ratio;;
D-06;data;Rate denominator корректен;high;yes/no+text;;
D-07;data;Timezone/DST корректны;high;yes/no+text;;
D-08;data;Freshness в пределах SLA;high;yes/no+duration;;
D-09;data;RLS проверен;high;yes/no+text;;
D-10;data;Visual/export/API согласованы;high;yes/no+delta;;
Готовые файлы отчета

Скачать Markdown
Скачать DOCX
Скачать PDF
Скачать схему корректной структуры
Скачать схему проблемной структуры

Источники
[1] W3C. Web Content Accessibility Guidelines (WCAG) 2.2 [Электронный ресурс]. Дата обращения: 11.08.2026. 

[2] W3C. Understanding Success Criterion 1.4.3: Contrast (Minimum) [Электронный ресурс]. Дата обращения: 11.08.2026. 

[3] W3C. Understanding Success Criterion 1.4.11: Non-text Contrast [Электронный ресурс]. Дата обращения: 11.08.2026. 

[4] W3C. Understanding Success Criterion 1.4.4: Resize Text [Электронный ресурс]. Дата обращения: 11.08.2026. 

[5] U.S. Web Design System. Typography [Электронный ресурс]. Дата обращения: 11.08.2026. 

[6] Tableau. Best Practices for Effective Dashboards [Электронный ресурс]. Дата обращения: 11.08.2026. 

[7] Grafana Labs. Grafana Dashboard Best Practices [Электронный ресурс]. Дата обращения: 11.08.2026. 

[8] Microsoft. Design Power BI Reports for Accessibility [Электронный ресурс]. Дата обращения: 11.08.2026. 

[9] Microsoft Playwright. Visual Comparisons [Электронный ресурс]. Дата обращения: 11.08.2026. 

[10] dbt Labs. About data tests property [Электронный ресурс]. Дата обращения: 11.08.2026. 

[11] Great Expectations. Data Quality Use Cases; Freshness; Integrity [Электронный ресурс]. Дата обращения: 11.08.2026. 

[12] Soda. SodaCL Checks; Freshness; Schema [Электронный ресурс]. Дата обращения: 11.08.2026. 

[13] Tableau. Organizational Assets — Dashboard Checklist and Style Guide [Электронный ресурс]. Дата обращения: 11.08.2026. 

[14] Tableau. Visual Best Practices; Tableau Blueprint Visual Best Practices [Электронный ресурс]. Дата обращения: 11.08.2026. 

[15] Microsoft. Power BI Report Accessibility Checklist [Электронный ресурс]. Дата обращения: 11.08.2026. 

[16] Google Cloud. Considerations when Building Performant Looker Dashboards [Электронный ресурс]. Дата обращения: 11.08.2026. 

[17] Grafana Labs. Dashboard JSON Model [Электронный ресурс]. Дата обращения: 11.08.2026. 

[18] Tableau. Tableau Server REST API; Metadata API [Электронный ресурс]. Дата обращения: 11.08.2026. 

[19] Tableau. tabcmd [Электронный ресурс]. Дата обращения: 11.08.2026. 

[20] Microsoft. Power BI Admin Scanner APIs; Execute Queries [Электронный ресурс]. Дата обращения: 11.08.2026. 

[21] Microsoft. Microsoft Fabric Command Line Interface [Электронный ресурс]. Дата обращения: 11.08.2026. 

[22] Google Cloud. Looker API: Content Validation, Query API and SDKs [Электронный ресурс]. Дата обращения: 11.08.2026. 

[23] Grafana Labs. HTTP API; Data Source API; gcx CLI; Foundation SDK [Электронный ресурс]. Дата обращения: 11.08.2026.
