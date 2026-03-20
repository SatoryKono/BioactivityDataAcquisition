# Consolidated Master Refactor Plan: Expanded Waves

Дата: 2026-03-20
Статус: detailed companion
Основание: [consolidated-master-refactor-plan-2026-03-20.md](/mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2/docs/plans/consolidated-master-refactor-plan-2026-03-20.md)

## Назначение

Этот документ расширяет описание каждой волны из consolidated master plan.
Исходный master plan остаётся коротким управленческим документом, а этот файл
служит подробной operational-версией: зачем существует каждая волна, где её
границы, какие риски она закрывает, какие ошибки нельзя допустить, как
правильно нарезать работу на safe slices и по каким критериям считать волну
реально завершённой. Здесь принципиально нет новых стратегических приоритетов;
все приоритеты унаследованы из уже утверждённой master-схемы. Задача этого
companion-документа — сделать каждую волну достаточно подробной, чтобы её
можно было использовать как основу для последующей декомпозиции, планирования
спринтов, составления execution checklists и отдельной консолидации частных
proposal-документов.

## Wave 0. Закрытие уже начатых structural хвостов

Wave 0 должна рассматриваться как стабилизационная и нормализующая фаза,
которая не создаёт новый thematic refactor direction, а приводит текущее
состояние structural backlog в форму, пригодную для осмысленного следующего
шага. Главная причина существования этой волны проста: за последнее время в
проекте накопилось несколько одновременно активных structural инициатив,
частично уже реализованных, частично ещё находящихся в исследовании, частично
закрытых локально, но ещё не схлопнутых в один чистый статус. Без этой
предварительной нормализации любая следующая крупная волна будет неизбежно
опираться на смесь актуальных и уже устаревших предпосылок. Это особенно
опасно для проекта, где refactor backlog доказательно ведётся по нескольким
основным программам: `RF-FS-*`, composition hotspot work, provider-registry
migration, ownership evidence, hotspot evidence и technical-debt roadmap. Пока
эти ветви не сведены в один честный snapshot, почти любая новая работа рискует
либо дублировать уже выполненное, либо пропускать важные ограничения, уже
зафиксированные в соседнем документе.

Смысл Wave 0 не в том, чтобы «ещё раз всё перепланировать», а в том, чтобы
добить уже открытые хвосты до статуса, когда они либо явно закрыты, либо явно
переведены в future waves. В текущем состоянии сюда в первую очередь относятся
остатки `RF-FS-004`, вопросы around `RF-FS-006a/006b`, а также выравнивание
remaining backlog против уже реально применённых локальных wave-изменений.
Например, если config-topology work уже продвинута до состояния, где canonical
owners по части config-flow зафиксированы, но общий документ всё ещё звучит как
будто это только гипотеза, Wave 0 должна устранить такую рассинхронизацию.
Точно так же, если orphan/dead-code baseline уже частично уточнён evidence
пакетами, но backlog всё ещё описывает его как «blind delete-wave», это нужно
переписать до начала следующих исполнений. На практике это означает, что Wave
0 должна завершиться обновлённым backlog snapshot, а не просто набором новых
заметок.

Работа в этой волне должна идти через reconciliation pass, а не через широкие
кодовые изменения. Сначала собирается список всех активных structural документов
с пометкой текущего статуса: `active`, `in progress`, `partially implemented`,
`implemented locally`, `proposed`, `completed analysis`. Затем по каждому
элементу определяется одно из трёх действий: оставить как активную волну,
перенести в context/constraint, либо отметить как закрытый исторический
документ. Важно, что здесь не нужно пытаться дополнительно “улучшить код”
по пути. Любая попытка одновременно нормализовать backlog и писать новый
production refactor почти гарантированно смешает задачи и снова сделает статус
нечистым. Поэтому Wave 0 должна быть предельно дисциплинированной: update plans,
sync statuses, align evidence with code state, verify that gating assumptions
match actual repo state.

Сильная сторона этой волны — низкий runtime risk и высокий leverage на
следующие шаги. Её результатом должен стать один корректный structural
контур, в котором уже не осталось “полуживых” инициатив. Это особенно важно
потому, что следующие волны будут heavily execution-oriented: provider-registry
simplification, adapter hotspot reduction, ownership closure и conservative
cleanup. Если они стартуют на нечистом фоне, то позже придётся снова тратить
время на meta-cleanup документации и backlog tracking. То есть Wave 0 — это не
бюрократия, а защита от второго порядка дублирования усилий.

В practical terms Wave 0 должна дать несколько осязаемых артефактов. Во-первых,
должен существовать один актуальный remaining backlog, который не противоречит
локально реализованным изменениям. Во-вторых, должны быть явно обозначены
waves, которые уже нельзя считать активными proposal-документами, а нужно
трактовать только как supporting context или implementation closeout. В-третьих,
должно стать ясно, какие блоки реально остаются открытыми: config-topology
tail, provider-registry migration, composition seams, dependency/complexity
hotspots, naming/facade hygiene и candidate-level cleanup. Пока это не сделано,
любая последующая консолидация будет условной.

Отдельный риск этой волны состоит в том, что команда может недооценить
количество неявных допущений, уже встроенных в существующие документы. На
первый взгляд кажется, что достаточно просто переименовать статусы. На деле же
часто приходится переписывать формулировки целей, потому что код уже ушёл
дальше, чем baseline. Например, документ мог начинать жизнь как план
“исследовать ownership”, а после нескольких локальных wave-изменений должен
звучать как “дожать remaining compat seam after canonical ownership already
moved”. Если такие формулировки не обновить, исполнители следующих волн будут
читать документ буквально и снова тратить усилия на уже решённые вопросы.

Definition of Done для Wave 0 должна быть очень чёткой. Волна считается
завершённой, когда существует единый непротиворечивый список активных refactor
направлений, когда все implemented-local plans отделены от реально будущей
работы, когда evidence-derived backlog больше не спорит с `docs/plans`, и когда
следующая активная волна выбрана на основе согласованного состояния, а не на
основе частичной памяти о предыдущих изменениях. После этого можно переходить к
Wave 1 без риска строить execution на устаревшем structural контексте.

Ещё один важный аспект Wave 0 связан с формой итогового артефакта. Частая
ошибка в подобных стабилизационных фазах состоит в том, что команда создаёт
ещё один “сводный документ”, но не меняет существующую навигацию. В результате
появляется новый supposedly authoritative файл, а старая сетка документов
остаётся рядом и продолжает жить собственной жизнью. Поэтому закрытие Wave 0
должно включать не только содержание, но и навигационную дисциплину. Нужно
понятно обозначить, какой документ теперь считается master backlog, какие
документы являются implementation closeout, какие остаются evidence context,
а какие служат только historical trace. Это избавляет будущих исполнителей от
главного источника путаницы: когда формально все документы “правильные”, но
непонятно, какой из них читать первым и какой из них имеет приоритет при
конфликте формулировок.

В этой же волне полезно ввести единый словарь статусов и не допускать, чтобы
одна и та же идея одновременно называлась “proposal”, “wave”, “tail”,
“follow-up” и “implementation slice” без ясного перехода между этими
состояниями. Для проекта с богатой refactor-историей это не косметика, а
реальный механизм снижения будущего долга. Если статусная модель нечёткая, то
любое новое решение будет приниматься на фоне расплывчатого контекста: никто
не сможет надёжно сказать, закрываем ли мы старую инициативу, продолжаем её
или запускаем новую. Значит, внутри Wave 0 нужно нормализовать не только
список работ, но и vocabulary: что такое “активная волна”, что такое
“поддерживающий evidence”, что такое “deferred boundary”, что такое “retained
seam” и что такое “candidate for later review”.

Полезно также зафиксировать явный anti-goal этой волны. Wave 0 не должна
превращаться в обсуждение конечной “идеальной архитектуры” проекта. Это очень
соблазнительно, потому что при сводке разных backlog-документов почти
автоматически хочется снова спорить о больших принципах. Но это уже задача
последующих execution waves и targeted decision passes. Здесь цель скромнее и
практичнее: добиться того, чтобы следующий исполнитель открывал один master
контур и видел там актуальный порядок работ, актуальные ограничения и честную
картину уже сделанного. Если Wave 0 удерживает именно эту дисциплину, то она
окупает себя многократно, потому что все последующие волны перестают тратить
время на повторное выяснение базового состояния системы.

