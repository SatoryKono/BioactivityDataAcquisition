# /smoke-run

**Goal:** Быстрый дымовой прогон выбранного пайплайна.


**Inputs**

- `--name NAME` (required): имя пайплайна
- `--limit N` (optional): ограничение строк
- `--sample N` (optional): детерминированная выборка
- `--output-dir PATH` (required)


**Steps**

1) Собрать минимальную конфигурацию
2) Запустить с `--limit/--sample`
3) Сохранить базовые QC/логи


**Constraints**

- Не менять публичный контракт
- Логгирование вместо print


**Outputs**

- `reports/smoke/<name>.md`


**Exit criteria**

- Код возврата 0; присутствуют QC и логи

