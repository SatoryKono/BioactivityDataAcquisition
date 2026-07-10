# Кросс-синтез: project-legacy-compatibility-remediation

> Recovery note (2026-05-21): исходный filesystem entry для этого path стал unreadable
> как в WSL/Linux tooling (`stat/open/read_text -> Invalid argument`), так и в native
> Windows tooling (`type/copy/del -> The file or directory is corrupted and unreadable`).
> Поврежденный entry был выведен из canonical curated surface в скрытый quarantine
> каталог `.quarantined-03-synthesis-corrupt-20260521/`. Текущий canonical файл
> восстановлен из shard summaries, parent summary, decision ledger, risk ledger и
> execution-status артефактов того же evidence pack.

Дата синтеза: 2026-03-29
Дата восстановления файла: 2026-05-21
Статус: recovered-canonical-copy

## Общий вывод

Evidence wave подтверждает, что legacy/compatibility тема в BioETL не сводится к
одному broad cleanup bucket. По подтвержденным shard findings repo-wide картина
распадается минимум на четыре устойчивые корзины:

- `retire-now`: узкие measured-only shims и test-retained helpers;
- `retain-with-window`: bounded compatibility seams с явным migration window;
- `retain-as-contract`: curated public facades, package-root exports и sanctioned
  entrypoints;
- `uncertain / migration-bridge`: old-shape bridges и mixed surfaces, где removal
  допустим только после adoption proof и явного exit criterion.

Главный parent-level вывод: first-wave remediation должна идти не от keywords
`legacy|compat|fallback|alias`, а от evidence-backed bucket classification плюс
tests/docs/governance migration gates.

## Межшардовые паттерны

### 1. Curated public facades нельзя смешивать с cleanup debt

Во всех крупных shard families повторяется один и тот же structural split:
package-root facades, top-level wrappers и sanctioned bootstrap surfaces выглядят
тонкими, но governance/tests/docs трактуют их как активные compatibility contracts,
а не как disposable glue.

Поддерживающие evidence:
- `EV-cli-top-level-command-wrappers-are-curated-retained-entrypoints`
- `EV-cli-package-root-declares-public-commands-surface-as-compatibility-layer`
- `EV-composition-entrypoints-is-curated-retained-public-facade`
- `EV-domain-filtering-package-root-is-retained-backcompat-facade`
- `EV-domain-exceptions-package-root-remains-cross-layer-compat-surface`
- `EV-infrastructure-config-package-root-is-curated-retained-config-facade`
- `EV-infrastructure-storage-package-root-and-delta-alias-are-test-facing-compat-surface`

Вывод:
- Первая removal wave не должна начинаться с top-level wrappers и package-root
  facades.
- Для этих surfaces нужен отдельный contract review, а не обычный cleanup pass.

### 2. Реальные first-wave removal candidates уже узкие и измеримые

Почти каждый shard дал небольшой класс seams, где compatibility value уже ниже,
чем maintenance cost: measured-only composition shims, helper-level CLI support
shims, legacy validation constructors и bounded validator aliases.

Поддерживающие evidence:
- `EV-composition-deprecated-pipeline-config-and-services-shims-are-measured-only`
- `EV-cli-support-shims-are-freeze-guarded-test-facing-seams`
- `EV-domain-validation-compat-constructors-are-test-retained-legacy-helpers`
- `EV-infrastructure-noop-validator-aliases-are-bounded-retain-with-window-seam`

Вывод:
- First-wave cleanup должен быть narrow и family-owned.
- Каждый such slice обязан включать import inventory и migration of tests.

### 3. Migration bridges требуют owner и exit criteria, а не мгновенного удаления

Config/infrastructure/application shards показывают, что часть старых shapes
все еще поддерживается намеренно: не как permanent contract, но и не как dead
code. Это bridge layer, где premature deletion опаснее задержки cleanup.

Поддерживающие evidence:
- `EV-config-filter-batch-size-is-an-explicit-transitional-alias`
- `EV-config-runtime-normalizers-still-bridge-selected-old-shapes`
- `EV-infrastructure-dq-contract-loader-keeps-legacy-dq-files-as-migration-bridge`
- `EV-infrastructure-source-normalizer-remains-active-legacy-shape-bridge`
- `EV-application-shutdown-request-wait-remain-backcompat-test-facing-seam`

Вывод:
- Bridge seams должны жить в explicit ledger с owner/review/exit criteria.
- Удаление bridge-кода без adoption proof противоречит parent synthesis.

### 4. `fallback` не равен legacy debt

Infrastructure shard зафиксировал важную границу: часть fallback helpers
существует ради текущей runtime resilience, а не ради historical compatibility.
Название модуля само по себе не классифицирует его как removal candidate.

Поддерживающие evidence:
- `EV-infrastructure-adapter-fallback-helpers-are-active-resilience-behavior-not-legacy-cleanup-target`
- `EV-infrastructure-retired-source-pagination-aliases-already-moved-to-rejection-guard`

Вывод:
- Active fallback behavior исключается из legacy-removal backlog, пока нет
  явного доказательства purely historical-only nature.

### 5. Tests, docs и governance образуют отдельный compatibility gate

