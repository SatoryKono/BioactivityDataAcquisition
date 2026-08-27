# Technical debt audit

| Field | Value |
| --- | --- |
| `domain_id` | `tech-debt` |
| `prompt_id` | `prompt.audit.tech-debt` |
| `version` | `1.2.0` |
| `MODE` | `audit` |
| `AUDIT_MODE` | `full` |
| `LANGUAGE` | `ru` |
| `REQUIRE_GH_TRACKING` | `false` |
| `SCOPE` | `reports/quality/` `configs/quality/` `src/` |
| `requested_HEAD` | `5af9180c354e4406da4bfdf17d94d6c8efee6aaa` |
| `origin/main` (на момент аудита) | `5af9180c354e4406da4bfdf17d94d6c8efee6aaa` |
| `audited_on` | `2026-08-27` |
| `surface_score` | **2** / 3 |
| `blocked` | `false` |
| `debt_outcome` | `unchanged` (только артефакты аудита) |
| `debt_budget_policy` | **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ** бюджеты / exemptions / hotspot caps |

Легенда `surface_score` (карточка tech-debt): 3 = долг с owner/risk/effort и новый код не хуже baseline; 2 = основной долг под контролем, часть пунктов informal; 1 = suppressions/workarounds без системного управления **или** материальных дыр в enforcement; 0 = критическое накопление, изменения небезопасны.

Оценка **2**: exemption-долг = 0, hotspot family coverage floors **pass** (5/5), inventory валидный JSON, live `source_tree_sha256` = `13b38110…` совпадает с inventory. Материальных `current>max` в scorecard/gates/closeout **нет**. Остаются honesty/drift: на пине `5af9180c` remote-main baseline держит чужой inventory hash; committed gates рисуют `generated_artifact_drift=0` и `budget_no_growth=not_evaluated` как `pass`; freeze-метрики на потолке.

## Pin vs working tree (не чинить)

Запрошенный HEAD: `5af9180c`. В начале сессии `reports/quality/` был dirty (4 файла). Аудитор **не** регенерировал и **не** коммитил их.

| Поверхность | На пине `5af9180c` (git show) | Dirty WT (наблюдение) |
| --- | --- | --- |
| `module-coverage-inventory.json` `source_tree_sha256` | `13b38110c2c0b4e1e3444894a09a76ce1bd560893ffa274e06526cf8ed2a6eea` | тот же (файл не dirty); live compute совпал |
| `architecture-debt-remote-main-baseline.json` inventory hash | `79a04203a43ce8e7e5d12ed105e27894a206ceeb3117d52d7ccd79a614383173` | `13b38110…` |
| baseline `remote_main_sha` / fingerprint | `813553ca…` / `1c7fc338…` | `5af9180c…` / `4603631c…` |
| `debt-governance-gates.json` `budget_increase_count` | `not_evaluated_without_changed_from_ref` + `status=pass` | `0` + `status=pass` |
| `generated_artifact_drift` | `count=0` `pass` | кратко `count=1` `fail`, затем снова `0` `pass` |
| `total-tech-debt-audit-main-current.md` SHA | `8472592a…` при заявлении 45/45 | не входило в 4 dirty файла |

Dirty files: `architecture-debt-remote-main-baseline.json/.md`, `debt-governance-gates.json/.md`. Baseline `dirty_closeout_guard.expected_output=""` нарушен, пока эти файлы unstaged.

Позже (вне этого аудитора) локальный HEAD ушёл на `a152047e` (`acb1922a88` re-pin/regen). Это **не** remediation данного аудита.

## Executive summary

