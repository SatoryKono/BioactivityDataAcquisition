# Паспорт приёмки эпика #13056

**Owner:** BioETL Team
**Status:** acceptance record
**Class:** repo-only

## Текущий вердикт — PARTIAL

Проверка от 18 ноября 2026 года для
[#13056](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13056).
Источник первоначального прогона: `d414d98f6169b48e7dda6e9995a25027503c39f9`.
Последующее source-bound продолжение записано отдельно ниже.
Этот документ не является разрешением закрыть эпик при незавершённой обязательной приёмке.

[PR #13133](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/13133)
фактически MERGED 16 ноября 2026, 20:57:43 UTC: head
`076944d012135ac488610ae7047d5c4c3dd9bc93`, merge
`5fd470a3d3ad5daef29af096c293b2de5002d864`.
Утверждение прежнего паспорта, что этот PR ещё открыт, относится к историческому
снимку `7e1cbcbd82ef156b29b12cec0947586d0d1a7b37` и больше не описывает текущее состояние.
[Прежний паспорт с трассировкой AUD-001–AUD-011](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/d414d98f6169b48e7dda6e9995a25027503c39f9/reports/review/ai-rules-epic-13056-acceptance.md) и все исходные измерения сохранены в Git и локальных архивах.

## Windows host

Повтор на source `2b59d3e23cf09b614bde74377bc9ea5caeb82625`: непустой native
commit прошёл за 14,20 s; native локальный push заблокирован по timeout за 180,58 s.
Штатный rollback восстановил исходное отсутствие owned callbacks; foreign hooks,
их ACL и env-файлы сохранены. Положительная последовательность rollback/reinstall
не достигнута. Предыдущий единичный push за 179,64 s не доказывает устойчивость.

## WSL host и установленная причина задержки

Создан отдельный полный WSL-клон в разрешённом каталоге
`D:/github/BioactivityDataAcquisition-worktrees/epic-13056-wsl-20261118`.
Windows/WSL absolute gitfile несовместимы, поэтому это independent clone,
а не linked worktree. Пользователь отдельно разрешил только checkout `.env.example`
в этом клоне; остальные env-файлы не создавались и не менялись.

Native Git 2.43.0, Python 3.13.18, pre-commit 4.7.0 и новый явно подготовленный
Linux-cache проверены отдельно. Install/doctor/idempotence прошли, но это только
идентичность установки. Валидный непустой commit завершился timeout pre-commit
(41,13 s с внешним runner/cleanup при лимите события 30 s). Неверный заголовок
тоже остановился на pre-commit (44,41 s), поэтому commit-msg negative control
остаётся NOT_REACHED, а не PASS. Push и положительная повторная установка
не достигнуты. Owned rollback восстановил исходное отсутствие callbacks;
staged probe и все неуспешные captures сохранены.

Вне event watchdog полный framework protocol прошёл за 79,05 s. Git trace
зафиксировал девять preload-проходов по 14 779 `lstat`, каждый примерно 6,76–8,03 s:
повторные whole-tree diff на DrvFS — подтверждённый основной расход этого прогона.
Metadata refresh index не помог: diff до него 11,37 s, после 18,66 s;
диагностический `core.preloadindex=false` замедлил diff до 81,00 s и не сохранён
в Git config. Семантика staged index до/после идентична.

При корректном PATH project-interpreter все 46 environment probes здоровы:
2,749 s против 0,282 s для шести различных environments. Ранний probe с другим
PATH — невалидный диагностический контекст, не доказательство поломанного cache
Git event. Дедупликация probes не заявлена исправлением 79-секундного framework.
Checks, containment и лимиты 30/10/180 s не ослаблялись.

Подготовительные ошибки collector/локального remote сохранены отдельно от результата hooks.

## Восемь критериев эпика

| № | Критерий | Фактический результат и граница |
| --- | --- | --- |
| 1 | AUD-001–AUD-011 → задачи и evidence | Все 16 задач карты повторно проверены через GitHub API: CLOSED / COMPLETED. Историческая трассировка сохраняется; состояние задач само по себе не доказывает host-приёмку. |
| 2 | Runtime identity и загрузка | Codex и Devin проверены на текущем source; presence, resolver/render и execution разделены ниже. Junie и native enforcement остаются NOT_PROVEN. |
| 3 | Матрица сценариев | Windows: 391 passed / 6 skipped; WSL: 231 passed / 0 skipped. Это профильные contract/fixture tests. Полная native WSL-приёмка предпринята на новом клоне: commit timeout, positive push/reinstall NOT_REACHED; это отдельный FAIL host-последовательности. |
| 4 | Дисциплина статусов | ERROR, FAIL, SKIP, DEGRADED, timeout и INCONCLUSIVE сохранены. Неуспешная подготовка локального remote не названа отказом hooks. |
| 5 | Guardrails и бюджеты | Full-tree и сравнение бюджетов current base→HEAD проходят. Исторический budget guard возвращает ERROR на новой policy, отсутствующей в старом base; это не PASS исторического диапазона. Эта задача не повышает бюджеты. |
| 6 | Inventories, mirrors, SHA и CI | Static doctor, Codex–Junie parity и module source hash проходят на source SHA. CI на main `f444a6b8…`: runtime checks и bounded Proof-or-Stop ADMIT подтверждены ниже. Это не приёмка failing native host-последовательностей и не CI нового документационного head. |
| 7 | Эффект #13033 | ASSESSED_INCONCLUSIVE. Сохранены исходные измерения; новые model turns не выполнялись. Причинная экономия контекста и улучшение качества не доказаны. |
| 8 | Проверенный откат | Изолированные installer/ownership/timeout tests прошли на обеих платформах. Реальный rollback после timeout прошёл на Windows и WSL; исходное отсутствие owned callbacks восстановлено. Положительная последовательность reinstall/commit/push на обеих платформах не завершена. |

## CI принятого main и границы ADMIT

PR #13205 фактически merged другим процессом 18 ноября 2026, 14:10:57 UTC:
head `85b46ffce5ed2b07fc721b143287bdde3aa177a5`, merge/main
`f444a6b8061965e7075bea10d64322fa4c4aac42`. Эта сессия merge не выполняла.
Между host source `2b59d3e…` и этим main меняются только девять отчётных/generated
файлов; runtime, guards, pre-commit config и тесты идентичны. Это сравнение
содержимого не переносит измерения автоматически на другой head.

[Skills Consistency run 44323116672](https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/44323116672)
успешен именно на `f444a6b8061965e7075bea10d64322fa4c4aac42`.
Исходный artifact `ai-runtime-proof-44323116672-1` скачан; canonical bundle и
receipt digests совпали. `verification.json`: ADMIT, claim_qualified=true,
task_id `epic-13056-final-admission`, bundle digest
`ab8adb91ca98ef42733eb022b9b202d2bff7300b05228ae14bbecb81d23d857a`.
Scope: записанные CI-команды tests, governance light, docs links и source-only debt.
Это bounded CI admission, не успешная Windows/WSL host-квалификация и не
доказательство native AI enforcement. До устранения host timeout эпик OPEN.
CI нового документационного head оценивается отдельно после push.

Локальные captures продолжения, Git trace и original CI artifact сохранены в
`reports/local/epic-13056-host-acceptance-20261118/` основного checkout.

## Проверки на source SHA

Команды запускались через Windows `.venv-win`, а в WSL — через отдельную
`/home/fedor/.venvs/bioetl-hook-final-20261116/bin/python`.
Полные argv, время, exit codes, JUnit и логи сохранены в machine-local
`reports/local/epic-13056-closeout-20261118/` основного checkout. Это локальные
материалы, не публичные GitHub artifacts.

- Windows: installer, offline pre-commit, process deadlines, budget/operation/full-tree guards,
  hook receipts и Codex/Junie runtime contracts — 391 passed, 6 skipped, 452.60 s.
- WSL: installer, offline pre-commit, process deadlines, operation/budget/full-tree guards —
  231 passed, 0 skipped, 545.35 s. Этот набор уже Windows-набора; результаты не суммируются
  в число уникальных тестов.
- `doctor.py static --no-write --json`: exit 0.
- `doctor.py rules --no-write --json`: exit 2, NOT_PROVEN по контракту; не PASS native execution.
- `check_junie_mirror.py --check`: exit 0.
- `check_no_partial_tree.py --base origin/main --tip HEAD`: exit 0.
- `budget_guard.py --base origin/main --tip HEAD`: exit 0.
- `report-module-coverage --check --allow-missing-coverage-xml`: exit 0, без нового замера покрытия.
- Read-only architecture audit: 11 checks, 8 pass, 3 fail; mutation_detected=false.
  Не прошли `runtime_import_scc`, `hotspot_family_baseline`, `debt_governance_gates`.
  Весь прогон остаётся FAIL; результаты не исправлялись ручной правкой generated artifacts.
- Read-only pre-task: exit 1, DEGRADED; отсутствуют RAG chunks и timeline projections.
  Refresh и session notes не создавались. Восстановление MCP/RAG относится к отдельной программе.

Исторический budget guard для `c3818114..d414d98f` возвращает
`budget.evidence_unavailable`. Диагностика установила попытку прочитать из старого
base новую policy `configs/quality/external_resource_inventory_ci_complexity_baseline_20261118_review.json`.
Старый base этого файла не содержит. Причина ERROR установлена; полная проверка
исторических бюджетов этим наблюдением не заменяется.

## Runtime: что именно наблюдалось

| Runtime | Identity | Наблюдение | Что не доказано |
| --- | --- | --- | --- |
| Codex | `0.167.0-alpha.3.2`, binary SHA-256 `4f91ae86895ff124760d70ed1630e2354ca874765c9bb61ae524b600327efc17` | `debug prompt-input` exit 0: полное тело текущего AGENTS.md присутствует. Полные тела runtime map, выбранного audit profile и skill отсутствуют в initial render. | Native role registration, model obedience и permission enforcement. Root требует task-driven чтения runtime map; отсутствие автоматической вставки не заменяется вымышленной настройкой. |
| Devin | `3000.11.3 (9c803229faa4)`, binary SHA-256 `bd2704d32669887a15164725d043e2d3aa18c529920ebe341fb6b70eabac2d30` | `rules show AGENTS` exit 0: полное тело root разрешено resolver. | Session injection, выполнение моделью и native enforcement. |
| Junie | Default current pointer отсутствует | Shim не исполнялся, runtime не устанавливался. | Default runnable version, loading и execution — NOT_PROVEN. |
| OpenCode | Подчинённая отключённая поверхность | Write paths и automation не активировались. | Native loading/execution — NOT_PROVEN. |

Сырые prompt/config, секреты и пользовательский контекст не сохранялись.
Новых моделей, агентов или внешних оценщиков эта проверка не запускала.
Процедура повторения: [AI rule loading evidence](../../docs/05-operations/runbooks/ai-rules-loading.md).

## Измерения эффекта сохранены

Исходный source seed: `7d5f01d89cd112e269fc7ea548fb42164c226af3`.
Sealed report SHA-256:
`fbe3abe3ced61ae8e4a58fdeafe86451fba7e7e607dc5aaedc37a987f63389e7`.
Наблюдались 20 native launches; 17 штатных завершений, два timeout и ошибка collector.
Фактические usage fields доступны в 17 записях. Эти наблюдения относятся к
сохранённому source seed и не перенесены на текущий source.
Вердикт `MEASUREMENTS_SEALED_INCONCLUSIVE_NOT_EPIC_ADMISSION` сохранён.

## Условия закрытия

Нужно завершить host commit/push/rollback/reinstall и отдельную WSL-приёмку,
разобрать обязательные неуспешные проверки, проверить документационные generated
artifacts, получить CI и применимый Proof-or-Stop ADMIT на итоговом head.
После этого обновить восемь строк матрицы по фактическим доказательствам и
опубликовать итоговый комментарий в issue. До выполнения этих условий #13056 OPEN.

Env-файлы, чужие изменения и callbacks сохраняются. Все Git-деревья остаются внутри
`D:/github`; бюджеты, exemptions и deadlines не увеличиваются. Merge требует
отдельного указания пользователя. Native AI adapters остаются OFF/NOT_PROVEN.

Машиночитаемое [локальное evidence](ai-rules-epic-13056-evidence.json) содержит source-bound результаты и ограничения; его trust tier — local_single_host.

## Диагностика native push

Отказы повторились в двух полных host-попытках и отдельном запуске с Git trace. Отдельный offline framework protocol прошёл за 100.27 s; прямой диагностический вызов pipeline с guards и containment прошёл за 127.97 s. Настоящий native Git push через тот же механизм с синтетическими system checks прошёл за 21.60 s. Эти результаты исключают общий отказ native pipe dispatch, но не доказывают причину превышения срока на полной конфигурации. Измерения повторных environment probes: 46 probes — 2.49 s, 6 различных окружений — 0.19 s. Такой разницы недостаточно для доказательства причины 180-секундного отказа; production code, лимиты и обязательные проверки ради гипотезы не менялись. Полный native push остаётся BLOCKED, после каждой диагностической установки восстановлено исходное отсутствие owned callbacks.

## Последующие проверки и исправленный drift

Первый read-only architecture audit сохранён как FAIL. При отдельном focused повторе SCC — 4 passed. Диагностика debt gate установила единственный failing gate `generated_artifact_drift`: устарели `config_surface_backlog` и `hotspot_family_baseline`. Оба отчёта и зависимая проекция debt gates обновлены owning generators. Последующие family/debt `--check` и budget guard для working tree прошли. Измеренный LOC в отчёте отражает уже существующий код; budgets, thresholds и exemptions не менялись. Эти повторы не переименовывают первый полный аудит в PASS.

Для pre-refresh documentation working tree созданы канонические plan, docs receipt и bundle; verifier и локальный closeout facade вернули STOP / claim_qualified=false. В bundle недоставало required receipts `tests`, `governance`, `debt`; local_single_host остаётся отдельной trust degradation. Это отказ приёмки, не разрешение завершить эпик. После последующих generated/report изменений данный bundle не является admission нового состояния; нужен свежий source-bound CI/closeout.


## Кандидат параллельного push и metadata-only commit-msg

Продолжение на source `30c1bfcf1dc291e268f64e72b2a2fee9072caa2e`; эпик остаётся **PARTIAL / OPEN**.
Четыре исходные независимые pre-push команды исполняются одновременно только
при точном совпадении квалифицированных команд и framework 4.7.0. Framework
сохраняет фильтрацию, порядок вывода, exit codes и mutation-detection diffs;
последующие hooks ждут завершения группы. Изменение контракта возвращает serial
execution. Конфигурационный набор hooks не сокращён.

Семантический commit-msg adapter исполняет исходный parser в выбранном project
Python. Квалификация проверяет семь исходных package/helper файлов, manifest,
команду, interpreter и отсутствие foreign message callbacks. Исполняются именно
проверенные source bytes, без доверия к stale bytecode. Этот metadata-only checker
не сканирует unstaged source: область явно ограничена Git-метаданными. Остальные
hooks сохраняют обычный путь. Каждый свежий index/HEAD/base/env bookend ждёт все
независимые read-only probes; защиты changed-index, env и history сохраняются.

Windows: install/idempotence, неверный header с отказом именно commit-msg,
непустой commit/push, malformed push protocol, rollback, reinstall и второй
непустой commit/push прошли. После финального rollback восстановлено исходное
отсутствие owned callbacks. Кандидат установлен только в private process-scoped
hooksPath внутри исходного common metadata; это **изолированная квалификация,
не production activation**. Исходные callbacks форвардились без изменения,
их bytes/ACL и env-файлы сохранены.

| Native hook в порядке событий | Секунды | Exit code |
| --- | --- | --- |
| pre-commit | 17.85 | 0 |
| commit-msg | 6.82 | 1 |
| pre-commit | 16.91 | 0 |
| commit-msg | 6.0 | 0 |
| pre-push | 114.29 | 0 |
| pre-commit | 23.01 | 0 |
| commit-msg | 9.08 | 0 |
| pre-push | 103.68 | 0 |

Лимиты событий остаются 30/10/180 s; whole Git command включает дополнительные
стадии и не сравнивается с лимитом одного hook. Первые неудачные кандидаты
сохранены: reinstall commit-msg timeout; timeout следующего correct message;
отдельный non-fast-forward fixture rejection после продвижения main. Последний
не является отказом configured checks и не доказывает полный push.

Локальные overlapping наборы: 96 passed / 3 skipped, receipts 44 passed / 1 skipped,
runtime/installation/workflow 50 passed / 1 skipped, source-bytes message tests
16 passed. Это проверки рабочего кандидата до коммитов, а не CI нового head и
не сумма уникальных тестов. POSIX-only пропуски явно сохранены. Docs links/drift,
cleanup inventory check, runtime parity, full-tree, budget и source-only debt
прошли; scripts inventory обновлён штатным генератором после интеграции main.

WSL: один heartbeat выполнился, но следующая попытка metadata profiling вернула
`Wsl/Service/0x8007274c` до исполнения скрипта. Owned callbacks отсутствуют,
staged probe и клон сохранены. Службы не перезапускались и не останавливались.
Новый кандидат в WSL **NOT_RUN**; прежний DrvFS pre-commit timeout остаётся
неустранённым. Windows sequence не заменяет эту границу и не закрывает #13056.

CI итогового публикуемого head и применимый closeout оцениваются отдельно;
исторические ADMIT, STOP и INCONCLUSIVE выше не переименовываются.
