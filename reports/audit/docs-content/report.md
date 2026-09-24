# Аудит содержания документации

- Scope: `docs/`
- Mode: `propose-patches` (патчи не применены; правка docs ждёт подтверждения)
- Audit mode: `full`
- Дата проверки: 2026-09-24
- `surface_score`: **2** — основной bootstrap и гейты ссылок/дрейфа верны; в операторских таблицах env и в одном предложении про bootstrap есть расхождение с кодом и Makefile
- Основание шкалы: таблица промпта («главный путь верен, часть разделов устарела»), без перевода из 0–5

Патчи ниже — предложение. Заголовки `Owner` / `Status` / `Class` и ссылки не менялись, `generate-cleanup-inventory` не запускался.

## Что проверено

| Проверка | Результат |
| --- | --- |
| `python -m scripts.docs check-links --report-json reports/audit/docs-content/check-links.json` | exit 0, 0 нарушений (ссылки, specs, configs, contracts, workflow inventory, provider overview, doc governance, not-in-nav, legacy paths) |
| `python -m scripts.docs check-drift --json` | exit 0, `errors=0`, `warnings=0` |
| Bootstrap `docs/03-guides/getting-started.md` и `quick-start.md` | цели `make install` / `test-deps` / `setup-plugins`, extras `dev`/`tests`/`tests_full`/`export`/`tracing`/`docs`, скрипты `setup_env_*.ps1/sh` и `run-tests smoke` существуют; `requires-python >=3.12` совпадает с CI `3.12` |
| Секреты в `docs/**/*.md` | префиксы `ghp_` / `AKIA` / private key не найдены (только упоминание префиксов в правиле) |
| MkDocs / генераторы | вне этого аудита (`prompt.audit.docs-pipeline`) |

Инвентарь: 1487 markdown-файлов в `docs-inventory.csv`. У 1467 есть дата последнего коммита. `stale-docs.csv` пуст: штатный freshness-check не вернул устаревших evidence summary; возраст файла сам по себе не считался дефектом.

## Находки

Семь `PROVEN`. Issue не открывались (`REQUIRE_GH_TRACKING=false`).

### DOCS-001 — P1 — несуществующее имя tracing

`docs/04-reference/cli.md:1578` и `docs/03-guides/cheatsheets/cli-commands.md:691` задают `BIOETL_TRACING_ENABLED`. `Settings` это имя игнорирует (`extra=ignore`). Рабочее имя — `BIOETL_OBSERVABILITY__TRACING_ENABLED` (`src/bioetl/infrastructure/observability/tracing.py:24`).

Проба `Settings(_env_file=None)` 2026-09-24: плоское имя оставляет `observability.tracing_enabled=False`; вложенное имя ставит `True`.

Требование: `REQ-DX-005`.

### DOCS-002 — P1 — выключение метрик не тем флагом

`docs/03-guides/running-pipelines.md:481-484`, `cli.md:1576`, `cli-commands.md:689` переключают метрики через `BIOETL_METRICS_ENABLED`. Гейт читает `settings.observability.metrics_enabled` (`metrics_bootstrap.py:43-48`).

Проба: `BIOETL_METRICS_ENABLED=false` даёт `metrics_root=False` и `metrics_nested=True`. `BIOETL_OBSERVABILITY__METRICS_ENABLED=false` выключает вложенный флаг. Верное имя уже есть в `docs/03-guides/metrics-monitoring.md:116`.

Требование: `REQ-DX-005`.

### DOCS-003 — P2 — режимы `BIOETL_ENV`

`docs/04-reference/environment-variables.md:12` перечисляет `dev, test, prod`. `Settings.env` — `Literal["dev", "staging", "prod"]` (`_base.py:72`). Проба: `env="test"` → `ValidationError`. `cli.md:1573` указывает `dev, prod` и не называет `staging`.

Требование: `REQ-ENV-001`.

### DOCS-004 — P2 — контракт ключа OpenAlex

