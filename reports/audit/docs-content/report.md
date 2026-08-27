# Аудит содержимого документации (docs-content)

| Поле | Значение |
| --- | --- |
| `domain_id` | `docs-content` |
| `prompt_id` | `prompt.audit.docs-content` |
| HEAD | `5af9180c354e4406da4bfdf17d94d6c8efee6aaa` |
| Ветка | `fix/stream-a-quality-9717` |
| Дата | 2026-08-27 |
| SCOPE | `README.md docs/` |
| MODE | `audit` |
| AUDIT_MODE | `full` |
| `surface_score` | **2** (acceptable) |

## Легенда surface_score (0–3)

| Балл | Качество | Смысл |
| ---: | --- | --- |
| 3 | good | Критические сценарии описаны; команды сверены; ссылки/сборка закрыты |
| 2 | acceptable | Основной путь верен; есть устаревшие или противоречивые секции |
| 1 | weak | Существенный drift docs↔code или в основном ручные проверки |
| 0 | unacceptable | Критические инструкции отсутствуют, невоспроизводимы или опасны |

## Итог

Основной onboarding-путь **работоспособен**: README описывает назначение проекта, Python `>=3.12` совпадает с `pyproject.toml`, 22 entity-конфига и rate-limit провайдеров совпадают с `configs/`, CLI-команды `run` / `quarantine inspect` / `checkpoint list` / `config list-pipelines` существуют в коде, 46 workflow-файлов совпадают с инвентарём. Относительные ссылки в 11 ключевых файлах (278 ссылок) разрешаются.

Балл **2**, а не 3: между каноническим `make install` и «рекомендованным» `uv sync --extra dev --extra tests --extra tracing` остаётся противоречие; mixed-checkout ставит Python 3.13 при заявленном baseline 3.12; диаграмма релиза всё ещё говорит про CI на 3.11; AI-зеркало CLAUDE.md держит мёртвую цель `make security` и устаревшие якоря `Makefile:63` / `tests.yml:158`.

P0/P1: нет. Секретов в проверенных docs не обнаружено.

## Инвентарь (SCOPE)

| Поверхность | Статус |
| --- | --- |
| `README.md` | Активный public onboarding; purpose, bootstrap, env, структура |
| `docs/**` | 1444 Markdown-файла; норматив — `docs/00-05` |
| `CONTRIBUTING.md` | Указатель на `.github/CONTRIBUTING.md` |
| `.github/SECURITY.md` | Политика + reporting (ссылка из README) |
| `CHANGELOG.md` / `LICENSE` / `.github/CODE_OF_CONDUCT.md` | На месте |
| `SUPPORT.md` | Отсутствует (не блокер; GitHub security/contributing есть) |
| ADR / runbooks / onboarding | Индексы живые (`00-map.md`, `docs/05-operations/runbooks/`) |

Diátaxis (ориентир): tutorial = `getting-started.md` / `quick-start.md`; how-to = `running-pipelines.md` / runbooks; reference = `cli.md` / `pipeline-catalog.md`; explanation = `RULES.md` / ADR.

## Сверка команд ↔ манифесты / CI

| Утверждение docs | Факт checkout | Вердикт |
| --- | --- | --- |
| `pyproject.toml` `requires-python = ">=3.12"`, classifiers 3.12/3.13 | Совпадает с README baseline/supported | OK |
| 22 entity YAML + 5 composite | `configs/entities/**` (22+5) | OK |
| ChEMBL 0.1 / PubChem 5 / UniProt 10→100 / PubMed 3→10 / S2 0.1→1 | `configs/providers/*.yaml` | OK |
| `python -m scripts.ops setup-plugins` | `Makefile` `setup-plugins` | OK |
| `python -m scripts.engineering.dev run-tests {cov,unit,arch,integration,smoke}` | `scripts/engineering/dev/run_tests.py` | OK |
| `python -m scripts.docs check-links\|check-drift\|check-docstrings` | `scripts/docs/__main__.py` | OK |
| `uv run python -m scripts.engineering.dev setup-mcp` | роутер на `scripts.ai.codex.setup_mcp` | OK (алиас `scripts/ai/codex/setup_mcp.py`) |
| GHA inventory «46 workflows» | 46 файлов `.github/workflows/*.yml` | OK |
| `make install` extras `dev,tests,tests_full,export` | `Makefile:99` | OK как operator-канон |
| README/quick-start extras `dev,tests,tracing` | не равны `make install` | **drift** |
| Mixed Windows/WSL: Python 3.13 в `setup_env_*.ps1/sh` | README/getting-started baseline 3.12 | **drift** |
| `make lint` = `ruff check src tests scripts` + `mypy src/bioetl` | README: `ruff check .` + mypy `--strict --no-incremental` | **расхождение scope** |
| `make test` игнорирует e2e/contract | README `run-tests cov` = `tests/` minus memory | **разные suite** |
| `make security` | цели нет; есть `security-check` = `pytest tests/security/` | **неверная команда в CLAUDE.md** |
| Release diagram: CI на 3.11+3.12+3.13 | `release.yml` только 3.13; tests 3.12+3.13 | **устарело** |

