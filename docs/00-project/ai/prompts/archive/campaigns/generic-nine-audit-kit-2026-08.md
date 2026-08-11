---
id: prompt.campaign.generic-nine-audit-kit
version: 1.0.0
status: archived
class: campaign
owner: BioETL Team
runtimes: [any]
tags: [audit, campaign, archive, generic-kit]
summary: Cleaned generic nine-domain audit kit (2026-08 intake); not default paste SSOT
related_ssot:
  - AGENTS.md
  - docs/00-project/ai/prompts/README.md
anti_patterns:
  - Using this megaprompt as default operator paste
  - Ignoring BioETL fragments and library cards
  - Writing audit artifacts to repo root
---

# Generic nine-domain audit kit (archive)

**Status:** archived campaign reference. Prefer short cards under
`library/audit/*` and `library/architecture/review-assessment.md`.

**Intake date:** 2026-08-11. Source was operator-supplied megaprompt set;
UI chrome (`Копировать`, `Показать код`) stripped; orthography «Промпт»
normalized; tables partially restored.

**BioETL note:** unknown-params defaults below are for *generic* multi-repo
use. On this repository, apply library fragments (`debt-budget-ban`,
`reports-output`, runtime discovery) and known SSOT instead of rediscovering
as «не указано».

**Citations:** `[S1]`… markers are unresolved in the source paste — see
`generic-nine-audit-kit-2026-08-SOURCES.md`.

---

Исходные допущения и единая шкала
TL;DR. Ниже — девять самостоятельных промтов для технического аудитора, LLM-агента или автоматизированного review-инструмента. Каждый промт заставляет сначала восстановить фактический контекст репозитория, явно сохранять неизвестные параметры как «не указано», собирать доказательства path:line, запускать воспроизводимые проверки, оценивать качество и приоритет, а затем выдавать машинно-обрабатываемые артефакты. В основу заложены актуальные на август 2026 года официальные рекомендации GitHub Actions, Git/GitHub, pytest/Jest/Playwright, Mermaid, C4, arc42, Diátaxis, Google и Microsoft по технической документации. 

Параметры, которые не следует выдумывать до анализа репозитория:

Параметр	Исходное значение
Стек технологий	не указано
Основной язык/языки	не указано
Размер репозитория	не указано
Тип репозитория: mono/polyrepo	не указано
CI-платформа, кроме явно проверяемого GitHub Actions	не указано
Требования к покрытию тестов	не указано
Поддерживаемые runtime/OS/browser versions	не указано
SLA/SLO	не указано
Threat model	не указано
Compliance/regulatory requirements	не указано
Deployment topology	не указано
Допустимый technical-debt budget	не указано

Единая шкала, которую можно применять внутри каждого промта:

Оценка	Качество / приемлемость	Интерпретация
3	хорошо	Проверка воспроизводима; существенные риски закрыты; автоматизация присутствует
2	приемлемо	Основной механизм корректен; имеются локальные непринципиальные пробелы
1	слабо	Есть существенные пробелы, ручные этапы, drift или слабое enforcement
0	неприемлемо	Механизм отсутствует, системно сломан либо создаёт непосредственный риск

Приоритет	Значение	Типичный критерий
P0	блокирующий	Компрометация, потеря данных, RCE, утечка secrets, опасный deploy, критически неверная инструкция
P1	высокий	Высокая вероятность дефекта/инцидента, нарушение release integrity, критический сценарий без контроля
P2	средний	Существенная стоимость сопровождения, нестабильность, архитектурный/documentation drift
P3	низкий	Локальная гигиена, удобство, форматирование, малорисковая оптимизация

Каждая находка должна по возможности иметь форму: ID → path:line → наблюдение → команда/метод проверки → ожидаемое состояние → фактическое состояние → влияние → confidence → score 0–3 → P0–P3 → remediation → automation.

Готовые файлы с девятью промтами: Markdown, DOCX, PDF.

Качество проектных материалов
Промпт 1 — Документация проекта

Executive summary. Проведи доказательный аудит документации как интерфейса между кодовой базой, разработчиками, эксплуатацией и пользователями. Определи не количество Markdown-файлов, а полноту, актуальность, внутреннюю непротиворечивость и воспроизводимость описанных процедур. Любое утверждение документации о команде, пути, конфигурации, API, версии или deployment-процессе по возможности перепроверь по исходному коду и конфигурации.

Контекст. Стек технологий — не указано. Размер репозитория — не указано. CI-платформа — не указано. Формальные требования к документации, язык документации, аудитории и политика versioning — не указано. Сначала установи факты из репозитория; отсутствие данных не заменяй предположениями.

