


  
  7. RF-07. Поздняя и осторожная миграция ProviderRegistry

  - Проблема с ProviderRegistry реальна, но в прошлом плане я переоценил её срочность. Сейчас в проекте уже есть instance-scoped модель через create_provider_registry() и одновременно широкий compatibility layer
    через class-level dispatch. Это значит, что задача не должна идти рано и “в лоб”. Её место — после RF-02 и RF-04, когда regression net уже усилен, а часть composition hubs уже стала понятнее. Только тогда можно
    безопасно сокращать hidden dependency seam без риска разрушить bootstrap/test ecosystem.
  - Первый шаг этой задачи должен быть инвентаризацией. Нужно получить полный список ProviderRegistry.ensure_loaded/is_registered/create_adapter/build_data_source_creator call sites в src и tests, разделить их на
    production paths, compatibility paths и test conveniences. Сейчас class-level API используется широко, и это нельзя игнорировать. Пока такой карты нет, любые разговоры о “удалить singleton seam” — слишком
    абстрактны.
  - Второй шаг — ввести explicit registry path там, где это даёт реальный выигрыш и минимальный blast radius. Например, начать с одного factory chain, где registry already conceptually local. При этом class-level
    methods должны остаться рабочим compatibility layer на переходный период. Цель не “сломать старое”, а постепенно сделать новое предпочтительным и лучше тестируемым.
  - Третий шаг — поставить ratchet. Когда первый explicit path заработает, нужен тест или search-based architectural guard, который не позволит новым production call sites без нужды добавлять ещё больше class-level
    registry access. Это важнее полного удаления legacy path на ранней стадии.
  - DoD для RF-07: есть карта текущих registry consumers; хотя бы один production path использует explicit registry instance; compatibility layer сохранён, но не растёт; tests подтверждают отсутствие скрытых
    регрессий в adapter creation/bootstrap lifecycle. Полное удаление default registry в этой задаче не требуется; главное — начать контролируемое уменьшение зависимости от него.

  8. RF-08. Уточнить naming policy и exception model, не устраивая массовых renames

  - Эта задача исправляет второй крупный перекос старого плана. Naming drift в проекте есть, но он не везде означает необходимость переименования. В частности, pubchem_compound и PubChemCompound* нельзя просто
    объявить “ошибкой”, потому что репозиторий уже фиксирует это как осознанное исключение для CLI/pipeline/API surface. Исправленная задача должна разделить два случая: где naming действительно плавает без
    политики, и где naming intentionally stabilized by exception registry.
  - Первая часть работы — ревизия configs/naming_exceptions.yaml. Нужно убедиться, что exception registry полон, актуален и соответствует реальному public surface. Если pubchem_compound — допустимая совместимость,
    это должно быть явно проверяемой частью naming governance, а не “негласным знанием”. Аналогично для uniprot_protein и других зафиксированных исключений.
  - Вторая часть — выровнять документацию вокруг различия “canonical domain name” и “stable external pipeline identifier”. Именно здесь прошлый план смешал два уровня. Доменная сущность PubchemMolecule и pipeline
    id pubchem_compound могут сосуществовать, если это явно объяснено и проверяется. Значит, задача не в rename, а в устранении двусмысленности. Хорошие кандидаты для обновления — glossary, naming policy docs и,
    возможно, targeted comments/docstrings в затронутых pipeline/contracts modules.
  - Риск задачи — снова скатиться в rename-churn без реальной пользы. Чтобы этого избежать, любые renames в этой волне должны происходить только там, где нет policy-backed exception и где drift действительно мешает
    поиску, ревью или automation. Второй риск — размножить exceptions без ясной причины. Поэтому каждый exception должен быть обоснован и проверяем.
  - DoD для RF-08: naming policy явно различает canonical domain names и intentional public IDs; exception registry синхронизирован с кодом и тестами; accidental naming drift устранён, а intentional exceptions
    формализованы. Массовых renames pubchem_compound в этой задаче быть не должно.

  9. RF-09. Разгрузить и типизировать resilience/observability logic без изменения поведения

  - Эта задача остаётся почти такой же, как в старом плане, потому что она опирается на реальный risk hotspot, а не на спорную интерпретацию политики. src/bioetl/infrastructure/adapters/http/client_retry_mixin.py
    действительно критичен, типово ослаблен и cognitively dense. Но исправленный план должен быть более строгим по последовательности: сначала фиксация поведения, потом только рефакторинг. Любая попытка “сразу
    улучшить дизайн” здесь рискованна.
  - Первый подэтап — characterization tests. Нужно зафиксировать backoff, retry classification, honoring Retry-After, circuit-breaker interaction, metrics emission и error-path behavior. Эти tests должны быть не на
    внутренние helper names, а на observable operational semantics. Без этого вся задача будет строиться на предположении, что мы и так понимаем поведение, а это как раз опасно для infrastructure cross-cutting
    code.
  - Второй подэтап — выделение узких collaborators. Не обязательно сразу разбивать всё на много классов; достаточно сначала отделить policy decision, metrics/tracing sink и request/retry context shape. Уже это
    уменьшит Any-пространство и облегчит targeted testing. Только после этого имеет смысл снижать mypy suppressions и усиливать типизацию интерфейсов.
  - Третий подэтап — повторная верификация на representative adapter paths. Поскольку mixin используется широко, нужно прогонять не только локальные tests, но и хоть небольшой набор реальных adapter-level
    сценариев. Это защитит от тихих regressions в operational behavior.
  - Риск здесь — либо сломать сетевую семантику, либо утонуть в типах без архитектурного выигрыша. Поэтому критерий успеха должен быть практическим: легче тестировать, легче читать, меньше опасных Any, при этом
    поведение не меняется.
  - DoD для RF-09: ключевое retry/resilience поведение зафиксировано tests; critical collaborators typed лучше; модуль становится проще для локального reasoning; representative adapter checks остаются зелёными. Это
    хороший завершающий этап, когда уже стабилизированы governance, tests и composition seams.

