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
| `audited_on` | `2026-08-26` |
| `surface_score` | **1** / 3 |
| `blocked` | `false` (аудит завершён; quality surface сейчас небезопасна для merge coverage-gates) |
| `debt_outcome` | `unchanged` (только артефакты аудита) |
| `debt_budget_policy` | **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ** бюджеты / exemptions / hotspot caps |

Легенда `surface_score` (карточка tech-debt): 3 = долг с owner/risk/effort и новый код не хуже baseline; 2 = основной долг под контролем, часть пунктов informal; 1 = suppressions/workarounds без системного управления **или** материальных дыр в enforcement; 0 = критическое накопление, изменения небезопасны.

Оценка **1**: реестры и ratchet в целом зрелые (0 metric exemptions, compatibility transition/sunset/expired = 0, flaky = 0, architecture integral **9.41**), но канонический `module-coverage-inventory.json` сейчас **невалидный JSON** (diff3 conflict), hotspot family coverage floors **fail** в 4/5 семействах, а закоммиченный `debt-governance-gates.json` всё ещё рисует 45/45 pass.

## Executive summary

1. **P0.** `reports/quality/module-coverage-inventory.json:49353-49359` содержит незакрытый merge conflict (`HEAD` `adfa9f79…` vs `fix/full-tests-20260826` `0790be72…`). Это вход `REQ-GOV-007` / debt-governance. Пока файл не пересобран, coverage-hash и `--check` gates нельзя считать доказанными.
2. **P1.** После починки JSON: 4 hotspot-семейства ниже `min_covered_line_percent` (`application_core` 95.98&lt;96.34, `control_plane` 95.21&lt;96.44, `factories/pipeline` 95.36&lt;96.8, `runtime_builders` 92.63&lt;94.9). Хвост до **11.9%** (`_ledger_metadata_candidates`). Floors **не снижать**.
3. **P1.** Закоммиченный `debt-governance-gates.json` сообщает `pass_count=45`, `generated_artifact_drift=0`, hash `adfa9f79` — это **stale snapshot** относительно conflicted inventory. `budget_increase_count=not_evaluated_without_changed_from_ref` при `status=pass`.
4. Управляемый freeze (не дефект, но cost-of-change): config 27/27 и 419/419; lazy-import 97/97 (target 60); private-import 15/15; control-plane fan-in 2/2; constructor waiver 1; public entrypoints 12.
5. Исторический тренд **улучшения** exemption-долга: `historical_baseline.total_exemptions=48` (2025-12-31) → `baseline.total_exemptions=0`; Sonar snapshot 2026-08-20: 0 open issues (signal only). Текущий worktree **ломает** этот зелёный нарратив через conflicted inventory.

**REJECTED_POLICY:** любое повышение `max_count` / exemptions / hotspot thresholds / family caps.

## Trend (без предложения поднять лимиты)

| Сигнал | Исторически | Сейчас | Направление |
| --- | --- | --- | --- |
| Architecture metric exemptions | 48 (Q4-2025) | 0 (пустые registries) | улучшение |
| Architecture integral | n/a в этом аудите | 9.41 `good_targeted_improvements` | стабильно-хорошо |
| Debt-governance gates (закоммиченный md) | 45/45 | snapshot 45/45, но inventory conflicted | **не доверять** до регенерации |
| Unmeasured modules (inventory summary) | 84 до #9678 | 0 в summary | улучшение |
| Unmeasured (live-residual-snapshot) | — | **84** (stale vs summary) | drift |
| Transition/sunset/expired compat | &gt;0 historically | 0/0/0 | улучшение |
| Twin pairs | — | 0 | hold |
| Flaky tests | — | 0 / 0 untriaged | hold |
| Lazy imports | — | 97/97, target 60 | freeze, paydown не завершён |
| Assertless tests | — | 87, target 77 | freeze |
| Constructor waivers | 2 | 1 (`QuarantineEntry`) | улучшение, hold |
| Sonar open (2026-08-20) | baseline 308 | 0 | signal only, не SSOT |

## Classification

| Класс | Состояние |
| --- | --- |
| CI / generated artifacts | **P0 conflict** + stale gates + live-residual drift |
| Tests / coverage | Hotspot family floors fail; branch tail 552 files &lt;85% при агрегате 86.15% |
| Architecture | 30 basedpyright cycles; 15 private-import pairs; lazy-import cap; F403 barrels |
| Data/schema | Config surface hard freeze 27/419; 6 governed duplicate clusters |
| Dependencies / compat | 12 permanent public entrypoints; ENTITY_MAPPING; **незарегистрированные** `MetricsStartResult` aliases |
| Code complexity | 15 xenon path exemptions + 4 function CC caps, expiry 2026-12-31 |
| Observability | Gates pass; review age 6/21 days |
| Documentation | Сломанный markdown в `total-tech-debt-audit-main-current.md`; stale `expected_action` «6 clusters» |
| Security | Sonar 0 vulns/bugs (signal); секреты в отчёт не включались; `.env` не трогался |