## Wave 1. ProviderRegistry и provider-assembly cluster

Wave 1 — это главный практический фокус master plan, потому что именно
provider-registry/provider-assembly cluster является единственной зоной,
которую одновременно подтверждают все ключевые линии evidence: dependency
pressure, duplication pressure и ownership ambiguity. Если переформулировать
совсем прямо, то именно здесь проект получает наибольшую отдачу от следующего
рефакторинга за единицу риска. Это не означает, что эта зона самая «плохая»
по всем метрикам. Это означает другое: одно и то же семейство модулей уже
выглядит проблемным сразу в нескольких независимых способах анализа, а значит
любое аккуратное улучшение здесь имеет мультипликативный эффект.

Главные файлы этой волны — `registration.py`, `registration_bio.py`,
`registration_biblio.py`, `_registration_contracts.py` и смежные call sites,
которые до сих пор участвуют в resolution-path для provider registration и
provider config assembly. На уровне намерения волна не должна «убивать»
совместимость. Наоборот, один из её важнейших принципов — отделить случайную
историческую сложность от действительно требуемых compatibility obligations.
Сейчас evidence показывает, что часть формы `ProviderRegistry` и default
access paths сохранена намеренно, а не по небрежности. Это значит, что задача
волны не в агрессивном упрощении, а в более честной географии: canonical path
должен быть один, а retained compatibility paths должны быть тонкими,
именованными и защищёнными тестами.

Первый шаг этой волны — symbol inventory. Нельзя безопасно упрощать
provider-assembly cluster, пока мы не зафиксировали, где именно происходят:
создание support object, разрешение registry instance, default-registry
fallback, assembly of provider configs, branching на bio/biblio families и
соответствующие compatibility seams. Это inventory должно делаться не на уровне
только файлов, а на уровне символов и responsibilities. Один файл может
содержать как честный owner-path, так и retained fallback. Если этого не
разделить явно, то refactor либо оставит дублирование на месте, либо разрушит
shared seam, на который всё ещё рассчитывают bootstrap/tests.

После inventory должен идти самый безопасный slice всей волны: canonicalization
resolution path without public removal. Это означает: сначала выбрать один
внутренний путь, через который composition действительно должна разрешать
provider registry context, и перевести на него внутренние вызовы в `src/`.
При этом нельзя одновременно удалять старые entrypoints, пока не подтверждено,
что они либо не нужны, либо являются тонкими compat re-exports. Такая
последовательность важна, потому что минимизирует blast radius. Пока canonical
path не зафиксирован и не используется изнутри, любое “удаление старого” будет
угадыванием. После этого уже можно идти к следующему slice — narrowing repeated
assembly skeleton in provider families. Здесь likely появится возможность
выделить общий helper path или contract-level adapter, который сократит
повторяющуюся scaffolding-логику без превращения всей registration family в
один god-module.

Очень важно, чтобы эта волна не захватывала слишком рано runtime/bootstrap
paths, которые уже явно помечены как deferred boundary. Evidence и планы
показывают, что runtime ownership around `ProviderRegistry` ещё не готов к
жёсткому forcing explicit instance ownership across all call sites. Это не
слабость плана, а разумный safe boundary. Значит, Wave 1 должна сознательно
работать только там, где выигрыш уже высок, а runtime semantics можно не
тронуть. Именно поэтому `rf-07d` не должен раствориться в Wave 1 полностью;
он даёт ограничение: preserve current bootstrap semantics while simplifying the
composition-side resolution and assembly logic.

В practical execution эта волна почти наверняка распадётся минимум на четыре
slices. Первый — resolution ledger и symbol map. Второй — canonical internal
resolution path. Третий — provider-family assembly narrowing. Четвёртый —
explicit documentation and ratchets for retained compatibility obligations.
Такое деление неслучайно: оно отделяет code motion и deduplication от policy
closure. Если попытаться сделать всё в одном batch, то итогом будет либо
невнятный компромисс, либо слишком большой diff для надёжного review.

Verify strategy этой волны должна быть одновременно локальной и жёсткой.
Минимальный mandatory набор выглядит так: `tests/unit/composition/providers`,
`tests/architecture/test_provider_registry_decomposition.py`, targeted
compatibility freeze guards, и `mypy --strict --no-incremental` по
`src/bioetl/composition/providers`. Но этим не стоит ограничиваться. Если в
ходе волны трогаются call sites вне непосредственного каталога providers, их
тоже нужно добавлять в verify set slice-by-slice. Главное правило — не
завершать slice, если тесты говорят “кажется, зелёно”, но ownership story стала
менее понятной, чем была до этого. Для этой волны readability и ownership
clarity — не побочный эффект, а один из core deliverables.

Риск у Wave 1 не только технический, но и семантический. Самая частая ошибка в
таком refactor cluster — принять compatibility shape за просто «старый код» и
слишком агрессивно выпрямить всё в один путь. Evidence прямо предупреждает,
что default-registry layer и class-level mirror — не случайность. Поэтому
любое упрощение должно сопровождаться вопросом: это убирает accidental
duplication или разрушает sanctioned compatibility surface? Пока на этот вопрос
нет явного ответа, удалять или схлопывать seam нельзя.

Definition of Done для Wave 1 выглядит так: repeated registry-resolution paths
внутри `src/` сокращены или централизованы; provider-family registration
scaffolding уже не копирует один и тот же skeleton в нескольких местах;
retained compatibility obligations явно перечислены; runtime/bootstrap semantics
не сломаны; architecture guards и strict typing остаются зелёными. Когда это
достигнуто, проект получает гораздо более чистую стартовую позицию для всех
дальнейших волн.

Чтобы эта волна действительно дала максимальный эффект, в ней стоит отдельно
развести две категории повторения: semantic duplication и procedural
duplication. Semantic duplication возникает тогда, когда несколько модулей
фактически знают одно и то же правило о registry ownership, default fallback
или provider-family assembly. Procedural duplication возникает тогда, когда
разные семейства registration вызывают почти одинаковую последовательность
шагов, но с минимальными вариациями в аргументах и helper wiring. Эти типы
повтора похожи снаружи, но лечатся по-разному. Первый требует явного owner
path и policy consolidation. Второй часто требует общего helper или narrow
orchestrator contract. Если их спутать, можно либо создать слишком умный
универсальный helper, который скрывает реальную policy-логику, либо наоборот
оставить policy размазанной по нескольким почти одинаковым call chains.

Wave 1 также должна сознательно фиксировать, какие формы `ProviderRegistry`
считаются допустимыми после рефакторинга. Например, одно дело сохранить
class-level compat mirror как sanctioned legacy surface, и совсем другое —
продолжать разрешать новым internal callers ходить в этот mirror напрямую.
Поэтому после canonicalization internal path нужна явная import discipline:
какие модули в `src/` обязаны использовать new canonical resolution route, а
какие публичные entrypoints разрешено сохранять только для внешней совместимости
или для существующих тестовых seam-ов. Без такой import policy рефакторинг
внешне сократит дублирование, но через несколько недель новое дублирование
вернётся просто потому, что разработчики не увидят разницы между owner path и
compatibility path.

Практически в этой волне важно подготовить и review-friendly форму диффов.
Provider-registration cluster легко сделать технически правильным, но тяжело
ревьюируемым, если сразу тронуть и contracts, и call sites, и naming, и docs.
Поэтому каждая подволна должна давать понятную историю для ревью: вот символы,
которые считаем canonical; вот callers, которые перевели; вот compat surface,
которую сознательно не удаляли; вот тесты, которые удерживают новую модель.
Такой способ подачи изменений особенно ценен в долгоживущем коде, где
архитектурная польза рефакторинга не всегда очевидна по line diff. Чем
лучше документирована логика каждого slice, тем меньше шанс, что следующий
исполнитель снова начнёт “упрощать” ту же зону, не понимая, какие seams уже
были сохранены намеренно.

