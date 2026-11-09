# Карточка 0.10: эксперимент «разделение class-lane»

**Статус:** черновик для утверждения владельцем. Утверждение чисел и старт эксперимента этой карточкой не выполняются.
**Issue:** [#12832](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12832) (CI1-05).
**Основание:** правило 0.10 — данные, метрики, допуски, n и правило остановки фиксируются до эксперимента; исходы ровно три: принять, отклонить, недостаточно данных. Правило не подбирается после результата.
**Исходные пункты:** план этапов 1–4, п. 1.1; правило 0.10.
**Снимок карты:** job `class-lane` в [`.github/workflows/pr-required.yml`](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/d32fd1f691644c6a549ef862c48e47ef68fd8a53/.github/workflows/pr-required.yml#L294-L793) на SHA `d32fd1f691644c6a549ef862c48e47ef68fd8a53`, строки 294–793. Тридцать шагов перечислены в разделе 7.

Карточка задаёт протокол измерения. Ожидаемый результат эксперимента в ней не утверждается.

Шаблон в [спецификации инструментирования](../reports/audit/phase-instrumentation-spec.md) (§5) к этому эксперименту не применяется: там другая цель. Карточка эксперимента 1.1 — этот документ.

## 1. Механизм

Один job `class-lane` разделяется на шесть независимых job по уже заданным гейтам `CLASS_LANE` в `scripts/engineering/ci/pr_lane_results.py` (`GATE_OWNERS` / `OWNER_STEPS`): `generated-artifacts`, `lint-arch`, `tests`, `type-checking`, `security`, `duplication`.

Каждый новый job получает собственную копию шагов Checkout и Set up Python + uv. Шаги schema, parity и shadow-compare входят в карту (строки 3, 4 и 13). Код workflow этой карточкой не меняется.

## 2. Метрики и допуски

Единица наблюдения: одна терминальная попытка workflow `pr-required` по API Actions, включая отмену до старта `pr-gate-complete`. Повтор `run_attempt` — отдельное наблюдение. Для отменённой попытки сохраняются её заключение и доступные времена. Если `completed_at` гейта отсутствует, значение кандидата `T_feedback` считается отсутствующим. Число таких попыток и отмен публикуется отдельно, а порядок учёта отсутствующих значений при сравнении метрик утверждается владельцем до сбора.

| Поле | Значение |
| --- | --- |
| Основная метрика | `T_feedback`: p50 и p95 длительности прогона. Операционное определение часов — **для утверждения владельцем**: кандидат — `run_started_at` прогона до `completed_at` job `pr-gate-complete` по API Actions. |
| Вторичная метрика `C_CI` | Имя зафиксировано постановкой. Единица и формула — **для утверждения владельцем**. |
| Порог X (допустимое изменение `C_CI`) | **для утверждения владельцем** |
| Размер выборки n | **для утверждения владельцем**. n задаётся отдельно на каждый класс изменений. |
| Правило остановки сбора | **для утверждения владельцем** |

Правила, которые уже фиксируются и не откладываются на утверждение чисел:

- В выборку входят таймауты, отмены, повторы и неполные данные.
- До сбора владелец утверждает, как отличать полные повторы от частичных и как учитывать их в p50 и p95. Все попытки сохраняются в журнале наблюдений.
- Для утверждения владельцем: контрольная выборка использует исходный граф с `class-lane`, экспериментальная — итоговый граф с шестью владельцами. Состав выборок и правило отнесения к графу фиксируются до сбора по версии графа и SHA workflow. Прогоны промежуточных фаз регистрируются отдельно для проверки миграции и не участвуют в сравнении двух графов.
- Отказы из статистики не исключаются.
- Наблюдение без полного набора полей идентичности остаётся в выборке как неполное, а не удаляется.
- Сбор начинается после записи прохождения ворот раздела 5. До этой записи прогоны в выборку эксперимента не входят.

## 3. Классы изменений

Класс прогона — один из четырёх: `src-only`, `docs-only`, `config`, `full`. Границы путей — **для утверждения владельцем**. Кандидат разметки, пока владелец не заменит его:

- `docs-only`: каждый путь diff лежит в `docs/` или равен `mkdocs.yml`.
- `src-only`: каждый путь лежит в `src/` или `tests/`.
- `config`: каждый путь лежит в `.github/` или `configs/`, либо равен `pyproject.toml`, `uv.lock` или `.pre-commit-config.yaml`.
- `full`: diff попадает больше чем в один класс либо не попадает ни в один.

Смесь классов записывается как `full`. Класс не перекодируется после расчёта метрик.

## 4. Идентичность и полнота

На каждое новое исполнение записываются: `run_id`, `run_attempt`, `head_sha`, `base_sha`, путь workflow и SHA файла workflow, pin каждой `uses:`-action этого job, SHA, который реально получил шаг Checkout.

Независимое U: полнота множества шагов сверяется по API Actions jobs/steps для конкретного `run_attempt`. `assert_step_outcomes` отдельно проверяет исходы из словаря, переданного recorder, по обязательным шагам владельца.

Диспозиция 0.2: сравниваются множества с кратностью, а не присутствие без числа копий. Акт `0.2_checkout_provenance` в фазе 0 остаётся `PARTIAL`. Запись checkout SHA на новое исполнение этот статус задним числом не меняет.

## 5. Ворота до старта

Все три пункта не пройдены. Эксперимент до их записи не начинается.

- [ ] (а) Наблюдаемый запрет merge для failure, cancel, missing и skip. Снятие `UNAVAILABLE` 0.5 — план [CI1-07 / #12834](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12834), текст плана на SHA `8981685bf4d743e794f5c41b004a50bb47be792e` (файл снят с дерева коммитом `#12838`). В акте фазы 0 пункт `0.5_live_ruleset` = `BLOCKED`.
- [ ] (б) Фазовый профиль class-lane. Входы: [CI1-01 / #12828](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12828), отчёт [`phase-profile-41570319793.md`](../reports/audit/phase-profile-41570319793.md) (статус PARTIAL: wall и фазы setup/call/teardown = `UNAVAILABLE`); [CI1-04 / #12831](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12831), спецификация [`phase-instrumentation-spec.md`](../reports/audit/phase-instrumentation-spec.md).
- [ ] (в) Фазовый протокол миграции агрегатора из base-ветки с откатом по фазам (v4.1 п. 1.1, R3-CI-01). Текст протокола — раздел 9. Исполнение не начато.

## 6. Правила исходов

Исход один на всю выборку после остановки сбора.

- **ПРИНЯТЬ:** полнота подтверждена, и семантика сохранена, и ограничения не ослаблены, и эффект по основной метрике соответствует утверждённому критерию, и прочие метрики в допуске.
- **ОТКЛОНИТЬ:** доказанное нарушение любого из условий принятия.
- **НЕДОСТАТОЧНО ДАННЫХ:** по утверждённым n и правилу статистики вывод не получается, нарушения при этом не доказано.

Пока X, n и правило статистики не утверждены, исход ПРИНЯТЬ не вычисляется.

## 7. Карта переноса

Статическая карта 0.3: тридцать шагов текущего job. Колонка «новый job» — назначенный исполнитель при разделении. Колонка агрегации ссылается на правило ниже.

Правило агрегации, которое карта сохраняет:

- Шаг из `OWNER_STEPS` при `decision=required` имеет исход `success`. `missing`, `failure` и `cancelled` успехом не являются (`assert_step_outcomes`).
- Шаг вне `OWNER_STEPS` в JSON исходов шага `record` не входит. Его `failure` валит job. Исключение: `osv-scan` помечен `continue-on-error`; обязательный исход безопасности — шаг `osv-gate`.
- Сегодня все гейты class-lane свёрнуты в один `--job-result class-lane=`. После разделения агрегатор получает отдельный `--job-result` на каждый новый job. До выполнения ворот (в) этот вызов не меняется.

| # | Проверка | Шаг | id | Новый job | Артефакт |
| --- | --- | --- | --- | --- | --- |
| 1 | общий вход шести гейтов | Checkout | `checkout` | копия в каждом из шести job | checkout `head_sha`, `fetch-depth: 0` |
| 2 | общий вход шести гейтов | Set up Python + uv | `setup-python` | копия в каждом из шести job | action pin `e890a12b5232f1feb50722de6433c7391bc30a7d` |
| 3 | `generated-artifacts` | Check generated schema artifacts | `schema-artifacts` | `generated-artifacts` | код шага, отдельного файла нет |
| 4 | `generated-artifacts` | Verify schema parity | `schema-parity` | `generated-artifacts` | `reports/quality/physical-schema-parity.xml` |
| 5 | `generated-artifacts` | Upload physical schema parity evidence | — | `generated-artifacts` | artifact `physical-schema-parity-<sha>` |
| 6 | `lint-arch` | Ruff check | `ruff` | `lint-arch` | аннотации `ruff` |
| 7 | `lint-arch` | Ruff format | `ruff-format` | `lint-arch` | код шага |
| 8 | `lint-arch` | Ruff isort | `ruff-isort` | `lint-arch` | аннотации `ruff` |
| 9 | `lint-arch` | C901 governance | `c901` | `lint-arch` | baseline `scripts/engineering/baselines/c901_baseline.json` (чтение) |
| 10 | `lint-arch` | Import contracts | `lint-imports` | `lint-arch` | код шага |
| 11 | `lint-arch` | Architecture pytest slice | `arch-pytest` | `lint-arch` | отчёты `reports/quality`, receipt `arch` |
| 12 | `tests` | Affected pytest | `affected-pytest` | `tests` | `reports/quality/affected-tests.txt` и дедуплицированный список |
| 13 | `tests` | Shadow compare impact selection | `impact-shadow-compare` | `tests` | `reports/quality/impact-shadow-compare.json` |
| 14 | `type-checking` | Restore mypy cache | — | `type-checking` | `.mypy_cache` |
| 15 | `type-checking` | Run mypy (strict mode, full gate) | `mypy` | `type-checking` | `reports/mypy_strict.log`, `reports/mypy_strict.exit_code` |
| 16 | `type-checking` | Verify NewType and Protocol usage in domain layer | `newtype-protocol` | `type-checking` | stdout шага |
| 17 | `type-checking` | Check for Any type usage in domain/application layers | `any-usage` | `type-checking` | stdout шага |
| 18 | `security` | Run detect-secrets baseline check | `detect-secrets` | `security` | код шага |
| 19 | `security` | Run pip-audit | `pip-audit` | `security` | код шага |
| 20 | `security` | Run Bandit | `bandit` | `security` | код шага |
| 21 | `security` | Run Gitleaks | `gitleaks` | `security` | код шага |
| 22 | `security` | Run OSV-Scanner | `osv-scan` | `security` | `osv-results.json` |
| 23 | `security` | Fail on HIGH/CRITICAL OSV findings | `osv-gate` | `security` | код шага |
| 24 | `duplication` | Validate duplication/complexity exemption registry | `duplication-exemptions` | `duplication` | код шага |
| 25 | `duplication` | Install Node.js | `setup-node` | `duplication` | кэш npm `.github/tooling/jscpd/package-lock.json` |
| 26 | `duplication` | Run jscpd for duplication detection | `jscpd` | `duplication` | `reports/jscpd` |
| 27 | `duplication` | Enforce BioETL hotspot duplication zero ratchet | `duplication-hotspots` | `duplication` | `reports/quality/hotspot-duplication-baseline.json`, `.md` |
| 28 | `duplication` | Upload hotspot duplication report | — | `duplication` | artifact `hotspot-duplication-<sha>` |
| 29 | `duplication` | Check constructor argument counts | `constructor-args` | `duplication` | код шага |
| 30 | запись исходов | Record required step outcomes | `record` | отдельный recorder в каждом новом job | `reports/quality/lane-step-outcomes.json` |

Строки 1, 2 и 30 имеют кратность больше единицы: checkout и setup копируются в шесть job, recorder — в каждый новый job. Это и есть учёт кратности из диспозиции 0.2.

## 8. Акты фазы 0

- Решение фазы 0 от 2026-11-06, статус `CLOSED_RESCOPED`: [PR #12788](https://github.com/SatoryKono/BioactivityDataAcquisition/pull/12788).
- Акт закрытия: [`docs/reports/ci/stage0_closure_report.md`](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/reports/ci/stage0_closure_report.md). Пункт `0.3_dag_phases` = `INHERITED_OBSERVATIONAL`. Пункт `0.10_pre_experiment_protocol` = `PARTIAL`. Пункт `0.5_live_ruleset` = `BLOCKED`. Пункт `0.2_checkout_provenance` = `PARTIAL`.
- Машинный акт: [`docs/reports/ci/stage0_closure.json`](https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/reports/ci/stage0_closure.json).
- Статическая матрица 0.4 (другое сопоставление, не карта 30 шагов): [`docs/ci/gate-platform-matrix-full.md`](gate-platform-matrix-full.md), [CI1-03 / #12830](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12830).

## 9. Протокол миграции агрегатора и откат

Протокол до старта, не описание выполненной миграции.

1. До переноса шагов доставить в базовую ветку совместимую версию агрегатора. `pr-gate-complete` загружает его с base SHA, поэтому подготовительный PR сохраняет действующий граф. По умолчанию действуют текущие `GATE_OWNERS` и `OWNER_STEPS`. Переходный контракт должен явно задавать карту владельцев и набор шагов для каждого графа. Выбор контракта проверяется по версии графа, которую передаёт workflow. В каждом графе у обязательного гейта один владелец.
2. Фаза на один гейт переносит его шаги из раздела 7 вместе с копией Checkout и Setup. В той же фазе recorder нового job получает свой `--owner` и набор шагов, а recorder `class-lane` проверяет оставшиеся шаги. Агрегатор использует карту именно этой фазы и требует результат соответствующего владельца для каждого `required` гейта. `skipped` без основания `not_applicable` успехом не считается.
3. Перед следующим переносом сквозной PR-прогон с агрегатором из базовой ветки подтверждает случаи `required` и `not_applicable`, включая блокировку при пропущенном обязательном шаге. Совмещение двух фаз в одном PR не делается.
4. Последняя фаза удаляет пустой `class-lane` после сквозной проверки карты всех шести владельцев. Она передаёт шесть результатов через `--job-result` и использует согласованную версию графа.
5. Откат фазы восстанавливает предыдущий граф job вместе с его версией, входами агрегатора и настройками recorder. Совместимый агрегатор сохраняется на базовой ветке. Уже собранные наблюдения сохраняются и в новую выборку не переносятся.

Пороги, membership тестов, `needs` успеха и каталог обязательных проверок протокол не ослабляет.