## Findings (max 20, PROVEN)

Полная схема: `reports/audit/tech-debt/findings.json`.

| ID | Pri | Path | Observation |
| --- | --- | --- | --- |
| AUD-TD-001 | P0 | `reports/quality/module-coverage-inventory.json:49353` | diff3 conflict на `source_tree_sha256` |
| AUD-TD-002 | P1 | `…inventory.json` hotspot_family_coverage | 4/5 family floors `threshold_status=fail` |
| AUD-TD-003 | P2 | `reports/quality/live-residual-snapshot.json:71` | unmeasured 84 vs inventory 0 |
| AUD-TD-004 | P1 | `reports/quality/debt-governance-gates.json` | 45/45 pass при невалидном inventory |
| AUD-TD-005 | P2 | `configs/quality/lazy_import_ratchet.yaml` | 97/97, target 60 |
| AUD-TD-006 | P2 | `configs/quality/private_import_ratchet.yaml` | 15/15 residual pairs, `strict_mode: false` |
| AUD-TD-007 | P2 | `configs/quality/debt_scorecard.yaml:256` | config 27/27, params 419/419 freeze |
| AUD-TD-008 | P2 | `debt_scorecard.yaml` control_plane family | fan-in 2/2 hard freeze |
| AUD-TD-009 | P2 | `basedpyright_import_cycle_allowlist.json` | 30 cycles, review_by 2026-10-28 |
| AUD-TD-010 | P2 | `assertless_ratchet.yaml` | 87 vs target 77 |
| AUD-TD-011 | P2 | `duplication_complexity_exemptions.yaml` | 15 paths + 4 functions, expiry 2026-12-31 |
| AUD-TD-012 | P2 | `src/bioetl/application/ports/metrics.py:108` | public deprecated aliases вне inventory |
| AUD-TD-013 | P2 | `debt_scorecard.yaml:449` | `expected_action` «6 clusters» при metrics=0 |
| AUD-TD-014 | P2 | `debt-governance-gates.json:40` | `budget_no_growth` not_evaluated, status=pass |
| AUD-TD-015 | P2 | `branch-coverage-gap-report.md` | 552 files &lt;85% branch; агрегат 86.15% |
| AUD-TD-016 | P2 | `compatibility_facade_inventory.yaml` | review cluster 2026-09-30 (12 entrypoints + ENTITY_MAPPING + 6 config clusters) |
| AUD-TD-017 | P3 | `constructor_waivers.yaml` | 1 waiver `QuarantineEntry` max_args=9 |
| AUD-TD-018 | P3 | `vcr_cassette_size_budget.yaml` | 4 oversized cassettes; 84% byte budget |
| AUD-TD-019 | P3 | `total-tech-debt-audit-main-current.md:69` | сломанные markdown anchors |
| AUD-TD-020 | P3 | `src/bioetl/application/core/field_transforms/__init__.py` | star-import `noqa: F403` barrels |

## Freeze register (shrink-before-grow, не повышать)

Источник: `configs/quality/debt_scorecard.yaml`, playbook `#8714`.

| Metric | current/max | Owner | Notes |
| --- | --- | --- | --- |
| `config_surface_ratchet.config_count` | 27/27 | `@bioetl-config` | hard freeze |
| `config_surface_ratchet.unique_parameter_count` | 419/419 | `@bioetl-config` | hard freeze |
| `application_services_control_plane.max_internal_fan_in` | 2/2 | `@bioetl-platform` | hard freeze |
| `lazy_import_ratchet.max_count` | 97/97 | `@bioetl-architecture` | target 60 |
| `private_import_ratchet.max_count` | 15/15 | `@bioetl-architecture` | residual pairs |
| `application_services_root_ratchet.root_module_count` | 1/1 | `@bioetl-architecture` | `#7728` |
| `retirement triaged_entry_count` | 18/18 | `@bioetl-architecture` | classified |
| `repo_wide_zero_import_candidate_count` | 3/3 | `@bioetl-architecture` | classified, untriaged=0 |
| `public_entrypoint_count` | 12 (permanent) | `@bioetl-architecture` | не transition debt |
| `public_export_facade_count` | 4/4 | `@bioetl-architecture` | hold |
| `constructor_waivers` | 1 | `@bioetl-domain` | ADR-051 |
| `architecture_metric_exemptions` | 0 | `@bioetl-architecture` | hold at zero |
| `composition` package modules | 295 / cap 300 | `@bioetl-architecture` | 5 слотов, не freeze |

