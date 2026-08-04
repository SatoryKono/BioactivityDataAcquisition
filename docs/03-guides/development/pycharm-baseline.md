______________________________________________________________________

Version: 1.0.0
Status: active
Class: repo-only
Owner: BioETL Team
Last verified: '2026-08-04'

______________________________________________________________________

# PyCharm configuration baseline (BioETL)

> Relocated from orphan `docs/development/pycharm.md` during documentation
> architecture audit cycle 2 (#7429). Prefer the published walkthrough
> [pycharm-setup.md](pycharm-setup.md).

Версия: 2026.01.4 stable, Python: 3.13.7 (Windows), проект: BioactivityDataAcquisition.

Полный operator guide: [pycharm-setup.md](pycharm-setup.md).

## Post-clone sync (canonical)

```powershell
.\scripts\engineering\dev\sync_pycharm_ide_templates.ps1
```

```bash
bash scripts/engineering/dev/sync_pycharm_ide_templates.sh
```

Скрипт копирует только portable surfaces из `configs/ide/pycharm/` в локальный
`.idea/` (codeStyles, inspectionProfiles, runConfigurations, `pyLspTools.xml`),
прогоняет policy check shared run-config и **не** трогает machine-local
`workspace.xml` / shelves / SDK paths (без `-ForceAll` / `--force-all`).

## Path model (важно)

| Surface | Типичное расположение | Примечание |
| ------- | --------------------- | ---------- |
| JetBrains config / system / index | `%APPDATA%` / `%LOCALAPPDATA%\JetBrains` (диск C:) | Обычно уже на SSD |
| Project root + `.venv-win` | checkout path | I/O risk, если tree на cloud-sync volume |
| UV / tool caches | `%LOCALAPPDATA%` или `%TEMP%` | Не класть под GDrive project tree |

«IDE на C:» **не** снимает hangs от чтения/записи project tree на synced disk.

## Зафиксированные настройки IDE

- PyCharm: stable 2026.1.4 (EAP 2026.2 отдельно, не для ежедневной работы).
- Baseline-вывод: верно идентифицированы ограничения в виде эффективного `heap`, отсутствия единой tool integration и избытка inline AI-плагинов; именно эти три пункта закрываются текущим планом.
- Ограничение: `-Xmx` — это настройка памяти JVM PyCharm, отдельная от памяти Python-процессов ETL; ETL-ресурсы измеряются и оптимизируются на уровне запусков пайплайнов.
- Включён: `Settings | Memory Usage | Show Memory Indicator`.
- `Xmx` подбирается по измерениям и настраивается только через UI Memory Usage.
- `custom GC flags` отсутствуют по умолчанию; новые `-XX` флаги не вводятся без
  диагностики memory pressure/GC.
- Предпочтительно: project root / `.venv-win` / tool caches на локальном SSD; IDE system cache уже на C: в default Windows layout. `.env` не коммитится.
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
- Run/debug конфигурации (shared):
  - `pytest-fast`
  - `pytest-full`
  - `pytest-coverage`
  - `pytest-debug`
  - `pytest-architecture` (offline lane `tests/architecture`)
  - `mypy-full`
  - `ruff-check`
  - `ruff-format-check`
  - `quality-gate`
  - `BioETL smoke (offline fixture)`
- Policy shared configs: no `PYTHONPATH`, `ADD_*_ROOTS=false`, `--no-cov` на
  non-coverage pytest lanes; `--cov*` только в `pytest-coverage`.
- Все shared run/debug конфигурации воспроизводимы на `clean clone` и не содержат
  ручного `PYTHONPATH`.
- Параметры и проверки не дублируются между UI, `pyproject.toml` и CI без необходимости.
- Local-only Live / compound configs **MUST NOT** публиковаться в
  `configs/ide/pycharm/`; см. anti-patterns в setup guide.

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
- Architecture tests (Run/Debug):
  - **pytest-architecture** — daily gate (`tests/architecture`, marker filter, offline)
  - **pytest-architecture-full** — полный sweep `tests/architecture`
  - CLI: `make test-architecture` или `pytest tests/architecture/ -m "architecture and not slow and not benchmark and not memory" --no-cov`
  - Sync в локальный `.idea/`: `bash scripts/engineering/dev/sync_pycharm_ide_templates.sh`
- `.idea` в VCS не публикуется целиком; только выбранные shared артефакты выше.
- `secrets` не хранятся в `.idea/` и не вшиваются в shared run/debug конфигурации.
- В `.gitignore` и `.gitattributes` зафиксированы line endings и исключения.
