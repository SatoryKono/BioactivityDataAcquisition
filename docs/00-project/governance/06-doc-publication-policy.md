# Documentation Publication Policy

*Версия: 1.4 (2026-03-24)*

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
- Документ включён в nav только в ветке `Internal / Extended`.
- Назначение: инженерные планы, отчёты, служебные материалы, каталоги skills.
- Требования:
  - в заголовке указывать внутренний статус (`Internal / Extended`);
  - не использовать как источник истины для архитектурных/продуктовых контрактов.

3. `internal`
- Документ хранится в `docs/`, но не включён в nav.
- Назначение: рабочие заметки, промежуточные черновики.
- Требования:
  - в заголовке указывать, что документ внутренний;
  - не использовать как источник истины для публичных инструкций.

4. `archive`
- Исторические материалы, superseded ADR/планы/отчёты.
- Рекомендуемое размещение: `docs/99-archive/`.
- Требования:
  - явная пометка исторического контекста;
  - допускаются legacy пути/команды только как историческая справка.

5. `internal-generated` (non-nav)
- Генерируемые или вариантные материалы, которые не должны перегружать публичную навигацию.
- Размещение: `docs/` вне `mkdocs.yml` nav.
- Примеры:
  - индексные/артефактные страницы `diagrams/**/INDEX.md`;
  - вариантные описания диаграмм (`*a/*b/*d` и подобные серии).
- Требования:
  - документ должен содержать пометку о служебном статусе;
  - нормативные утверждения должны ссылаться на `published` документы.

## Правила поддержки

1. Документы класса `published` являются нормативными и должны отражать текущее состояние репозитория.
   Для текущего project guidance источником истины остаются активные docs в `docs/00-05`.
2. Документы класса `internal-published` публикуются для удобства команды, но не являются нормативным источником требований.
3. При миграции структуры (пути, команды, конфиги) сначала обновлять `published`, затем `internal-published` и `internal`.
4. Исторические упоминания legacy-путей в `published` документах должны быть явно помечены как historical context.
5. Для активных docs использовать автоматические проверки `check_doc_links` и nav/strict-build guardrails в CI.
6. Документы по runtime, который не является стандартным (например Kubernetes при ADR-010 Local-Only), публикуются только как `internal-published` в разделе `Internal / Extended` и должны содержать явный experimental/disclaimer баннер.
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
2. Затем обновлять high-signal `internal-published` indexes и summaries, если они:
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
3. Для generated surfaces прогнать owner `--check`.
4. Для runtime/governance freshness прогнать:
```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_drift.py --freshness
```

## Минимальный чек-лист перед merge

1. Прогнать базовую docs-проверку:
```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py
```
2. При изменениях вокруг nav/non-nav проверить рост вне навигации:
```bash
./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --not-in-nav-growth
```
3. Проверить, что docs-site всё ещё собирается в strict-режиме:
```bash
bash scripts/docs/build_docs_site.sh --strict
```
4. Если менялись active internal-published summaries, проверить, что они либо
   refreshed, либо снабжены явной freshness/rebaseline note.
 
## Связанный документ

- [Documentation Navigation Policy](07-doc-nav-policy.md)