## Quick wins vs strategic vs dependency

**Quick wins (S, не трогают бюджеты вверх):**

1. Регенерировать `module-coverage-inventory.json` (снять conflict) и gates с `--changed-from-ref origin/main`.
2. Пересобрать `live-residual-snapshot.json`, чтобы `unmeasured=0`.
3. Починить markdown generator для `total-tech-debt-audit-main-current.md`.
4. Синхронизировать `expected_action` hotspot families с `duplication_clusters=0`.
5. Зарегистрировать или удалить `MetricsStartResult` / `MetricsGatewayResult` из public `__all__`.

**Strategic (M–XL):**

1. Owner-тесты на hotspot coverage tail (не снижать floors).
2. Paydown lazy-import 97→60 и private-import 15→0.
3. Сужение xenon path exemptions до expiry 2026-12-31.
4. Branch-coverage tail (552 files) — ranked, не агрегат.

**Dependency / review calendar:**

1. 2026-09-30: compatibility facades, ENTITY_MAPPING, config duplicate clusters.
2. 2026-10-21–30: internal shims, basedpyright cycles, closeout ratchet, public lazy facades, dead-code review.
3. 2026-12-31: constructor waiver + xenon exemptions expiry.

## Top remediations

1. **Не мержить coverage/quality PR**, пока `module-coverage-inventory.json` содержит `<<<<<<<`. Только каноническая регенерация.
2. `python -m scripts.engineering.qa report-module-coverage --allow-missing-coverage-xml` затем `refresh_governance_artifacts` и `report-debt-governance-gates --check --changed-from-ref origin/main`.
3. Пересобрать `live-residual-snapshot.json`; сверить `unmeasured_module_count` с inventory **summary**, не с устаревшим 84.
4. Закрыть hotspot family line-coverage gaps owner-тестами; **запрещено** понижать `min_covered_line_percent`.
5. Убрать или инвентаризировать deprecated aliases в `bioetl.application.ports`.
6. Исправить stale `expected_action` «6 clusters».
7. Планировать 2026-09-30 review 12 public entrypoints / ENTITY_MAPPING / 6 config clusters.
8. Lazy-import и private-import: только shrink `max_count` после live удаления.

## Markers in `src/` (не приоритет по количеству)

- TODO/FIXME/HACK как комментарии в `src/bioetl`: **0** совпадений `# (TODO|FIXME|HACK|XXX|WORKAROUND)`.
- `# type: ignore` в `src/bioetl`: локальные typing shims (CLI Click, HTTP, UniProt client, ports pipeline `attr-defined`) — не отдельный P0.
- `pytest.skip` в `src/`: 0.
- Deprecated: управляемый `ENTITY_MAPPING`; **неуправляемые** ports aliases (AUD-TD-012).

## Deliberate tradeoffs (не findings-дефекты)

- `QuarantineEntry` max_args=9 — ADR-051 intentional_exception.
- 12 retained public entrypoints — permanent public API, burn-down wave empty by design (`#7461`).
- 6 config duplicate clusters — `retain_shared_composite_policy` (`#5568`).
- 3 classified zero-import modules — dynamic/public retain, untriaged=0.
- Architecture exemptions registries пустые; `lint_diagrams` SIZE-001 остаётся в том же YAML как diagram rule, не metric exemption.

## Skipped checks

- `python -m memory.tooling.workflow pre-task` — в этой сессии нет shell tool.
- Живой `report-debt-governance-gates --check --changed-from-ref origin/main` — нет shell; плюс inventory сейчас не парсится как JSON.
- `git blame` / возраст маркеров.
- GitHub tracking (`REQUIRE_GH_TRACKING=false`).
- Junie mirror check — runtime trees не менялись.
- Повторный прогон coverage.xml — не выполнялся; цифры из committed inventory/reports.

## Validation intended (после P0)

```text
python -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml
python -m scripts.engineering.qa.refresh_governance_artifacts --check
python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main
python -m scripts.engineering.qa validate-technical-debt-audit --json
python -m scripts.engineering.qa check-exemptions
```

## Guard

- `.env` не читался на предмет секретов в отчёт и **не изменялся**.
- Бюджеты техдолга **не предлагается повышать**.
- `MODE=audit` — патчи продукта не предлагаются к применению.