Начни с полного inventory: README*, docs/**, CONTRIBUTING*, SECURITY*, SUPPORT*, CHANGELOG*, LICENSE*, CODE_OF_CONDUCT*, ADR/architecture decisions, API/OpenAPI/GraphQL schemas, runbooks, deployment/operations instructions, diagrams, onboarding, troubleshooting и release documentation. GitHub рассматривает README вместе с contribution guidelines и другими community-health файлами как основные средства объяснения назначения проекта и ожиданий от участников [S1]. 

Для каждого документа зафиксируй: аудиторию; назначение; источник истины; связанный модуль; владельца, если определён; last meaningful change; входящие/исходящие ссылки; наличие generated sections. Оцени информационную архитектуру через категории Diátaxis: tutorial, how-to, reference, explanation; Diátaxis намеренно разделяет эти четыре типа по потребностям пользователя [S2]. 
 При оценке языка и структуры используй проектный style guide первым, а при его отсутствии — рекомендации Google Developer Documentation Style Guide или Microsoft Writing Style Guide, ориентированные на ясную и последовательную техническую документацию [S3]. 

Контрольные вопросы и чек-лист. Проверь: [ ] понятно ли из README назначение проекта; [ ] существует ли подтверждённый bootstrap; [ ] совпадают ли install/build/test/run/lint команды с manifests; [ ] описаны ли обязательные environment variables; [ ] ссылки и относительные пути разрешаются; [ ] версии runtime не устарели относительно CI; [ ] API reference согласован с кодом/schema; [ ] contribution/security procedures существуют там, где они нужны; [ ] deployment/runbook не содержит опасных или устаревших действий; [ ] архитектурные решения имеют rationale; [ ] нет ли двух документов, дающих несовместимые инструкции; [ ] все TODO/TBD в operational/security документации имеют owner или issue.

Примеры проверок:

bash

git ls-files |
  rg -i '(^|/)(readme|contributing|security|support|changelog|code_of_conduct|license|adr|docs)(\.|/|$)'

rg -n -i '\b(TODO|FIXME|TBD|OUTDATED|DEPRECATED|LEGACY)\b' \
  --glob '*.md' --glob '*.mdx' --glob '*.rst' --glob '*.adoc'

rg -n '\[[^]]+\]\([^)]+\)' --glob '*.md' --glob '*.mdx'

rg -n -i '(npm|pnpm|yarn|pip|poetry|uv|pytest|cargo|go test|mvn|gradle|docker|make) ' \
  README* docs/ 2>/dev/null
Проверяй относительные ссылки с учётом правил GitHub Markdown: GitHub поддерживает относительные ссылки между файлами репозитория, что позволяет избегать хрупких абсолютных URL внутри документации [S4]. 

Критерии оценки.

Балл	Критерий
3	Критические пользовательские и инженерные сценарии описаны; команды проверены; links/build docs контролируются автоматически
2	Основной путь корректен; имеются отдельные stale/недостающие разделы
1	Документация существенно расходится с кодом либо большая часть проверок ручная
0	Критические инструкции отсутствуют, невоспроизводимы или опасно ошибочны

P0 назначай за инструкции, способные привести к компрометации, потере данных или разрушительному production-действию; P1 — за неправильные bootstrap/deploy/security/recovery процедуры; P2 — за большие gaps и drift; P3 — за редакционные и навигационные проблемы.

Ожидаемые артефакты: docs-audit.md, docs-inventory.csv, broken-links.json, stale-docs.csv, docs-code-drift.csv, карта документации, топ remediation items и конкретные proposed patches. В CSV минимум: path,type,audience,owner,last_change,status,score,priority,evidence.

Автоматизация: markdown/content lint; link checker; проверка generated reference; executable code examples; CI job, который проверяет documentation build; правило, что изменение публичного API/configuration требует соответствующего docs diff или явного exemption.

Inventory документации

Сопоставление с кодом и config

Проверка команд и ссылок

Поиск gaps и drift

Оценка 0-3 и P0-P3

Отчёт и CI-контроли




Промпт 2 — Тесты проекта

Executive summary. Проведи аудит тестовой системы как механизма обнаружения регрессий, а не как формальную проверку количества тестов или одной метрики coverage. Определи, какие продуктовые и технические риски реально проверяются, насколько тесты изолированы и воспроизводимы, где есть flaky/disabled tests и какие требования CI фактически блокируют merge/release. Не устанавливай произвольный целевой coverage, если проект его не определяет.

Контекст. Стек — не указано. Тестовый framework — не указано. Требования к coverage — не указано. Поддерживаемые платформы/runtime/browser versions — не указано. CI-платформа — не указано. Сначала найди manifests и конфигурацию: pyproject.toml, pytest.ini, package.json, Jest/Vitest/Playwright config, go.mod, Cargo.toml, Maven/Gradle, .csproj, Makefile, Bazel и CI workflow.

Инвентаризируй unit, integration, contract, API, e2e, smoke, migration, security и performance tests. Зафиксируй, какие уровни существуют фактически, а какие отсутствуют. Найди skip, xfail, .only, todo, quarantine, retries, shared fixtures и глобальное состояние. pytest отдельно документирует организацию тестов, fixtures и integration practices [S1], Jest может собирать coverage и принудительно применять coverageThreshold, если проект его задал [S2], а Playwright рекомендует независимые тесты и предоставляет retries, parallelism, traces и CI-oriented controls [S3]. 

Не считай retry исправлением flaky test. Используй retry как диагностический сигнал; Playwright прямо определяет retries как повторный запуск упавшего теста, а исследования Google по собственным test suites связывают крупные/сложные тесты с повышенной flakiness и подчёркивают потерю доверия к нестабильному suite [S4]. 

Контрольные вопросы. [ ] Запускаются ли tests из clean checkout? [ ] Есть ли single canonical command? [ ] Изолированы ли test data/temp dirs/ports? [ ] Не зависят ли unit tests от внешней сети? [ ] Тестируются ли negative/error paths? [ ] Покрыты ли authentication/authorization boundaries? [ ] Проверяются ли schema migrations? [ ] Есть ли contract tests для внешних API? [ ] Можно ли запустить один тест? [ ] Есть ли детерминированное управление time/randomness? [ ] Публикуются ли JUnit/coverage/traces? [ ] Есть ли timeout? [ ] Запрещён ли accidentally committed .only? [ ] Не маскирует ли quarantine многолетние дефекты?

Примеры:

bash

git ls-files |
  rg -i '(^|/)(test|tests|spec|specs|e2e|integration|fixtures)(/|$)|(\.test\.|\.spec\.)'

rg -n -i '(skip|xfail|todo|quarantine|flaky|\.only\b|@disabled|@ignore)' \
  --glob '!vendor/**' --glob '!node_modules/**'

rg -n -i '(coverage|cov|threshold|fail-under|coverageThreshold)' .

# Выполняй только после подтверждения соответствующего стека:
pytest -q
pytest --cov --cov-report=term-missing
npm test -- --coverage
go test ./...
cargo test
При обнаружении подозрения на flaky test повтори конкретный тестовый набор в контролируемой среде и укажи число попыток, а не просто поставь ярлык flaky.

Пример CI-gate после адаптации к стеку:

yaml

- name: Test
  run: ./scripts/test
- name: Ensure no focused tests
  run: |
    ! rg -n '\.only\(' tests src
Критерии оценки.

Балл	Критерий
3	Критические paths покрыты; tests изолированы и стабильны; CI реально блокирует нарушения
2	Хорошая основа; есть локальные gaps или ограниченная observability
1	Существенные flaky/disabled зоны, слабая изоляция либо необязательный CI
0	Tests системно не работают, отсутствуют на критическом пути или зелёный CI не отражает реальность

P0 — механизм позволяет заведомо небезопасный/невалидный release; P1 — критический business/security path без проверки; P2 — flaky/performance/diagnostic debt; P3 — organization/convenience.

Ожидаемые артефакты: test-audit.md, test-matrix.csv, coverage-evidence.json, flaky-tests.csv, disabled-tests.csv, critical-gap-map.md, CI recommendations. У каждого gap должен быть не только отсутствующий test, но и соответствующий production risk.

Автоматизация: запрет focused tests; JUnit/coverage/traces as artifacts; scheduled repeated flaky detection; quarantine только с owner и expiry; test sharding для достаточно больших suites; быстрый presubmit и дорогие проверки отдельно.

Определить test stack

Inventory уровней

Clean run

Повтор и flakiness

Coverage рисков

CI enforcement

Приоритетный test plan




Промпт 3 — Технический долг

Executive summary. Построй доказательный реестр технического долга, связывающий конкретные признаки в коде с риском, стоимостью изменения и предлагаемой последовательностью погашения. Не называй техническим долгом любое стилистическое несовершенство: отделяй осознанные компромиссы, исторические ограничения, maintainability debt, obsolete dependencies, тестовый долг и архитектурный drift. Приоритизация должна учитывать вероятность проблемы и blast radius, а не количество TODO.

Контекст. Стек — не указано. Возраст системы — не указано. Roadmap — не указано. SLA/SLO — не указано. Maintainability targets и допустимый debt budget — не указано.

Найди явные маркеры TODO, FIXME, HACK, XXX, WORKAROUND, TEMP, deprecated API, lint/type/test suppressions, compatibility layers, отключённые checks, копипасту configuration, ручные release steps, old migrations, dead feature flags, циклические dependencies, excessively large modules и инфраструктурные workaround. arc42 рекомендует включать известные риски и technical debt вместе с предлагаемыми мерами уменьшения/устранения [S1]. 

Если репозиторий использует SonarQube, собирай его maintainability/technical-debt metrics и Quality Gate как дополнительный сигнал. Sonar определяет technical debt через remediation effort для maintainability issues и позволяет использовать такие метрики в quality gates; сам gate представляет набор условий, проверяемых при анализе кода [S2]. 
 Не подменяй этим архитектурный анализ.

Команды:

bash

rg -n -i '\b(TODO|FIXME|HACK|XXX|WORKAROUND|TEMP|DEPRECATED)\b' \
  --glob '!vendor/**' --glob '!node_modules/**'

rg -n -i \
  '(noqa|nolint|eslint-disable|ts-ignore|type:\s*ignore|pragma: no cover|noinspection)' .

git log --oneline --all \
  --grep='debt\|refactor\|workaround\|temporary' -i

git ls-files -z |
  xargs -0 -r wc -l |
  sort -n |
  tail -50
Для наиболее важных записей исследуй history/blame: один вчерашний TODO и workaround, переживший четыре года и 80 изменений, имеют разный риск.

Контрольные вопросы. [ ] Почему возник долг? [ ] Есть ли owner? [ ] Что мешает удалить workaround сегодня? [ ] Какой affected surface? [ ] Как часто изменяется код? [ ] Какие tests защищают рефакторинг? [ ] Есть ли dependency/version deadline? [ ] Блокирует ли долг security patch или новый feature? [ ] Есть ли architectural boundary violation? [ ] Можно ли исправить локально, или нужен migration plan? [ ] Какова приблизительная стоимость исправления диапазоном, а не псевдоточной цифрой?

Классифицируй debt, например: code, tests, dependencies, architecture, data/schema, CI, observability, documentation, security, operational.

Критерии оценки.

Балл	Состояние
3	Долг идентифицирован, owner/риск/effort известны; новый код не ухудшает базовую линию
2	Основной долг контролируется, часть записей неформализована
1	Debt проявляется через suppressions и workaround без системного управления
0	Критические накопленные проблемы игнорируются или делают изменения небезопасными

P0 — security, data integrity, release correctness; P1 — высокая вероятность incident/feature blockade; P2 — существенная cost-of-change; P3 — локальный cleanup.

Ожидаемые артефакты: technical-debt-register.csv с минимум id,path,line,type,evidence,age,risk,blast_radius,effort,owner,priority; debt-heatmap.md; top-20 risk-adjusted items; quick wins; strategic debt; dependency debt; suppressions report.

Автоматизация: baseline для нового кода; Quality Gate там, где используется соответствующий анализатор; запрет новых необоснованных suppressions; dependency update bots; scheduled debt trend; policy, требующая issue/reference для долгоживущих TODO/FIXME.

Репозиторий и CI
Промпт 4 — Файловая структура и гигиена корня

Executive summary. Проведи аудит дерева репозитория с целью уменьшить неоднозначность, accidental artifacts, generated noise, large files и конфигурационный drift. Не навязывай универсальную «идеальную» файловую структуру: оцени, насколько текущее дерево выражает реальные architectural/build/test boundaries и позволяет новому разработчику или агенту найти canonical files без догадок. Особый приоритет отдай secrets, binaries и generated content, ошибочно попавшим под version control.

Контекст. Стек — не указано. Mono/polyrepo — не указано. Исторические ограничения структуры — не указано. Generated-file policy — не указано.

Сними inventory корня и первых нескольких уровней. Классифицируй элементы как source, test, docs, scripts, config, infra, vendor, generated, build, cache, temporary, binary, unknown. Установи, зачем каждый root-level file находится именно в корне. Проверь .gitignore, .gitattributes, .editorconfig, lockfiles, manifests, README, license/community-health files, .env.example, tool-version files.

Git определяет .gitignore как механизм игнорирования намеренно неотслеживаемых файлов; уже tracked files правила .gitignore автоматически не перестают отслеживать [S1]. 
 GitHub рекомендует коммитить repository-specific .gitignore, чтобы правила разделялись всеми клонами [S2]. 
 Для крупных binary assets учти ограничения GitHub и возможность Git LFS; GitHub выдаёт warning для файлов свыше 50 MiB и отдельно документирует Git LFS [S3]. 

Команды:

bash

# Что лежит непосредственно в корне
git ls-files | awk -F/ 'NF==1 {print}' | sort

# Быстрый снимок первых уровней
git ls-files | awk -F/ 'NF<=3 {print}' | sort | head -500

# Игнорируемые/неотслеживаемые объекты
git status --ignored --short

# Только DRY-RUN: ничего не удалять
git clean -ndX

# Крупнейшие tracked files
git ls-files -z |
  xargs -0 -r du -h |
  sort -h |
  tail -40

# Потенциальные credentials: сигнал, не доказательство
rg -n -i \
  '(password|secret|token|api[_-]?key|private[_-]?key)\s*[:=]' \
  --glob '!*.lock'
git clean -n принципиально используй в audit mode: сам git clean способен удалять untracked files, тогда как -n позволяет предварительный просмотр [S4]. 

Контрольные вопросы. [ ] Root содержит только глобально значимые files? [ ] Есть ли duplicate manifests/config? [ ] Не закоммичены ли dist, build, coverage, caches, IDE metadata? [ ] Generated assets отличимы от authored? [ ] Есть ли огромные JSON/dumps/logs? [ ] Есть ли secrets/history problem? [ ] Согласована ли структура source с архитектурными building blocks? arc42 отдельно рекомендует стремиться к понятному mapping между source directories и architecture building blocks [S5]. 
 [ ] Нет ли нескольких конкурирующих bootstrap scripts? [ ] Однозначно ли расположены tests/docs/scripts/infra? [ ] Не используются ли filenames вроде temp2, old, final-final?

Критерии оценки.

Балл	Состояние
3	Root минимален; generated/cache исключены; структура отражает реальные boundaries
2	Есть небольшой historical clutter без существенного влияния
1	Значительный шум, duplication, смешение source/generated или неясные ownership boundaries
0	Secrets, опасные binaries, неконтролируемые generated files либо структура ломает reproducibility

P0 — secrets/private keys/опасные данные; P1 — artifacts, влияющие на supply chain/build correctness; P2 — structural ambiguity; P3 — cosmetic cleanup.

Ожидаемые артефакты: repo-tree-audit.md, root-inventory.csv, large-files.csv, ignore-gaps.txt, generated-files.csv, current-vs-target-tree.md. Не предлагай массовое перемещение директорий без измеримой выгоды и migration plan.

Автоматизация: secret scanning; file-size rules; checks на известные build/cache patterns; pre-commit hooks; clean-build CI; .gitattributes для generated assets — GitHub поддерживает linguist-generated для маркировки generated paths [S6]. 

Промпт 5 — GitHub Actions

Executive summary. Проведи аудит .github/workflows как исполняемой части software supply chain и security boundary. Вначале оцени trust model: события, токены, secrets, third-party actions и runners; затем correctness, reproducibility, performance, caching, artifact lifecycle и reuse. Любая рекомендация по оптимизации вторична по отношению к безопасности credential и integrity release.

Контекст. Общая CI-платформа проекта — не указано. Однако если .github/workflows существует, GitHub Actions является непосредственно проверяемой частью CI/CD. Production environments, self-hosted runners, branch protection и cloud provider — не указано, пока они не установлены.

Инвентаризируй:

workflow → trigger → path/branch filters → permissions → jobs → runner → environment → dependencies/actions → cache → artifacts → secrets/OIDC → deployment.

GitHub хранит workflow YAML в .github/workflows и поддерживает push, pull_request, schedules, workflow_call, matrix, permissions и concurrency [S1]. 

Безопасность проверяй особенно строго. GitHub рекомендует выдавать GITHUB_TOKEN минимально необходимые permissions и, как безопасную базу, ограничивать default access чтением содержимого, повышая права лишь там, где это действительно нужно [S2]. 
 Для сторонних actions полный commit SHA является наиболее жёсткой формой immutable pinning; официальный Secure Use Reference прямо указывает full-length SHA как способ immutable reference и предупреждает о рисках movable tags [S3]. 

Команды:

bash

git ls-files '.github/workflows/*.yml' '.github/workflows/*.yaml'

rg -n \
  'pull_request_target|workflow_run|permissions:|write-all|id-token:|secrets:|runs-on:' \
  .github/workflows

rg -n \
  'uses:\s+[^ ]+@(main|master|v[0-9]+|latest)\b' \
  .github/workflows

rg -n '\$\{\{\s*github\.event\..*\}\}' .github/workflows

rg -n \
  'curl .*\| *(bash|sh)|wget .*\| *(bash|sh)|sudo |eval ' \
  .github/workflows
Не считай найденную interpolation автоматически уязвимой. Проверь, попадает ли untrusted context непосредственно в generated shell. GitHub рекомендует не вставлять untrusted expression прямо в inline shell и, если inline script необходим, сначала передавать значение через environment variable [S4]. 

Проверь: [ ] pull_request_target действительно необходим; [ ] untrusted PR code не выполняется в привилегированном context; [ ] permissions минимальны; [ ] secrets не печатаются; [ ] third-party actions pinned; [ ] self-hosted runners изолированы; [ ] deploy использует environment protections; [ ] cloud auth по возможности использует OIDC вместо долгоживущих credentials — GitHub документирует OIDC как способ доступа к cloud provider без хранения долгоживущих cloud secrets [S5]; 
 [ ] присутствуют timeout/concurrency; [ ] cache key связан с lockfile/runtime; [ ] cache не используется как единственный источник обязательных файлов; GitHub отдельно подчёркивает, что job должен уметь восстановиться при cache miss [S6]; 
 [ ] artifact retention разумен; GitHub позволяет задавать retention-days [S7]; 
 [ ] matrix соответствует поддерживаемым версиям; [ ] copy-paste workflows могут быть reusable через workflow_call [S8]. 

Пример минимальной базы:

yaml

permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
Concurrency groups позволяют ограничить одновременно выполняющиеся jobs/workflows с одинаковым ключом [S9]. 
 Для production deploy не копируй cancel-in-progress: true автоматически: проверь semantics deployment.

Критерии оценки.

Балл	Состояние
3	Least privilege, безопасные triggers, pinned dependencies, воспроизводимый CI, контролируемые artifacts/deploy
2	Безопасная база с несколькими локальными пробелами
1	Broad permissions, unpinned actions, duplication, слабый timeout/cache policy
0	Exploitable trust boundary, credential leakage, unsafe privileged PR execution или небезопасный deploy

P0 — credential/supply-chain/RCE; P1 — release integrity; P2 — CI reliability/cost; P3 — YAML hygiene.

Ожидаемые артефакты: actions-audit.md, workflow-matrix.csv, permissions-matrix.csv, third-party-actions.csv, trigger-risk.csv, cache-artifact-policy.csv, concrete YAML patches.

Автоматизация: SHA-pinning policy; explicit permissions; dependency review — GitHub dependency review показывает изменения dependencies в PR и может использоваться как enforcement action [S10]; 
 CodeQL/code scanning там, где применимо [S11]; 
 reusable workflows; workflow lint; Dependabot; scheduled security review.

Workflows inventory

Triggers и trust boundary

Permissions и secrets

Actions, runners, dependencies

Correctness, cache, artifacts

Deploy и environments

Risk score + patches




Скрипты, агенты, диаграммы и документационный pipeline
Промпт 6 — Работа с агентами в проекте, включая scripts

Executive summary. Проведи аудит repository-level инструкций и scripts, предназначенных для AI coding/review agents или автоматизированного выполнения инженерных задач. Главные критерии: правильное понимание project context, минимально необходимые полномочия, воспроизводимый bootstrap/build/test, отсутствие конфликтующих инструкций и безопасное выполнение shell/tool operations. Не привязывай аудит к конкретному AI provider, пока используемый механизм не установлен из репозитория.

Контекст. Агентная платформа — не указано. Использование GitHub Copilot — не указано. Наличие иных агентных инструментов — не указано. Требуемый permission model — не указано.

Выполни discovery:

bash

git ls-files |
  rg '(^|/)(AGENTS\.md|CLAUDE\.md|GEMINI\.md|SKILL\.md|\.github/(copilot-instructions\.md|instructions/.*\.instructions\.md|agents/.*\.agent\.md))$'

git ls-files scripts/ |
  rg -i '(agent|bootstrap|setup|validate|check|review|docs|diagram|release|deploy)'

rg -n -i \
  '(rm\s+-rf|sudo\b|eval\b|curl .*\| *(sh|bash)|env\b|printenv\b|set -x|chmod 777)' \
  scripts/ .github/ 2>/dev/null

rg -n -i \
  '(token|secret|password|api[_-]?key|private[_-]?key)' \
  scripts/ .github/ 2>/dev/null
Если обнаружен GitHub Copilot customization, учти фактическую модель 2026 года: GitHub поддерживает repository-wide .github/copilot-instructions.md, path-specific .github/instructions/**/*.instructions.md и AGENTS.md; для AGENTS.md ближайший файл в directory tree имеет приоритет в соответствующем контексте [S1]. 
 Custom agents могут быть описаны в .github/agents/*.agent.md с frontmatter, определяющим в том числе доступные tools [S2]. 
 Agent skills могут включать SKILL.md и дополнительные scripts/resources [S3]. 

Не требуй эти форматы, если данный provider не используется. Для любого агентного механизма построи instruction scope graph: root instructions → path-specific instructions → agent profile → skills → scripts → CI validation. Ищи противоречия: одна инструкция говорит npm test, другая pnpm test; разные Node/Python versions; один agent может deploy, хотя его роль — read-only review.

GitHub в собственном onboarding prompt для cloud agent рекомендует документировать bootstrap/build/test/run/lint, версии инструментов, структуру проекта и реально проверять команды, включая clean environment [S4]. 
 Используй это как критерий и для provider-neutral audit.

Контрольные вопросы. [ ] Может ли агент понять назначение репозитория без полного blind scan? [ ] Указана ли canonical build/test command? [ ] Проверены ли команды фактически? [ ] Есть ли working-directory assumptions? [ ] Scripts идемпотентны? [ ] Есть ли dry-run для write/destructive операций? [ ] Разделены ли audit/read и deploy/write capabilities? [ ] Ограничены ли tools? [ ] Не передаются ли secrets через stdout/CLI args? [ ] Ошибки дают non-zero exit? [ ] Есть ли timeout? [ ] Формат output пригоден для машинного чтения? [ ] Нет ли curl|bash, eval, unquoted inputs и неконтролируемого rm -rf?

Для shell scripts отдельно проверь поведение при unset variables, whitespace/globs и partial failure. Не исправляй автоматически destructive script до понимания его contract.

Пример безопасного wrapper pattern:

bash

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

./scripts/lint
./scripts/test
Критерии оценки.

Балл	Состояние
3	Инструкции непротиворечивы; scripts воспроизводимы; tools ограничены; validation automated
2	Основной workflow надёжен, но есть небольшие undocumented preconditions
1	Неявные environment assumptions, чрезмерные permissions или inconsistent instructions
0	Агент способен раскрыть secret, разрушить данные или выполнить неконтролируемый privileged action

P0 — destructive/secret/RCE; P1 — ошибочный build/release/deploy; P2 — nondeterminism/maintenance; P3 — discoverability/style.

Ожидаемые артефакты: agent-audit.md, agent-instruction-map.md, agent-scripts.csv, tool-permissions.csv, instruction-conflicts.csv, validated command matrix, specific remediation patches.

Автоматизация: frontmatter/schema lint; smoke-run agent scripts в disposable environment; security grep/policy; contract snapshots; test bootstrap → lint → test from clean checkout; diff-based validation path-specific instructions.

Discover instructions и scripts

Resolve scopes

Сопоставить команды с project tooling

Security и permission audit

Clean-environment smoke test

Contract + CI policy




Промпт 7 — Работа с диаграммами в проекте, включая scripts

Executive summary. Проведи аудит архитектурных и технических диаграмм как version-controlled engineering artifacts. Определи canonical source каждой диаграммы, возможность воспроизводимого rendering, соответствие фактическому коду/infrastructure и состояние scripts/CI, которые их строят. Изображение, которое красиво рендерится, но противоречит реальной архитектуре, оценивай хуже, чем минималистичную, но актуальную text-as-code диаграмму.

Контекст. Diagramming tool — не указано. Использование Mermaid/C4/PlantUML/Graphviz/Structurizr — не указано. Политика хранения generated PNG/SVG — не указано.

Discovery:

bash

git ls-files |
  rg -i '\.(mmd|puml|plantuml|dot|drawio|svg|png|webp)$'

rg -n \
  '^```mermaid|sequenceDiagram|flowchart|architecture-beta|C4Context|C4Container' \
  --glob '*.md' --glob '*.mdx' --glob '*.mmd'

git ls-files scripts/ |
  rg -i '(diagram|mermaid|plantuml|graphviz|c4|structurizr)'
Классифицируй диаграммы: system context, container/service, component/module, runtime/sequence, deployment, data model, state, CI/CD flow. Для каждой запиши source, generated output, renderer/version, owner, scope, последний meaningful update, linked docs.

Mermaid использует текстовый синтаксис для диаграмм и поддерживает flowchart, sequence, architecture и другие типы [S1]. 
 Официальная документация Mermaid перенаправляет CLI-раздел к проекту Mermaid CLI [S2]. 
 Если Mermaid CLI уже принят проектом, пример smoke-render:

bash

npx -y @mermaid-js/mermaid-cli \
  -i docs/architecture/system-context.mmd \
  -o /tmp/system-context.svg
Не вводи npx -y в production CI без учёта dependency pinning. Предпочитай версию CLI, зафиксированную lockfile/project tooling.

Для architecture diagrams используй C4 как модель zoom levels, а не как обязательную религию. C4 определяет четыре основных уровня — system context, container, component, code — и отдельно отмечает, что context/container обычно достаточно для большинства команд, а code diagram часто не нужен как долгоживущая документация [S3]. 

Контрольные вопросы. [ ] Есть ли editable text/source? [ ] Можно ли render с нуля? [ ] Renderer pinned? [ ] Fail приводит к non-zero exit? [ ] Generated output отличается от source-controlled image? [ ] Изменение архитектуры требует обновления диаграммы? [ ] Имена services совпадают с manifests/deploy? [ ] Внешние системы и data stores видны? [ ] Направление protocol/data flow корректно? [ ] Есть ли legend/context? [ ] Не содержит ли диаграмма secrets/internal endpoints, которые не должны публиковаться?

Пример generated-drift проверки выполняй только в чистом CI workspace:

bash

./scripts/render-diagrams
git diff --exit-code -- docs/
Если project policy не коммитит generated images, проверяй rendering в temporary output, а не требуй git diff.

Критерии оценки.

Балл	Состояние
3	Text/source under version control, deterministic render, CI validation, модель соответствует системе
2	Диаграммы актуальны, но часть regeneration/manual review не автоматизирована
1	Binary-only diagrams, unclear source или регулярный drift
0	Ключевая диаграмма фактически неверна и способна вести к ошибочному security/deployment решению

P0 — ошибочная security/deployment model с operational consequence; P1 — неверная ключевая architecture dependency; P2 — stale runtime/component diagrams; P3 — layout/style.

Ожидаемые артефакты: diagram-audit.md, diagram-inventory.csv, render-failures.txt, diagram-code-drift.csv, canonical-source map, stale diagrams list.

Автоматизация: render-all gate; renderer version pinning; source/output drift check; link check; architecture dependency comparison; PR preview artifacts.

Inventory diagram sources

Render

Source/output drift

Сверка с code/infra

Risk scoring

CI render gate




Промпт 8 — Работа с документацией проекта, включая scripts

Executive summary. Проведи отдельный аудит scripts и pipelines, которые генерируют, проверяют, собирают, синхронизируют или публикуют документацию. Цель — доказать цепочку source-of-truth → generator → validation → artifact → publication, исключить скрытые локальные зависимости и обнаружить generated documentation drift. Особо проверь API reference и code examples: автоматически созданная документация не является корректной лишь потому, что generator завершился с кодом 0.

Контекст. Documentation stack — не указано. Использование Sphinx/MkDocs/Docusaurus/TypeDoc/Javadoc/rustdoc/OpenAPI — не указано. Publication platform — не указано. CI — не указано.

Выполни discovery:

bash

git ls-files scripts/ |
  rg -i '(doc|readme|openapi|swagger|mkdocs|sphinx|typedoc|javadoc|docgen|link)'

rg -n -i \
  '(docs|docgen|openapi|swagger|mkdocs|sphinx|typedoc|javadoc|linkcheck)' \
  package.json pyproject.toml Makefile* .github/workflows/* 2>/dev/null

rg -n -i \
  '(curl|wget|http://|https://|TOKEN|SECRET|PASSWORD)' \
  scripts/ 2>/dev/null
Построй pipeline map. Например:

OpenAPI schema → generator → reference markdown → static-site builder → link checker → preview artifact → publication.

Для каждого шага установи: executable/entrypoint; package/version; inputs; outputs; environment variables; network dependencies; cache; failure semantics; кто вызывает script локально и в CI. Если generated files коммитятся, определи, является ли source-of-truth исходная schema/code или generated Markdown.

Содержательную структуру docs оценивай отдельно от генератора. Diátaxis различает tutorial/how-to/reference/explanation [S1], а reference documentation должна быть ориентирована на точное и упорядоченное описание технического интерфейса [S2]. 
 Google Style Guide подчёркивает ясность и последовательность developer documentation, а процедуры рекомендует оформлять как явную последовательность действий [S3]. 

Контрольные вопросы. [ ] Существует ли one-command docs build? [ ] Работает ли он from clean checkout? [ ] Tool versions pinned? [ ] Выход детерминирован? [ ] Generator failure не проглатывается? [ ] API reference отражает фактический public API? [ ] OpenAPI generated из canonical schema? [ ] Code examples компилируются/тестируются? [ ] Link checker охватывает internal relative links? [ ] Publication не требует hidden developer-local state? [ ] Secret не попадает в generated pages/logs? [ ] Docs preview строится для PR? [ ] Generated timestamps/random IDs не создают бессмысленный diff?

Clean-workspace pattern:

bash

git status --porcelain

./scripts/docs-build
./scripts/docs-check

# Только если generated docs намеренно tracked:
git diff --exit-code -- docs/
Если docs output untracked/by-design, рендери в temporary directory и валидируй artifact там.

Для README/reference links учитывай GitHub relative-link behavior [S4]. 

Критерии оценки.

Балл	Состояние
3	One-command clean build; pinned toolchain; deterministic output; links/API/examples проверяются CI
2	Pipeline воспроизводим, но отдельные semantic checks ручные
1	Hidden preconditions, drift generated docs или непредсказуемая публикация
0	Docs build системно сломан, раскрывает secrets либо публикует опасно неверный материал

P0 — secret leakage или неверная production/security procedure; P1 — stale API/contracts published as current; P2 — nondeterministic build/broken links; P3 — style/format.

Ожидаемые артефакты: docs-scripts-audit.md, docs-pipeline.csv, generated-files.csv, docs-build.log, link-report.json, source-of-truth-map.md, remediation commands.

Автоматизация: canonical docs:check; clean build; executable snippets; generated diff gate; link check; preview artifact; schema/reference consistency test; dependency caching только как ускорение, а не correctness requirement.

Sources

Generation scripts

Docs build

Links API examples validation

Drift check

Preview

Publish




Архитектура проекта
Промпт 9 — Архитектура проекта

Executive summary. Восстанови фактическую архитектуру из codebase, manifests, infrastructure, CI, configuration и runtime relationships, а затем сравни её с заявленной архитектурой. Итог не должен быть каталогом директорий: покажи systems, deployable units, major components, interfaces, data stores, dependency direction, runtime scenarios, architectural decisions и quality risks. Везде отделяй доказанный факт от вывода и архитектурной гипотезы.

Контекст. Architecture style — не указано. Stack — не указано. Deployment topology — не указано. SLA/SLO — не указано. Threat model — не указано. Quality attributes и formal architecture constraints — не указано.

Начни снизу вверх. Определи:

software systems → deployable units/containers → modules/components → public interfaces → data stores/queues → external systems → infrastructure.

C4 использует иерархию system context → container → component → code, причём container diagram показывает high-level shape системы, major technology choices и способы коммуникации между deployable/runtime units [S1]. 
 Не интерпретируй C4 «container» автоматически как Docker container: сначала установи конкретный deployment/runtime unit.

arc42 предлагает complementary architecture structure: goals/constraints, context, solution strategy, building blocks, runtime, deployment, cross-cutting concepts, decisions, quality requirements, risks/debt [S2]. 
 Building Block View в arc42 описывает статическую декомпозицию и зависимости, а Runtime View — поведение и взаимодействия в важных сценариях [S3]. 

Первичный discovery:

bash

git ls-files |
  awk -F/ 'NF>1 {print $1}' |
  sort |
  uniq -c |
  sort -nr

rg -n -i \
  '(http://|https://|grpc|kafka|rabbit|redis|postgres|mysql|mongodb|s3|queue|topic|webhook)' \
  --glob '!*.lock'

rg -n -i \
  '(Dockerfile|compose|kubernetes|helm|terraform|pulumi|serverless)' .

rg -n -i \
  '(ADR|decision|architecture|design|trade-?off|rationale)' \
  docs/ .github/ README* 2>/dev/null
После определения языка не ограничивайся regex: используй language-native dependency tooling для import/module graph, cycles и package boundaries. Зафиксируй точную использованную команду и версию.

Анализ boundaries. Проверь dependency direction, cycles, shared state, direct cross-layer imports, database ownership, bypass публичных interfaces, скрытые filesystem/network contracts, duplicated domain models, feature flags, background jobs, schema migrations и vendor coupling. При микросервисах отдельно оцени наличие shared database, synchronous call chains и failure propagation; при монолите — module boundaries и внутренние API. Не называй distributed system «лучше» монолита или наоборот без quality requirements.

Runtime scenarios. Восстанови минимум: startup; основной business transaction; authentication/authorization flow; асинхронный/background processing; external integration; failure/retry path; schema migration; deploy/rollback. arc42 прямо включает important use cases, external-interface interactions, operational startup/shutdown и error scenarios в Runtime View [S4]. 

Architecture-documentation drift. Сопоставь diagrams и ADR с manifests/code. Для каждого элемента диаграммы найди real implementation path; для каждого крупного deployable unit проверь наличие в architecture view. arc42 рекомендует понятное mapping source code к building blocks и явно указывать location соответствующего source [S5]. 

Контрольные вопросы. [ ] Где system boundary? [ ] Какие external actors/systems? [ ] Какие deployable units? [ ] Кто владеет данными? [ ] Какие protocols? [ ] Где trust boundaries? [ ] Какие dependencies разрешены/запрещены? [ ] Есть ли cycles? [ ] Как обрабатываются partial failures? [ ] Где retries/timeouts/idempotency? [ ] Как выполняются migration/rollback? [ ] Есть ли observability contract? [ ] Почему сделаны ключевые design decisions? [ ] Существуют ли ADR? [ ] Какие quality goals движут архитектурой? [ ] Какие известные risks/debt?

C4 отмечает, что context/container diagrams меняются относительно медленно во многих системах и являются удобными high-level views; component/code детализацию добавляй только там, где это помогает объяснить существенную сложность [S6]. 

Критерии оценки.

Балл	Качество архитектуры и её управляемости
3	Boundaries понятны; dependencies контролируются; quality goals/ADR актуальны; docs соответствуют code/infra
2	Архитектура последовательна, присутствует локальный drift или несколько implicit contracts
1	Значимые cycles/hidden dependencies/unrecorded decisions существенно повышают change cost
0	Критические boundaries отсутствуют либо архитектура создаёт непосредственный security/reliability/data-integrity risk

Приоритет:

Priority	Архитектурные примеры
P0	Broken authorization boundary, неконтролируемый data ownership, single failure с catastrophic impact
P1	Critical coupling, unsafe deployability, migration risk, dependency cycle на core path
P2	Architecture drift, excessive change amplification, undocumented integration
P3	Неполный diagram/ADR metadata без непосредственного runtime impact

Ожидаемые артефакты: architecture-audit.md; system-context.mmd; container-view.mmd; dependency graph в machine-readable формате; boundary-violations.csv; runtime-scenarios.md; adr-gaps.md; architecture-risk-register.csv; roadmap, разделённый на quick wins, tactical refactoring и strategic changes.

Не создавай огромную code-level diagram всего проекта. Официальный C4 guidance прямо рассматривает code diagram как optional и советует по возможности получать такую детализацию автоматически из tooling для наиболее важных/сложных компонентов [S7]. 

Автоматизация: architecture fitness functions; dependency/boundary rules; cycle detection; architecture tests; public-contract diff; ADR template/check; Mermaid render gate; проверки source-to-building-block mapping; scheduled architecture-drift report.