Наконец, у этой волны есть важный организационный результат за пределами
самого provider-кластера. Если она выполнена хорошо, команда получает
повторяемый шаблон для следующих ownership-heavy refactors: сначала symbol
ledger, потом canonical internal path, затем deduplication skeleton, затем
compat ratchets и documentation closeout. Этот шаблон сам по себе является
активом проекта, потому что позволяет делать следующие structural waves более
предсказуемыми и менее конфликтными. В этом смысле Wave 1 не просто чинит один
кластер, а задаёт операционную методику для всего последующего refactor
контура.

## Wave 2. Composition hotspots и ownership-heavy seams

Wave 2 должна восприниматься как логическое продолжение Wave 1, но не как её
механическое расширение. Если первая волна сосредоточена на одном
high-leverage cluster, то вторая работает уже на уровне broader composition
topology. Здесь цель не в том, чтобы массово “сжимать composition”, а в том,
чтобы закрепить composition как честный слой assembly и orchestration, а не как
место, где по историческим причинам осели mixed owners, half-compat shims и
остаточные semantic responsibilities. Это особенно важно после уже проведённых
локальных рефакторингов: часть composition hotpots уже уменьшена, но именно
поэтому оставшиеся seams теперь лучше видны и требуют более deliberate pass, а
не broad rewrite.

На уровне содержания эта волна объединяет несколько ранее разрозненных
направлений. Во-первых, сюда входят незакрытые части `rf-04` по composition
hotspots. Во-вторых, сюда же naturally ложатся ownership-heavy seams,
подсвеченные technical-debt evidence: места, где compat surface и canonical
ownership ещё недостаточно явно разведены. В-третьих, сюда попадает работа по
policy alignment: когда tests, reports и код уже говорят примерно об одном, но
не совсем одинаковыми словами. Именно такие зоны часто становятся источником
следующего слоя долга, потому что никто не может уверенно сказать, является ли
данный модуль owner, shim, façade или временный bridge.

Практически эту волну нужно начинать не с файлового списка, а с seam
classification matrix. Для каждого существенного composition-side seam нужно
понять минимум четыре вещи: где canonical owner; есть ли retained compatibility
surface; кто потребитель этого seam внутри `src/`; какие tests/guards уже
фиксируют его intended shape. Такой matrix особенно полезен, потому что
позволяет отказаться от ложного бинарного выбора “либо оставить как есть, либо
удалить”. У нас почти всегда будет третий вариант: thin shim with explicit
owner elsewhere. И как раз он должен стать нормой для composition, где это
подтверждено evidence.

Одна из самых важных целей Wave 2 — закрыть ownership ambiguity там, где она
осталась после уже выполненных локальных migrations. Хороший пример того, как
должна работать эта волна, уже виден на config-flow work: canonical path moved,
compat seam retained, tests updated, reports adjusted. То же самое нужно
повторить для других composition-heavy seams, но только там, где ownership
действительно ещё остаётся mixed. При этом нельзя превращать эту волну в
глобальный rename campaign. Названия модулей и paths имеют значение, но их
изменение должно быть следствием ясного owner-model, а не самостоятельной
целью.

Safe slicing здесь особенно важен. Самая опасная форма этой волны — попытка
одним diff-ом “привести composition в порядок”. Вместо этого нужно идти через
bounded subtracks. Один subtrack — provider-related seams after Wave 1. Второй
— pipeline/config related seams, где canonical owners уже mostly moved, но
retained wrappers ещё требуют чёткого статуса. Третий — services/factories
seams, где package root exports, compat shims и internal canonical paths должны
быть выровнены. Каждый subtrack должен завершаться собственной closure note:
что теперь owner, что retained, что больше нельзя импортировать из `src/`,
какие guards это удерживают.

В verify-подходе эта волна должна быть, возможно, самой дисциплинированной из
всех. Именно composition layer чаще всего имеет широкий blast radius по imports,
при том что behaviour change может быть нулевым. Это значит, что обязательны
не только unit tests и mypy, но и targeted architecture tests на forbidden
imports, compatibility freeze guards и canonical path checks. Хороший признак
того, что slice выполнен верно: code diff кажется небольшим, а clarity of
ownership заметно возрастает. Если же diff огромный, а сформулировать новый
owner-model по-прежнему трудно, значит slice был нарезан неправильно.

У этой волны есть и организационный риск: temptation решать одновременно
ownership, naming, packaging и runtime wiring. Evidence и master plan специально
разводят эти вещи по разным следующим волнам. Ownership closure — это про
“кому принадлежит ответственность”, а не про “как красивее назвать файл” и не
про “можно ли уже убрать все deferred runtime paths”. Поэтому Wave 2 должна
жёстко сопротивляться scope creep. Если по ходу работы становится ясно, что
проблема уже требует явного retained/retire decision, её нужно поднять как
input для Wave 3, а не пытаться добить внутри этой волны любой ценой.

В конечном счёте Wave 2 успешна тогда, когда composition становится более
предсказуемым слоем для всех следующих инициатив. После неё должно быть легче
делать hotspot reduction и conservative cleanup, потому что станет понятнее,
какие seams являются intentional bridges, какие — canonical assembly owners, а
какие — действительно оставшийся historical residue. Это и есть главное
практическое назначение волны: подготовить систему к более агрессивному, но
безопасному уменьшению долга в следующих этапах.

Ещё один критически важный элемент Wave 2 — работа с package roots и
реэкспортами как с самостоятельной формой долга. Во многих зрелых Python
кодовых базах двусмысленность ownership живёт не только внутри конкретных
модулей, но и на уровне пакетов: `__init__.py`, package-level aliases и
historical convenience imports продолжают показывать наружу старую картину
мира, даже когда canonical owners уже переехали. Именно composition особенно
чувствителен к этой проблеме, потому что package roots здесь часто выступают
как удобные точки сборки. Значит, внутри волны нужно честно определить, где
package root остаётся sanctioned facade, а где он должен перестать быть местом
новой логики и стать просто тонким barrel с хорошо контролируемыми exports.

Wave 2 также выигрывает от явного разделения “assembly semantics” и
“configuration semantics”. Composition вправе знать, как собрать зависимости,
в каком порядке построить фабрики, какой wiring должен произойти для runtime
bundle. Но composition не должен долго оставаться owner-слоем для semantic
правил конфигурации, контрактной валидации данных или shape-level knowledge,
если для этого уже существует более естественный дом в infrastructure или
domain. Поэтому при каждом disputed seam полезно задавать один вопрос:
содержит ли этот composition-модуль логику о том, как соединять части системы,
или он фактически содержит знание о самих данных, конфигурациях и инвариантах?
Если второе, значит это сильный сигнал для дальнейшего owner move либо для
чёткого compat-shim статуса.

Отдельно стоит предусмотреть эффект для новых участников команды. Composition
часто становится первым слоем, куда смотрят, когда пытаются понять “как всё
собирается вместе”. Если именно здесь ownership ambiguity особенно высокая,
то даже хорошие тесты и зелёный mypy не спасают от когнитивной перегрузки.
Поэтому качественный outcome Wave 2 можно оценивать не только через набор
guards, но и через narrative test: может ли человек, не участвовавший в
предыдущих волнах, открыть composition-пакет и без долгих археологических
раскопок понять, где owner, где shim и где sanctioned facade. Если после wave
это стало проще, то она действительно уменьшила долг, а не просто переставила
импорты.

Последний важный акцент здесь касается порядка выполнения. Wave 2 нельзя
растягивать в бесконечную программу “пока composition не станет идеальным”.
Нужен measured stop condition. Как только основные ownership-heavy seams
классифицированы, canonical paths закреплены, а compat surfaces отделены от
owners и удерживаются guards, волну нужно считать завершённой. Иначе она
начнёт пожирать задачи следующих этапов: naming, cleanup и even infrastructure
hotspot reduction. В зрелой refactor-программе не менее важно уметь
останавливаться в правильной точке, чем начинать работу в правильной зоне.

## Wave 3. Adapter и infrastructure hotspot reduction

Wave 3 открывает самый «масштабный по объёму, но не по стратегии» кусок
работы. Evidence показывает, что инфраструктурный слой, особенно
`src/bioetl/infrastructure/adapters`, концентрирует на себе значительную долю
structural pressure. При этом важно не попасть в ловушку: это не приглашение к
полной перестройке infrastructure. Layer policy остаётся чистой, drift guards
работают, а значит проблема не в нарушении архитектуры как таковой. Проблема в
том, что внутри allowed seams накопились крупные плотные участки, где
responsibilities смешиваются быстрее, чем успевает обновляться owner-model и
локальная структура каталогов. Именно это делает Wave 3 сложной: она должна
уменьшать давление без разрушения существующих, в целом рабочих границ.

