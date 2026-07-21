# PyCharm configuration baseline (BioETL)

Версия: 2026.01.4 stable, Python: 3.13.7 (Windows), проект: BioactivityDataAcquisition2.

## Зафиксированные настройки IDE

- PyCharm: stable 2026.1.4 (EAP 2026.2 отдельно, не для ежедневной работы).
- Baseline-вывод: верно идентифицированы ограничения в виде эффективного `heap`, отсутствия единой tool integration и избытка inline AI-плагинов; именно эти три пункта закрываются текущим планом.
- Ограничение: `-Xmx` — это настройка памяти JVM PyCharm, отдельная от памяти Python-процессов ETL; ETL-ресурсы измеряются и оптимизируются на уровне запусков пайплайнов.
- Включён: `Settings | Memory Usage | Show Memory Indicator`.
- `Xmx` подбирается по измерениям и настраивается только через UI Memory Usage.
- `custom GC flags` отсутствуют по умолчанию; новые `-XX` флаги не вводятся без
  диагностики memory pressure/GC.
- Работа на локальном SSD для project root/venv/system cache; `.env` не коммитится.
- Activity Monitor используется для оценки нагрузки; функции IDE не отключаются без измерений.

## Quality tools

- Ruff: единственный владелец lint/format/import optimizer (через pyproject.toml);
  ровно один formatter и ровно один import optimizer.
- `External Tools` не используется как основная интеграция для `ruff`/`black`/`pytest`/`mypy`; все вызовы идут через нативные PyCharm tools и shared run/debug конфигурации.
- Форматтерная политика едина: одновременно Ruff format и Black formatter не включаются как активные пути форматирования (On Save/Actions/CI).
- Black: выключен в PyCharm при использовании Ruff formatter.
- `mypy-full` — один и основной type-checking authority для типа, совпадает с CI target.
 - `mypy --strict $FilePath$` не используется как основной quality gate; допускается только как вспомогательная локальная проверка.
 - Ruff check/mypy/pytest запускаются по репозиторным конфигам и имеют те же
 параметры в CI/quality-gate.
- `pytest-debug` выполняется без coverage (по умолчанию для debug сценариев),
  coverage используется только в `pytest-coverage`.
 - Для CI/IDE quality gate `coverage` не ставится глобальным default-флагом в `pytest-fast`, `pytest-full`, `pytest-debug` — покрытие включается только в `pytest-coverage`-конфигурации.
  - Чек-лист по coverage: нет `--cov` в `pytest-fast/full/debug`, нет global `--cov` в addopts/IDE defaults, `pytest-coverage` держит `--cov*` и пороги в одном месте.
- Run/debug конфигурации:
  - `pytest-fast`
  - `pytest-full`
  - `pytest-coverage`
  - `pytest-debug`
  - `mypy-full`
  - `ruff-check`
  - `ruff-format-check`
  - `quality-gate`
- Все shared run/debug конфигурации воспроизводимы на `clean clone` и не содержат
  ручного `PYTHONPATH`.
- Параметры и проверки не дублируются между UI, `pyproject.toml` и CI без необходимости.

## AI

- Один active inline completion provider; остальные плагины в режиме чата/agent или отключены.
- Проверены duplicate shortcuts и автоматическая индексация контекста.

## Determinism and templates

- RunContext: `run_id`, `started_at`, `seed`, `source_version`, `config_hash`.
- Детерминированный export: канонизация schema/dtypes/columns/timezone/nulls, stable sort с tie-breaker, canonical hash-set.
- `atomic write` для outputs + reproducibility tests (двойной запуск с одинаковым input/context).
- Live templates: только короткие API snippets; большой pipeline — в шаблоны/генераторы.
- Детерминизм (сортировка/hash/canonicalization, clock) реализуется в коде и тестах; snippets/template не содержат deterministic control-flow.
- Для Python отладка идёт через `debugpy`/`pydevd` (локально) и удалённый Python Debug Server/Attach по необходимости; режим `GDB-compatible` как отдельная IDE-настройка для PyCharm не существует.
- Шаблоны используют корректный синтаксис (`$VARIABLE$`, `$END$`) и только существующие API/импорты проекта.
- Для повторного pipeline run проводится reproducibility check: два прогонов с одинаковым
  input/config/context должны давать тот же output hash и совпадение key metadata.
- Улучшения выражаются измеримыми метриками (latency/время выполнения/heap/GC/coverage),
  а не неопровергнутыми процентными оценками без baseline.

## Git/shared settings

- `configs/ide/pycharm/` содержит shared run/debug templates и inspection/code-style settings:
  - `configs/ide/pycharm/runConfigurations/`
  - `configs/ide/pycharm/codeStyles/`
  - `configs/ide/pycharm/inspectionProfiles/`
  - `configs/ide/pycharm/pyLspTools.xml`
- `.idea` в VCS не публикуется целиком; только выбранные shared артефакты выше.
- `secrets` не хранятся в `.idea/` и не вшиваются в shared run/debug конфигурации.
- В `.gitignore` и `.gitattributes` зафиксированы line endings и исключения.
