______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-10-03'

______________________________________________________________________

# Локальная приёмка при недоступном GitHub Actions

## Trigger

Порядок принят по решению владельца проекта от 2026-10-03 для интеграции
`codex/integrate-priority-1-2-20261003` при заблокированном GitHub Actions.
Он задаёт ручную локальную приёмку этой интеграции и не объявляет GitHub checks
успешными. Выполнение самого порядка не означает разрешение на push или merge.

Недоступность Actions фиксируется как `CI=BLOCKED_EXTERNAL`, с источником
сведений и датой. Заявление владельца допустимо: его следует обозначить как
заявление владельца, а не результат самостоятельной проверки GitHub.

## Impact

Недоступен внешний исполнитель CI. Требуется независимая локальная проверка
кандидата; продуктовые дефекты и неполные доказательства остаются блокирующими.

## Preconditions

Доступны полный checkout, подготовленное окружение и место для сохранения
журналов. Владелец подтвердил недоступность Actions и применимость этого порядка.

## Compliance

- Исторический [test telemetry baseline](../../05-engineering/test-telemetry-baseline.md)
  сохраняет исходные SHA, run ID, URL, дату, branch/event и показатели.
  Нельзя присваивать локальному запуску GitHub run ID или обновлять дату старого
  измерения для прохождения freshness-проверки.
- Пороги покрытия, бюджеты долга, assertions, состав тестов и исключения
  остаются неизменными. Падающие тесты не удаляются, не переводятся в skip/xfail
  и не исключаются из команд ради положительного результата.
- Машинный `proof-or-stop` сохраняет фактический verdict. Ручной локальный
  протокол не превращает `STOP` в `ADMIT` и не подделывает producer receipts.
- Этот порядок не меняет branch protection и не обходит required checks.
  Если GitHub технически запрещает merge, изменение правил требует отдельного
  решения владельца репозитория.

## Procedure

### 1. Зафиксировать кандидата

Использовать полный изолированный checkout без незакоммиченных изменений.
Записать candidate SHA, SHA базы main, ветку, worktree, UTC-время, ОС,
версию Python и зависимости из lock-файла. Проверить отсутствие параллельной
записи в checkout. Проверить полноту дерева:

```powershell
python scripts/engineering/repo/check_no_partial_tree.py --base origin/main --tip HEAD
git status --porcelain
git rev-parse HEAD
```

На Windows `python` означает интерпретатор подготовленного окружения
`.venv-win/Scripts/python.exe`; при общем окружении записать его абсолютный путь.
Не создавать или изменять `.env`. Не выводить токены в журналы.

### 2. Выполнить локальные обязательные проверки

На одном candidate SHA выполнить:

```powershell
python -m scripts.engineering.dev run-tests all
python -m scripts.engineering.qa.run_local_coverage_verify
python -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml
python -m scripts.engineering.qa report-debt-governance-gates --check
python -m scripts.docs check-links
python -m scripts.docs check-drift --runtime-mirrors --freshness
python -m scripts.docs generate-cleanup-inventory --check
```

Дополнительно выполнить обязательные lint/type/architecture/config gates из
действующих project commands и workflow для затронутых поверхностей; в протоколе
перечислить точные команды и соответствующие им проверки. Для изменённых
Grafana-плагинов нужны их lint/typecheck/test/build. Если runtime mirrors
изменены, выполнить `python scripts/ai/junie/check_junie_mirror.py --check`.
Не считать отсутствие Actions основанием пропустить локально исполнимую проверку.

Для каждой команды сохранить stdout/stderr, terminating exit code, начало и
конец UTC, HEAD до/после, состояние дерева и JUnit/JSON/XML, если команда их
создаёт. Проверить итоги в самих артефактах, включая collection errors,
failed/skipped counts и завершение всех shards. Таймаут, crash, неполный запуск
или отсутствие результата не равны pass. Если wrapper останавливается на первом
падении, оставшиеся lanes надо выполнить отдельно и сохранить их результаты.

Полное coverage-доказательство требует всех shards канонического runner и
выполнения глобальных и модульных gates. Аддитивные целевые XML не заменяют
полный прогон. Обновление измерений и зависимых отчётов выполняется по
[generated artifact workflow](generated-artifact-drift-workflow.md).
После исправлений или изменения отслеживаемых файлов создать новый candidate
commit и повторить обязательную приёмку; старые результаты сохраняются под
своими SHA. Не смешивать результаты нескольких ревизий в один успешный прогон.

### 3. Классифицировать CI-зависимые падения

Сначала выполнить проверки без фильтрации. В отдельном реестре записать точный
node ID, assertion, журнал, причину внешней зависимости и локальную замену либо
явно указать, что эквивалентной замены нет. Для этой интеграции известны:

- `tests/architecture/test_test_telemetry_governance.py::test_committed_test_telemetry_baseline_is_populated`
- `tests/architecture/test_test_telemetry_governance.py::test_committed_test_telemetry_branch_accurate_source_identity`

Только падение из-за отсутствия актуального реального CI-доказательства может
быть классифицировано как `BLOCKED_EXTERNAL`. Любое другое assertion в этих
тестах проверяется отдельно. Список не распространяется автоматически на новые
падения. Структурные, функциональные и coverage-дефекты остаются локальными
блокерами. Для проверки покрытия вместо свежего CI используется полный локальный
coverage runner; подтверждение факта запуска GitHub Actions локально невозможно.

