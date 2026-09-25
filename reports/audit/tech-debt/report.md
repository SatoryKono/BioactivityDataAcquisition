# Technical debt audit

- prompt: `prompt.audit.tech-debt` 1.3.0
- HEAD: `32d77a51e556de60d6dc0daf871a442becc709c5`
- SCOPE: `reports/quality/`, `configs/quality/`, `src/`
- MODE: `audit` / AUDIT_MODE: `full` / REQUIRE_GH_TRACKING: `false`
- Дата проверки (UTC): 2026-09-25T08:50:00Z
- surface_score: **2** (шкала карточки домена: основной долг под гейтами; часть свидетельств и shrink-потолок не закрыты). Это не оценка 0–3 отдельных находок.

## Итог

Программные debt-гейты в зафиксированном `reports/quality/debt-governance-gates.json` зелёные: **46 pass / 0 warn / 0 fail**, `release_gate_status=passing`, `stale_artifacts` все `false`, `budget_growth_allowed=false`, baseline exemptions **0**. Непокрытых и неизмеренных модулей **0**.

Канонический реестр аудита при этом **не сходится** с этими артефактами (`validate-technical-debt-audit` exit 1). Единственный измеримый просад интегрального балла — `composition_util` **0.9661** при диагностическом потолке **0.95** (`src/bioetl/composition`: **285** модулей при closeout-потолке **280**, жёсткий cap **295** не превышен). Поднимать бюджеты, exemptions и пороги нельзя.

## Находки

| id | priority | status | суть |
| --- | --- | --- | --- |
| TD-001 | P1 | PROVEN | Семантика и SHA-256 current audit устарели относительно live scorecard / inventory / gates |
| TD-002 | P1 | PROVEN | Composition 285 > 280 и util 0.9661 > 0.95 при shrink-only cap 295 |
| TD-003 | P1 | PROVEN | Current-state и closeout всё ещё цитируют score 10.00, 2479 модулей и 45 гейтов |

## TD-001 — реестр аудита не перепривязан

`python -m scripts.engineering.qa validate-technical-debt-audit --json` @ 2026-09-25T08:50:00Z, SCOPE=`reports/quality` + `configs/quality`, exit **1**:

- `current audit evidence_surface_sha256 is stale`
- `current audit semantic summary is stale`
- нет headline: `46 pass / 0 fail`, `source_module_count: **2499**`, `fully_covered: **2491**`, `= 2499 == source_module_count`

В `reports/quality/total-tech-debt-audit-main-current.md` машинный блок (строки 66–94) пишет integral **10.0** / `excellent`, **2479** модулей, fully covered **2471**, **45** гейтов. Executive summary того же файла пишет integral **9.47** и **2493** модуля. Живые артефакты:

- `architecture-quality-scorecard.json`: integral **9.47**, `good_targeted_improvements`, `source_module_count` **2499**
- `module-coverage-inventory.json` summary: **2499** = fully **2491** + partial **7** + no_executable **1**
- `debt-governance-gates.json` summary: gate_count **46**, pass **46**, fail **0**, integral **9.47**

Реестр `configs/quality/technical_debt_audit_registry.yaml` держит `audited_commit_sha` `09ab9ac286bacb7eee3324e950603539a5c62ee6`, не HEAD. Это drift свидетельства, не рост бюджета.

Требование: `REQ-GOV-012` / `QG-DEBT-001`. Закрытие: validator exit 0 без увеличения лимитов.

## TD-002 — composition выше shrink-потолка

Подсчёт `src/bioetl/composition/**/*.py`: **285**. Cap в `configs/quality/package_cohesion_budget.yaml:21` = **295** (комментарий строк 18–20 всё ещё говорит «live 279» и util ≤ 0.95). `285/295 = 0.9661`.

`tests/architecture/test_issue_10595_composition_util_shrink.py:71-75` требует `live <= 280` и `live/cap <= 0.95`, а также `max_modules <= 295`. Жёсткий S7-тест (`len <= max_modules`) при 285 ещё проходит; диагностический штраф уже включён.

