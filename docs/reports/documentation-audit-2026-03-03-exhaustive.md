# Documentation Audit Report (Exhaustive)

**Date:** 2026-03-03  
**Branch:** `main`  
**Scope:** полный аудит документации проекта (`docs/00-05`, `docs/99-archive`, `docs/plans`, `docs/reports`, `docs/skills`) с верификацией ссылок, nav-покрытия, drift-guardrails и согласованности с ADR.

## 1. Executive Summary

Аудит не выявил блокирующих проблем: все контрольные проверки проходят, `mkdocs --strict` собирается успешно, drift-guardrails чистые, provider docs приведены к каноническому `snake_case`.

Основные зоны для доработки — не блокирующие:
- большое количество документов вне nav (частично ожидаемо: архив/внутренние разделы);
- orphan-кандидаты внутри этих зон;
- технологический риск по будущей совместимости MkDocs/Material.

## 2. Inventory

- Всего markdown в `docs/`: **697**
- В `mkdocs` nav: **565**
- Вне nav: **132**
- Orphan-кандидаты (вне nav и без входящих ссылок): **70**

### Разбивка по разделам

| Раздел | Всего | В nav | Вне nav | Orphan-кандидаты |
|---|---:|---:|---:|---:|
| `00-project` | 19 | 19 | 0 | 0 |
| `01-requirements` | 1 | 1 | 0 | 0 |
| `02-architecture` | 371 | 338 | 33 | 10 |
| `03-guides` | 27 | 27 | 0 | 0 |
| `04-reference` | 86 | 86 | 0 | 0 |
| `05-operations` | 35 | 35 | 0 | 0 |
| `99-archive` | 58 | 0 | 58 | 54 |
| `plans` | 9 | 6 | 3 | 3 |
| `reports` | 10 | 6 | 4 | 0 |
| `skills` | 79 | 45 | 34 | 3 |

## 3. Findings by Severity

### Critical
- Нет.

### High
- Нет.

### Medium
1. **Nav coverage gap: 132 файла вне nav**
   - Основной объём: `99-archive/**` (58), `02-architecture/**` (33), `skills/**` (34), `plans/**` (3), `reports/**` (4).
   - Риск: ухудшение discoverability и размывание «единого источника истины». 

2. **Orphan-кандидаты: 70 файлов**
   - Преимущественно в `99-archive/**` и индексах рендер-артефактов диаграмм.
   - Риск: накопление мёртвой/неиспользуемой документации и сложность ревью.

3. **Toolchain warning (future risk)**
   - При `mkdocs --strict` есть предупреждение о несовместимости Material с MkDocs 2.0.
   - Сейчас не блокирует, но требует миграционного решения.

### Low
1. **Несогласованный путь REQUIREMENTS в части audit-артефактов**
   - Фактический файл: `docs/01-requirements/REQUIREMENTS.md`.
   - В ряде вспомогательных материалов/чеклистов ранее фигурировал путь `docs/00-project/REQUIREMENTS.md`.

2. **Сервисные CRLF/LF предупреждения в diff**
   - Не влияют на build/checks, но создают шум в анализе и ревью.

## 4. Compliance Snapshot

- **RULES/REQUIREMENTS:** содержательно согласованы для Local-Only/Deterministic/Observability.
- **ADR alignment:** ссылки на ADR-010/014/017 присутствуют в README, RULES и архитектурном контуре.
- **Providers docs drift:** legacy naming drift не обнаружен (проверка по ключевым паттернам прошла).

## 5. Verification (executed)

- `./.venv/Scripts/python.exe scripts/check_doc_links.py` — PASS
- `./.venv/Scripts/python.exe -m mkdocs build --strict` — PASS
- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_docs_version_sync.py -q -p no:xdist --tb=short` — PASS
- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_check_doc_links_guardrails.py -q -p no:xdist --tb=short` — PASS
- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_documentation_sync.py -q -p no:xdist --tb=short` — PASS
- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_documentation_sync.py::test_mkdocs_nav_references_existing_markdown_files -q -p no:xdist --tb=short` — PASS

## 6. Corrective Plan (prioritized)

### Phase A — Nav Policy Hardening (P1)
- Зафиксировать политику для `99-archive/**`, `skills/**`, `plans/**`, `reports/**`:
  - `active` (в nav),
  - `internal` (вне nav, но индексируемо),
  - `archive` (вне nav с явным дисклеймером).
