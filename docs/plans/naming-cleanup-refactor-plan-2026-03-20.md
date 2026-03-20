# Naming Cleanup Refactor Plan

Date: 2026-03-20
Status: proposed
Basis:
- `DEC-project-naming-drift-use-prioritized-shortlist-instead-of-repo-wide-rename-wave`
- `DEC-project-naming-drift-prioritize-function-and-variable-semantics-before-object-and-file-convergence`
- `DEC-project-naming-drift-accept-compatibility-file-and-facade-drift-unless-surface-expands`

## Цель

Этот план описывает осторожную, evidence-backed волну рефакторинга naming debt без глобальной rename-кампании. Главная идея проста: мы не пытаемся одномоментно унифицировать все имена в проекте. Мы сначала исправляем те naming seams, где название и фактическое поведение расходятся настолько, что это ухудшает чтение кода, ревью, сопровождение и отладку. По уже принятому decision layer приоритет отдаётся не file-level cosmetic drift, а semantic drift в функциях, методах, переменных и orchestration paths.

План сознательно не включает массовые package/file renames, потому что текущий evidence этого не оправдывает. В compatibility surfaces и helper/private layers drift признан реальным, но пока accepted-by-default, если он не расширяет public surface и не размывает ownership. Это позволяет удержать blast radius под контролем и одновременно получить измеримый выигрыш в clarity там, где он дороже всего недостаёт.

## Принципы выполнения

1. Каждый slice должен быть маленьким, локальным и проверяемым.
2. Переименование допустимо только вместе с подтверждением semantic mismatch, а не “для красоты”.
3. Если имя уже стало compatibility surface, предпочтительнее сначала ввести clearer alias или documentation seam, чем ломать imports в лоб.
4. При любом rename public API нужно отдельно решить: делаем ли compatibility alias, deprecation shim или прямую замену.
5. Каждая волна должна заканчиваться targeted tests + doc sync, если меняются public names или contract wording.

## Wave 1. Function Contract Semantics

Первая волна должна взять функции, где имя напрямую формирует неправильное ожидание у читателя. Это самый высокий приоритет, потому что здесь naming drift уже соприкасается с риском логических ошибок.

Первый подslice касается `src/bioetl/domain/schemas/validators.py`. Evidence показал, что `is_*` helpers в Pandera-валидации возвращают не scalar `bool`, а vectorized `pd.Series`. Это допустимо технически, но семантически расходится с обычным ожиданием от `is_*`. Здесь есть два безопасных пути: либо сохранить имена, но очень явно задокументировать vectorized contract и закрепить его в тестах, либо переименовать такие функции в более check-oriented vocabulary. В этой волне приоритетнее не “сразу переименовать всё”, а выбрать единое правило и применить его последовательно к наиболее видимым validators.

Второй подslice касается `src/bioetl/domain/registry/publication_data.py`, где `validate_publication_entity_type()` возвращает policy message или `None`, а не классический boolean verdict. Здесь нужно решить, хотим ли мы naming contract уровня `validate_*` трактовать как “возвращает результат валидации в широком смысле” или всё-таки сузить его до boolean/exception semantics. Практически безопасный путь: ввести более точное имя для message-returning helper, затем сохранить compatibility wrapper только если call sites широкие. Рядом нужно обновить tests, чтобы caller contract читался без догадок.

Третий подslice в этой же волне затрагивает `create_run_all_execution_plan()` и `create_pipeline_runner()`. Evidence не говорит, что имена обязательно неверны, но показывает, что они покрывают не просто construction, а смесь validation, setup и orchestration. Здесь стоит сделать мини-аудит call sites и решить, где достаточно docstring clarification, а где нужен более явный naming seam вроде `build_*_plan` или `bootstrap_*`. Эта подзадача должна идти только после фиксации validator semantics, иначе мы смешаем два разных naming rule sets.

## Wave 2. Composition Accessor Semantics

Вторая волна адресует composition-root helpers, особенно `get_*` family. Это важный слой, потому что `get_*` в глазах читателя означает cheap lookup/accessor, а evidence показал bootstrap-heavy behavior.

Основные файлы здесь:
- `src/bioetl/composition/_services.py`
- `src/bioetl/composition/_resource_management.py`
- `src/bioetl/interfaces/cli/commands/domains/run/service_access.py`
- `src/bioetl/interfaces/cli/__init__.py`