1. **P1.** На `5af9180c` канонический inventory (`13b38110`) **не равен** hash внутри remote-main baseline (`79a04203`, revision `813553ca`). Gates при этом `generated_artifact_drift=0` / `remote_main_architecture_debt_baseline=pass`. Scorecard honesty: drift gate не сверяет embedded inventory hash с live inventory.
2. **P1.** Dirty regen тех же артефактов сдвинул fingerprint `1c7fc338` → `4603631c` и оценил `budget_increase_count=0`. Не коммитить как closeout: `dirty_closeout_guard` требует пустой `git status --porcelain`.
3. **P1.** На пине gate `debt_scorecard_budget_no_growth` = `not_evaluated_without_changed_from_ref` при `status=pass`. Playbook `#8714`: bare `--check` не доказывает no-growth.
4. Scan `current_count>max_count` / gates `current>limit` / `*closeout*.json` current>max: **0** нарушений. Не предлагать поднять caps.
5. Управляемый freeze (не дефект, cost-of-change): config 27/27 и 419/419; control-plane fan-in 2/2; lazy-import 97/97 (target 60); private-import 15/15; public entrypoints 12; facades 4/4.

**REJECTED_POLICY:** любое повышение `max_count` / exemptions / hotspot thresholds / family caps.

## Trend (без предложения поднять лимиты)

| Сигнал | Исторически | На пине `5af9180c` / live | Направление |
| --- | --- | --- | --- |
| Architecture metric exemptions | 48 (Q4-2025) | 0 (пустые registries) | улучшение |
| Architecture integral | — | 9.41 `good_targeted_improvements` | hold |
| Hotspot family coverage floors | fail 4/5 (аудит 2026-08-26) | **pass 5/5** | улучшение |
| Inventory JSON conflict | `<<<<<<<` (аудит 2026-08-26) | валидный JSON | улучшение |
| Unmeasured modules | 84 до #9678 | 0 (inventory + live-residual 2026-08-27) | улучшение |
| Debt-governance gates (committed pin) | 45/45 | 45/45, но baseline hash чужой | **honesty drift** |
| `budget_no_growth` на пине | — | `not_evaluated` + pass | слабое доказательство |
| Transition/sunset/expired compat | >0 historically | 0/0/0 | улучшение |
| Closeout `current>max` | — | 0 hits | hold |
| Lazy imports | — | 97/97, target 60 | freeze, paydown не завершён |
| Supporting scripts zero-ref | 32 → 15 max | current 0 / max 15 | leftover cap, не рост |

## Classification

| Класс | Состояние |
| --- | --- |
| CI / generated artifacts | P1 hash mismatch baseline↔inventory; dirty closeout; `not_evaluated` pass |
| Tests / coverage | Hotspot floors pass; branch tail 552 files <85% при агрегате 86.15% |
| Architecture | 30 basedpyright cycles; 15 private-import pairs; lazy-import cap; F403 barrels |
| Data/schema | Config surface hard freeze 27/419; 6 governed duplicate clusters |
| Dependencies / compat | 12 permanent public entrypoints; unregistered `MetricsStartResult` aliases |
| Code complexity | 15 xenon path exemptions + 4 function CC caps, expiry 2026-12-31 |
| Observability | Gates pass; review age 6/21 days |
| Documentation | Scorecard `expected_action` «6 clusters» при metrics=0; audit SHA на пине = `8472592a` |
| Security | Секреты не включались; `.env` не трогался |

## Findings (max 20, PROVEN)

Полная схема: `reports/audit/tech-debt/findings.json`.