- Добавить/обновить индексные страницы для зон вне nav.
- Acceptance: каждая зона имеет документированную policy + entrypoint.

### Phase B — Orphan Cleanup (P1)
- Обработать 70 orphan-кандидатов:
  - связать ссылками через index,
  - либо перевести в явный archive/internal,
  - либо удалить дубли/устаревшие элементы по решению.
- Acceptance: orphan-кандидаты сокращены минимум на 50% без потери нужных артефактов.

### Phase C — Guardrails Extension (P2)
- Расширить `check_doc_links` дополнительными правилами на path-consistency (например, REQUIREMENTS path contract).
- Сохранить baseline-подход для `not_in_nav` и запрет роста без явного обновления baseline.
- Acceptance: CI падает при новом drift/path regression.

### Phase D — MkDocs/Material Migration Track (P3)
- Подготовить ADR/план миграции toolchain (вариант pin или переход на рекомендуемый stack).
- Acceptance: утверждён owner, сроки, стратегия rollout.

## 7. Required Decisions

1. Считаем ли `skills/**` частью публичной проектной документации или internal-only секцией вне nav?
2. Делаем ли целевой KPI на `not_in_nav` (например, `132 -> <=100`) в ближайшем цикле?
3. Для `99-archive/**`: оставляем полнотекстово в репо или переносим часть historical reports во внешнее хранилище (artifact storage)?

## 8. Execution Update (2026-03-03)

В рамках исполнения Phase A/Phase B выполнено:

1. Добавлена governance-политика навигации:
   - `docs/00-project/governance/07-doc-nav-policy.md`
   - добавлен nav-узел `Docs Navigation Policy` в `mkdocs.yml`.
2. Добавлен entrypoint для archive-зоны:
   - `docs/99-archive/README.md` с явным historical/disclaimer контекстом.
3. Синхронизирован baseline non-nav:
   - `scripts/baselines/not_in_nav_baseline.txt` обновлён до **135** записей
     (добавлены `99-archive/README.md` и уже присутствующий `prompts/qa_orchestrator.md`).
4. Закрыт конфликт MkDocs site_dir:
   - в `mkdocs.yml` исправлено `site_dir: docs/site` -> `site_dir: site`;
   - `mkdocs build --strict` снова проходит без override.
5. Выполнен Orphan Cleanup (Phase B):
   - orphan-кандидаты снижены с **73** до **0**;
   - добавлены связующие индексы/ссылки для `99-archive/**`, `plans/**`,
     `reports/**`, `skills/**` и non-nav индексов `mmd-diagrams/**`.
6. Перепроверка:
   - `scripts/check_doc_links.py` — PASS;
   - `tests/architecture/test_check_doc_links_guardrails.py` — PASS;
   - `tests/architecture/test_documentation_sync.py` — PASS;
   - `mkdocs build --strict` — PASS.
7. Введён weekly KPI-контроль docs-nav:
   - новый workflow `.github/workflows/docs-kpi-weekly.yml` (schedule + manual);
   - новый отчётный скрипт `scripts/report_docs_kpi.py`;
   - KPI: target `not_in_nav <= 120` (до `2026-06-30`), hard-limit `<= 135`, orphan budget `<= 0`.
8. Расширен `check_doc_links` path-contract guardrails:
   - добавлена проверка канонического пути `REQUIREMENTS.md`;
   - добавлена проверка канонических governance-ссылок;
   - добавлены архитектурные тесты на contract-violations.
9. Выполнено снижение `not_in_nav` до целевого уровня и ниже:
   - расширен `mkdocs` internal nav (wave-1 + wave-2) на curated набор документов (`architecture extras`, `plans`, `reports`, `prompts`, `skills/local`);
   - метрика изменена `135 -> 109`.
10. Выполнена wave-3 корректировка и стабилизация:
   - добавлены curated записи для `02-architecture/**` и `skills/**`;
   - `qa_orchestrator` переведён на канонический путь `00-project/agents/qa_orchestrator.md` (nav + links);
   - `docs/site/**` исключён из KPI/nav-growth как generated-артефакт;
   - с учётом текущего workspace-состояния (удаления архивных отчётов) метрика снижена до `65`;
   - KPI статус `on_track` (target `<=120` достигнут с запасом).