Первый обязательный шаг — hotspot ledger для инфраструктуры. Нельзя начинать
рефакторить “самые большие файлы” по ощущениям. Нужно собрать и сопоставить
минимум четыре сигнала: overlap hotspots, size/LOC hotspots, test hotspots и
integration coupling. Это даёт не один линейный список файлов, а карту
кластеров. В одних местах pressure возникает из-за семейства adapter clients,
в других — из-за helper/mixin stack, в третьих — из-за observability or retry
wrappers, в четвёртых — из-за storage-support primitives. Каждый такой кластер
имеет разную правильную стратегию: где-то нужен split, где-то owner extraction,
где-то local API tightening, а где-то вообще лучше ничего не трогать до
следующей evidence wave.

Почти наверняка первым кандидатом внутри этой волны должны быть не все
adapters разом, а один или два наиболее плотных provider-family clusters.
Причина проста: project already has strong integration surface with VCR,
contract tests and provider-specific edge cases. Если трогать слишком много
adapters сразу, мы потеряем возможность различать “структурное улучшение”
и “случайную регрессию в provider behavior”. Поэтому bounded-cluster strategy
здесь не просто удобна, а обязательна. Один кластер — одна история pressure,
один набор unit/integration tests, один локальный mypy run, один drift check.

Внутри выбранного кластера работа должна идти по той же дисциплине, что и в
предыдущих волнах: сначала inventory responsibilities, затем выделение narrow
helpers or owner paths, только потом thinning public or semi-public façades.
Особенно важно не множить thin wrappers ради самого “разрезания файла”.
Большой adapter file не перестаёт быть техническим долгом, если вместо него
появилось пять маленьких файлов без более ясного ownership. Поэтому любой
structural split внутри этой волны должен отвечать на вопрос: какую
ответственность теперь легче локализовать, тестировать и развивать? Если
ответа нет, значит split cosmetic and likely harmful.

Отдельное место в этой волне занимает observability and support logic. Очень
часто infrastructure hotspots растут не только от provider-specific fetch
logic, но и от того, что рядом оседают retry, health-check, tracing,
serialization, normalization и envelope-building concerns. Это опасные зоны для
рефакторинга, потому что они выглядят “второстепенными”, но часто являются
скрытым glue code между множеством runtime paths. Поэтому их нельзя просто
вынести “куда-нибудь в helpers”. Если они выносятся, то только в явный owner
module с понятной областью действия и доказуемым набором callers.

Verify-модель Wave 3 должна быть наиболее тяжёлой из всех волн после Wave 1.
Для каждого subcluster минимум нужен такой: unit tests соответствующего
infrastructure scope, связанные integration tests, architecture dependency drift
check, code-metric tests для hotspot-sensitive areas и mypy по затронутому
дереву. Важно, что global full-suite не должен быть единственным способом
понимать, успешен slice или нет. Эта волна будет слишком дорогой, если после
каждого маленького изменения запускать всё подряд. Но equally dangerous было бы
довольствоваться одним локальным unit run без integration/tests around edges.
Значит, нужна layered verify strategy: local first, cluster second, global
sanity periodically.

Главный управленческий риск этой волны — scope explosion. Поскольку hotspot
evidence в infrastructure богата, всегда будет ощущение, что “раз уж мы уже
здесь, давайте заодно поправим ещё вот этот соседний cluster”. Это почти
всегда ошибка. Wave 3 должна завершаться не максимумом touched files, а
сокращением pressure в конкретных densest seams. Всё, что выходит за границы
текущего bounded-cluster, нужно либо explicitly defer, либо вынести в next
subcluster ledger. Такой discipline защищает от превращения wave в
unreviewable broad churn.

Успешный результат Wave 3 выглядит не как «infrastructure стала маленькой», а
как «the densest allowed seams стали менее хрупкими и менее дорогими в
сопровождении». Если после этой волны hotspot tail visibly thinner, architecture
tests зелёные, integration behavior стабилен, а новые shims не proliferated,
значит волна выполнила свою задачу. Именно после такого уменьшения давления
можно безопасно переходить к более локальным complexity и cleanup waves.

Wave 3 особенно нуждается в явной экономике рефакторинга. В инфраструктурном
слое очень легко найти много правдоподобных причин “зайти ещё чуть глубже”:
ещё один helper, ещё один retry wrapper, ещё один adapter client, ещё один
metrics path. Но в таком слое стоимость изменений определяется не только тем,
насколько файл кажется большим или плотным, а тем, сколько внешних систем,
кассет, integration expectations и косвенных behavioural contracts этот код
цепляет. Поэтому каждая подволна должна начинаться с вопроса не просто “где
самый большой hotspot”, а “где сейчас лучшее соотношение maintenance gain к
verification cost”. Иногда это будет действительно крупнейший кластер. Иногда
— чуть менее крупный, но гораздо лучше изолированный, а значит дающий более
чистую победу за меньший operational risk.

Есть и ещё одна тонкость: infrastructure hotspot reduction не должна
превращаться в спор о “правильной архитектуре провайдеров” в целом. Разные
provider packages уже сейчас могут быть асимметричными по вполне уважительным
причинам: разные API, разные модели paging, разная retry semantics, разная
степень зрелости интеграции, разные типы контрактов. Значит, целью волны не
может быть декоративная симметрия каталогов. Целью может быть только снижение
напряжения в тех местах, где конкретный кластер стал слишком дорогим в
сопровождении. Если после рефакторинга пакеты останутся неодинаковыми, но
каждый из них будет честнее отражать свою ответственность, это хороший исход,
а не failure of standardization.

Практически полезно заранее определить типы разрешённых операций внутри этой
волны. Разрешёнными должны считаться owner extraction, responsibility split,
thinning facade, helper localization, import tightening и instrumentation
clarification. Ограниченно разрешёнными — naming cleanup и package moves, но
только если они прямо уменьшают hotspot pressure. Неразрешёнными по умолчанию
должны считаться broad provider normalization, large runtime policy rewrites и
массовая унификация adapter shapes. Такая операционная рамка сильно помогает в
долгих волнах, потому что команда меньше спорит “а можно ли заодно”, и больше
фокусируется на том, что было доказано evidence как реальный источник долга.

Хорошо выполненная Wave 3 даёт проекту ещё один долгосрочный актив: улучшенную
локальность тестирования. Когда hotspot-кластеры становятся более узкими по
ответственности, проще понять, какие unit suites действительно являются
owner-suites, какие integration tests являются обязательными, а какие прогоны
можно не запускать на каждом маленьком slice. Это снижает не только долг кода,
но и долг процесса. В крупных инфраструктурных зонах именно способность быстро
и уверенно верифицировать локальное изменение часто определяет, будет ли
следующий рефакторинг вообще возможен.

## Wave 4. Complexity hotspot implementation

Wave 4 берёт отдельный класс долга, который нельзя полностью слить с общими
dependency-hotspots. Complexity hotspot — это не просто большой файл и не
просто плотный import graph. Это место, где одна единица кода уже содержит
слишком много branching, orchestration, envelope-building или mixed concerns,
чтобы оставаться дешёвой в изменении. В текущем наборе evidence это особенно
хорошо видно на Crossref-related batch logic, где runtime и тесты уже сами
показывают, что seam просится на split. Именно поэтому complexity backlog
нужно сохранить отдельной волной: иначе он потеряется между provider migration
и adapter hotspot work, хотя фактически является независимым типом риска.

Главный смысл этой волны — не бороться со всеми большими функциями и классами
сразу, а реализовывать те complexity reductions, которые уже подтверждены
evidence и governance policy. Здесь есть важный нюанс: policy around file size,
function length и exemptions уже достаточно сильна. То есть проект уже умеет
выявлять большие сложные units. Следовательно, задача Wave 4 — не построить
ещё одну систему сигналов, а использовать уже существующие сигналы для narrow
implementation slices. Это сильно отличает её от Wave 3: там нам нужен
hotspot ledger по инфраструктуре, а здесь у нас уже есть готовый evidence-backed
complexity backlog.

