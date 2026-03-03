# План полного рефакторинга документации и скриптов по работе с диаграммами

Дата: 2026-03-01  
Область: `docs/02-architecture/mmd-diagrams/**`, `scripts/diagrams/**`, CI workflow диаграммных проверок  
Основание: результаты 5 независимых аудитов (документация, скрипты, CI, манифесты, синтаксическая валидность)

## 1. Контекст и цель

Текущая диаграммная подсистема в проекте функционально богата, но неустойчива в части консистентности «policy → docs → scripts → CI». Выявлены системные разрывы между каноническим контуром (`mmd-diagrams/**`) и фактически обрабатываемым контуром (`docs/**`), а также расхождение между green-статусом отдельных quality-gates и реальными падениями синтаксической валидации на полном массиве диаграмм. Дополнительно присутствуют документационные противоречия (устаревшие количества, команды, сообщения по drift-check), а также архитектурный технический долг в форме legacy-набора диаграмм, частично дублирующего canonical views.

Цель этого плана — перевести диаграммную подсистему в полностью воспроизводимое, наблюдаемое и управляемое состояние с единым источником истины, детерминированным поведением скриптов и прозрачной CI-валидацией, исключающей ложное ощущение «всё хорошо», когда в реальности есть блокирующие ошибки.

## 2. Консолидированные выводы аудита

### 2.1 Ключевые подтвержденные проблемы

1. Подтверждены синтаксические падения в канонических диаграммах (14 файлов) при полном прогоне `validate_mermaid_syntax.sh`.
2. Подтверждена runtime-нестабильность дефолтного Puppeteer-конфига в ряде сценариев рендера (`mmdc` launch error / ICU descriptor failure).
3. По умолчанию `render.sh` и `validate_mermaid_syntax.sh` работают по всему `docs/**`, тогда как документация позиционирует `mmd-diagrams/**` как canonical root.
4. `quality-gate-manifest` и `visual-smoke-manifest` покрывают очень узкий baseline (5 файлов), из-за чего hard/soft quality signal не отражает состояния всей канонической базы.
5. Документация содержит устаревшие данные и противоречия (счетчики файлов, команды, поведение drift-check против `.gitignore`).

### 2.2 Корневые причины (Root Causes)

- RC-01: Отсутствие жёсткой границы scope между canonical и legacy слоями.
- RC-02: Неунифицированный runtime-конфиг Puppeteer между локальным и CI контуром.
- RC-03: Слабая диагностируемость скриптов (подавление stderr, недостаток structured report output).
- RC-04: Разрыв между «быстрым baseline-гейтом» и «полноценной проверкой флота».
- RC-05: Нет автоматического контроля синхронизации документации с реальным состоянием tree/скриптов.

## 3. Принципы рефакторинга

1. **Canonical-first**: по умолчанию все обязательные проверки работают только на canonical контуре; legacy проверяется отдельно.
2. **Fail-loud**: любая ошибка рендера/синтаксиса должна иметь читаемую первопричину без ручного повторного запуска.
3. **Single command contract**: один унифицированный entrypoint для локального и CI запуска профилей проверок.
4. **Measured coverage**: метрики покрытия quality-gates должны быть количественно измеримы и публиковаться.
5. **Docs as executable contract**: документированные числа/команды должны проверяться автоматикой.

## 4. Дорожная карта рефакторинга

## Фаза A — Stabilization Freeze (день 1-2)

Цель: зафиксировать baseline и исключить «плавающую» диагностику.

Задачи:
1. Ввести baseline-отчет в `reports/diagrams/`:
   - `source_count_all`, `source_count_canonical`, `source_count_legacy`;
   - `syntax_fail_count`;
   - `lint_warning_by_rule`;
   - `quality_gate_coverage`.
2. Добавить явный признак scope в runbook: `canonical`, `legacy`, `all`.
3. Зафиксировать текущие манифесты и их роль: baseline/smoke-only.

Критерии завершения:
- baseline-отчет стабильно воспроизводится локально и в CI;
- все участники понимают, какой контур является блокирующим для merge.

## Фаза B — Syntax Repair (день 2-4)

Цель: устранить блокирующие parse errors в canonical диаграммах.

Задачи:
1. Исправить 14 подтвержденных файлов (sequence/class синтаксис стрелок и конфликтные операторы).
2. Добавить безопасный codemod-скрипт `scripts/diagrams/fix_mermaid_operators.py`:
   - режим `--check` (report only),
   - режим `--fix` (controlled rewrite),
   - dry-run summary.
3. Добавить тестовые фикстуры в `tests/architecture/` на недопустимые операторы.

Критерии завершения:
- `validate_mermaid_syntax.sh --scope canonical` проходит без fail;
- в regression-tests есть защита от повторного внесения тех же operator-pattern.