`dev` extra уже содержит import-linter/grimp/radon/vulture, поэтому отсутствие `tests_full` в README Option A **не ломает** architecture-тесты. Функциональный разрыв — в основном `export` (openpyxl) и ясность канона.

## Ссылки

Выборочная проверка относительных markdown-ссылок (не MkDocs-пайплайн):

- Файлы: `README.md`, `docs/00-project/00-map.md`, `docs/03-guides/getting-started.md`, `quick-start.md`, `docs-verification.md`, `CONTRIBUTING.md`, `.github/CONTRIBUTING.md`, `docs/04-reference/cli.md`, `pipeline-catalog.md`, `local-storage-layout.md`, `docs/DOCKER_QUICKSTART.md`
- Результат: **278 OK / 0 missing / 13 внешних пропущены**

Полный `python -m scripts.docs check-links` **не запускался** (граница с `prompt.audit.docs-pipeline`).

## Топ пробелов

1. Два «канонических» extra-набора (`make install` vs `uv sync … tracing`) при том, что quick-start/running-pipelines **приравнивают** их.
2. Getting-started: mixed path → Python **3.13**, manual Windows fallback → **`py -3.12`**.
3. `docs/03-guides/github-workflow-diagrams.md` описывает релизный CI на Python 3.11.
4. `CLAUDE.md`: `make security`, `Makefile:63`, `tests.yml:158`, RULES v6.1.5, PipelineRunner «189 строк» (файл 222).
5. Разная раскладка quarantine: `running-pipelines.md` (`quarantine/_delta_log/`) vs `getting-started.md` / `local-storage-layout.md` (`common.quarantine`).
6. README `run-tests cov` vs CONTRIBUTING/cheatsheet `make test` — разные наборы тестов.

## Remediation (без патчей в этом режиме)

1. Выбрать один канон extras и везде явно пометить второй как subset (README уже близок; убрать «canonical = make install» из quick-start Option A).
2. Зафиксировать mixed-checkout Python (3.12 baseline **или** 3.13 wrapper) в getting-started и README.
3. Убрать 3.11 из релизной диаграммы; синхронизировать с `release.yml` / `tests.yml`.
4. Обновить CLAUDE.md якоря по live Makefile/CI; заменить `make security` на `make security-check` + отдельно `pip-audit`/OSV.
5. Выровнять дерево quarantine в running-pipelines с ADR-025 layout.
6. В cheatsheet таблице не называть `make test-deps` установкой зависимостей.

## Проверки

| Проверка | Статус |
| --- | --- |
| Инвентарь README/docs/CONTRIBUTING/SECURITY/CHANGELOG | выполнено |
| Команды bootstrap/test/lint vs Makefile/`pyproject.toml`/CI | выполнено (выборка) |
| Относительные ссылки (11 файлов) | выполнено |
| Rate-limit / entity count vs configs | выполнено |
| CLI flags vs `src/bioetl/interfaces/cli` | выполнено (выборка) |
| Полный `scripts.docs check-links` / MkDocs build | **пропущено** (docs-pipeline) |
| Живость внешних HTTP-ссылок | **пропущено** |
| `docs/99-archive/**` как норма | не аудировался (historical) |
| Техдолг-бюджеты / `.env` | не изменялись |

Tech-debt outcome: **unchanged**.
