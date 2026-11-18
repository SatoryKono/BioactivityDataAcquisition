# Паспорт приёмки эпика #13056

**Owner:** BioETL Team
**Status:** acceptance record
**Class:** repo-only

## Текущий вердикт — PARTIAL

Проверка от 18 ноября 2026 года для
[#13056](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/13056).
Источник кода: `d414d98f6169b48e7dda6e9995a25027503c39f9`.
Этот документ не является разрешением закрыть эпик при незавершённой обязательной приёмке.

[PR #13133](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/13133)
фактически MERGED 16 ноября 2026, 20:57:43 UTC: head
`076944d012135ac488610ae7047d5c4c3dd9bc93`, merge
`5fd470a3d3ad5daef29af096c293b2de5002d864`.
Утверждение прежнего паспорта, что этот PR ещё открыт, относится к историческому
снимку `7e1cbcbd82ef156b29b12cec0947586d0d1a7b37` и больше не описывает текущее состояние.
[Прежний паспорт с трассировкой AUD-001–AUD-011](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/d414d98f6169b48e7dda6e9995a25027503c39f9/reports/review/ai-rules-epic-13056-acceptance.md) и все исходные измерения сохранены в Git и локальных архивах.

## Windows host

Windows host: непустой commit прошёл; локальный push достиг лимита 180 секунд и был заблокирован. Штатный аварийный rollback восстановил отсутствие owned callbacks; foreign hooks и env-файлы сохранены. Положительная host-приёмка и повторная установка остаются незавершёнными.

Подготовительные ошибки collector/локального remote сохранены отдельно от результата hooks.

## Восемь критериев эпика

| № | Критерий | Фактический результат и граница |
| --- | --- | --- |
| 1 | AUD-001–AUD-011 → задачи и evidence | Все 16 задач карты повторно проверены через GitHub API: CLOSED / COMPLETED. Историческая трассировка сохраняется; состояние задач само по себе не доказывает host-приёмку. |
| 2 | Runtime identity и загрузка | Codex и Devin проверены на текущем source; presence, resolver/render и execution разделены ниже. Junie и native enforcement остаются NOT_PROVEN. |
| 3 | Матрица сценариев | Windows: 391 passed / 6 skipped; WSL: 231 passed / 0 skipped. Это профильные contract/fixture tests. Полная WSL-приёмка на действующей конфигурации ещё NOT_RUN; host-результат учитывается отдельно. |
| 4 | Дисциплина статусов | ERROR, FAIL, SKIP, DEGRADED, timeout и INCONCLUSIVE сохранены. Неуспешная подготовка локального remote не названа отказом hooks. |
| 5 | Guardrails и бюджеты | Full-tree и сравнение бюджетов current base→HEAD проходят. Исторический budget guard возвращает ERROR на новой policy, отсутствующей в старом base; это не PASS исторического диапазона. Эта задача не повышает бюджеты. |
| 6 | Inventories, mirrors, SHA и CI | Static doctor, Codex–Junie parity и module source hash проходят на source SHA. Проверки документационного changeset и его CI должны быть зафиксированы отдельно; зелёные проверки старого source не являются приёмкой нового head. |
| 7 | Эффект #13033 | ASSESSED_INCONCLUSIVE. Сохранены исходные измерения; новые model turns не выполнялись. Причинная экономия контекста и улучшение качества не доказаны. |
| 8 | Проверенный откат | Изолированные installer/ownership/timeout tests прошли на обеих платформах. Общий host rollback и его последующая повторная квалификация требуют отдельного результата; наличие команды revert не заменяет репетицию. |

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