## Фаза C — Runtime Config Hardening (день 3-5)

Цель: сделать запуск `mmdc` предсказуемым независимо от окружения.

Задачи:
1. Пересмотреть default Puppeteer strategy:
   - по умолчанию без фиксированного `executablePath`;
   - опциональный override через env (`PUPPETEER_EXECUTABLE_PATH`).
2. Исправить `run_diagram_checks.sh`:
   - не перезаписывать существующий `--puppeteer` файл без явного флага;
   - валидировать JSON-конфиг перед запуском.
3. Добавить preflight-step с явной диагностикой: browser discovery, permissions, sandbox flags.

Критерии завершения:
- локальный запуск и CI используют одинаковый, прозрачный конфиг-контракт;
- исчезают нестабильные launch-errors в штатном контуре.

## Фаза D — Observability and Error Reporting (день 4-6)

Цель: радикально улучшить дебажимость скриптов.

Задачи:
1. В `render.sh` убрать «слепое» подавление stderr:
   - писать stderr в `.render-logs/<diagram>.stderr`;
   - при ошибке печатать краткую причину и ссылку на лог.
2. В `validate_mermaid_syntax.sh` добавить `--report-json`:
   - файл,
   - error class (syntax/runtime/environment),
   - exit status normalization.
3. В конце прогона формировать сгруппированный summary по типам ошибок.

Критерии завершения:
- любой fail воспроизводим по structured report;
- triage занимает минуты, а не часы.

## Фаза E — Coverage Expansion for Gates (день 5-8)

Цель: устранить разрыв между baseline-green и реальным качеством флота.

Задачи:
1. Расширить `check_diagram_quality_gates.py` и `check_diagram_artifacts.py`:
   - `--scope canonical` discovery mode;
   - поддержка merged-mode: `baseline + changed + dependent views`.
2. Обновить CI:
   - PR: baseline + changed scope (hard gate);
   - Nightly: полный canonical scope;
   - Отдельный informational legacy check.
3. Добавить coverage-metric в отчет quality gates:
   - checked files / canonical files.

Критерии завершения:
- невозможно пройти hard-gate при критических проблемах в измененном canonical контуре;
- nightly дает полную картину состояния canonical флота.

## Фаза F — Documentation Normalization (день 6-10)

Цель: синхронизировать документы с фактом и убрать противоречия.

Задачи:
1. Обновить `docs/02-architecture/mmd-diagrams/README.md`:
   - актуальные counts,
   - полный список decomposed architecture slices,
   - команды только через canonical scripts.
2. Обновить `ADR-040` и policy-документы:
   - убрать/пометить deprecated script-path,
   - выровнять правила с текущим поведением CI.
3. Исправить drift-check messaging в workflow:
   - если артефакты gitignored, не требовать их commit;
   - требовать успешный рендер/валидацию в CI.
4. Ввести auto-generated фрагменты (counts/sections), чтобы не поддерживать их вручную.

Критерии завершения:
- нет конфликтующих инструкций между README, policy, ADR, workflow;
- документация проходит path/link/consistency lint.

## Фаза G — Legacy Strategy and De-duplication (день 8-12)

Цель: управляемо развести legacy и canonical без поломки истории.

Задачи:
1. Зафиксировать policy:
   - legacy `docs/02-architecture/diagrams/mermaid/*` = read-only historical layer,
   - canonical = единственный writable source of truth.
2. Добавить guard:
   - изменения в legacy требуют специального флага/лейбла PR.
3. Подготовить roadmap:
   - либо полная архивация в `docs/99-archive`,
   - либо поддержание минимального «snapshot-only» слоя.

Критерии завершения:
- исчезает двусмысленность “какой файл главный”;
- любой diff в legacy — осознанное исключение, а не случайность.

## Фаза H — Test Architecture Upgrade (день 10-14)

Цель: перевести тесты от “проверки wiring” к поведенческим гарантиям.

Задачи:
1. Добавить интеграционные тесты скриптов на mini-fixtures:
   - syntax fail,
   - runtime fail,
   - manifest mismatch,
   - successful pipeline.
2. Добавить тест на отсутствие принудительного перезаписывания external Puppeteer config.
3. Добавить tests на docs consistency:
   - counts,
   - canonical commands,
   - deprecated path usage.

Критерии завершения:
- критические регрессии из аудита имеют автотестовое покрытие;
- CI ловит эти дефекты до merge.

## Фаза I — Governance Automation (день 12-16)

Цель: внедрить постоянную автоматическую синхронизацию policy/docs/scripts.

Задачи:
1. Создать meta-lint `scripts/diagrams/check_diagram_docs_consistency.py`:
   - проверка актуальности счетчиков,
   - запрет deprecated paths в актуальных docs,
   - проверка согласованности CI сообщений с `.gitignore`.
