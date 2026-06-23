______________________________________________________________________

Version: 1.7.3
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-12'

______________________________________________________________________

# Documentation Publication Policy

## Цель

Снизить дрейф документации и сделать статус каждой страницы явным: опубликованная, внутренняя или архивная.

D-01 задаёт содержательные требования к документационным пакетам и cross-link
consistency, а этот документ задаёт правила публикации, nav-видимости и
классификации. Эти документы MUST использоваться совместно, а не как
взаимозаменяемые политики.

## Классы документации

1. `published`

- Документ входит в `mkdocs.yml` nav.
- Требования:
  - актуальные пути/команды;
  - отсутствие ссылок на удалённые legacy-директории конфигов;
  - регулярная проверка в CI.
- Для supported runtime / inspection surface этот класс охватывает не только
  user guides, но и published contracts, CLI reference и обязательные runbooks.

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
  - published и `internal-published` страницы MUST NOT оформлять ссылки на такие
    материалы как built-site navigation links; допустимы только repository-path
    references, inline code paths или curated summaries.
  - `docs/99-archive/README.md` MAY использоваться как стабильный
    repository-path entrypoint для archive discovery, но это не делает архивное
    дерево текущей MkDocs navigation surface.

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

7. `code-navigation-only`

- Документ или семейство документов существует для чтения структуры кода, а не
  как operator/reference truth surface.
- Типичный пример: package maps в `src/**/README.md`.
- Требования:
  - MAY ссылаться на live package structure и import seams;
  - MUST NOT подменять published docs как canonical source of contracts,
    operator workflows или runtime policy;
  - SHOULD направлять читателя в `docs/04-reference/**`,
    `docs/02-architecture/**` или другой published entrypoint.

## Path-Classified Bulk Surfaces

Для bulk / generated семейств допускается классификация по path-prefix и
курируемому entrypoint, а не через frontmatter в каждом файле.

Это применяется только если одновременно выполнены все условия:

1. семейство уже ratified в governance policy;
1. у семейства есть discoverable entrypoint (`README`, `INDEX`, `SUMMARY` или
   каталог в nav / repository path);
1. документы не используются как первичный источник архитектурной,
   продуктовой или операционной политики;
1. bulk family целиком рассматривается как `repo-only` или
   `internal-generated`.

Текущие ratified path-classified family buckets:

- `docs/00-project/ai/agents/agents/**` -> `internal-generated`
- `docs/00-project/ai/prompts/collected/**` -> `repo-only` / `internal-generated`
- `docs/00-project/ai/skills/_references/**` -> `internal-generated`
- unpublished bulk skill bodies / references under
  `docs/00-project/ai/skills/local/**` -> `internal-generated`
- `reports/**` and `reports/evidence/**` -> `repo-only`
- `src/**/README.md` package maps -> `code-navigation-only`

AI runtime ownership note:

- `.codex/**` remains the canonical runtime-owned tree for local AI workflow.
- `docs/00-project/ai/**` is the published/internal mirror surface for AI
  guidance and discoverability.
- Runtime behavior MUST be authored in the runtime-owned trees first; mirrors in
  `docs/00-project/ai/**` SHOULD follow them and MUST NOT silently override
  runtime source-of-truth.

Для этих семейств отсутствие per-file frontmatter не считается policy violation,
если entrypoint и surrounding policy остаются актуальными.

## Правила поддержки

1. Документы класса `published` являются нормативными и должны отражать текущее состояние репозитория.
   Для текущего project guidance источником истины остаются активные docs в `docs/00-05`.
1. Документы класса `internal-published` публикуются для удобства команды, но не являются нормативным источником требований.
1. Документы класса `repo-only` остаются discoverable через repository-path ссылки и curated summaries, но не должны маскироваться под nav-published guidance.
1. `code-navigation-only` surfaces помогают читать live source tree, но не
   должны рассматриваться как самостоятельный нормативный слой поверх
   `published` docs.
1. Path-classified bulk families MAY inherit class from governance policy and
   entrypoint without per-file frontmatter, если они не претендуют на
   normative status.
1. Published specialist families such as `docs/05-engineering/**`,
   `docs/04-reference/providers/**`, `docs/04-reference/pipelines/**`, and
   `docs/04-reference/contracts/**` MAY be nested under a broader `Reference`
   navigation branch when that better matches the current information
   architecture.
1. При миграции структуры (пути, команды, конфиги) сначала обновлять `published`, затем `internal-published`, затем `repo-only` и `internal`.
1. Исторические упоминания legacy-путей в `published` документах должны быть явно помечены как historical context.
1. Для активных docs использовать автоматические проверки
   `python -m scripts.docs check-links` и nav/strict-build guardrails в CI.
1. Документы по runtime, который не является стандартным или default-supported, могут быть `published`, `internal-published` или `repo-only` только при явной пометке experimental/disclaimer и без конфликта с ADR-010 Local-Only posture.
1. `internal-generated` документы не используются как первичный источник архитектурной или операционной политики.
1. Материалы в `docs/99-archive/` сохраняются для traceability, но не являются нормативными для текущего поведения проекта.

## Repo-Only Reports Boundary

Для report-like материалов MUST применяться следующая развилка:

1. `docs/reports/**`

- curated repo-only surface;
- допустимы evidence indexes, bounded summaries, synthesis, decisions, risks,
  curated internal analysis;
- материал здесь SHOULD already be down-selected and navigable;
- `docs/reports/**` MUST NOT становиться зеркалом raw run-by-run working output.

2. `reports/**`

- working-output surface;
- допустимы generated outputs, iteration-heavy audits, temporary analysis
  snapshots, model-specific run artifacts, reusable machine-readable bundles;
- содержимое здесь MAY быть сырым, промежуточным, tool-specific, or transient;
- `reports/**` MUST NOT использоваться как published or operator-default
  guidance surface.

3. `docs/00-05/**`

- canonical published or internal-published guidance;
- если материал содержит instructions, operator workflow, contract semantics,
  or contributor-default guidance, он MUST жить здесь, а не в
  `docs/reports/**` или `reports/**`.

4. `docs/99-archive/**`

- archive-only lane for historical, superseded, or traceability-preserved
  materials;
- если report or note больше не является active curated surface, но его нужно
  сохранить для истории, он SHOULD переехать сюда, а не зависать между
  `docs/reports/**` и `reports/**`.

Practical routing rule:

- normative guidance -> `docs/00-05/**`
- curated repo-only evidence / bounded summary -> `docs/reports/**`
- generated or working output -> `reports/**`
- superseded but retained context -> `docs/99-archive/**`

## Published Control-Plane & Feature-Rollout Pack

Для supported control-plane / traceability surface документы MUST трактоваться
как active published documentation, а не как internal notes или archive.

Обязательный published pack для такой surface включает:

1. contract-spec в `docs/04-reference/contracts/`;
1. CLI reference entry в `docs/04-reference/cli.md`;
1. operations runbook в `docs/05-operations/runbooks/`;
1. связанные ADR, которые фиксируют runtime semantics и rollout posture.

Текущий ratified пример такого пакета:

- published contract:
  [`docs/04-reference/contracts/run-manifest-ledger.md`](../../04-reference/contracts/run-manifest-ledger.md)
- supported inspection runbook:
  [`docs/05-operations/runbooks/run-manifest-inspection.md`](../../05-operations/runbooks/run-manifest-inspection.md)
- CLI reference:
  [`docs/04-reference/cli.md`](../../04-reference/cli.md)
- reference landing page:
  [`docs/04-reference/index.md`](../../04-reference/index.md)
- governing ADRs:
  [`ADR-044`](../../02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md),
  [`ADR-045`](../../02-architecture/decisions/ADR-045-dq-contract-system.md)

Нормативные правила для таких пакетов:

- control-plane contract MUST оставаться `published`, если surface
  поддерживается оператором или CLI;
- supported inspection surface MUST иметь published runbook и CLI routing;
- feature-rollout pack MUST обновляться согласованно при изменении storage
  layout, rollout flags, inspection commands или traceability invariants;
- retired surface MUST сначала получить explicit deprecation / unsupported note в
  published docs, а не тихо переводиться в `internal` или `archive`.
- archive-only published material SHOULD route through an explicit archive index
  (for example `docs/05-operations/archive-index.md`) instead of being surfaced
  as if it were current operator guidance.

## Publication Metadata Note

Published site metadata canonical source находится в `mkdocs.yml`:

- `site_name = BioETL Project`
- `site_url = https://SatoryKono.github.io/BioactivityDataAcquisition/`
- `repo_name = SatoryKono/BioactivityDataAcquisition`
- `repo_url = https://github.com/SatoryKono/BioactivityDataAcquisition`

Verified 2026-04-01: drift между publication policy и текущим MkDocs metadata не
обнаружен. Разница между site title и repository slug считается intentional,
но при rename / move MUST обновляться в одном changeset вместе с published
governance и navigator pages.

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
1. Затем обновлять high-signal `internal-published` indexes/summaries и
   `repo-only` entrypoints, если они:
   - используются в planning/review;
   - ссылаются на уже закрытые волны как на текущие;
   - содержат current-tense рекомендации, переставшие быть актуальными.
1. Исторические raw/evidence/archive материалы не переписывать без необходимости;
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
1. Проверить, что active indexes (`docs/plans`, `docs/reports`, evidence indexes)
   не ведут к stale interpretation без rebaseline note.
1. Для path-classified bulk families проверить, что entrypoint / catalog /
   `SUMMARY.md` остаются достаточными для discoverability и не ведут к stale
   interpretation.
1. Для generated surfaces прогнать owner `--check`.
1. Для runtime/governance freshness прогнать:

```bash
uv run python -m scripts.docs check-drift --freshness
./.venv/Scripts/python.exe -m scripts.docs check-drift --freshness
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
uv run python -m scripts.docs build-site --strict
```

4. Если менялись active internal-published или repo-only summaries/indexes,
   проверить, что они либо refreshed, либо снабжены явной freshness/rebaseline
   note.

## Связанный документ

- [D-01: Governance & Style Guide документации BioETL](01-documentation-governance-style-guide.md)
- [Documentation Navigation Policy](07-doc-nav-policy.md)
- [Template Index](../../04-reference/templates/index.md)