Работа должна идти от strongest candidate outward. Если evidence уже прямо
говорит, что условный Crossref batch cluster смешивает batch workflow,
pagination workflow и observability envelope, именно этот seam должен идти
первым. Не потому, что он самый большой, а потому что по нему уже есть
согласованная evidence story: метрика, runtime exposure, тестовое покрытие и
policy implication. Это означает, что slice можно строить уверенно: выделять
sub-responsibilities, оставлять stable shell around orchestration point и
переносить внутреннюю сложность в более локальные owner units.

Однако complexity reduction нельзя путать с general cleanup. Частая ошибка —
увидеть complexity hotspot и начать одновременно переименовывать сущности,
двигать файлы по пакетам и сливать helper modules. Всё это может быть разумным,
но почти всегда превращает complexity wave в бесконтрольный structural rewrite.
Правильная стратегия здесь другая: сначала уменьшить внутреннюю сложность узла,
сделать control flow более локальным и читаемым, зафиксировать это тестами,
только потом смотреть, есть ли дополнительная польза от package-level moves.
Иначе проект рискует получить меньшие функции, но более хаотичную географию
кода.

В этой волне особенно полезен “functional seam first” подход. То есть сначала
выделяется не новый файл как такой, а functional boundary: input validation,
page/window planning, response normalization, retry envelope, metrics emission,
batch aggregation. Затем смотрится, какие из этих boundaries уже существуют в
полускрытом виде и могут стать owner units. Это важнее, чем просто “поделить
пополам длинный класс”, потому что уменьшает именно semantic complexity, а не
только line count.

Verify для этой волны должен быть очень чувствителен к behavioural regression.
Complexity hotspots часто сидят в местах, где логика вроде бы “служебная”, но
на самом деле сильно влияет на runtime envelopes, retries, ordering и
observability. Поэтому кроме unit tests нужен targeted run на связанные
integration или behavioural suites. Плюс обязательно сохраняются metric/god
object gates, чтобы refactor реально уменьшал сложность, а не просто переносил
её из одного файла в другой. В идеале после каждого complexity slice должен
быть measurable delta: меньше branches in owner unit, меньше exemption pressure,
лучше test locality.

Самый большой риск Wave 4 — переоценить силу evidence и начать broad complexity
campaign. Даже очень качественный backlog не делает безопасным одновременное
лечение десяти hotspots. Complexity work почти всегда требует fine-grained
understanding of behavior, а значит должна идти narrow batches. Лучше закрыть
два сильных кандидата полностью, чем начать шесть и оставить все в
полуразрезанном состоянии. Поэтому roadmap уже правильно ставит эту волну после
provider/infrastructure work: только на более стабильном structural фоне имеет
смысл делать аккуратное semantic complexity reduction.

Wave 4 считается успешной, когда проект уменьшает reliance на metric
exemptions, делает один или несколько evidence-confirmed hotspots заметно
проще, и при этом не рождает новый compatibility or packaging debt. Иными
словами, это волна не про “красоту кода”, а про measurable reduction of
maintenance cost in already proven complexity-sensitive seams.

Для этой волны особенно полезно удерживать разницу между “сложностью как
свойством формы” и “сложностью как свойством домена”. Не вся длинная функция
или крупный класс является плохим design artifact. Иногда код длинный потому,
что сам бизнес-процесс действительно богат шагами и развилками. Поэтому перед
каждым complexity-slice нужно честно отвечать: уменьшаем ли мы accidental
complexity, то есть сложность, возникающую из-за смешения ролей и слабой
локальности, или пытаемся убрать inherent complexity, которую всё равно придётся
где-то выразить. Правильная волна работает в основном с первым типом. Если же
мы пытаемся “сделать проще” то, что по природе своей сложно, рефакторинг быстро
становится либо декоративным, либо опасным.

Отсюда следует ещё один принцип: complexity hotspots не должны лечиться только
через разбиение по строкам. Инструментально приятно увидеть, что файл стал
короче и метрика успокоилась, но это не гарантирует, что reading complexity
снизилась. Иногда полезнее оставить orchestration shell почти того же размера,
но вынести decision-heavy подэтапы в ясные функции с хорошими именами и
локальными тестами. В других случаях, наоборот, лучше выделить объект-сервис,
если именно stateful coordination мешала понимать код. То есть волна должна
быть методологически гибкой, но evaluatively жёсткой: каждая операция должна
объясняться тем, какую конкретную cognitive или change complexity она убирает.

Wave 4 также выигрывает от явной связи с политикой code metrics. Если проект
уже имеет guards на class size, function length, god object patterns и
exemptions, то каждый выполненный slice стоит завершать небольшой closure
нотой: какая именно метрика перестала быть напряжённой, какой exemption можно
снять или уменьшить, какой hotspot теперь не выглядит как следующий очевидный
кандидат на поломку. Такая практика превращает волну из просто “серии
рефакторингов” в measurable program of debt reduction. В долгой перспективе
это очень ценно, потому что даёт не только ощущение улучшения, но и
трассируемый след того, зачем был нужен каждый complexity move.

Наконец, у этой волны есть важное ограничение на параллелизм. Даже если в
backlog сразу видно несколько сильных complexity candidates, не стоит запускать
их все одновременно. Complexity refactors требуют высокой концентрации на
поведении и редко хорошо сочетаются с массовой параллельной работой в одной
и той же подсистеме. Лучше выбрать ограниченное число кандидатов, довести их
до закрытого состояния и только потом переходить к следующему пулу. Именно
последовательность, а не ширина охвата, делает complexity wave безопасной и
воспроизводимой.

Дополнительно для Wave 4 полезно заранее определить форму итоговой
демонстрации результата. После каждого slice должно быть возможно показать не
только diff и зелёные тесты, но и короткий ответ на три вопроса: какая именно
сложность была уменьшена, где теперь находится основная orchestration shell, и
почему новая структура делает следующие изменения дешевле. Такая дисциплина
помогает не спутать реальный complexity reduction с просто более модной формой
кода и делает волну убедительной даже для тех, кто не участвовал в её
реализации.

## Wave 5. Domain facade, naming и narrative hygiene

Wave 5 intentionally стоит после structural/provider/hotspot work, потому что
она про когнитивную чистоту системы, а не про её наиболее острые концентраторы
долга. Это не делает её второстепенной в долгосрочном смысле. Наоборот, именно
такие волны часто определяют, насколько легко новым участникам команды читать
архитектуру, понимать ownership и безопасно вносить изменения. Но с точки
зрения стоимости-риска именно она должна идти после того, как high-leverage
structural seams уже сужены и более не доминируют над backlog.

Эта волна объединяет три близкие, но не одинаковые вещи. Первая — domain facade
hygiene around `domain.ports`, `PipelineContext` и related architectural
narrative. Вторая — naming cleanup, особенно там, где naming drift уже доказан
evidence, а не является просто эстетическим раздражителем. Третья — governance
calibration там, где naming и facade policy уже поддерживаются тестами и
документами, но ещё не сведены в одну достаточно ясную форму. Важно, что волна
не должна становиться repo-wide rename wave. Evidence уже прямо предупреждает:
нужно приоритизировать semantic convergence, а не повсеместное переименование.

Работу в этой волне лучше строить через semantic clusters. Один cluster —
domain facade narrative: что именно обещает `domain.ports`, что считается
нормальной фасадной политикой, какие runtime ports intentionally remain in
domain and why. Другой cluster — naming drift в функциях, переменных,
объектных семействах и файлах, но только там, где drift реально мешает
ownership reading или создаёт false expectations. Третий — alignment between
docs, naming decisions and code paths. Такой подход полезен тем, что не даёт
смешать “улучшить читаемость” с “массово переименовать проект”.

Очень полезным будет правило: любое rename в этой волне должно отвечать хотя бы
на один из трёх вопросов. Что именно станет менее двусмысленным? Какой owner
или responsibility теперь читается яснее? Какой существующий drift between docs
and code реально уменьшается? Если ни на один из вопросов нет сильного ответа,
значит rename probably not worth the churn. Особенно это важно для файловых
rename-ов, потому что их стоимость обычно выше, чем локальное улучшение
внутренней семантики.

