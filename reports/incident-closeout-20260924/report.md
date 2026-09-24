# Incident Workspace: implementation and acceptance evidence

Дата: 2026-09-24. Scope: #10977–#10982. Итог всей серии: **BLOCKED**, не полный PASS.

Реализованы GLOBAL-контекст, отдельная Cause verification, отсутствие пустого
разделителя Object, Not provided для отсутствующего атрибута provider, сброс
несовместимого исторического Run ID в Action и таблица исходных измерений.
Атрибут provider добавляется только в результат display query: исходные ALERTS
и verdict здоровья не переписываются. Raw UNVERIFIED сохранён.

## Проверенные результаты

- 38 dashboard integration tests: PASS, включая readability, no-scroll и новые
  регрессии контекста/переходов/актуальности.
- Promtool: PASS для lag 299/300/301, backlog 0/1, missing/stale после 16 минут,
  отсутствующего provider во всех строках и смешанных серий с provider/без него.
- На фиксированный конец диапазона 2026-09-24 10:40 UTC получено 10 suspect
  series, 12 alert series, 3 строки измерений. Таблицы summary показывают 2 строки.
- Stage lag ChEMBL: 600.194919 s, порог >=300 s, maximum за 15 минут.
  Backlog: 2 records, >0, instant. Сохранённые gauges не доказывают текущую
  активность запуска. Время наблюдения/публикации недоступно и обозначено явно.
- Живые panels Grafana совпали с локальным JSON; resource version и SHA-256
  находятся в render-context.json. Это не утверждение идентичности всего runtime.
- Реальные viewport screenshots: 1011x920 и 1366x768, dark, одинаковые UTC range
  и variables. На 1366x768 нижняя таблица требует прокрутки страницы; полного
  first-screen parity не заявлено. Измерения открыты отдельно в viewPanel=22011.
- Action из ChEMBL-строки открыл Pipeline Diagnostics с
  pipeline=chembl_compound_record, workflow=All, run_type=All, run_id=-;
  абсолютный диапазон сохранён. Подтверждение: row-action.ax.txt.

## Незакрытые критерии

Для #10981 найдено точное историческое доказательство: Pipeline filter-options
workflow=.* в 10:09:50 UTC; Infinity вернул downstream 504 через 33.705 s
в 10:10:24 UTC. Это не parser error и не VALID EMPTY. В текущем повторе
10 запросов подряд прошли за 4.135–5.030 s, три параллельных — 6.827–7.054 s.
Проверены All, chembl_baseline и отсутствующий workflow. Исходная причина
замедления чтения не установлена; таймаут не увеличен, ошибка не замаскирована.
Исторический сбой CONFIRMED; текущее воспроизведение NOT_REPRODUCED;
исправление причины NOT_VERIFIED. API-прогоны не выдаются за 10 browser reloads.

Поэтому #10981 и #10982 остаются открытыми. Итоговая приёмка также не заявляет
полной error-state UI матрицы или проверки всех 48 702 контекстов #10961.
CI оценивается отдельно от этих локальных проверок. AI runtime mirrors: N/A;
.env не изменялся; бюджеты технического долга не повышались.
