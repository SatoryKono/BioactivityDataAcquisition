# Аудит содержания документации

- domain_id: `docs-content`
- prompt_id: `prompt.docs.audit`
- HEAD: `e1c184857e46` (`origin/main`, полный `e1c184857e460461bbb3e20829e60ab8bb262e2f`)
- SCOPE: `README.md`, `docs/`
- MODE: `audit` (read-only)
- AUDIT_MODE: `full`
- REQUIRE_GH_TRACKING: `false`
- surface_score: **2**
- blocked: **false**
- proven_count: **5**
- p0_p1_count: **0**

## Легенда surface_score

| Балл | Смысл |
| --- | --- |
| 3 | Критические сценарии описаны; команды сверены; ссылки/build под гейтом |
| 2 | Основной путь верен; есть устаревшие или неполные разделы |
| 1 | Существенный дрейф docs↔code |
| 0 | Критические инструкции отсутствуют или опасно неверны |

Балл **2**: bootstrap/README, 22 entity-конфига, ChEMBL 0.1 req/s, RPO/RTO runbook↔RULES, относительные ссылки и spec/config refs проходят `check-links`. Остаются дрейф ADR-потолков, env-таблицы README vs runtime, mismatch триггеров GHA-инвентаря. MkDocs strict build не запускался (зона `prompt.audit.docs-pipeline`).

## Метод

Worktree: `.worktrees/nine-domain-audit-9f71c6444175` @ `e1c184857e46`.

Инвентарь: README, onboarding (`getting-started.md`, `quick-start.md`), `docs-verification.md`, `cli.md`, `pipeline-catalog.md`, `environment-variables.md`, `github-actions-workflows.md`, `RULES.md`, `REQUIREMENTS.md`, `00-map.md`, `rules-summary.md`, runbook `data-recovery.md`, ADR-индексы.

Команда (UTC `2026-09-26T08:43:27Z`, exit **1** на workflow-inventory, остальное OK):

`python -m scripts.docs check-links --links --specs --configs --workflow-inventory --provider-overview`

- Links: OK
- Specs/Configs: OK
- ChEMBL provider overview: OK
- Workflow inventory: **4 trigger mismatches** (labeler, pr-hygiene, quality-debt-weekly, stale)

Дополнительно: `pyproject.toml` `version=6.1.0`, `requires-python>=3.12`; `Makefile` `install` = dev+tests+tests_full+export; README minimal uv sync согласован с quick-start; `rg BIOETL_LOG_FORMAT src` — пусто; `rg BIOETL_PUBMED_EMAIL src` — пусто.

Секреты не копировались. `.env` не изменялся. Бюджеты техдолга не менялись. Продукта не редактировал.

## Закрыто на этом коммите (не в findings)

- **RULES.md** шапка `Version: 6.1.13`, `Last verified: 2026-09-25`; changelog 6.1.13 для ADR-061 со статусом **Accepted** — прежние DOCS-001/002 с `32d77a51` устранены.
- **00-overview.md:73** уже through ADR-061.

## PROVEN (5)

| ID | Pri | Path | Кратко |
| --- | --- | --- | --- |
| DOCS-001 | P2 | `docs/01-requirements/REQUIREMENTS.md:86` | Потолок ADR-052 vs ADR-057 в списке и ADR-060/061 в RULES |
| DOCS-002 | P3 | `docs/00-project/rules-summary.md:16` | ADR-053–059 в скобках без 060/061 |
| DOCS-003 | P3 | `docs/00-project/rules-summary.md:10` | Last verified 2026-08-14 vs v6.1.13 (2026-09-16) |
| DOCS-006 | P2 | `docs/04-reference/github-actions-workflows.md` | Triggers ≠ executable `on:` (REQ-DOC-001 / check-links) |
| DOCS-007 | P3 | `docs/00-project/00-map.md:10` | Last verified 2026-08-14 vs body 2026-09-25 |

## NOT_PROVEN (2)

| ID | Pri | Path | Причина статуса |
| --- | --- | --- | --- |
| DOCS-004 | P2 | `README.md:288` | `requirement_id=GAP` — нет REQ-* на каждую env-строку README |
| DOCS-005 | P2 | `environment-variables.md:36` | `requirement_id=GAP` — контракт PubMed email vs код без SSOT binding |

## Top remediations

1. Исправить ADR coverage в `REQUIREMENTS.md:86` до ADR-061 или явно делегировать на `decisions/README.md`.
2. Синхронизировать колонку Triggers в `github-actions-workflows.md` с YAML (или split design vs executable) до `check-links` exit 0.
3. Обновить ADR-диапазон и `Last verified` в `rules-summary.md` и `00-map.md` в одном docs changeset с `generate-cleanup-inventory --update`.
4. Согласовать README / `environment-variables.md` с фактическим чтением env (отдельно docs vs product).

## Post-change validation (этот прогон)

| Check | Result |
| --- | --- |
| `check-links --links --specs --configs --provider-overview` | OK |
| `check-links --workflow-inventory` | FAIL (4 mismatches) |
| Junie/Codex mirror | skipped (runtime не менялся) |
| module-coverage inventory | skipped (src не менялся) |
| documentation-cleanup inventory | skipped (Owner/Status/Class headers не менялись) |
