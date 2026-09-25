# Аудит содержания документации

- domain_id: `docs-content`
- prompt_id: `prompt.docs.audit`
- HEAD: `32d77a51e556` (`origin/main`, полный `32d77a51e556de60d6dc0daf871a442becc709c5`)
- SCOPE: `README.md`, `docs/`
- MODE: `audit` (read-only; патчи не предлагались к применению)
- AUDIT_MODE: `full`
- REQUIRE_GH_TRACKING: `false`
- surface_score: **2**

## Легенда surface_score

| Балл | Смысл для этого домена |
| --- | --- |
| 3 | Критические пользовательские и инженерные сценарии описаны; команды сверены; ссылки и сборка закрыты гейтом |
| 2 | Основной путь верен; есть устаревшие или неполные разделы |
| 1 | Существенный дрейф docs↔code или почти только ручные проверки |
| 0 | Критические инструкции отсутствуют, невоспроизводимы или опасно неверны |

Балл 2: bootstrap, каталог пайплайнов, CLI, rate limit ChEMBL и относительные ссылки сходятся с манифестами. Версия `RULES.md` и несколько операторских утверждений об env расходятся с текстом или кодом. Сборка MkDocs не запускалась: это зона `prompt.audit.docs-pipeline`.

## Метод

Инвентарь ограничен активными точками входа, а не подсчётом Markdown. Сверены `README.md`, `docs/03-guides/getting-started.md`, `docs/03-guides/quick-start.md`, `docs/03-guides/docs-verification.md`, `docs/04-reference/cli.md`, `docs/04-reference/pipeline-catalog.md`, `docs/04-reference/environment-variables.md`, `docs/00-project/RULES.md`, `docs/01-requirements/REQUIREMENTS.md`, runbook восстановления и ADR-индексы.

Команда (SCOPE=checkout, UTC `2026-09-25T08:48:49Z`, exit 0):

`python -m scripts.docs check-links --links --specs --configs --workflow-inventory --provider-overview`

Результат: битых относительных ссылок нет; nav-файлы на месте; spec/config файлы существуют; инвентарь workflow совпадает с `.github/workflows`; обзор ChEMBL совпадает с entity-config.

Дополнительно вручную: `pyproject.toml` `version = "6.1.0"` и `requires-python = ">=3.12"`; `.python-version` = `3.13`; CI `tests.yml` — матрица 3.12 и shard 3.13; `Makefile` target `install` = `dev,tests,tests_full,export`; 22 YAML в `configs/entities/*/` вне `composite/`; `configs/providers/chembl.yaml` `requests_per_second: 0.1`; имена команд в `src/bioetl/interfaces/cli/main.py` совпадают с заголовками `docs/04-reference/cli.md`; RPO 24 ч / RTO 4 ч в `data-recovery.md` совпадают с `RULES.md` §5.5.

Не запускалось: MkDocs strict build, Docker, полный `scripts.docs verify`, публикация сайта.

Секреты в отчёт не копировались. `.env` не изменялся. Бюджеты техдолга не менялись.

## PROVEN

1. **DOCS-001** (`REQ-GOV-006`, P2). В `docs/00-project/RULES.md:3` поле `Version: 6.1.11`, `Last verified: 2026-08-25`. Changelog в том же файле (`:2166-2169`) уже содержит **6.1.12** и **6.1.13**. Зеркала `REQUIREMENTS.md`, `00-map.md` и `rules-summary.md` повторяют 6.1.11, то есть согласованы с шапкой, но не с головой changelog. `tests/architecture/test_docs_version_sync.py` берёт версию из шапки, поэтому этот разрыв не ловит.

2. **DOCS-002** (`REQ-GOV-006`, P3). Changelog 6.1.13 (`RULES.md:2166-2167`) называет ADR-061 `Proposed`. Сам ADR (`ADR-061-persisted-selected-run-assessment.md:14`) и приложение F (`RULES.md:2162`) имеют статус Accepted.

## NOT_PROVEN

Путь и строки есть. Статус `NOT_PROVEN`, потому что в каталоге нет `REQ-*`, который прямо требует эти инварианты (`requirement_id=GAP`, evidence-contract v3). Issue по ним не открывать.

3. **DOCS-003** (P2). `REQUIREMENTS.md:86` пишет, что каталог покрывает архитектуру through ADR-052, а ниже в том же разделе перечислены ADR-053…ADR-057 и нет ADR-058…ADR-061. `docs/02-architecture/00-overview.md:73` ограничивает ключевые ADR фразой through ADR-059. `docs/00-project/rules-summary.md:16` указывает диапазон ADR-053–059. Канонический индекс `docs/02-architecture/decisions/README.md` уже содержит Accepted ADR-060 и ADR-061. Тест `test_rules_and_requirements_do_not_publish_stale_adr_ceiling` проверяет `RULES.md` и `decisions/README.md`, но не эти три абзаца.

4. **DOCS-004** (P2). `README.md:288` описывает `BIOETL_LOG_FORMAT` со значениями `json` / `text` и default `json`. В `src/` строка `BIOETL_LOG_FORMAT` отсутствует. `src/bioetl/composition/bootstrap_logger.py:63` вызывает `configure_logging(json_format=True, log_level="INFO")`. Переменная из README не меняет формат логов. `BIOETL_LOG_FILE` при этом читается в `logging_config.py:228`.

5. **DOCS-005** (P2). `docs/04-reference/environment-variables.md:36` и `docs/05-operations/verification/endpoint-validation-checklist.md:450` говорят, что пустой `BIOETL_PUBMED_EMAIL` даёт `None` и не подставляет фиктивный адрес. В `src/` нет чтения `BIOETL_PUBMED_EMAIL`. `Settings.default_email` (`src/bioetl/infrastructure/config/_base.py:161-164`) по умолчанию равен `default@example.com`. `_resolve_biblio_contact_email` (`_registration_biblio_profiles.py:48-55`) возвращает pipeline email или этот default. В `configs/**/*.yaml` поля `email:` нет, поэтому unset-путь попадает в placeholder. `.env.example:74` всё равно публикует пустой `BIOETL_PUBMED_EMAIL=`.

## Что сверено и не стало finding

- Назначение проекта и Local-Only (ADR-010) в README есть.
- Минимальный bootstrap `uv sync --extra dev --extra tests --extra tracing` согласован между README и `quick-start.md`; отличие от `make install` названо явно.
- 22 entity-конфига и ChEMBL 0.1 req/s совпадают с YAML.
- `bioetl rollback` в runbook помечен как отсутствующий; `rm -rf data/` в `retention-sensitive-cleanup.md:227-235` стоит в блоке Disallowed.
- Kubernetes-гайд помечен как экспериментальный и запрещает `kubectl apply` для `k8s-deployment.yaml`.
- Маркеры TODO/FIXME/TBD в `docs/05-operations/**` как незакрытые операционные дыры не найдены. `ADR-060:239` содержит TBD владельцев overlay; это не runbook и не security-процедура.

## Остаточный риск

Оператор может выставить `BIOETL_LOG_FORMAT=text` или `BIOETL_PUBMED_EMAIL` и решить, что runtime это принял. Индекс требований может быть прочитан как покрытие только до ADR-052. Номер версии RULES в шапке отстаёт от changelog на два пункта.