`environment-variables.md:26`: ключ необязателен и нужен «for higher rate limits». `docs/04-reference/providers/openalex/publication.md:172-174` и `:272`: для production-like запуска ключ обязателен, email его не заменяет. Адаптер по-прежнему принимает legacy-путь `api_key or mailto` и падает, только если нет обоих (`_client_support.py:95-99`).

Требование: `REQ-ENV-003`.

### DOCS-005 — P2 — два bootstrap склеены в один

`running-pipelines.md:59-60` называет одним каноническим bootstrap и `uv sync --extra dev --extra tests --extra tracing`, и `make install`. `Makefile:99-100`: `uv sync --extra dev --extra tests --extra tests_full --extra export`. `quick-start.md:50-55` прямо пишет, что наборы разные.

Требование: `REQ-DX-001`.

### DOCS-006 — P2 — `BIOETL_LOG_LEVEL` никуда не читается

Переменная указана в `getting-started.md:159`, `environment-variables.md:14`, `cli.md:1575`, `cli-commands.md:688`, `metrics-monitoring.md:119`. У `Settings` нет поля `log_level`. Поиск `BIOETL_LOG_LEVEL` в `src/` и `.env.example` пуст.

Требование: `REQ-DX-005`.

### DOCS-007 — P3 — `make test-deps` не устанавливает зависимости

`cli-commands.md:708`: «Install test-only dependencies». `Makefile:102-103` только импортирует уже установленные `pytest`, `pytest_cov`, `pytest_asyncio`, `hypothesis`, `vcr`.

Требование: `REQ-DX-001`.

## Предлагаемые патчи

Не применять без подтверждения.

1. В таблицах env `cli.md` и `cli-commands.md` заменить `BIOETL_TRACING_ENABLED` на `BIOETL_OBSERVABILITY__TRACING_ENABLED`.
2. В `running-pipelines.md:481-484` и тех же двух таблицах заменить переключатель метрик на `BIOETL_OBSERVABILITY__METRICS_ENABLED`.
3. В `environment-variables.md:12` и `cli.md:1573` перечислить режимы `dev`, `staging`, `prod`.
4. Строку OpenAlex в `environment-variables.md` выровнять с `publication.md`: ключ нужен для production-like запуска; email — только attribution; mailto без ключа — legacy fallback адаптера, не production boundary.
5. В `running-pipelines.md:59-60` убрать слэш-эквивалентность и повторить два набора из `quick-start.md`.
6. Убрать `BIOETL_LOG_LEVEL` из ключевых таблиц либо пометить, что Settings её не читает. Сначала подтвердить, какой контроль уровня логов считать рабочим (CLI debug, не новая переменная).
7. В `cli-commands.md:708` заменить «Install test-only dependencies» на «Check that test dependencies import».

## Что не является находкой

- `getting-started.md` и `quick-start.md` различают minimal tracing-набор и `make install` явно.
- `docs/05-operations/runbooks/retention-sensitive-cleanup.md:227-235` запрещает `rm -rf` по корням data/fixtures/reports.
- `docs/05-operations/runbooks/docker-stability.md:66-68` запрещает `docker system prune` и `docker compose down -v` как ответ на инцидент.
- Kubernetes-руководство помечено как experimental и не является ADR-010 path (`deployment-guide.md:16-21`).
- `RULES.md:1242` про «Python 3.10+ стиль типизации» относится к `from __future__ import annotations`, не к runtime baseline 3.12.
- TBD в `ADR-060:239` — владелец overlay, не operational/security процедура без owner.

## Артефакты

- `reports/audit/docs-content/findings.json`
- `reports/audit/docs-content/docs-inventory.csv`
- `reports/audit/docs-content/docs-code-drift.csv`
- `reports/audit/docs-content/broken-links.json`
- `reports/audit/docs-content/stale-docs.csv`
- сырьё гейтов: `check-links.json`, `check-drift.json`