Самый сильный кандидат — `get_quarantine_store(pipeline)`, потому что параметр `pipeline` фактически не влияет на возвращаемый shared port. Это не просто naming smell, а слабый contract smell. Лучший порядок действий: сначала подтвердить все call sites и тесты, затем либо убрать misleading parameter, либо переименовать helper так, чтобы shared/global semantics читалась из названия. Для `get_*_service()` accessors стратегия должна быть мягче: если они реально выполняют bootstrap and construct, возможно, достаточно отделить internal bootstrap helper и thin public accessor, либо переименовать только самый “тяжёлый” subset, где misreadability максимальна.

Важно: эта волна легко цепляет CLI tests и compatibility imports. Поэтому здесь нужен не one-shot rename, а phased change: clear internal naming first, compatibility wrapper second, cleanup third. Если сохраняются старые public names, это надо оформить как explicit compatibility layer, а не как случайную смесь vocabulary.

## Wave 3. Variable Naming In Orchestration Hotspots

Третья волна самая дешёвая по blast radius и одна из самых полезных по readability payoff. Она не должна менять поведение, только повышать semantic density в плотных orchestration paths.

Основные target files:
- `src/bioetl/composition/_pipeline_execution.py`
- `src/bioetl/interfaces/cli/commands/domains/run_all/command.py`
- `src/bioetl/application/composite/runner_pkg/runner.py`
- `src/bioetl/domain/context.py`

Главный паттерн здесь — `ctx`, `candidate`, `handler`, generic `result`, а также boolean-sounding `vacuum_enabled` с tri-state semantics. Для `ctx` и generic temporaries правило должно быть узким: не запрещать короткие names везде, а заменить их в тех местах, где локальная переменная участвует в orchestration contract. Например, в CLI resolution path reader выигрывает от `click_context`, `registry_candidate`, `validation_context`, `check_result` гораздо больше, чем от компактности `ctx`/`candidate`/`result`.

Эта волна должна быть специально отделена от широких API renames. Здесь almost everything можно сделать безопасно и локально: поменять внутренние локальные имена, обновить tests и не трогать public imports. Это хороший “momentum slice”: после тяжёлых semantic contract changes в Wave 1 и Wave 2 он даст быстрое улучшение читаемости без риска.

## Wave 4. Tri-state Vacuum Contract

`vacuum_enabled` deserves отдельный slice, потому что это уже на границе naming и API semantics. Если значение реально `bool | None`, то имя, читающееся как plain boolean, способно создавать неверные assumptions у callers. Это надо решать осознанно, а не как обычный rename.

Здесь есть два варианта. Первый: сохранить tri-state semantics и переименовать surface так, чтобы она явно отражала optional/defaulted nature. Второй: оставить имя, но нормализовать API до strict boolean с отдельным explicit default-resolution path. Второй вариант дороже, потому что затрагивает смысл, а не только naming. Поэтому план должен начинаться с небольшого design checkpoint: посмотреть на call sites, tests и intended semantics. Только после этого открывать implementation slice.

## Wave 5. Object-family Convergence

Это вторая очередь, не первая. Сюда попадают `Creator` vs `Factory`, `Support` vs `Helper`, `RunResult` vs `PipelineRunResult`, а также `YamlConfig` vs `Config`/`SectionConfig`. Evidence подтвердил, что drift real, но его immediate cost ниже, чем у function/variable semantics. Здесь правильнее идти family-by-family, а не всем фронтом.

Лучший кандидат внутри этой волны — `RunResult` family, потому что это уже public mental model и tests/CLI actively reference it. `Creator` vs `Factory` и `Support` vs `Helper` можно брать позже, особенно если будущие refactors всё равно будут трогать provider assembly seams.

## Verification Matrix

После каждого slice:
- targeted unit tests по touched files
- architecture tests, если меняются public surfaces или import paths
- `mypy --strict` по затронутым модулям
- `tests/architecture/test_documentation_sync.py`, если обновлялись docs или public wording
- `git diff --check`

Для waves с public renames:
- explicit compatibility review
- search for stale imports in `src/`, `tests/`, `docs/`
- follow-up doc update only where naming change visible externally

## Рекомендуемый порядок

1. Function contract semantics
2. Composition accessor semantics
3. Variable naming in orchestration hotspots
4. Tri-state vacuum contract
5. Object-family convergence

Такой порядок соответствует уже принятым decisions: сначала исправляем naming drift, который влияет на reasoning and correctness expectations, потом берём navigation/public vocabulary drift, и только в самом конце трогаем accepted compatibility surfaces, если evidence усилится.
