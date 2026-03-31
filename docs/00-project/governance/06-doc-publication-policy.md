---
Version: 1.6.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-31'
---

# Documentation Publication Policy

## Цель

Снизить дрейф документации и сделать статус каждой страницы явным: опубликованная, внутренняя или архивная.

## Классы документации

1. `published`
- Документ входит в `mkdocs.yml` nav.
- Требования:
  - актуальные пути/команды;
  - отсутствие ссылок на удалённые legacy-директории конфигов;
  - регулярная проверка в CI.

2. `internal-published`
- Документ включён в `mkdocs.yml` nav как non-normative internal surface
  (обычно в ветке `Internal / Extended`).
- Назначение: curated mirrors, runtime-facing guides, служебные каталоги и
  другие discoverable внутренние материалы, которые команда должна находить в
  docs-site.
- Требования:
  - в заголовке указывать внутренний опубликованный статус;
  - не использовать как источник истины для архитектурных/продуктовых контрактов.

3. `internal`
- Документ хранится в `docs/`, но не включён в nav.
- Назначение: рабочие заметки, промежуточные черновики.
- Требования:
  - в заголовке указывать, что документ внутренний;
  - не использовать как источник истины для публичных инструкций.

4. `repo-only`
- Документ хранится в репозитории как рабочий или curated extended surface, но
  намеренно исключён из MkDocs publication.
- Назначение: `docs/plans/**`, `docs/reports/**`, excluded AI entrypoints и
  другие repo-path surfaces (включая `reports/**` и `reports/evidence/**`),
  которые должны быть discoverable через ссылки из published docs, но не через nav.
- Требования:
  - в тексте или status note указывать, что это repo-only surface;
  - не использовать как источник истины для опубликованных контрактов;
  - published docs должны ссылаться на такие материалы как на repository path.

5. `archive`
- Исторические материалы, superseded ADR/планы/отчёты.
- Рекомендуемое размещение: `docs/99-archive/`.
- Требования:
  - явная пометка исторического контекста;
  - допускаются legacy пути/команды только как историческая справка.

6. `internal-generated` (non-nav)
- Генерируемые или вариантные материалы, которые не должны перегружать публичную навигацию.
- Размещение: `docs/` вне `mkdocs.yml` nav.
- Примеры:
  - индексные/артефактные страницы `diagrams/**/INDEX.md`;
  - вариантные описания диаграмм (`*a/*b/*d` и подобные серии).
- Требования:
  - документ должен содержать пометку о служебном статусе;
  - нормативные утверждения должны ссылаться на `published` документы.

## Path-Classified Bulk Surfaces

Для bulk / generated семейств допускается классификация по path-prefix и
курируемому entrypoint, а не через frontmatter в каждом файле.

Это применяется только если одновременно выполнены все условия:

1. семейство уже ratified в governance policy;
2. у семейства есть discoverable entrypoint (`README`, `INDEX`, `SUMMARY` или
   каталог в nav / repository path);
3. документы не используются как первичный источник архитектурной,
   продуктовой или операционной политики;
4. bulk family целиком рассматривается как `repo-only` или
   `internal-generated`.

Текущие ratified path-classified family buckets:

- `docs/00-project/ai/agents/agents/**` -> `internal-generated`
- `docs/00-project/ai/prompts/collected/**` -> `repo-only` / `internal-generated`
- `docs/00-project/ai/skills/_references/**` -> `internal-generated`
- unpublished bulk skill bodies / references under
  `docs/00-project/ai/skills/local/**` -> `internal-generated`
- `reports/**` and `reports/evidence/**` -> `repo-only`

Для этих семейств отсутствие per-file frontmatter не считается policy violation,
если entrypoint и surrounding policy остаются актуальными.

## Правила поддержки

1. Документы класса `published` являются нормативными и должны отражать текущее состояние репозитория.
   Для текущего project guidance источником истины остаются активные docs в `docs/00-05`.
