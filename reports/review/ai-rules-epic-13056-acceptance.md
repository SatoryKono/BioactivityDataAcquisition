# Паспорт приёмки эпика #13056

**Owner:** BioETL Team
**Status:** acceptance record
**Class:** repo-only

Сквозная приёмка эпика
[#13056](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13056)
по его чеклисту. Issue не закрывается этим документом.

Проверка выполнена на полном checkout `origin/main`
`7e1cbcbd82ef156b29b12cec0947586d0d1a7b37`
(2026-11-16 14:08:18 +0300, `fix(ci): record an unopened 48-minute Nightly pilot`).
Все 16 задач карты на этот момент `CLOSED` / `COMPLETED`.
Ни одна не была открыта или переоткрыта.

## Baseline, который не входит в main

[PR #13133](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/13133)
на момент приёмки: `OPEN`, draft, `mergeStateStatus=BLOCKED`,
head `698b65d743a5fe06e5bf1c095d79df6fd84b9a24`
(`codex/qualify-host-hooks-20261113`).
`git merge-base --is-ancestor` этого head относительно `origin/main` не выполнен.
Evidence #13133 не используется как PASS. Зависимые пункты — `NOT_VERIFIABLE`.

## Вердикты чеклиста

| Пункт | Вердикт | Evidence |
| --- | --- | --- |
| 1. AUD-001–AUD-011 | PASS | Закрывающие merge SHA ниже являются предками `origin/main`; указанные файлы прочитаны на этом SHA. #13133 не использован. |
| 2. Паспорт runtime | PASS | Четыре состояния разделены. `NOT_PROVEN` и `UNKNOWN` не названы PASS. |
| 3. Сценарии | NOT_VERIFIABLE | Контрактные тесты: 276 passed / 2 skipped / 0 failed. V3/V4 pre-task — DEGRADED. Hash-only и полный read-only architecture audit на чистом дереве не запускались. |
| 4. Дисциплина статусов | PASS | SKIP, DEGRADED, ERROR, exit 2 и невлитый #13133 не переведены в PASS. |
| 5. Guardrails | PASS | Тексты ограничений на месте. Числовое повышение потолков не найдено. Изменение реестра budget guard явное и не молчаливое. |
| 6. Inventories и mirrors | NOT_VERIFIABLE | Локально mirror `--check` exit 0 и cleanup inventory обновлён вместе с этим файлом. CI на head этого PR в момент коммита не исполнен и не объявляется PASS. |
| 7. Эффект #13033 | UNKNOWN | Статический снимок воспроизведён. Tokens, tool calls, repeated reads и loaded-source effect — `NOT_MEASURED`. |
| 8. Откат | PASS | У каждого закрывающего commit один parent. Способ — `git revert <sha>` без переписывания истории. Репетиция revert не выполнялась. |

## AUD-001–AUD-011

Нумерация взята из комментария эпика
(восстановление по тексту аудита, не по названиям задач).
Файлы перечитаны на `7e1cbcbd82ef156b29b12cec0947586d0d1a7b37`.

| ID | Находка | Задача | Evidence в main | Граница |
| --- | --- | --- | --- | --- |
| AUD-001 | Непереносимый worktree guard | #13032, PR #13086, merge `ffbc484dae248889de8e6aa3fc1ed512d209fdb1` | `scripts/engineering/repo/create_worktree.py` (`APPROVED_ROOT = D:/github`, отказ при junction/symlink, строки 19–59); `AGENTS.md` Local Git Tree Placement | Наличие helper не доказывает установку на каждом хосте. Квалификация hooks из #13133 в main отсутствует. |
| AUD-002 | Subset detector пропускает схлопывание | #13037, PR #13087, merge `938a19ff244e8d516c6c6c88bb55ef5170728dff` | `scripts/engineering/repo/check_no_partial_tree.py` `is_collapsed_tree` (строки 63–76): сравнение с trusted base, а не только с родителем | Дополнительная Windows/batch квалификация живёт в #13133 и здесь не является PASS. |
| AUD-003 | Ненадёжный base ручного workflow | #13037, тот же merge | `.github/workflows/no-partial-tree-commits.yml`: `pull_request_target`, `push`, `workflow_dispatch` с обязательным `base` (строки 5–21); проверка `--base/--tip` и отдельный статус `bioetl/no-partial-tree` | Обязательность ruleset подтверждена текстом issue #13037 для более раннего SHA, не перепроверялась live в этой приёмке. |
| AUD-004 | Wrappers расширяют bootstrap | #13030, PR #13070, merge `4608080f1a7ba48e7ae56533ffe69a40911d0339` | `AGENTS.md` Required AI Context (строки 74–79) — одна матрица; `.codex/skills/py-audit-bot/references/wrapper-contract.md` (строки 20–37): post-task только в `read-write` | |
| AUD-005 | Альтернативный приоритет и Gemini | #13052, PR #13060, merge `985457dde09b8453c3dcfdf7eb6cb7f05c12e37a` | `AGENTS.md` Canonical Precedence; запрет Gemini runtime (строка 195); `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md` | |
| AUD-006 | Read `.env` одновременно ask и allow | #13054, PR #13088, merge `1f922be869477882c63ae79af1373b71157f2510` | `.devin/config.json`: `Read(.env*)` и `Read(**/.env*)` только в `ask`; `Write(.env*)` в `deny`; в `allow` этих путей нет | Статический файл не доказывает native enforcement. |
| AUD-007 | Exec не доказывает ограничение записи | #13054, тот же merge | `.devin/agents/DEVIN-RUNTIME.md` (строки 183–209): нет автоматических Exec/Write grants; Windows sandbox не поддерживается; итог native isolation — `NOT_PROVEN` | Это запрет неподтверждённого пути, не sandbox PASS. |
| AUD-008 | Read-only debug назначен исполнителем fix | #13027 PR #13040 merge `b283d1759fbaedfb1efe731307ccbd0c8024eaa8`; #13031 PR #13083 merge `ac894968c851b46ae25631b4bfadce7e333d9083` | `.devin/agents/py-test-bot/AGENT.md` (строки 209–213): при failed retest debug даёт RCA, исправляет authorized parent / implementer | Исполнение Devin-сессии не наблюдалось. |
| AUD-009 | Неразрешимый post-change skill | #13028, PR #13050, merge `0abadcec835dffd1107d116247649de0e4ecd79c` | `.codex/agents/py-config-bot.md` строка 75: entrypoint `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` | |
| AUD-010 | Parity не покрывает защитные обязательства | #13055, PR #13094, merge `e63e7c2ac9080e2c1265856962d69f30f573993e` | `scripts/ai/junie/junie-mirror-contract.json`: 25 `guardrail_obligations`. Локальный `check_junie_mirror.py --check` exit 0 | Проверка формата и обязательных clauses, не общая семантическая эквивалентность. Native loading этим check не доказан. |
| AUD-011 | В нормативном индексе нет REQUIREMENTS | #13052, тот же merge `985457dde09b8453c3dcfdf7eb6cb7f05c12e37a` | `docs/00-project/NORMATIVE_SOURCES.md` (строки 21–29): Requirements, Constitution, Decisions | |

Остальные закрывающие merge этой серии, не входящие в таблицу находок, тоже предки main:
#13033/#13089 `1af023ba26813732f984d4c70bf8c7d7afe06828`,
#13034/#13048 `e0b4ad51f478dfdd9e9f2e69d02f12786d61eb81`,
#13035/#13085 `c3818114beca66129db6ca97e78196314d854308`,
#13036/#13093 `26eb08a1226550598bd666c6720d599a9ddbf235`,
#13038/#13097 `ceec83ef63587fbe6ea2b61a7ae5ebfe2c7c3723`,
#13039/#13126 `ac99a373b2a55174f1ca211df07c46a94e4a7bf3` и
#13132 `7d5f01d89cd112e269fc7ea548fb42164c226af3`,
#13053/#13084 `a2a2b6c34113004835fa453aa0a3615c7edd4614`.
У каждого из перечисленных commit ровно один parent: это squash, не merge с `-m 1`.

## Паспорт runtime

Статический doctor
`python scripts/ai/codex/doctor.py rules --no-write --json`
завершился exit 2, `status=NOT_PROVEN`, `runtime_process_started=false`.
Для Codex, Junie, Devin и OpenCode поля loading и execution в этом отчёте — `NOT_PROVEN`.
Наличие файла doctor не повышает до loaded или executed.

Отдельные native-наблюдения ниже не заменяют exit 2 doctor.

| Runtime | Binary / version / config | file-present | configured | loaded | executed |
| --- | --- | --- | --- | --- | --- |
| Codex | Прямой exe, `codex-cli 0.167.0-alpha.3.2`, SHA-256 `4f91ae86895ff124760d70ed1630e2354ca874765c9bb61ae524b600327efc17`. Резолвер выбирает самый новый `codex.exe` в каталоге приложения. | PRESENT: `AGENTS.md`, `.codex/config.toml`, runtime map, профили и skills (29). MISSING: `AGENTS.override.md`. | Файл `.codex/config.toml` есть. Значения effective config не снимались. Doctor: `native_configuration=NOT_PROVEN`. | `debug prompt-input` (exit 0, без model turn) содержит полное тело `AGENTS.md` (SHA-256 LF `128cc2df825d11c8a5617d79737d7ed9bcc0ce2dc578b92afd4964082ff3430b`). Полных тел `CODEX-RUNTIME.md`, `py-audit-bot.md`, skill `py-audit-bot`, `.junie/guidelines.md` и `POST_CHANGE_VALIDATION.md` в этом render нет. | NOT_PROVEN. Model turn не запускался. |
| Junie | PATH shim есть. Файл `current` и каталог `versions` отсутствуют. Версия UNKNOWN. Shim не запускался: он применяет pending update до старта. | PRESENT: `AGENTS.md`, `.junie/guidelines.md`, runtime map и зеркала (23). MISSING: `.junie/AGENTS.md`, `.junie/config.json`. | Default runnable CLI NOT_PROVEN. | NOT_PROVEN | NOT_PROVEN |
| Devin | Прямой exe `devin 3000.11.3 (9c803229faa4)`. | PRESENT: 24 источника, включая `.devin/config.json` и `DEVIN-RUNTIME.md`. | В проектном `.devin/config.json` Read `.env*` = ask, Write `.env*` = deny. Слои organization/session не читались. Doctor: `native_configuration=NOT_PROVEN`. | `rules show AGENTS` вернул текст, содержащий полное тело `AGENTS.md`. Это resolver, не session injection. В stderr захвата после тела — panic `failed printing to stdout` / os error 232 из-за закрытого pipe harness. Это не отказ продукта и не PASS enforcement. | NOT_PROVEN. Изоляция Exec и model obedience не наблюдались. |
| OpenCode | Файл exe на машине есть. `package.json` manifest `1.18.1` не является аттестацией бинарной версии. Процесс не запускался. | PRESENT: `opencode.json` и 8 агентов `.opencode/agent/`. | Репозиторный `opencode.json` задаёт модель `model_api/muse-spark-1.3-contributor`. Phase 2 не включена. | NOT_PROVEN | NOT_PROVEN |

Эта сессия Cursor не подменяет loaded/executed для четырёх runtime выше.

## Сценарии

Изолированный scope: текущий checkout main, без нового worktree, без изменения `.env`,
без активации OpenCode и без model turn.
`PYTHONDONTWRITEBYTECODE=1`.

Общий прогон, exit 0:

`pytest` файлов
`tests/architecture/test_codex_task_routing.py`,
`tests/architecture/test_junie_runtime_ci_contract.py`,
`tests/unit/scripts/engineering/repo/test_create_worktree.py`,
`tests/unit/scripts/repo/test_check_no_partial_tree.py`,
`tests/unit/scripts/repo/test_operation_guards.py`,
`tests/unit/tools/test_opencode_agent_header.py`,
`tests/unit/scripts/ai/test_opencode_agent_headers.py`.

Собрано 278. Итог: 276 passed, 2 skipped, 0 failed.

| Сценарий | Вход | Ожидание | Факт | Статус |
| --- | --- | --- | --- | --- |
| V1 docs | Матрица `AGENTS.md` и `test_codex_task_routing.py` | Guardrails + POST_CHANGE docs slice; memory read-only optional | Тесты маршрута вошли в exit 0 | PASS контракта. Живая правка документа не делалась. |
| V2 focused fix | Та же матрица; негативные тесты worktree ref | Role/skill + pre-task; отказ options/expressions до Git | Тесты вошли в exit 0. Seed в main не вносился. | PASS контракта. Живой fix не запускался. |
| V3 | `BIOETL_AI_MEMORY_MODE=read-only`, `pre-task --task-id epic-13056-acceptance --skip-refresh-if-missing --skip-session-note --json` | Либо успешный read-only retrieval, либо явный DEGRADED без записи | Exit 1, `ok=false`, `degraded=true`, `session_note=null`, `refresh_report=null`. Missing: `rag_chunks` (`missing_or_empty_rag_chunk_manifest`), `timeline_events` (`missing_or_empty_timeline_event_projections`). | DEGRADED. Не PASS. |
| V4 | Та же строка матрицы, что V3 | Полный пакет и обязательный pre-task | Отдельной строки V4 нет. Тот же pre-task. | DEGRADED. Не PASS. |
| read-only audit | `python -m scripts.engineering.qa run-architecture-audit-read-only` | Check-only, без записи governance-артефактов | Не запускался. | NOT_VERIFIABLE |
| hash-only refresh | `report-module-coverage --check --allow-missing-coverage-xml` | Совпадение `source_tree_sha256` без новой `coverage.xml` | Не запускался. | NOT_VERIFIABLE |
| worktree | `test_create_worktree.py` | Вне `D:/github` и без helper создание запрещено; validate-only без дерева | Файл вошёл в exit 0. Skip: `test_create_worktree.py:367` POSIX negative control. | PASS на Windows-контракте. POSIX-кейс — SKIP, не PASS. |
| .env | `test_operation_guards.py` и `.devin/config.json` | Мутация `.env` запрещена; чтение — ask, не allow | Тесты вошли в exit 0. Рабочий `.env` не изменялся и не цитируется. | PASS контракта. Native enforcement Devin — NOT_PROVEN. |
| partial-tree | `test_check_no_partial_tree.py` | Пустая база, shallow, timeout и схлопывание не дают PASS | Файл вошёл в exit 0. Skip: строка 558, host не создаёт fixture symlink. | PASS кроме symlink-кейса (SKIP). Квалификация #13133 — NOT_VERIFIABLE. |
| debug handoff | `.devin/agents/py-test-bot/AGENT.md` строки 209–213 | RCA у debug, fix у authorized parent | Текст на месте. | PASS текста. Исполнение — NOT_PROVEN. |
| OpenCode fix | `.opencode/agent/bugfix.md`, `.github/workflows/opencode-pr-review.yml`, `opencode-triage.yml` | Write path выключен, workflow не вызывает installer | `write/edit/patch: false`, bash `deny`. Оба workflow — `workflow_dispatch` и echo disabled. Процесс OpenCode не запускался. | PASS отрицательной проверки. Executed — NOT_PROVEN. |

Причина NOT_VERIFIABLE для read-only audit и hash-only: во время приёмки в том же checkout появились несвязанные незакоммиченные правки IUPHAR/target classification (`src/bioetl/**`, `src/iuphar_target_class/**`, тесты и скрипты, mtime 2026-11-16 17:36–17:41 +0300). Они не входят в этот PR. Stash и `git checkout` по ним не делались. Проверка хеша дерева на таком checkout смешала бы чужой diff с main.

## Guardrails

Сохранено на `origin/main`:

- `.env`: `AGENTS.md` Env File Guardrail; `.gitignore` по-прежнему содержит `.env`, `.env.*`, `*.env` и исключение `!.env.example`. Diff `.gitignore` от audit SHA `cc441a7cc9d438e4c9c54b2ad01ee279a5a3a016` до `origin/main` пуст.
- `D:\github` и helper: `create_worktree.py`, как в AUD-001.
- Full-tree: checker и workflow из AUD-002/AUD-003.
- Runtime parity: `check_junie_mirror.py --check` exit 0. Обязательные зеркала не удалялись.
- Post-change: `POST_CHANGE_VALIDATION.md` остаётся владельцем процедуры в Canonical Precedence.
- OpenCode Phase 2 не активирована.

Бюджеты:

- `budget_guard.py --base cc441a7cc9d438e4c9c54b2ad01ee279a5a3a016 --tip origin/main` → exit 2, `ERROR`, `budget.evidence_unavailable` (реестра ещё нет на audit SHA). Это не PASS.
- Тот же guard `--base c3818114beca66129db6ca97e78196314d854308 --tip origin/main` → exit 1, единственный finding `budget.registry_change_requires_review` на `configs/quality/agent_guard_budget_surfaces.json`. Finding числового повышения лимита нет.
- Diff реестра: добавлены наблюдаемые поверхности `private_import_ratchet.yaml` и `vcr_cassette_size_budget.yaml`; `not_in_nav_baseline.txt` переведён в `line_exemptions`. Для этого kind рост множества — `exemption_scope_added` (`new <= old` иначе отказ).
- `debt_scorecard.yaml` от audit SHA: `total_loc` 6735 → 6693, `helper_function_ratio` 0.323 → 0.305.
- `duplication_complexity_exemptions.yaml`: снято исключение `src/memory/` (xenon / critical_check). Новых path-exemption в этом diff нет.
- `pyproject.toml` в том же диапазоне добавляет dev-зависимость `openpyxl`; это не потолок долга.

## Inventories, mirrors, SHA и CI

Раздельно:

- Локально до этого файла: `python -m scripts.docs generate-cleanup-inventory --check` — inventory synchronized, exit 0. После добавления паспорта и ссылки в `docs/reports/index.md` инвентарь обновлён тем же producer `--update` и входит в этот PR.
- Локально: `python scripts/ai/junie/check_junie_mirror.py --check` — exit 0. Зеркала `.junie/**` не удалялись.
- Head main, к которому привязаны наблюдения: `7e1cbcbd82ef156b29b12cec0947586d0d1a7b37`.
- CI этого приёмочного PR на момент коммита паспорта не запускался. Зелёный локальный check не объявляется CI. URL прогона, если он появится после push, не задним числом превращает более ранний SKIP/DEGRADED в PASS.

`report-module-coverage` не перезаписывался: исходники `src/bioetl` этим PR не меняются. Чужой dirty diff в coverage inventory не коммитится.

## Эффект (#13033)

Повтор `efficiency_baseline.py --instruction-refs b283d1759fbaedfb1efe731307ccbd0c8024eaa8 ffbc484dae248889de8e6aa3fc1ed512d209fdb1` совпал с
`docs/reports/generated/skill-efficiency-source-comparison.json`:
34 изменённых источника; группы Codex/Junie/Devin/shared по files, LF-bytes и lines совпали с зафиксированным baseline `b283d175` и after `ffbc484d`.

`runtime_metrics` снимка, все поля: `NOT_MEASURED`
(`loaded_sources`, `repeated_reads`, `tool_calls`, `tokens`, `elapsed_time`, `route_correctness`, `skipped_checks`, `task_quality`).

Рост LF-байтов (например Codex 124032 → 127530) не является расходом токенов и не является эффектом.

Один render Codex `prompt-input` показывает, что полное тело root попало в prompt, а полные тела runtime map и выбранных profile/skill — нет. Это одно наблюдение текущего бинаря, не парное baseline/after и не token usage. Живые парные запуски протокола D1/F1/C1/G1/A1/R1 не выполнялись.

Вердикт эффекта: UNKNOWN.

## Откат

Для каждого squash-commit выше: `git revert <sha>` новым commit. Без `--force`, без `reset --hard`, без `-m` (parent один; `-m` здесь неприменим). Чужие изменения, пришедшие позже, сохраняются, если revert не конфликтует. Конфликт разрешается отдельно и не снимает guardrails.

Репетиция revert не выполнялась: она изменила бы рабочее дерево и соседние незакоммиченные правки.

Откат адаптера оставляет запрет и явный `NOT_PROVEN`, а не вымышленный sandbox. OpenCode при откате остаётся выключенным. `.env` откатом этой серии не редактируется.

## Что сознательно не сделано

- Issue #13056 и дочерние issues не закрывались и не редактировались.
- Код, конфиги, бюджеты и `.env` не менялись.
- OpenCode и внешние сервисы не активировались.
- Хук `.cursor/hooks/gate.py` этот прогон не блокировал: `python.exe` на машине есть. Обхода хука не было.