В domain facade части этой волны основной риск — случайно превратить narrative
hygiene в скрытую layer migration. Evidence already suggests that some runtime
ports intentionally remain in `domain`, and это не нужно пересматривать только
потому, что кому-то кажется “интуитивнее” хранить их в application or
infrastructure. Значит, эта волна должна работать не через перемещение
сущностей между слоями, а через уточнение контрактов, фасадов, docstrings,
exports и guardrails. Иными словами, цель не “переразложить домен”, а сделать
существующую логику layering более читаемой и менее спорной.

Verify у этой волны тоже специфический. Здесь мало просто прогнать mypy и
architecture tests. Нужны targeted checks, которые удерживают naming policy,
documentation drift, facade exports и public narrative invariants. Где-то это
будут naming guards, где-то doc drift checks, где-то contract/facade tests.
При этом поведение runtime почти не должно меняться. Если в процессе naming
cleanup приходится чинить behaviour, это сигнал, что волна съехала в другой
тип работы и её нужно переупаковать.

Наиболее вероятный результат Wave 5 — не dramatic structural change, а заметное
снижение cognitive friction. После неё проект должен быть легче читать:
фасады — понятнее, naming — ближе к ответственности, docs — менее расходятся с
кодом, а architectural narrative — меньше полагается на “контекст в голове
автора”. Это особенно важно для последующих maintenance waves: чем яснее
семантика системы, тем ниже вероятность, что будущий refactor снова создаст
ownership ambiguity.

Волна считается успешной, если naming and facade changes действительно
уменьшают confusion without large churn, если не происходит скрытого layer
migration, если docs/code drift уменьшается, и если итоговая модель становится
проще для объяснения новым участникам команды. Это одна из немногих волн,
где качественный outcome partly определяется тем, насколько проще стало
“рассказать” архитектуру, а не только тем, сколько строк кода было изменено.

Wave 5 полезно понимать как программу снижения семантического шума. В зрелом
репозитории большой процент трения возникает не потому, что код “неправильный”,
а потому, что разные части системы называют похожие вещи по-разному, а разные
уровни документации объясняют одни и те же фасады с разной степенью точности.
Это не ломает runtime напрямую, но постоянно повышает стоимость понимания и
обсуждения. Поэтому волна должна работать не столько с “красотой” названий,
сколько с предсказуемостью архитектурного языка проекта. Когда разработчик
видит слово `Port`, `Facade`, `Resolver`, `Builder`, `RuntimeConfig` или
`Context`, он должен иметь хорошие шансы угадать класс ответственности ещё до
чтения реализации. Именно такая предсказуемость и есть главный актив naming
and narrative hygiene.

В практическом исполнении для этой волны особенно важна связь с документацией.
Если naming cleanup делается только в коде, но не отражается в коротких
архитектурных объяснениях, glossary или policy notes, то cognitive drift быстро
возвращается. Значит, часть волны должна сознательно включать “малые”
документационные правки: обновление кратких описаний фасадов, уточнение
decision notes, синхронизацию README-level ориентиров для тех пакетов, где
semantic drift был заметен сильнее всего. Это не означает крупный documentation
campaign, но означает, что narrative hygiene нельзя закрыть без минимального
code-plus-doc sync.

Ещё одна важная часть этой волны — защита от перфекционизма. Naming debt почти
всегда бесконечен: при желании можно находить ещё десятки мест, где имя “можно
сделать лучше”. Поэтому нужен принцип достаточности. Волна должна исправлять
те drift-зоны, которые создают систематическую путаницу, а не те, что просто
раздражают эстетически. Хороший фильтр здесь такой: если неправильное или
слабое имя регулярно провоцирует неверные ожидания о слое, типе зависимости,
ownership или поведении, оно в scope. Если имя лишь неидеально, но не мешает
работе и не конфликтует с архитектурной историей, его стоит оставить в покое.
Именно этот фильтр защищает Wave 5 от превращения в непродуктивную rename-wave.

Наконец, качественный результат этой волны создаёт базу для будущих людей и
будущих решений. Чем чище narrative around facades и naming, тем легче
следующие рефакторинги будут принимать корректные локальные решения без
постоянного обращения к историческому контексту. В этом смысле Wave 5 влияет
не только на читаемость текущего состояния, но и на вероятность того, что
новый долг вообще появится снова в тех же местах.

Важно и то, что эта волна задаёт эталон качества для коммуникации внутри
репозитория. Когда naming и facade narrative выровнены, code review становится
короче и точнее: обсуждения чаще касаются реального поведения и ownership, а
не расшифровки того, что “автор имел в виду под этим именем”. Для проекта,
который уже пережил несколько серий structural refactor-ов, такой эффект очень
ценен, потому что снижает нагрузку не только на чтение кода, но и на сам
процесс совместного принятия изменений.

## Wave 6. Conservative cleanup и residual debt follow-up

Wave 6 замыкает мастер-программу и специально поставлена в конец, потому что
она состоит из двух типов работы, которые нельзя безопасно делать раньше:
conservative cleanup по candidate-level evidence и дополнительный follow-up по
residual debt, который пока не покрыт основными pillars. Это очень важная
структурная позиция. Если broad cleanup начать раньше, проект легко перепутает
санкционированные compatibility surfaces с настоящими deletion targets. Если
раньше времени уйти в residual CI/test debt, то можно потратить много времени
на второстепенную оптимизацию, пока основные structural seams ещё не сужены.

Первая часть Wave 6 — conservative cleanup queue. Здесь главное правило уже
известно из evidence: no broad delete campaign. Каждый кандидат должен входить
в работу только после индивидуальной проверки по четырём вопросам. Есть ли
доказательство, что это действительно dormant or mergeable code? Не является ли
он retained wrapper, sanctioned aggregate seam или public compatibility
surface? Есть ли tests, docs или import paths, которые всё ещё предполагают его
существование? Что именно выигрывает проект, если этот кандидат будет удалён
или repurposed? Без явного ответа на эти вопросы cleanup не начинается. Это
делает волну медленной, но именно такая медленность и есть плата за
безопасность.

Отличный пример того, как должна работать эта часть волны, — `batch_transformer_orchestration.py`.
Evidence уже допускает его как moderate review candidate, но не поддерживает
straight deletion. Это означает, что сначала нужен candidate-level review
batch: usage scan, test touchpoints, runtime expectations, relation to adjacent
orchestration paths. Только после этого можно выбрать действие: retain, merge,
deprecate-later или delete. И так для каждого кандидата. Это звучит
консервативно, но именно такая дисциплина защищает проект от потери seams,
которые «выглядели лишними», а потом внезапно оказываются частью public or test
contract.

Вторая часть Wave 6 — residual test/CI debt follow-up. Test-swarm уже показал,
что даже при хорошем audit process остаётся gap между global collected test
inventory и audited shard outcomes. Это не обязательно ошибка, но это уже
самостоятельный источник технического долга: shard model, CI cost,
classification gaps и потенциально uneven visibility across test areas.
Поэтому логично завершить общий structural roadmap отдельным evidence-backed
follow-up по test/CI debt. Важно не путать эту задачу с “просто прогнать ещё
больше тестов”. Нужен именно research + planning pass: какие тестовые области
не входят в текущие shard models, какие CI shards можно оптимизировать, где
есть performance hotspots, а где просто отсутствует ясная ownership model для
tests themselves.

Практически эту волну лучше строить в двух параллельных треках, но не
одновременно в одном batch. Сначала cleanup candidates, затем residual test/CI
evidence, либо наоборот, если operationally выгоднее. Но эти треки всё равно
должны оставаться независимыми. Cleanup candidate review работает по одной
логике: object-level доказательство. Test/CI follow-up — по другой: evidence
and classification. Смешивать их опасно, потому что тогда выводы про тестовые
gaps начнут подменять собой решения о deletion, или наоборот.

Verify для cleanup части должен включать targeted unit suites конкретных
ownership packages, architecture tests и global mypy. Verify для test/CI
follow-up, наоборот, может быть более evidence/document oriented, хотя
architecture and mypy sanity checks всё равно полезны. В обоих случаях финальный
deliverable волны не обязан быть исключительно кодовым. Для cleanup — это
может быть updated candidate ledger with resolved statuses. Для CI/test follow-up
— отдельный evidence pack и новый planning input. Такой подход сохраняет
честность: не вся волна refactor программы обязана заканчиваться production
diff-ом, если её ценность в снижении неопределённости перед следующим шагом.