| ID | Pri | Path | Observation |
| --- | --- | --- | --- |
| AUD-TD-001 | P1 | `architecture-debt-remote-main-baseline.json` @ `5af9180c` | baseline inventory hash `79a04203` ≠ inventory `13b38110`; gates drift=0 |
| AUD-TD-002 | P1 | dirty `reports/quality/*baseline*` + `*gates*` | fingerprint `1c7fc338`→`4603631c`; нарушен `dirty_closeout_guard` |
| AUD-TD-003 | P1 | `debt-governance-gates.json:40` @ pin | `budget_no_growth=not_evaluated` при `status=pass` |
| AUD-TD-004 | P2 | `debt_scorecard.yaml:449` | `expected_action` «6 clusters» при `duplication_clusters=0` |
| AUD-TD-005 | P2 | `total-tech-debt-audit-main-current.md` @ pin | audited SHA `8472592a`, не `5af9180c` |
| AUD-TD-006 | P2 | `lazy_import_ratchet.yaml:5` | 97/97, target 60 |
| AUD-TD-007 | P2 | `private_import_ratchet.yaml:6` | 15/15, `strict_mode: false` |
| AUD-TD-008 | P2 | `debt_scorecard.yaml:256` | config 27/27, params 419/419 freeze |
| AUD-TD-009 | P2 | `debt_scorecard.yaml:538` | control_plane fan-in 2/2 hard freeze |
| AUD-TD-010 | P2 | `basedpyright_import_cycle_allowlist.json:199` | 30 cycles, review_by 2026-10-28 |
| AUD-TD-011 | P2 | `assertless_ratchet.yaml:5` | 87 vs target 77 |
| AUD-TD-012 | P2 | `duplication_complexity_exemptions.yaml` | 15 paths + 4 functions, expiry 2026-12-31 |
| AUD-TD-013 | P2 | `src/bioetl/application/ports/metrics.py:108` | deprecated aliases вне inventory |
| AUD-TD-014 | P2 | `debt_scorecard.yaml:638` | supporting-scripts max=15 при current=0 (leftover cap) |
| AUD-TD-015 | P2 | `compatibility_facade_inventory.yaml:12` | review cluster 2026-09-30 |
| AUD-TD-016 | P2 | `branch-coverage-gap-report.md:14` | 552 files <85% branch; агрегат 86.15% |
| AUD-TD-017 | P3 | `constructor_waivers.yaml:6` | 1 waiver `QuarantineEntry` max_args=9 |
| AUD-TD-018 | P3 | `vcr_cassette_size_budget.yaml:16` | 4 oversized cassettes |
| AUD-TD-019 | P3 | `dead-code-inventory.json:1` | snapshot_date 2026-08-01 vs HEAD 2026-08-27 |
| AUD-TD-020 | P3 | `field_transforms/__init__.py:5` | star-import `noqa: F403` barrels |

## Freeze register (shrink-before-grow, не повышать)

Источник: `configs/quality/debt_scorecard.yaml`, playbook `#8714`.

| Metric | current/max | Owner | Notes |
| --- | --- | --- | --- |
| `config_surface_ratchet.config_count` | 27/27 | `@bioetl-config` | hard freeze |
| `config_surface_ratchet.unique_parameter_count` | 419/419 | `@bioetl-config` | hard freeze |
| `application_services_control_plane.max_internal_fan_in` | 2/2 | `@bioetl-platform` | hard freeze |
| `lazy_import_ratchet.max_count` | 97/97 | `@bioetl-architecture` | target 60 |
| `private_import_ratchet.max_count` | 15/15 | `@bioetl-architecture` | residual pairs |
| `retirement triaged_entry_count` | 18/18 | `@bioetl-architecture` | classified |
| `repo_wide_zero_import_candidate_count` | 3/3 | `@bioetl-architecture` | untriaged=0 |
| `public_entrypoint_count` | 12 (permanent) | `@bioetl-architecture` | не transition debt |
| `public_export_facade_count` | 4/4 | `@bioetl-architecture` | hold |
| `zero_reference_supporting_script_count` | 0/15 | `@bioetl-platform` | leftover max; ratchet вниз, не вверх |
| `architecture_metric_exemptions` | 0 | `@bioetl-architecture` | hold at zero |
| `composition` package modules | 295 / cap 300 | `@bioetl-architecture` | 5 слотов |

## Quick wins vs strategic vs dependency

**Quick wins (S, не трогают бюджеты вверх):**