### 4. Сформировать отдельный протокол решения

Сохранить протокол и неизменяемый evidence bundle вне исторического CI baseline,
например в `reports/local-acceptance/<candidate-sha>/`. Если каталог игнорируется
Git, передать или архивировать bundle отдельно; одной ссылки на локальный путь
недостаточно для другого проверяющего. Добавить SHA-256 каждого артефакта.

Минимальные поля протокола:

```text
candidate_sha / base_sha / branch / worktree
started_at_utc / finished_at_utc / environment
ci_status: BLOCKED_EXTERNAL
ci_unavailability_source: owner statement, 2026-10-03
checks: command, exit_code, head_before, head_after, log, junit, sha256
test_totals: collected, passed, failed, errors, skipped
external_failures: exact node ID, assertion, reason, replacement evidence
local_failures: complete list
coverage: full-run manifest, line/branch gates, module regression result
automated_proof_verdict: actual result and bundle path
local_decision: HOLD | ACCEPTED_LOCAL
reviewer / reviewed_at_utc / rationale
```

`ACCEPTED_LOCAL` допустим только после завершения всех обязательных локальных
проверок, отсутствия локальных дефектов и рассмотрения владельцем каждого
внешнего ограничения. При этом итог полного pytest может оставаться ненулевым
из-за перечисленных CI-зависимых проверок: сообщать точные числа, а не «suite
зелёный». Непроверенные lanes или иные падения означают `HOLD`.

Перед merge повторно сверить candidate SHA, чистоту дерева и базу main.
Если база изменилась, проверить новый интеграционный кандидат по этому порядку.
Решение о merge принимается отдельно с явным указанием `CI=BLOCKED_EXTERNAL`.

## Verification

Проверить совпадение SHA во всех receipts, полноту обязательных lanes,
контрольные суммы артефактов и обоснование каждой внешней классификации.
Убедиться, что исторический CI baseline и бюджетные ограничения не изменены.

## Rollback/Recovery

При ошибке или изменении кандидата установить `HOLD`, сохранить неуспешные
журналы и исправить первопричину. Новый прогон записать отдельно; не удалять
неуспешные результаты и не восстанавливать старые хеши для прохождения checks.

## Post-incident

Сохранить решение владельца и evidence bundle. Если Actions станет доступен,
получить настоящий CI run нового кандидата обычным порядком; локальное решение
остаётся историческим локальным решением и не превращается в CI-доказательство.

### Исходное состояние интеграции

На `f386ca99264172e5a63f7da531208f1372588cac` локальная приёмка — `HOLD`:
pipeline factories имеют 4096 LOC при лимите 3870; runtime builders — 51 модуль
при структурном минимуме 55. Последний целевой архитектурный прогон: 49 passed,
4 failed, включая два telemetry-теста выше. Полный успешный локальный набор
приёмки не подтверждён. Этот документ не закрывает перечисленные блокеры.

### Миграция контракта runtime builders

Коммит интегрируемой ветки `51dde7fd774762eb7f489823fca0c7bbd41c5d02`
удалил четыре файла. `_config_access_loaders.py` перенесён в `config_access.py`;
три остальных файла были re-export-обёртками: `_effective_config_graph_support.py`
над `infrastructure.config.effective_config_graph`, `_run_manifest_sink_policy.py`
над `domain.control_plane.run_manifest_sink_policy` и
`_runner_control_plane_artifact_policy.py` над
`domain.control_plane.artifact_publication_policy`. Они не представляли четыре
утраченных реализации.

Для этого семейства `require_all_modules_covered: true` заменяет исторические
минимумы измеренных/покрытых файлов. Условие требует непустого семейства,
измерения и покрытия каждого фактического модуля и наличия line coverage.
Порог 94,9% и отсутствие неожиданных неизмеренных модулей сохраняются.
Новый непокрытый модуль блокирует приёмку независимо от того, достигнуто ли 55;
allowlist не обходит требование полноты. Состав файлов не является доказательством
поведенческой совместимости — её проверяют тесты владельцев и полный прогон.

### Консолидация factories и синхронизация с main

При интеграции `main` до `45da427d46702769d87765d9f2616f1c26aa06ad`
сокращены повторные конструкторы, проверки аргументов и экспортные списки.
Схемы и transformer-классы остаются явно заданными для каждой pipeline;
provider/entity извлекаются из её полного имени с сохранением составного entity.
Pipeline factories сокращены до 3870 LOC при прежнем лимите 3870;
доля приватных helper-функций составляет 0,358 при прежнем лимите 0,358.

Исправления cohort/resume сохраняют исходный результат producer и проверяют
цепочку записанных FK-изменений. Исторические CI run ID, дата и source hash
не перепривязываются к текущему дереву без нового измерения.

Это не означает `ACCEPTED_LOCAL`: полный набор приёмки ещё не подтверждён,
а граф зависимостей содержит 332 межгрупповые связи при лимите 330.
Локальное слияние по явному решению владельца фиксируется отдельно от `HOLD`
и `CI=BLOCKED_EXTERNAL`; оно не выдаётся за завершённую техническую приёмку.
