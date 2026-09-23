# Аудит контента документации — отчёт

- Scope: `README.md docs/` (ключевые entry-доки + свип 601 файла публикуемого дерева)
- Mode: `audit` (без патчей), Language: `ru`, Audit mode: `full`
- Дата: 2026-09-23
- surface_score: **2** — главный путь корректен, есть воспроизводимый дефект bootstrap и точечные расхождения

## Проверено и соответствует (evidence)

- Относительные `.md`-ссылки: 0 битых в 9 ключевых entry-доках; свип 601 файла публикуемого дерева — 0 битых (1 ложное срабатывание regex в code span).
- Версии: бейдж README 6.1.0 == `pyproject.toml` 6.1.0; `requires-python >=3.12` согласуется с "поддерживаются 3.12 и 3.13".
- `make install` (extras `dev,tests,tests_full,export`) совпадает с описанием в README; extras `docs`/`tests_full`/`tracing` существуют.
- Coverage-бейдж ≥85% совпадает с гейтом CI (`coverage report --fail-under=85`, `tests.yml:1487`); локальный `LOCAL_COV_FAIL_UNDER=80` — намеренная нижняя граница.
- CLI: `run --required-persistence-profile`, `quarantine inspect`, `checkpoint list` существуют и совпадают с README-примерами.
- TODO/FIXME/TBD в `runbooks/*.md` и `03-guides/*.md` — нет. Секреты (ghp_/sk-/AKIA/xox) в сканированных доках — нет.
- Diátaxis: README — how-to+reference; 00-map — navigation; cli/env — reference; docs-verification — how-to. Покрытие учебных сценариев (tutorial) — через guides, gaps не критичны.

## Находки

| ID | Приоритет | Суть | Статус |
| --- | --- | --- | --- |
| F1 | P1 | `uv run python -m scripts.ops setup-plugins` (рекомендованный bootstrap в README) падает на нативном Windows PowerShell: `/bin/bash: ...setup_plugins.sh: No such file or directory` (воспроизведено). Обход — `setup_env_windows.ps1`, но основной путь невоспроизводим | proven |
| F2 | P2 | `.env.example` рекомендует `bioetl quarantine serve --port 8081`, а CLI помечает `serve` как retired-legacy и `cli.md` фиксирует, что compose его не стартует | proven |
| F3 | P3 | `.python-version` = 3.13 при README-baseline 3.12 (поддерживаются обе; риск расхождения окружений новичков) | proven-minor |
| F4 | P3 | Дефолты PIPELINE/DQ/Quarantine/Delta живут только в таблице README; `.env.example` (11 ключей) и env-reference (partial) их не дублируют. Противоречий нет, сверка с кодом настроек не выполнена | observation |

Детали: `findings.json`, `docs-inventory.csv`, `broken-links.json`, `stale-docs.csv`, `docs-code-drift.csv` в этом каталоге.

## Ремедиация (без применения, mode=audit)

- F1: починить резолв пути `setup_plugins.sh` под Windows в `scripts/ops` либо заменить рекомендованную команду в README на `setup_env_windows.ps1` для PowerShell.
- F2: в `.env.example` пометить `serve` как legacy/retired со ссылкой на `quarantine inspect`, либо вернуть `serve` в поддерживаемый путь и обновить `cli.md`.
- F3: выровнять `.python-version` с baseline 3.12 либо явно зафиксировать 3.13 как baseline в README.
- F4: продублировать дефолты в `environment-variables.md` или сгенерировать таблицу из кода настроек.