1. На чистом tree: `python -m scripts.engineering.qa report-architecture-debt-remote-main-baseline --update` затем `report-debt-governance-gates --check --changed-from-ref origin/main`. Не поднимать caps.
2. Синхронизировать `expected_action` hotspot families с `duplication_clusters=0`.
3. Зарегистрировать или удалить `MetricsStartResult` / `MetricsGatewayResult` из public `__all__`.
4. После live current=0 shrink `supporting_scripts` `max_count` 15→0 (только вниз).

**Strategic (M–XL):**

1. Paydown lazy-import 97→60 и private-import 15→0.
2. Сужение xenon path exemptions до expiry 2026-12-31.
3. Branch-coverage tail (552 files) — ranked, не агрегат; **не** снижать 85%.
4. Review 2026-09-30: 12 public entrypoints / ENTITY_MAPPING / 6 config clusters.

**Dependency / review calendar:**

1. 2026-09-30: compatibility facades, ENTITY_MAPPING, config duplicate clusters.
2. 2026-10-21–30: basedpyright cycles, dead-code review.
3. 2026-12-31: constructor waiver + xenon exemptions expiry.

## Top remediations

1. Считать committed gates на `5af9180c` **недоказательством** no-growth и baseline freshness. Требовать `--changed-from-ref origin/main` и совпадение baseline inventory hash с `module-coverage-inventory.json`.
2. Не принимать dirty `reports/quality/*baseline*` / `*gates*` как closeout (`dirty_closeout_guard`).
3. Обновить `expected_action` (0 clusters). Не менять `bounded_growth_budgets` вверх.
4. Lazy/private/xenon/assertless: только shrink `max_*` после live удаления.
5. Закрыть или инвентаризировать deprecated aliases в `bioetl.application.ports`.
6. Review 2026-09-30 без silent delete и без `max_count++`.

## Markers in `src/` (не приоритет по количеству)

- `# TODO|FIXME|HACK|XXX|WORKAROUND` в `src/bioetl`: нет (кроме комментария `# TEMPORAL:` в `publication_fields.py:265` — не debt marker).
- Deprecated: управляемый public API; **неуправляемые** ports aliases (AUD-TD-013).

## Deliberate tradeoffs (не findings-дефекты)

- `QuarantineEntry` max_args=9 — ADR-051 intentional_exception.
- 12 retained public entrypoints — permanent public API (`#7461`).
- 6 config duplicate clusters — `retain_shared_composite_policy` (`#5568`).
- 3 classified zero-import modules — untriaged=0.
- Architecture exemptions registries пустые; `lint_diagrams` SIZE-001 — diagram rule, не metric exemption.
- Hotspot coverage floors сейчас pass — не дефект.

## Checked clear

- `current_count > max_count` в `debt_scorecard.yaml`: 0.
- Gates WT `current > limit`: 0.
- `reports/quality/**/*closeout*.json` current>max: 0.
- Live `compute_source_tree_sha256` = inventory `13b38110`.
- Conflict markers `<<<<<<<` в `reports/quality/`: 0.

## Skipped checks

- `python -m memory.tooling.workflow pre/post-task` — запрет писать что-либо кроме `reports/audit/tech-debt/{report.md,findings.json}`.
- GitHub tracking (`REQUIRE_GH_TRACKING=false`).
- Junie mirror check — runtime trees не менялись этим аудитом.
- Повторный прогон coverage.xml / xenon live — цифры из committed inventory/reports.
- `git blame` возраста маркеров.

## Validation intended

```text
python -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml
python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main
python -m scripts.engineering.qa validate-technical-debt-audit --json
python -m scripts.engineering.qa check-exemptions
```

## Guard

- `.env` не читался на предмет секретов в отчёт и **не изменялся**.
- Бюджеты техдолга **не предлагается повышать**.
- `MODE=audit` — патчи продукта не предлагаются к применению.
- Dirty quality artifacts **не** «чинили».
