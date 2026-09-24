# docs-content

- prompt: `prompt.docs.audit`
- surface_score: **1**
- proven: 8; P0/P1: 3
- run_id: `20260924T183653Z-9d9d303fa3f6-e28b4aa3`

Bootstrap README сверен с pyproject.toml, Makefile и .github/workflows/tests.yml: uv extras dev/tests/tracing, make install (dev,tests,tests_full,export), Python >=3.12, локальный .python-version 3.13, CI 3.12 и coverage на 3.13. 22 entity YAML (27 минус 5 composite) подтверждены. Материальное расхождение: README публикует нечитаемые ручки BIOETL_DQ_HARD_THRESHOLD=0.20, LOG_LEVEL, CB/RETRY/DELTA/QUARANTINE; иерархический hard_fail в configs/base/quality.yaml равен 0.50. Шпаргалки DQ вызывают удалённый bioetl dq validate --entity --show-rules. deployment-guide предписывает kubectl apply манифеста с шапкой «do not apply».

## Findings

- **DOCS-001** P1 PROVEN `README.md:297` — README задаёт BIOETL_DQ_HARD_THRESHOLD со значением по умолчанию 0.20 как порог остановки батча, но это имя не читается кодом.
- **DOCS-002** P1 PROVEN `docs/03-guides/cheatsheets/data-quality-rules.md:107` — Активные шпаргалки и troubleshooting предписывают удалённый CLI bioetl dq validate --entity --show-rules и bioetl diagnostics --pipeline --quarantine.
- **DOCS-003** P1 PROVEN `docs/05-operations/deployment/deployment-guide.md:117` — Активный deployment-guide шаг 2 выполняет kubectl apply -f k8s-deployment.yaml, тогда как сам манифест запрещает apply.
- **DOCS-004** P2 PROVEN `docs/03-guides/running-pipelines.md:446` — Инструкция export BIOETL_LOG_LEVEL=DEBUG не меняет уровень логов: код эту переменную не читает.
- **DOCS-005** P2 PROVEN `README.md:299` — Таблица README для circuit breaker, retry, Delta vacuum и quarantine retention называет переменные, которых нет в Settings и в src.
- **DOCS-006** P2 PROVEN `README.md:294` — README указывает дефолт BIOETL_OBSERVABILITY__DQ_MONITOR_ENABLED=false, код инициализирует dq_monitor_enabled=True.
- **DOCS-007** P2 PROVEN `docs/04-reference/cli.md:1578` — Справочник CLI называет ручку трейсинга BIOETL_TRACING_ENABLED, рабочее имя — BIOETL_OBSERVABILITY__TRACING_ENABLED.
- **DOCS-008** P2 PROVEN `docs/00-project/RULES.md:1146` — RULES §4.2.1 фиксирует нижние границы pytest, pytest-asyncio и vcrpy ниже, чем extra tests в pyproject.toml.

## Remediations

- Удалить несвязанные BIOETL_DQ_HARD_THRESHOLD и BIOETL_DQ_SOFT_THRESHOLD из README и k8s ConfigMap; порог описывать как hard_fail 0.50 из configs/base/quality.yaml.
- Заменить в шпаргалках DQ и common-errors вызов на bioetl dq validate <PIPELINE> и bioetl diagnostics quarantine --pipeline <NAME>.
- Убрать kubectl apply неподдерживаемого k8s-deployment.yaml из deployment-guide и не публиковать placeholder соли.
- В running-pipelines оставить включение DEBUG только через bioetl run --debug, пока код не читает BIOETL_LOG_LEVEL.
- Поднять пины pytest, pytest-asyncio и vcrpy в RULES §4.2.1 до extra tests в pyproject.toml.