2. Документы класса `internal-published` публикуются для удобства команды, но не являются нормативным источником требований.
3. Документы класса `repo-only` остаются discoverable через repository-path ссылки и curated summaries, но не должны маскироваться под nav-published guidance.
4. Path-classified bulk families MAY inherit class from governance policy and
   entrypoint without per-file frontmatter, если они не претендуют на
   normative status.
4. При миграции структуры (пути, команды, конфиги) сначала обновлять `published`, затем `internal-published`, затем `repo-only` и `internal`.
4. Исторические упоминания legacy-путей в `published` документах должны быть явно помечены как historical context.
5. Для активных docs использовать автоматические проверки `check_doc_links` и nav/strict-build guardrails в CI.
6. Документы по runtime, который не является стандартным или default-supported, могут быть `published`, `internal-published` или `repo-only` только при явной пометке experimental/disclaimer и без конфликта с ADR-010 Local-Only posture.
7. `internal-generated` документы не используются как первичный источник архитектурной или операционной политики.
8. Материалы в `docs/99-archive/` сохраняются для traceability, но не являются нормативными для текущего поведения проекта.

## Freshness Protocol

### 1. Trigger events

Обязательный refresh или rebaseline note требуется, если меняется хотя бы одно из:

- structural refactor, который меняет ownership, package boundaries или public seams;
- config-topology / runtime-wiring change;
- test/governance baseline, который меняет активную интерпретацию summary pages;
- generated artifact refresh (`--check` / regeneration) для активного derived surface;
- entry/index page, через которую команда реально находит текущее руководство.

### 2. Refresh order

1. Сначала обновлять `published` docs в `docs/00-05`.
2. Затем обновлять high-signal `internal-published` indexes/summaries и
   `repo-only` entrypoints, если они:
   - используются в planning/review;
   - ссылаются на уже закрытые волны как на текущие;
   - содержат current-tense рекомендации, переставшие быть актуальными.
3. Исторические raw/evidence/archive материалы не переписывать без необходимости;
   вместо этого обновлять верхний `SUMMARY.md`, `INDEX.md` или добавлять
   явный freshness / rebaseline note.

### 3. Dated reports and assessment snapshots

- Dated reports под `reports/` и `reports/plans/` сохраняют исходную дату
  создания как traceability marker.
- Если позже меняется live posture, такие документы не нужно “переиздавать задним числом”;
  нужно добавить короткий `Freshness note` / `Примечание о rebaseline`, который:
  - явно указывает дату переоценки;
  - перечисляет закрытые волны или changed assumptions;
  - отправляет читателя к текущему active backlog / current summary.

### 4. Generated artifacts

- Generated artifacts не редактируются вручную, если для них существует generator.
- Для них canonical protocol: `--check` в verify, regeneration через owner script,
  и явная пометка, что артефакт derivative rather than policy.

### 5. Minimum freshness checklist

Перед merge для changeset, затрагивающего docs/governance surfaces:

1. Проверить, не остались ли current-tense рекомендации для уже закрытых waves.
2. Проверить, что active indexes (`docs/plans`, `docs/reports`, evidence indexes)
   не ведут к stale interpretation без rebaseline note.
3. Для path-classified bulk families проверить, что entrypoint / catalog /
   `SUMMARY.md` остаются достаточными для discoverability и не ведут к stale
   interpretation.
3. Для generated surfaces прогнать owner `--check`.
4. Для runtime/governance freshness прогнать:
```bash
uv run python -m scripts.docs check-drift --freshness
./.venv/Scripts/python.exe scripts/check_doc_drift.py --freshness
```

## Минимальный чек-лист перед merge

1. Прогнать базовую docs-проверку:
```bash
uv run python -m scripts.docs check-links
```
2. При изменениях вокруг nav/non-nav проверить рост вне навигации:
```bash
uv run python -m scripts.docs check-links --not-in-nav-growth
```
3. Проверить, что docs-site всё ещё собирается в strict-режиме:
```bash
uv run bash scripts/docs/build_docs_site.sh --strict
```
4. Если менялись active internal-published или repo-only summaries/indexes,
   проверить, что они либо refreshed, либо снабжены явной freshness/rebaseline
   note.
 
## Связанный документ

- [Documentation Navigation Policy](07-doc-nav-policy.md)
