RF-001. Разрезать composition-hotspots на меньшие assembly seams

  - Замысел. Главная проблема проекта сейчас не в нарушении слоёв, а в том, что слой composition стал слишком “умным” и слишком объёмным. Это видно по src/bioetl/composition/factories/services/pipeline_builder.py,
    src/bioetl/composition/bootstrap/runtime/composite.py, src/bioetl/composition/bootstrap/runtime/runner_factory_builder_service.py и src/bioetl/composition/bootstrap/runtime/
    composite_support_services_factory.py. Формально это допустимо, потому что wiring и должен жить в composition, но practically стоимость чтения, локализации бага и безопасного изменения уже слишком высока. Идея
    RF-001 не в том, чтобы “разнести всё по новым папкам”, а в том, чтобы в уже существующем слое composition ввести более явные bundles и под-узлы сборки: отдельно registry/bootstrap, отдельно observability
    bundle, отдельно composite-support bundle, отдельно pipeline-runner bundle.
  - Что именно меняем. В src/bioetl/composition/factories/services/pipeline_builder.py и src/bioetl/composition/bootstrap/runtime/runner_factory_builder_service.py нужно перестать собирать “всё и сразу” через
    длинные последовательности вспомогательных вызовов и перейти к typed bundle objects вроде RegistryAssemblyBundle, ObservabilityAssemblyBundle, StorageAssemblyBundle, CompositeRuntimeBundle. В src/bioetl/
    composition/bootstrap/runtime/composite.py и src/bioetl/composition/bootstrap/runtime/composite_support_services_factory.py стоит отделить подготовку composite-specific collaborators от общего bootstrap path,
    чтобы обычный pipeline path и composite path читались как разные сценарии, а не как одна ветвистая функция. На уровне модулей это обычно означает: меньше “orchestration by helper chain”, больше явных dataclass-
    bundles и маленьких фабрик с узким контрактом.
  - Риски. Это high-risk задача, потому что composition-touchpoints много, и даже “чистый” рефакторинг может случайно изменить порядок сборки зависимостей, инициализацию observability, регистрацию трансформеров или
    lazy-loading provider registry. Второй риск в том, что можно заменить одну сложность другой: вместо длинной функции получить десять мелких модулей с неочевидным порядком вызова. Третий риск связан с тестами:
    часть текущих сценариев, возможно, покрыта только smoke-level проверками, а не точечными unit tests на assembly behavior.
  - Как снижать риски. Делать рефакторинг по bundle-family, а не сразу по всему composition. Сначала выделить один очевидный seam, например observability assembly, и зафиксировать его контракт через targeted tests
    в tests/unit/composition/. Затем повторить тот же паттерн для composite support и только потом для runner assembly. Важно на каждом шаге сохранять старые public entrypoints и менять только внутреннюю сборку.
    Если при выделении bundle обнаружится скрытая циклическая зависимость, её не надо маскировать ещё одним local import; её нужно вытащить в отдельный контрактный объект или explicit provider callable. Хорошая
    промежуточная метрика здесь: уменьшение количества модулей, которые “знают обо всём” сразу.
  - Definition of Done. В composition/bootstrap/runtime и composition/factories/services больше нет 1-2 центров, которые одновременно знают про registry, storage, observability, composite support и runner
    lifecycle. Каждый bundle имеет явный тип и понятный набор полей, а public entrypoints по-прежнему работают через те же внешние API. Архитектурные тесты зелёные, smoke composition tests зелёные, а новые unit
    tests покрывают хотя бы три семейства сборки: registry/bootstrap, observability и composite support. Ожидаемый эффект на scorecard: рост категорий module boundaries, DI/composition quality и частично
    complexity/hotspots.

  RF-002. Ужесточить default-registry и loader state

  - Замысел. Сейчас в проекте нет грубого service locator anti-pattern, но есть контролируемый drift в сторону ambient defaults и глобального состояния. Это видно по src/bioetl/composition/factories/pipeline/
    registry.py, src/bioetl/composition/registry_default.py, src/bioetl/composition/providers/_loading.py, src/bioetl/composition/providers/_default_registry.py и src/bioetl/composition/factories/datasource/
    http_client.py. Пока это не ломает архитектуру, но ухудшает тестируемость, предсказуемость bootstrap path и ясность ownership: не всегда очевидно, кто именно создал registry, кто гарантирует его заполненность и
    в какой момент произошло “default initialization”.
  - Что именно меняем. Суть RF-002 в том, чтобы перевести “глобально доступное, лениво инициализируемое состояние” в “локальное, явно протянутое состояние с ограниченной зоной видимости”. В src/bioetl/composition/
    registry_default.py и src/bioetl/composition/providers/_default_registry.py нужно отделить compatibility helper от основного runtime path: default-registry может остаться как thin compat seam, но основной код
    должен работать с явно переданным экземпляром. В src/bioetl/composition/providers/_loading.py стоит заменить module-level flags на registry-local markers или bootstrap tokens, чтобы состояние “регистрация уже
    выполнена” жило рядом с конкретным registry instance, а не “в воздухе”. В src/bioetl/composition/factories/datasource/http_client.py важно проверить, нет ли похожих скрытых singletons и implicit cache
    assumptions.
  - Риски. Это high-risk рефакторинг, потому что он затрагивает базовые bootstrap-пути. Есть риск получить двойную регистрацию провайдеров, ленивую недозагрузку registry, проблемы в CLI path или несогласованность
    между “старым compat entrypoint” и “новым explicit entrypoint”. Есть и организационный риск: если сделать всё слишком строго, не оставив совместимого adapter-layer, проект на короткое время может потерять
    удобство локального запуска.
  - Как снижать риски. Правильная стратегия здесь не “удалить все globals за один PR”, а ввести explicit path и затем переключить на него основные callers. Сначала нужно добавить новый API с обязательным registry
    parameter и покрыть его unit/integration tests. Потом перевести main runtime path на новый API. И только после этого сузить default-registry usage до специальных compat-seams. Полезно добавить архитектурный
    guard, который запрещает прямое использование default-registry вне конкретного allowlist. Для loader state стоит сделать отдельные tests на idempotency registration: “двойной вызов безопасен”, “отдельные
    registry instances не делят hidden state”, “compat path и explicit path дают одинаковый набор registered providers”.
  - Definition of Done. Основной runtime bootstrap не зависит от module-level default flags. Default registry остаётся максимум как thin compatibility seam, явно помеченный как deprecated-or-compat-only. Тесты
    доказывают, что отдельные registry instances изолированы, повторная регистрация предсказуема, а CLI и composition entrypoints работают без неявной глобальной инициализации. На уровне scorecard это должно
    поднять DI/composition quality, module boundaries и частично Hexagonal / DDD, потому что composition станет не просто “местом, где всё собирается”, а местом, где ownership зависимостей действительно прозрачен.

  RF-003. Сделать один canonical resolver для config-root и version resolution

  - Замысел. Сейчас конфигурационная механика в проекте в целом отделена неплохо, но пути до configs/ и версия runtime/package вычисляются в нескольких местах. Это создаёт тихий класс проблем: логика выбора root
    path и fallback version живёт не в одном центре, а размазана по src/bioetl/composition/bootstrap/runtime/pipeline.py, src/bioetl/infrastructure/config/pipeline_config_api.py, src/bioetl/infrastructure/config/
    _base.py, src/bioetl/infrastructure/config/contract_policy_loader.py и src/bioetl/composition/services/versioning.py. Пока всё это работает, но каждый новый caller увеличивает риск несовместимого fallback
    behavior.
  - Что именно меняем. В рамках RF-003 нужен один canonical ConfigRootResolver и один понятный VersionResolver. Первый должен отвечать на вопрос: “где находится корень runtime-конфигов в данном execution context?”
    Второй: “какая версия считается канонической для логирования, metadata и reporting?” Эти resolver’ы не обязаны быть сложными, но они должны стать единственным местом, где разрешены Path("configs"), env-based
    overrides и fallback semantics. После этого src/bioetl/infrastructure/config/pipeline_config_api.py перестаёт самостоятельно принимать решение о roots, src/bioetl/composition/bootstrap/runtime/pipeline.py
    перестаёт дублировать эти assumptions, а src/bioetl/composition/services/versioning.py становится единственным провайдером version metadata для runtime.
  - Риски. Главный риск здесь не архитектурный, а операционный: можно сломать локальные сценарии, CI, тестовые фикстуры и документационные примеры, где неявно предполагалось, что корень configs находится рядом с
    текущим cwd. Ещё один риск связан с договорённостями о version semantics: package version, pipeline version и docs version могут иметь разные источники истины, и неаккуратное “объединение всего в один resolver”
    способно смешать разные уровни ответственности.
  - Как снижать риски. Делать рефакторинг через совместимый слой. Сначала ввести resolver’ы, которые повторяют текущую логику один в один. Затем переключить на них существующие callers без изменения поведения. И
    только после этого удалить дублирующие ветки. Для version resolver полезно явно описать приоритет источников, например: runtime override -> package metadata -> fallback constant, и закрепить это tests’ами. Для
    config-root resolver нужны как минимум сценарии: локальный запуск из корня репо, тестовый запуск из другого cwd, CLI execution, и загрузка policy/config из infrastructure layer.
  - Definition of Done. В кодовой базе больше нет scattered Path("configs") решений в runtime path. Все критические callers получают root через один resolver, а version metadata формируется через один сервис с
    понятным приоритетом fallback’ов. Документация по configuration/version semantics синхронизирована с кодом. Категории, которые должны вырасти после этого шага: config/composition/DI, docs/ADR alignment и
    частично extensibility/operability, потому что новые execution contexts будет легче поддерживать без локальных path hacks.

  RF-004. Схлопнуть CLI compatibility debt в canonical command surfaces

  - Замысел. Сейчас CLI в проекте работает, но в нём накопился типичный зрелый долг: существует и canonical command structure, и слой compatibility wrappers. Это видно по src/bioetl/interfaces/cli/commands/
    _compat.py, src/bioetl/interfaces/cli/main.py, src/bioetl/interfaces/cli/commands/domains/run/command.py и src/bioetl/interfaces/cli/commands/domains/run_all/command.py. Для пользователя это ещё терпимо, но для
    разработчика цена выше: не всегда ясно, какой модуль считается настоящим public seam, где допустимы shims, а где уже должен жить только канонический flow.
  - Что именно меняем. RF-004 не означает “сломать старые команды”. Он означает: сделать один public story. domains/*/command.py должны стать единственными discoverable canonical entrypoints, а compat wrappers
    должны превратиться в тонкие адаптеры без бизнес-логики, без доступа к registry internals и без собственного orchestration path. В src/bioetl/interfaces/cli/main.py стоит централизовать регистрацию команд и
    явно показать, что compat-команды существуют только как переходный слой. В src/bioetl/interfaces/cli/commands/_compat.py стоит оставить минимум glue-кода, а доступ к health/metrics/registry вынести за boundary
    helpers, чтобы compatibility layer не протаскивал внутрь себя пол-composition.
  - Риски. Основной риск — backwards compatibility. Даже если проект primarily internal, смена структуры CLI почти всегда бьёт по automation scripts, docs snippets и привычным путям команды. Второй риск — случайно
    затянуть в CLI ещё больше wiring-кода, если попытаться решить compat долг “ещё одним helper module”. Третий риск — ухудшение discoverability, если canonical story будет объявлена, но старые wrappers останутся
    слишком “видимыми”.
  - Как снижать риски. Вводить явную политику sunset. Старые команды можно сохранить, но они должны делать ровно две вещи: логировать deprecation warning и делегировать canonical implementation без своей логики.
    Хорошая практика здесь — отдельный architecture test, который запрещает в compat layer импортировать что-либо, кроме canonical command modules и простых adapter helpers. Ещё важно заранее поправить docs и help-
    text, чтобы интерактивные пользователи видели только canonical commands. Если существуют скрипты в CI/ops, нужно сначала мигрировать их на новые entrypoints, и только потом урезать compat surface.
  - Definition of Done. У команды проекта один ответ на вопрос “где живёт команда run?”. Это src/bioetl/interfaces/cli/commands/domains/run/command.py. Все legacy/compat entrypoints либо удалены, либо сведены к
    thin delegating wrappers с явной deprecation policy. В main.py registration path читабелен, help output ориентирует на canonical surface, а тесты подтверждают, что compat wrappers не содержат бизнес-логики и не
    тянут composition internals напрямую. Ожидаемый выигрыш — рост naming/package consistency, module boundaries и частично test/regression safety, потому что CLI станет проще стабильно покрывать.

  RF-005. Нормализовать vocabulary: publication/document и UniProt/Uniprot

  - Замысел. Это выглядит как “косметика”, но на деле vocabulary drift в архитектурно строгих проектах быстро превращается в источник багов, неверных поисков, дрейфа документации и неправильных API assumptions. У
    BioETL уже есть такие признаки: document_* и publication_* одновременно встречаются в src/bioetl/composition/factories/transformer_factory.py и src/bioetl/composition/factories/pipeline/registry_manifest.py, а
    UniProt и Uniprot сосуществуют в src/bioetl/application/pipelines/uniprot/transformer.py, src/bioetl/application/pipelines/uniprot/transformer_business_data_mixin.py и доменных сущностях. Пока это не ломает
    runtime, но делает mental model менее устойчивой.
  - Что именно меняем. Сначала нужен один canonical mapping vocabulary. Это может быть YAML-манифест, таблица в configs/naming_exceptions.yaml или отдельный internal glossary, но он должен ответить на два вопроса:
    какой внутренний термин канонический и какие внешние compatibility aliases допустимы. Для publication/document решение, скорее всего, должно быть в пользу publication, потому что именно это слово уже доминирует
    в доменной и документационной модели. Для UniProt/Uniprot нужно определить единый casing rule: внешне бренд может быть UniProt, но в Python class/module names нужен один последовательный стиль. После этого
    обновляются src/bioetl/composition/factories/pipeline/registry_manifest.py, src/bioetl/composition/factories/transformer_factory.py, uniprot transformer/entity/schema и все docs, которые ссылаются на эти имена.
  - Риски. Главный риск — затронуть stable external IDs или конфиги, которые уже используются как contract surface. Поэтому здесь нельзя просто массово rename’ить всё по rg | sed. Нужно жёстко различать внутренний
    vocabulary и внешний stable ID. Второй риск — если naming cleanup сделать частично, проект окажется в промежуточном ещё более путаном состоянии. Третий риск — сломать test fixtures, docs paths или snapshots,
    где имя зашито в строках.
  - Как снижать риски. Начинать не с rename, а с mapping table. Затем ввести compatibility aliases там, где внешний contract уже закреплён. После этого переходить family-by-family: registry/manifest, transformer
    registration, domain entities/schemas, docs/tests. Полезно добавить naming guard test, который проверяет конкретно эти пары drift’а, а не только общий “package consistency”. Ещё важно оформить явное правило:
    внешний pipeline ID может оставаться legacy-compatible, но внутренние class/function/module names должны сходиться с canonical glossary.
  - Definition of Done. Для каждой спорной пары терминов есть один canonical internal name и один documented policy for aliases. В коде больше нет ситуации, где два authoritative registry-файла используют разный
    vocabulary для одной и той же сущности. Поиск по репозиторию по ключевым словам возвращает предсказуемый набор результатов, а docs и code references используют одну и ту же лексику. На scorecard это прямо
    улучшает naming/package consistency, а косвенно помогает docs/ADR alignment и extensibility, потому что добавлять новые pipelines становится проще в понятном словаре.

  RF-006. Дедуплицировать CrossRef publication transformation hotspot

  - Замысел. CrossRef сейчас выглядит как типичный кандидат на family-scoped refactor: проблема не в том, что “провайдер плохой”, а в том, что логика сборки publication payload расползлась по нескольким местам и
    повторяет паттерны, которые уже есть в более чистом виде в других publication-oriented pipelines. Основной фокус по плану — src/bioetl/application/pipelines/crossref/transformer.py, src/bioetl/application/
    pipelines/crossref/_business_data_builder.py, src/bioetl/application/pipelines/crossref/author_extractors.py, src/bioetl/application/pipelines/crossref/extractors.py и src/bioetl/application/pipelines/crossref/
    reference_extractors.py. Отдельно я бы держал в поле зрения и src/bioetl/infrastructure/adapters/crossref/batch.py, потому что часть duplication smell приходит и оттуда.
  - Что именно меняем. Надо перестать собирать publication business data через несколько partially overlapping pathways. В идеале transformer.py остаётся тонким orchestrator, _business_data_builder.py становится
    центром business-shape assembly, а author/date/reference extraction превращаются в чистые, узкие helpers с минимальным shared mutable context. Если где-то есть title fallback, author normalization, date
    precedence, reference flattening или abstract/subject enrichment в двух вариантах, их нужно свести к одному canonical path. Если часть логики действительно специфична для CrossRef, её всё равно лучше держать
    как набор чётко названных subroutines, а не как “если-то-иначе” прямо в основном transformer flow.
  - Риски. Основной риск — data regression. Именно в publication pipelines очень легко сломать не типы, а semantics: например, начать по-другому выбирать preferred title, author order, publication year или DOI
    normalization. Второй риск — скрытое расхождение с downstream schemas, когда refactor внешне ничего не ломает, но меняет состав business fields. Третий риск — если затронуть и adapter batch logic в том же PR,
    можно смешать transformation refactor и transport refactor в одну слишком опасную волну.
  - Как снижать риски. Делать refactor только через characterization tests. Сначала зафиксировать текущий output на representative CrossRef payloads: минимальный record, полный record, edge cases по authors/
    references/dates. Потом выносить по одной family функций, не меняя конечную форму output. Если duplication partly живёт и в batch layer, лучше оформить это как отдельный follow-up subtask, а не смешивать в
    первом PR. Полезно также сравнить CrossRef path с PubMed/OpenAlex publication shapes и воспользоваться их более удачными decomposition ideas без механического copy-paste.
  - Definition of Done. В CrossRef pipeline существует один очевидный путь сборки publication business data. В transformer нет повторяющихся ветвей для authors/dates/references/title fallbacks, а helper-модули
    имеют чёткую responsibility boundary. Characterization tests доказывают, что output shape не деградировал, а если он осознанно меняется, это отражено в schemas/tests/docs. Этот RF должен заметно улучшить
    complexity/hotspots, test architecture и частично extensibility, потому что publication-family refactors перестанут требовать ручного обхода множества дублирующихся веток.

  RF-007. Заменить storage mixin/MRO complexity на explicit capabilities

  - Замысел. Storage subsystem в проекте зрелый и функционально богатый, но местами уже слишком сильно завязан на mixin/MRO-композицию. Это особенно важно не потому, что mixins “плохи”, а потому, что при
    определённом масштабе они перестают быть дешёвой абстракцией и становятся скрытым графом поведения. По плану основной фокус — src/bioetl/composition/factories/storage/adapter.py, src/bioetl/composition/
    factories/storage/merged_mixin.py, src/bioetl/composition/factories/storage/maintenance_mixin.py, src/bioetl/composition/factories/storage/health_mixin.py, src/bioetl/composition/factories/storage/
    write_mixin.py, src/bioetl/composition/factories/storage/_helpers.py. С operational side это связано и с src/bioetl/infrastructure/storage/bronze_writer.py и src/bioetl/infrastructure/storage/silver_writer.py.
  - Что именно меняем. Вместо “класс получает поведение через наследование от четырёх-пяти mixins” стоит перейти к модели “тонкий facade владеет explicit collaborators”. Например, write concerns, health concerns,
    maintenance concerns и clear/merge concerns могут стать отдельными capability objects с явными методами. Тогда src/bioetl/composition/factories/storage/factory.py остаётся thin facade, который собирает
    StorageAdapter, но сам adapter уже не зависит от хрупкого порядка MRO, а делегирует в write_capability, health_capability, maintenance_capability. Это не обязательно уменьшит число файлов, но резко упростит
    ответ на вопрос “откуда взялось это поведение?” и “что я сломаю, если поменяю один аспект записи?”
  - Риски. Это high-risk задача. Storage path — критический runtime surface, и любая ошибка может ударить по Bronze/Silver/Gold semantics, DQ hooks, health probes и cleanup behavior. Есть риск ухудшить performance,
    если capability objects будут сконструированы неудачно или породят лишние промежуточные аллокации. Есть и риск перепроектировать слишком рано: если дробить на capability classes без ясных boundaries, можно
    получить просто новую форму усложнения.
  - Как снижать риски. Начинать не с полной замены всех mixins, а с одного наиболее понятного среза, например health/maintenance. Если этот паттерн показывает выигрыш в тестируемости и читаемости, переносить его на
    write/merge path. Обязательно закрепить behavior contract для каждого capability через focused unit tests, а на уровне integration оставить проверку end-to-end storage semantics. Ещё один важный шаг — измерять
    performance до и после хотя бы на нескольких hot scenarios, потому что удобный дизайн не должен неожиданно ухудшить throughput критичных writers.
  - Definition of Done. Основные storage behaviors читаются как explicit composition, а не как “угадай MRO”. factory.py собирает адаптер из capability objects, и тесты покрывают эти capabilities отдельно. Bronze/
    Silver/Gold writers сохраняют существующее внешнее поведение, а health/maintenance/write/merge concerns можно развивать независимо. Категории, которые здесь должны вырасти сильнее всего: complexity/hotspots,
    module boundaries, test architecture, а в долгую — и extensibility, потому что новые storage behaviors будет проще добавлять без ещё одного mixin.

  RF-008. Усилить type-safety, ownership и coverage ratchets

  - Замысел. У BioETL уже очень сильные quality gates, но часть из них сейчас работает как “не ухудшай”, а не как “доводи до идеала”. Это видно по pyproject.toml, где mypy формально strict, но ослаблен рядом
    override’ов, по tests/smoke/test_smoke_composition.py, который даёт smoke-level покрытие composition hotspots, по tests/architecture/test_vcr_provider_balance.py, и по configs/quality/
    source_test_owner_inventory.yaml, который пока не покрывает все крупные CLI/pipeline hotspots. Иными словами, quality system хорош, но ещё не полностью “замыкает контур” вокруг самых дорогих модулей.
  - Что именно меняем. Во-первых, постепенно tighten’им mypy allowances: не всё сразу, а начиная с проектных модулей, где можно безопасно включить более жёсткие правила без войны с внешними stubs. Во-вторых,
    расширяем ownership inventory на большие interfaces/cli и application/pipelines модули, чтобы важные hotspots имели конкретные owner tests, а не только глобальный coverage contribution. В-третьих, coverage
    governance нужно дополнить named critical surfaces: не просто “85% по всему”, а обязательные minimal guarantees для CrossRef, OpenAlex, Semantic Scholar, UniProt idmapping и других рискованных provider flows.
    В-четвёртых, smoke-only import coverage для composition hotspots нужно постепенно заменять точечными unit suites.
  - Риски. Самый очевидный риск — CI noise. Если слишком резко закрутить type/coverage гайки, команда начнёт тратить время на массовые мелкие фиксы вместо прицельных улучшений. Второй риск — metric gaming: если
    добавить много named critical surfaces, можно получить формально зелёную матрицу, но по-прежнему дырявую по смыслу. Третий риск — ownership inventory может превратиться в бюрократию, если owner tests будут
    прописываться формально, без реального полезного покрытия.
  - Как снижать риски. Вводить ratchets ступенчато. Для mypy сначала переводить правила в informational mode на конкретные project modules, затем делать blocking only when noise is low. Для coverage surfaces
    полезно выбрать 5-7 действительно рискованных потоков, а не пытаться оцифровать всё. Для ownership inventory стоит добавлять только те модули, которые либо превышают hotspot threshold, либо часто меняются. Ещё
    важно сопровождать каждое ужесточение одним-двумя конкретными refactor’ами, чтобы метрика не стала абстрактной цифрой без архитектурного смысла.
  - Definition of Done. Количество смягчающих mypy-настроек уменьшается, а не только документируется. В ownership inventory появляются крупные CLI/pipeline hotspots. Coverage governance включает named critical
    surfaces, и по ним есть реальные tests, а не только общий процент. Smoke coverage остаётся как baseline, но composition hotspots получают более точные unit tests. Этот RF должен поднять type-safety, test
    architecture/regression safety, частично docs/ADR alignment и косвенно DI/composition quality, потому что более явные контракты и ownership делают refactors безопаснее.

  RF-009. Пересинхронизировать docs и ADR с новым устройством seams

  - Замысел. Документация в проекте сильная, но как раз поэтому drift в ней особенно опасен: люди ей доверяют. Сейчас есть точечные расхождения вокруг pipeline registration, versioning, observability naming и CLI
    compatibility story. Это видно по docs/03-guides/registry-pattern.md, docs/02-architecture/observability-layers.md, docs/03-guides/coverage-configuration.md, docs/04-reference/providers/crossref/publication.md
    и docs/04-reference/providers/uniprot/protein.md. RF-009 должен быть не косметическим постскриптумом, а финальным закреплением новых seams после RF-002..RF-008.
  - Что именно меняем. После завершения кодовых RF нужно обновить narrative docs так, чтобы они отражали реальную архитектуру, а не её прошлую версию. Для registry-story важно явно зафиксировать ownership src/
    bioetl/composition/factories/pipeline/registry_manifest.py и объяснить, какие части registration flow канонические, а какие compat-only. Для observability — синхронизировать naming и layering между кодом,
    guide’ами и ADR. Для coverage docs — описать не только общий 85%, но и новую логику critical surfaces. Для provider docs — выровнять terminology publication/document и UniProt/Uniprot. Если после RF-004 CLI
    compatibility layer будет сужен, docs тоже должны перестать рекламировать legacy-paths как нормальный способ расширения или запуска.
  - Риски. Главный риск — сделать docs “в конце, когда всё устаканится”, и в итоге получить ещё один период drift’а. Второй риск — обновить только явные guide-файлы, но забыть про ADR, governance docs и operation
    runbooks. Третий риск — слишком сильно переписать narrative, не сохранив исторический контекст, который ещё нужен для понимания старых compat seams.
  - Как снижать риски. Связать RF-009 с каждым предыдущим RF через checklist: если меняется registry seam, обновляется registry doc; если меняется observability naming, обновляется observability ADR/guide; если
    меняется coverage model, обновляется coverage guide. Полезно завести правило Last verified для активных guide-файлов и опираться на уже существующие drift-checks. Исторический контекст лучше не удалять, а
    переводить в clearly marked compatibility/deprecation sections, чтобы docs оставались и полезными, и честными.
  - Definition of Done. Активные guides и ADR больше не расходятся с кодом по registry ownership, versioning semantics, observability naming и CLI extension path. В документации есть единая canonical история для
    добавления provider/pipeline, и она совпадает с текущими code seams. Drift tests зелёные, version/freshness markers единообразны, а ссылки из governance/operations/docs больше не ведут в устаревшие registration
    points. Ожидаемый эффект — рост docs/ADR alignment, extensibility/operability, а также снижение вероятности регрессий при следующих рефакторингах, потому что архитектурные решения снова становятся читаемыми не
    только из кода, но и из документации.
