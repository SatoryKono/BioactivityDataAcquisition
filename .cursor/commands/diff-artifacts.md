# /diff-artifacts

**Goal:** Сравнить два артефакта (CSV/Parquet) по ключам и сформировать отчёт расхождений.


**Inputs**

- `--left PATH` (required): левый артефакт
- `--right PATH` (required): правый артефакт
- `--keys COLS` (required): список колонок-ключей
- `--show N` (optional): лимит примеров расхождений


**Steps**

1) Считать оба артефакта и нормализовать типы/колонки
2) Подсчитать added/removed/changed по ключам
3) Сохранить `diff_report.md` и образцы строк


**Constraints**

- Потоковая обработка больших файлов (избежать OOM)
- Кодировка и сепаратор должны определяться явно


**Outputs**

- `artifacts/diff/diff_report.md`
- `artifacts/diff/samples.csv`


**Exit criteria**

- Отчёт создан, код возврата 0
- Размер примеров не превышает `--show`