Главный риск Wave 6 — усталость от программы и желание “просто добить всё, что
осталось”. Именно на этом этапе команда чаще всего делает broad cleanup,
аргументируя, что “основное уже готово”. Этот соблазн нужно сознательно
отклонять. Консервативный характер волны — не недостаток, а её ключевое
назначение. Лучше оставить три слабых кандидата в `retain/defer`, чем удалить
один нужный aggregate seam и потом восстанавливать compatibility post-factum.

Волна считается успешной, если cleanup-кандидаты проходят через
candidate-level evidence, а не через визуальные предположения; если sanctioned
wrappers и compatibility seams остаются защищёнными по умолчанию; если residual
test/CI debt описан отдельным reusable artifact; и если на выходе программа
рефакторинга не распадается в хаотичную “добивку хвостов”, а завершается
контролируемым и воспроизводимым closure pass.

Есть ещё одна причина, по которой Wave 6 логично завершает программу, а не
идёт раньше. Финальные cleanup-решения почти всегда выглядят проще, чем они
есть на самом деле. Когда большая часть крупных волн уже выполнена, возникает
иллюзия, что оставшиеся элементы очевидны: тонкие wrappers, малоиспользуемые
helpers, старые package-level entrypoints, недавние deferred candidates. Но как
раз в этот момент проект особенно уязвим к ошибочным удалениям, потому что
контекст про эти seams часто хранится не в коде, а в памяти о прошлых
рефакторингах. Значит, финальная волна должна компенсировать ослабление этой
памяти формализованной дисциплиной: каждый candidate review должен быть
достаточно маленьким, чтобы его можно было честно проверить, и достаточно
документированным, чтобы решение не пришлось переоткрывать через месяц.

Residual test/CI follow-up тоже важно рассматривать не как “хвостик после
основной работы”, а как подготовку следующего цикла зрелости репозитория.
Если после завершения крупных structural волн остаётся неясность в shard
model, в стоимости прогонов, в coverage visibility или в classification of
test ownership, то это уже не случайная операционная мелочь, а полноценный
источник будущего замедления. Следовательно, даже если Wave 6 не приводит к
большому production diff, она всё равно может существенно повысить способность
команды продолжать эволюцию проекта. Хорошо оформленный evidence pack по
residual CI debt становится входом для следующей программы улучшений так же,
как dependency и ownership evidence стали входом для текущей.

Практически здесь полезно заранее определить формат закрытия волны. Для
cleanup track это может быть таблица кандидатов со статусами `delete`,
`merge`, `retain`, `defer`, плюс ссылки на verify batches и rationale. Для
test/CI track это может быть отдельный roadmap с приоритетами по shard model,
coverage accounting и cost hotspots. Такой формализованный closeout важен,
потому что без него конец программы часто растворяется в серии несвязанных
commit-ов и временных заметок. А главная ценность Wave 6 как раз в том, чтобы
закрыть программу рефакторинга не “по ощущению”, а воспроизводимым набором
решений и остаточных входов для будущего.

Именно поэтому успех финальной волны измеряется не количеством удалённых
файлов и не числом мелких фиксов, а качеством завершения. Если по итогам
проекта стало ясно, какие швы были intentionally retained, какие хвосты
действительно убраны, какие debt-зоны откладываются осознанно, и какой
следующий цикл улучшений имеет уже готовый evidence input, значит программа
завершилась зрело. Для долгоживущего репозитория это гораздо ценнее, чем
агрессивная “последняя зачистка”.

## Дополнительные operational addenda по волнам

### Addendum к Wave 0

Для Wave 0 особенно важно заранее договориться, что считать “активным”
документом, а что — просто носителем контекста. Если этого не сделать, команда
неосознанно начнёт спорить о приоритетах на уровне названий файлов и статусов,
а не на уровне реального remaining work. Практически это означает, что в начале
волны нужно составить короткую matrix: документ, текущий status, тип
артефакта, остающаяся исполнимая ценность, proposed destination after cleanup.
Уже на этом этапе обычно становится видно, какие документы больше не должны
входить в список future proposals, хотя продолжают быть важными как history,
evidence или constraints. Такой matrix лучше всего вести рядом с master plan,
а не в отдельном одноразовом заметочном файле, иначе сама волна снова
порождает новый meta-artifact, который через неделю станет ещё одним хвостом.

Второй важный operational принцип Wave 0 — не замораживать backlog в слишком
детальной форме. Цель этой волны не в том, чтобы сделать идеальную taxonomy
навсегда, а в том, чтобы убрать очевидные противоречия. Поэтому полезно
применять правило двух уровней. На первом уровне фиксируется лишь то, что
действительно влияет на execution order: active, proposed, implemented,
context-only. На втором уровне остаются finer distinctions вроде “partially
implemented” или “decision-closed but still referenced”. Если сначала пытаться
разрешить все тонкие статусы, волна рискует превратиться в endless discussion.
Для исполнения следующих волн достаточно, чтобы крупные границы были чистыми,
а тонкие различия могли быть уточнены уже внутри соответствующих workstreams.

Наконец, у Wave 0 есть важный социальный эффект: она создаёт единый язык для
следующих волн. Если structural backlog синхронизирован, исполнители начинают
обсуждать не “какой из старых документов правильнее”, а “какой следующий safe
slice имеет лучший cost/benefit ratio”. Это заметно уменьшает coordination
overhead. И именно поэтому Wave 0 должна быть короткой, жёсткой и конечной.
Как только получен согласованный active set, волну надо закрывать, а не
пытаться совершенствовать каталогизацию бесконечно.

### Addendum к Wave 1

Для Wave 1 полезно заранее зафиксировать, какие изменения считаются
допустимыми, а какие пока запрещены. Допустимыми нужно считать только те
изменения, которые уменьшают duplicated assembly или централизуют resolution
path без изменения публичной semantics bootstrap/test ecosystem. Запрещёнными
стоит считать два класса работ: скрытый runtime migration и implicit removal of
class-level compatibility. Это надо обозначить прямо в начале execution, иначе
любой хороший локальный simplification refactor начнёт “тянуть за собой”
дискуссию о том, можно ли уже убрать default registry fallback вообще. На этой
волне такой вопрос должен закрываться ответом “ещё нет, если это не доказано
отдельным slice”.

Практически очень помогает деление результатов на три корзины: centralized,
retained, deferred. В centralized попадает всё, что реально удалось перевести
на один shared internal path. В retained — всё, что осталось как compatibility
surface и больше не должно masquerade as canonical owner. В deferred — всё, что
связано с runtime/bootstrap semantics и сознательно не трогается в этой волне.
Такое деление полезно не только для отчёта, но и для code review: reviewer
сразу понимает, где ожидать реального structural change, а где change only in
clarity and labeling.

Отдельно нужно следить за тем, чтобы Wave 1 не превратилась в “generic cleanup
providers folder”. Даже если по ходу инвентаризации обнаруживаются соседние
странности, их нельзя автоматически включать в ту же волну. Правильная реакция
— записать их в sibling backlog или в next-wave notes, но не расширять scope
пока не закрыт текущий high-leverage cluster. В противном случае волна потеряет
самую ценную свою характеристику — высокую объяснимость и высокий confidence
в каждом изменении.

### Addendum к Wave 2

Wave 2 требует особенно аккуратной коммуникации между кодом, тестами и
документами. Здесь легко получить ситуацию, когда код уже стал лучше, tests
зелёные, но документы и internal vocabulary всё ещё описывают старую картину.
Именно поэтому внутри этой волны стоит считать полноценным deliverable не
только code diff, но и local ownership note: короткое, но однозначное
описание, что теперь owner, что shim, что preserved for compatibility, и что
запрещено использовать как canonical path из `src/`. Такой note снижает риск,
что через две-три недели кто-то снова начнёт импортировать старый seam просто
потому, что он “кажется удобным”.