Tests/docs/governance shard показал, что многие code-level seams удерживаются не
runtime callers, а contract tests, curated inventories, review history и policy
rules. Это не secondary paperwork, а отдельная boundary layer.

Поддерживающие evidence:
- `EV-test-ownership-inventory-makes-facade-tests-part-of-compat-contract`
- `EV-governance-retained-entrypoints-are-review-driven-not-auto-delete`
- `EV-history-current-cycle-forbids-deprecation-of-retained-adapter-entrypoints`
- `EV-rules-canonical-pk-policy-makes-legacy-aliases-time-bound-migration-only`
- `EV-naming-registry-forbids-domain-legacy-aliases-without-explicit-window`

Вывод:
- Любой retirement PR должен включать tests/docs/governance delta.
- Отсутствие docs/inventory migration считается blocker, а не follow-up task.

## Parent Decision Model

Parent synthesis прямо поддерживает следующий decision frame:

1. `DEC-legacy-use-four-bucket-classification-instead-of-broad-purge`
2. `DEC-legacy-keep-curated-public-facades-and-package-roots-as-supported-contracts`
3. `DEC-legacy-prioritize-measured-only-and-test-retained-shims-for-wave-one-removal`
4. `DEC-legacy-keep-migration-bridges-until-adoption-proof-and-explicit-exit-criteria`
5. `DEC-legacy-exclude-active-resilience-fallbacks-from-removal-backlog`
6. `DEC-legacy-require-tests-docs-and-governance-migration-before-removal`

Смысл этой модели:
- не трактовать весь legacy surface как homogeneous debt;
- не деприватизировать curated public facades без отдельного contract decision;
- не задерживать cleanup measured-only seams дольше необходимого;
- не удалять migration bridges и operational fallbacks по keyword logic alone.

## Карта Backlog по корзинам

### `retain-as-contract`

- top-level CLI wrappers;
- `composition.entrypoints`;
- provider/bootstrap package roots и sanctioned loaders;
- `bioetl.domain.filtering`, `bioetl.domain.exceptions`;
- `bioetl.infrastructure.config` и test-facing storage facades.

### `retain-with-window`

- helper-level CLI support shims;
- narrow old API methods;
- bounded validator aliases;
- selected aliases, для которых уже есть explicit migration semantics.

### `retire-now / first-wave candidates`

- measured-only composition shims;
- legacy validation constructors;
- helper shims, удерживаемые только tests/patch paths;
- short-window aliases после import/test migration.

### `uncertain / migration-bridge`

- `filter_batch_size`;
- runtime normalizers;
- selected old-shape config bridges;
- `DQContractConfigLoader`-style bridge surfaces;
- source normalization bridges;
- narrow backcompat application APIs без полного adoption proof.

## Противоречия и развилки

- Одни и те же families часто содержат сразу несколько bucket types; broad
  family-level deletion policy здесь будет ошибочной.
- Внешне thin wrappers оказываются contractual, а визуально менее заметные
  helper seams — реальными cleanup candidates.
- Config/domain/application compatibility удерживается не только code paths, но
  и schema/docs/operator expectations.

## Волны исполнения

### Wave 0

- import inventory и gating для first-wave removal candidates собраны.

### Wave 1

- composition shims;
- legacy validation constructors;
- validator aliases;
- CLI alias-only cluster.

Wave 1 интерпретируется как already-executed narrow cleanup around the safest
measured-only/test-retained seams.

### Wave 2

- inventory-first и narrowed-cleanup wave для `retain-with-window` и
  `migration-bridge` seams;
- shortlist и bridge ledger уже зафиксированы в `06-status/`;
- DQ contract legacy fallback narrowed without removing the public loader surface.

### Wave 3

- `filter_batch_size` и runtime normalizer families narrowed, но не переведены в
  broad removal scope;
- selected bridges остаются под governance watch, а не в auto-delete backlog.

## Открытые риски

Parent synthesis поддерживает уже оформленные risks:

- `RISK-legacy-classification-complexity-delays-obvious-cleanups`
- `RISK-legacy-public-facades-harden-into-permanent-overhead`
- `RISK-legacy-wave-one-breaks-test-patch-paths-before-migration`
- `RISK-legacy-wave-one-misses-hidden-first-party-callers`
- `RISK-legacy-migration-bridges-never-get-retired`
- `RISK-legacy-program-overlooks-real-fallback-debt`
- `RISK-legacy-governance-gates-slow-down-cleanup-program`

Их общая интерпретация:
- без bucket classification cleanup становится unsafe;
- без review dates и exit criteria migration bridges станут permanent residue;
- без synchronous tests/docs/inventory migration даже narrow deletions будут
  ломать supported seams.

## Финальная интерпретация

`project-legacy-compatibility-remediation` подтверждает `decision-driven,
bucketed retirement program`, а не repo-wide purge.

Практический смысл для следующих изменений:

1. Начинать cleanup только с узких measured-only/test-retained seams.
2. Сохранять curated public facades до отдельного contract review.
3. Для bridge surfaces требовать owner, review date и exit criterion.
4. Исключать active resilience fallbacks из cleanup backlog по умолчанию.
5. Рассматривать tests/docs/governance migration как mandatory part of every
   retirement slice.