11. Выполнена wave-4 корректировка:
   - дополнительно опубликованы curated подпредставления `02-architecture/**` и reference-страницы `skills/**`;
   - метрика снижена `65 -> 53` (локальная цель `<=55` достигнута);
   - orphan budget сохранён на `0`.
12. Выполнена wave-5 корректировка:
   - опубликованы оставшиеся `02-architecture/**` non-nav элементы и часть `skills/global/.system/**`;
   - метрика снижена `53 -> 45` (локальная цель `<=45` достигнута);
   - orphan budget сохранён на `0`.

## 9. Re-Audit Snapshot (2026-03-03, latest)

### Verification

- `./.venv/Scripts/python.exe scripts/check_doc_links.py` — PASS
- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_docs_version_sync.py -q -p no:xdist --tb=short` — PASS
- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_check_doc_links_guardrails.py -q -p no:xdist --tb=short` — PASS
- `./.venv/Scripts/python.exe -m pytest tests/architecture/test_documentation_sync.py -q -p no:xdist --tb=short` — PASS
- `./.venv/Scripts/python.exe -m mkdocs build --strict` — PASS

### Coverage Metrics

- Total markdown docs under `docs/`: **675**
- In mkdocs nav: **630**
- Outside nav: **45**
- Orphan candidates (outside nav, zero inbound links): **0**

Outside-nav distribution:
- `99-archive`: 33
- `skills`: 12

### Drift and ADR Alignment

- ADR anchors (`ADR-010`, `ADR-014`, `ADR-017`) are present across README, RULES, REQUIREMENTS, and architecture docs.
- Legacy provider/path token scan for active docs (`docs/04-reference/providers`, `docs/03-guides`, `docs/00-project`) returned no matches.

### Residual Risks

1. **P3 — Toolchain migration risk (MkDocs 2.0 advisory)**
   - `mkdocs build --strict` passes, but Material emits advisory on MkDocs 2.0 compatibility.
2. **P2 — High non-nav volume remains intentional but large**
   - No orphan drift, yet 45 non-nav docs still require ongoing governance discipline.

## 10. Curated Cleanup (Detailed)

### 10.1 Definition and Goal

`Curated cleanup` is a controlled reduction of `not_in_nav` where we:
- publish high-value internal docs into `Internal / Extended`;
- keep archive/historical or generated bulk outside nav by policy;
- preserve zero-orphan and strict-build guarantees.

Goal is not "put everything into nav", but "maximize discoverability with minimal nav noise".

### 10.2 How Waves Were Selected

Selection criteria used in wave-1/wave-2/wave-3:
1. Repeatedly referenced by maintainers/review workflows.
2. Stable enough to be discoverable in nav.
3. Useful as entrypoints for non-nav clusters.
4. Low risk of confusing normative vs archival content.

Applied result:
- promoted architecture extras, selected plans/reports/prompts, curated local skills, and additional architecture/skill reference pages in wave-3;
- kept `99-archive/**` out of nav intentionally;
- retained generated/auxiliary docs as non-nav but linked via indexes;
- aligned `qa_orchestrator` references to canonical `00-project/agents/` path;
- excluded `docs/site/**` from KPI/nav-growth accounting as generated local artifacts.

### 10.3 Residual `outside nav` Backlog (45)

Current buckets after curated cleanup:
- `99-archive/**`: 33 (`archive`, intentional non-nav)
- `skills/**`: 12 (references/assets/system skills)

Sub-buckets worth prioritizing next:
- selected `skills/local/*/references/**` pages with recurring practical value;
- selected `skills/global/.system/**` references that should be discoverable in docs UI.

### 10.4 Proposed Next Wave (optional, P2)

If objective is further reduction below `45` (for example `<=40`):

1. Promote 3 to 5 high-use `skills/**` reference pages and keep low-value/internal-only references outside nav.
2. Re-evaluate whether all `skills/global/.system/**` pages should be represented in nav or linked only from catalog pages.
3. Keep `99-archive/**` unchanged unless policy decision explicitly reclassifies archive discoverability.

Expected effect:
- estimated `not_in_nav` improvement: `-3` to `-6`;
- orphan budget expected to remain `0` if index linkage is preserved.

### 10.5 Safety Gates for Each Wave

- `scripts/check_doc_links.py` — PASS
- `mkdocs build --strict` — PASS
- `scripts/report_docs_kpi.py --fail-on-breach` — PASS
- no baseline growth unless intentional and justified