2. Подключить meta-lint в PR workflow.
3. Публиковать в `GITHUB_STEP_SUMMARY` consolidated status:
   - syntax,
   - render,
   - quality,
   - docs consistency.

Критерии завершения:
- policy drift обнаруживается автоматически;
- ручной аудит нужен только для архитектурных решений, а не для механической синхронизации.

## 5. Приоритеты и порядок внедрения

Приоритет P0 (немедленно):
1. Фаза B (Syntax Repair)
2. Фаза C (Runtime Config Hardening)
3. Фаза D (Observability)

Приоритет P1 (после стабилизации):
1. Фаза E (Coverage Expansion)
2. Фаза F (Documentation Normalization)

Приоритет P2 (структурное улучшение):
1. Фаза G (Legacy Strategy)
2. Фаза H (Test Architecture Upgrade)
3. Фаза I (Governance Automation)

Такой порядок минимизирует риск длительного «красного» CI и одновременно быстро закрывает операционные боли.

## 6. План миграции без остановки команды

1. Ввести dual-mode проверок на переходный период (`canonical required`, `legacy informational`).
2. Выпускать изменения короткими пакетами:
   - пакет 1: syntax/runtime fixes,
   - пакет 2: coverage + CI,
   - пакет 3: docs + meta-lint.
3. Для каждого пакета — отдельный rollout checklist и rollback strategy.
4. Поддерживать “migration dashboard” в `reports/diagrams/` с KPI по неделям.

## 7. KPI успеха

Технические KPI:
1. `syntax_failures_canonical = 0`.
2. `render_failures_canonical = 0` в nightly.
3. `quality_gate_coverage >= 95%` canonical files (PR changed scope + nightly full).
4. `runtime_launch_errors = 0` в стандартном CI окружении.

Документационные KPI:
1. `README_counts_match_fs = true`.
2. `deprecated_script_paths_in_active_docs = 0`.
3. `policy_workflow_conflicts = 0`.

Процессные KPI:
1. Среднее время triage diagram failure < 10 минут.
2. Повторные регрессии по operator-syntax = 0 после внедрения codemod + tests.
3. Доля manual hotfixes без тестов -> снижается до 0.

## 8. Риски и меры снижения

Риск 1: рост времени CI после расширения coverage.  
Митигирование: динамический changed-scope в PR + полный флот только в nightly.

Риск 2: непредвиденные различия Mermaid CLI версий.  
Митигирование: зафиксировать единый диапазон версий для локального dev и CI; добавить canary job.

Риск 3: сопротивление изменениям из-за legacy-зависимостей.  
Митигирование: staged migration, read-only legacy policy, прозрачные исключения.

Риск 4: повторный документационный дрейф.  
Митигирование: auto-generated sections + meta-lint в PR.

## 9. Конкретные deliverables

1. Обновленные скрипты:
   - `docs/02-architecture/mmd-diagrams/render.sh`
   - `scripts/diagrams/validate_mermaid_syntax.sh`
   - `scripts/diagrams/run_diagram_checks.sh`
   - `scripts/diagrams/check_diagram_quality_gates.py`
   - `scripts/diagrams/check_diagram_artifacts.py`
2. Новые утилиты:
   - `scripts/diagrams/fix_mermaid_operators.py`
   - `scripts/diagrams/check_diagram_docs_consistency.py`
3. Обновленная документация:
   - `docs/02-architecture/mmd-diagrams/README.md`
   - `docs/02-architecture/06-diagram-policy.md`
   - `docs/02-architecture/decisions/ADR-040-diagram-governance.md`
   - `docs/02-architecture/mmd-diagrams/docs/diagrams-index.md`
4. Тесты:
   - расширение `tests/architecture/*diagram*`
   - новые integration fixtures для script behavior.
5. CI обновления:
   - `.github/workflows/docs.yml`
   - при необходимости `.github/workflows/diagram-nightly.yml`.

## 10. Валидация консолидированного результата

Итог рефакторинга считается завершенным только при выполнении всех пунктов:
1. Синтаксическая валидация canonical флота проходит стабильно.
2. Рендер canonical флота проходит без runtime-flakes в CI и локально.
3. Quality-gates репрезентативно покрывают canonical scope, а не только baseline-пул.
4. Документация синхронизирована с кодом/скриптами/CI и не содержит конфликтующих инструкций.
5. Legacy слой четко отделен и не влияет на canonical hard-gate pipeline.
6. Все ключевые регрессии из аудита покрыты автотестами.

---

Этот план предназначен как рабочий документ реализации. Следующий практический шаг — выполнить Phase B + C как единый «stability patch set», затем зафиксировать новый baseline и перейти к расширению coverage (Phase E).