Ещё один важный practical trick — проверять composition changes не только на
architecture tests, но и на narrative consistency. Это можно делать
полуформально: после каждого slice формулировать в двух-трёх предложениях
новую модель ответственности. Если сформулировать её трудно, значит refactor
либо не закончен, либо был произведён в неверном месте. Такой текстовый smoke
test иногда выявляет проблемы раньше, чем code metrics. Composition — это слой,
где cognitive architecture почти так же важна, как техническая.

Наконец, в Wave 2 нельзя стремиться к полной elimination of shims. Для
composition это unrealistic and unnecessary goal. Качественный outcome состоит
не в полном исчезновении промежуточных seams, а в том, что они становятся
тонкими, честно названными и ограниченными. Если после волны остаётся shim,
но все знают, что он retained on purpose и guarded by tests, это хороший
результат. Гораздо хуже ситуация, когда shim вроде бы исчез, но ownership снова
расползлась по соседним модулям.

### Addendum к Wave 3

В инфраструктурной волне критично заранее договориться об единице измерения
успеха. Если смотреть только на line count, почти любой split будет выглядеть
хорошо. Если смотреть только на passing tests, можно не заметить, что pressure
tail фактически никуда не делся. Поэтому лучше использовать composite success
view: локально уменьшился owner-surface одного bounded cluster, не увеличилось
число thin wrappers, остались зелёными drift/metrics gates, и reviewers могут
объяснить новую внутреннюю структуру without reading the whole folder. Такой
набор критериев помогает отличить реальное hotspot reduction от cosmetic
reshuffling.

Также важно помнить, что adapters не все одинаковы. В одном provider family
горячей точкой может быть pagination and fetch orchestration, в другом —
normalization envelope, в третьем — health/retry mixin stack. Значит, нельзя
готовить один универсальный refactor recipe. Лучше иметь общий протокол:
inventory, hotspot statement, proposed local ownership model, verify set, exit
criteria. А concrete transformation уже подстраивать под характер кластера. Это
не замедляет волну, а наоборот, уменьшает число неверных starts.

Ещё одна полезная практика — фиксировать “что мы сознательно не трогаем” в
каждом adapter slice. В инфраструктуре границы очень заразительны: как только
трогаешь один dense seam, рядом обнаруживается ещё три почти такие же. Если не
записать explicit non-goals, команда почти неизбежно расползётся по соседним
paths. Наличие non-goals делает bounded-cluster strategy реальной, а не
декларативной.

### Addendum к Wave 4

В complexity wave нужно различать два типа выигрыша: выигрыш для читаемости и
выигрыш для изменения поведения. На этой волне главным должен быть первый тип.
Если после split одного hotspot unit проекту стало значительно проще вносить
следующие изменения без страха сломать весь envelope, значит волна работает.
Если же выигрыш измеряется только тем, что функция стала короче, но понять,
где теперь owner logic, не проще, значит complexity лишь перераспределилась.

Очень полезно до начала каждого slice формулировать hotspot hypothesis в одной
строке. Например: “этот unit сложен не потому, что длинный, а потому что
смешивает batch planning, paging and observability envelope”. Такая гипотеза
задаёт критерий правильного разрезания. Если после рефакторинга три
ответственности всё ещё живут вместе, то даже при меньшем line count гипотеза
не закрыта. Это помогает не обманывать себя метриками.

Нужно также помнить, что complexity debt часто лучше всего уменьшается через
staged extraction, а не через сразу идеальную новую структуру. На первом шаге
достаточно выделить один helper owner или один subflow boundary, если это уже
сильно снижает cognitive load. Пытаться в одном проходе получить окончательную
идеальную modular architecture почти всегда избыточно и рисково. Эта волна
любит incremental wins, а не grand redesigns.

### Addendum к Wave 5

В facade/naming wave самой полезной практикой является explicit semantic audit
before rename. То есть перед любым предложением переименования нужно коротко
ответить: какой текущий смысл name транслирует? В чём именно drift? Это drift
против runtime role, против ownership, против public contract или против docs?
Только после этого rename имеет шанс быть содержательным. Без такого шага
любая naming cleanup легко превращается в субъективную косметику.

Отдельно стоит удерживать правило “rename only where it improves decisions”.
Если после переименования команде проще понять, куда вносить будущие изменения,
кто owner и какой слой за что отвечает, значит rename имеет operational value.
Если эффект ограничивается тем, что новое имя кажется эстетически приятнее,
лучше не трогать. Особенно дорого обходятся file-level rename-ы в местах, где
уже много внешних ссылок, docs mention-ов и mental models.

Для domain facade части волны хорошей практикой будет сопровождать изменения
небольшим narrative test: коротким абзацем “как теперь объясняется этот фасад
новому участнику”. Это звучит мягко, но реально помогает. Архитектура становится
сильнее не только когда tests зелёные, но и когда модель можно объяснить без
десятиминутного экскурса в исторические причины. Такая проверка особенно ценна
для `domain.ports` и связанных facade surfaces.

### Addendum к Wave 6

Консервативная cleanup wave почти наверняка будет психологически самой сложной.
К этому моменту у команды уже появится желание “добить хвосты”, и именно тогда
наиболее велик риск broad delete campaign. Чтобы защититься, полезно заранее
ввести жёсткий rule of admission: кандидат попадает в cleanup slice только если
по нему есть отдельная evidence note или прямое подтверждение из существующих
pack-ов, что он не является sanctioned wrapper, aggregate seam или deferred
compat path. Это rule полезно сформулировать письменно, а не держать в голове.

Для residual test/CI debt follow-up полезно не смешивать вопрос “каких тестов
не хватает” с вопросом “как лучше шардировать или оптимизировать CI”.
Первый вопрос про coverage and ownership of tests, второй — про execution
economics. Они взаимосвязаны, но не тождественны. Если свалить их в одну кучу,
появится соблазн лечить организационные проблемы тестовой инфраструктуры чисто
через новые тесты или наоборот. Лучше выделить минимум две оси анализа внутри
follow-up pillar.

И наконец, финальный closure этой волны должен оставлять после себя не
ощущение “что-то ещё почистили”, а понятное состояние: какие cleanup candidates
resolved, какие intentionally retained, какой residual debt теперь описан
отдельным evidence artifact, и что именно больше не стоит возвращать в master
backlog без нового evidence. Только так конец программы будет не размазанным,
а контролируемым.

## Closing Notes Per Wave

### Closing note for Wave 0

Wave 0 должна завершаться не ощущением “мы разобрались в бумагах”, а очень
конкретной способностью назвать один active master source для следующего шага.
Если после неё исполнители всё ещё вынуждены спрашивать, какой план “главнее”,
значит reconciliation проведена недостаточно глубоко.

### Closing note for Wave 1

Wave 1 нужно считать удачной только если после неё provider-registry cluster
становится не просто “менее дублированным”, а заметно лучше объяснимым.
Canonical path и retained compatibility path должны различаться буквально с
первого чтения, иначе structural debt просто поменял форму.

### Closing note for Wave 2

Wave 2 имеет смысл только тогда, когда composition действительно становится
более assembly-like. Если после неё число путей, через которые можно случайно
дотянуться до старого compat seam, не уменьшается, значит ownership closure
фактически не произошла.

### Closing note for Wave 3

Wave 3 должна уменьшать давление, а не только распределять строки по новым
файлам. Самый полезный post-check здесь: изменился ли practical cost следующих
локальных изменений в hotspot cluster. Если нет, значит restructuring было
скорее декоративным.

### Closing note for Wave 4

Wave 4 стоит продолжать только пока complexity evidence остаётся конкретным и
кандидаты можно защищать по одному. Как только волна превращается в абстрактную
борьбу со “сложностью вообще”, она теряет свою доказательную опору и должна
быть снова сужена.

### Closing note for Wave 5

Wave 5 нельзя мерить количеством rename-ов. Её настоящий результат — снижение
semantic drift между названием, ответственностью и архитектурной ролью. Если
rename не уменьшает этот drift, его лучше не делать.

### Closing note for Wave 6

Wave 6 — это проверка зрелости всей программы. Если команда способна закончить
её без broad delete campaign и без хаотичного добивания хвостов, значит весь
consolidated master plan действительно работал как управляемая refactor
программа, а не как набор разрозненных инициатив.