`architecture_quality_scoring.py`: `_over_cap_penalty` при util > 0.95 снимает **3.5** с `composition_di` (балл **6.5**) и **3.0** с `debt_burden_evolution_friction` (балл **7.0**). Остальные 8 категорий scorecard = **10.0**. Вклад в integral: `0.65 + 0.42` вместо `1.00 + 0.60` → **9.47** вместо 10.00. `families_at_budget_count=0`, layer violations **0**.

Оплата: убрать не меньше 5 модулей composition. `max_modules` не поднимать.

## TD-003 — нарратив и pin отстают от JSON

`docs/02-architecture/current-state-inventory.md:39-47` пишет score ``10.00`` (`excellent`), **2479** модулей, **2471** fully covered, **45** gates. Строка 305 того же файла ещё упоминает **295** partially covered — это не summary инвентаря (там partial **7**).

`tests/architecture/test_tech_debt_issues_5752_5755_closeout.py:116-117` ждёт пустой `validate_technical_debt_audit_registry`. Строка **141** пинит `gate_count == 45`. Строка **171** ждёт в current-state текст живого integral (сейчас `9.47`).

`tests/architecture/test_arch_s4_s9_gates.py` (`test_s8_domain_framework_import_ratchet`) требует в том же документе backticks живых `source_module_count` и `fully_covered` (**2499**, **2491**). Их в документе нет.

Исправление pin 45 → равенство committed `summary.gate_count` не ослабляет порог качества и не поднимает бюджет. Удалять assert нельзя.

## Контролируемый остаток (не находки)

Сырые TODO/FIXME не считались. Ниже — метрики внутри действующих ratchet, без превышения:

| поверхность | факт | лимит | чтение |
| --- | --- | --- | --- |
| exemptions `debt_scorecard.yaml` baseline | 0 | 0 | исторические 48 сняты |
| transition/sunset/expired compat | 0/0/0 | 0 | twin pairs 0 |
| uncovered / unmeasured modules | 0 / 0 | 0 | partial **7** гейт не обнуляет |
| public entrypoints / export facades | 12 / 3 | 12 / 3 | на потолке, не выше |
| constructor waiver | 1 (`QuarantineEntry`, expiry 2026-12-31) | shrink-only | intentional, не просрочен |
| zero-import untriaged | 0 | 0 | classified residue 2 на потолке |
| config inconsistent parameters | 0 | 0 | unique parameters 418/418 |
| hotspot budget warnings | 0 | 0 | families at budget 0 |
| layer violations | 0 | 0 | |

Частичное покрытие (не нарушение zero-uncovered ratchet): 7 модулей, missing lines 1–9. Самые низкие доли: `src/bioetl/infrastructure/adapters/health_check_provider_mixin.py` 80% (9 строк), `src/bioetl/composition/archive_assessment.py` 90.16% (6 строк). Отдельного `REQ-*` на обнуление partial нет → в `findings` не включены.

## Тренд

Integral в нарративе аудита завышен (10.0 / excellent) относительно live **9.47**. Расхождение целиком объясняется штрафом `composition_util`, а не падением слоёв, compat или coverage-uncovered. Каталог гейтов вырос 45 → 46 без fail; это смена состава отчёта, не разрешение на рост лимитов. Число модулей в нарративе (2479 и 2493) ниже live **2499**.

## Не запускалось

- `report-debt-governance-gates --check`: entrypoint пишет proof receipt; вердикт снят с committed JSON, а не с повторной сборки.
- Docker / monitoring не поднимались.
- Счётчики TODO/FIXME/XXX как долг не использовались.

## Запрет

Любое поднятие tech-debt / quality budgets, exemptions, hotspot thresholds или `max_modules` для «зелёного» прогона — отклоняется. Допустимы только shrink или обновление свидетельств до уже зафиксированных лимитов.
