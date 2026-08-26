# Technical debt audit — `prompt.audit.tech-debt`

| Field | Value |
| --- | --- |
| `domain_id` | `tech-debt` |
| `prompt_id` | `prompt.audit.tech-debt` |
| `version` | 1.2.0 |
| Date | 2026-08-26 |
| SCOPE | `reports/quality/` `configs/quality/` `src/` |
| MODE | `audit` |
| AUDIT_MODE | `full` |
| LANGUAGE | `ru` |
| REQUIRE_GH_TRACKING | `false` |
| `surface_score` | **1** (weak: механизм есть, evidence surface нецелостен) |
| Debt budgets | **не поднимались** (audit-only) |
| Debt outcome | `unchanged` |

## Executive summary

Система управления техдолгом зрелая: exemption-реестры пусты (48→0), flaky=0, uncovered=0, twins=0, uuid4=0, layer_violations=0, compatibility transition/sunset/expired=0, Sonar open=0 (2026-08-20). TODO/FIXME в `src/bioetl` нет.

Текущий checkout **нельзя** считать coherent closeout:

1. **P1 coverage residual.** `module-coverage-inventory.json` держит **unmeasured=84** (`coverage_xml_has_no_class_entry`) при ratchet `max_count=0`. Hotspot-семьи `application_core` / control_plane / pipeline / runtime_builders — `threshold_status=fail`.
2. **P1 split-brain SSOT.** Scorecard категории ≈**9.41** (unmeasured=0) при `integral_score`=**7.41**; `debt-governance-gates.json` гейт unmeasured=`pass/0`, `summary`=`failing`; md-зеркало пишет **84 fail**. Hash inventory/manifest `29bf3d81…` ≠ scorecard/gates `ef737d02…`.
3. **P1 freeze cluster.** `current==max`: config 27/27, params 419/419, control_plane fan-in 2/2, lazy import 98/98, private import 15/15, assertless 87/87. Playbook #8714: **не** поднимать `max_count`.

Во время аудита в `reports/quality/*.json` наблюдались merge-конфликты `HEAD` vs `fix/architecture-governance-23`; к финализации маркеры сняты. Остаточный риск — невалидная склейка payload, не conflict markers.

`surface_score=1`, не 0: enforcement-контур существует. Не 2: P1 целостность quality SSOT ломает доказательность релиза.

**УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО.**

## Method

- Карта: `docs/00-project/ai/prompts/library/audit/tech-debt.md` + fragments (evidence-contract, finding-schema, debt-budget-ban, env-guardrail, reports-output, audit-scale).
- Норматив: `AGENTS.md` → `NORMATIVE_SOURCES.md` → `docs/00-project/governance/08-debt-ownership-playbook.md` → `configs/quality/debt_scorecard.yaml`.
- Маркеры: TODO/FIXME в `src/bioetl` не найдены; собраны suppressions, ratchets, exemptions, inventories.
- Shell/memory workflow: **пропущены** (нет `run_terminal_command`). Claims сверены чтением файлов.
- Worktree менялся во время аудита; финальные цифры — на момент записи артефактов.

## Trend (без предложения поднять лимиты)

| Signal | Historical | Current (checkout) | Direction |
| --- | --- | --- | --- |
| Architecture metric exemptions | 48 (2025-12-31) | **0** | improved |
| Exemption-debt integral (0..100) | — | **100** at zero exemptions | held |
| Architecture quality integral (0..10) | audit pin **9.41** (2026-08-25) | header **7.41** vs categories **≈9.41** | **incoherent** |
| Unmeasured modules | ratchet `max_count=0` | inventory **84**; gates json `0`; md **84** | **incoherent + residual** |
| Uncovered modules | 1611 historical | **0** | improved |
| Flaky / twins / uuid4 / layers | — | **0** | held |
| Constructor waivers | 2 → 1 | **1** | freeze |
| Lazy imports | cap 98 / target 60 | **98/98** | freeze |
| Config surface | 27 / 419 | **27/27**, **419/419** | freeze |
| Sonar open | baseline 308 | **0** (2026-08-20) | improved |

Q3: `max_total_exemptions=0` (шкала 0..100 exemption-debt). Architecture 0..10 — отдельный track (`program_done_criteria.score_semantics`).

## Findings (max 20)

| ID | Pri | Status | Path | Observation |
| --- | --- | --- | --- | --- |
| TD-001 | P1 | PROVEN | `reports/quality/module-coverage-inventory.json:49532` | unmeasured=84 vs ratchet 0; hotspot families fail |
| TD-002 | P1 | PROVEN | `reports/quality/debt-governance-gates.json:77` | gate pass/0 vs summary fail |
| TD-003 | P1 | PROVEN | `reports/quality/architecture-quality-scorecard.json:181` | categories ≈9.41 vs integral 7.41 |
| TD-004 | P1 | PROVEN | `reports/quality/debt-governance-gates.md:22` | md unmeasured=84 fail vs json pass/0 |
| TD-005 | P1 | PROVEN | `reports/quality/architecture-quality-scorecard.json:263` | hash/xml sha mismatch vs inventory |
| TD-006 | P1 | PROVEN | `reports/quality/total-tech-debt-audit-main-current.md:19` | registry pin 45/45 / 9.41 / 2465 vs live 7.41 / 84 / 2467 |
| TD-007 | P1 | PROVEN | `scripts/engineering/qa/report_live_residual_snapshot.py:85` | unmeasured из `rows`, не `summary` (snapshot 0 vs 84) |
| TD-008 | P1 | PROVEN | `configs/quality/debt_scorecard.yaml:256` | cluster `current==max` freezes |
| TD-009 | P2 | PROVEN | `configs/quality/basedpyright_import_cycle_allowlist.json:199` | 30 typing cycles |
| TD-010 | P2 | PROVEN | `configs/quality/constructor_waivers.yaml:6` | 1 waiver max_args=9 |
| TD-011 | P2 | PROVEN | `configs/quality/duplication_complexity_exemptions.yaml:9` | wide xenon path exemptions |
| TD-012 | P2 | PROVEN | `src/bioetl/interfaces/cli/.../_observability_backend_startup.py:124` | ≥82 `type: ignore` |
| TD-013 | P2 | PROVEN | `src/bioetl/application/core/transformer_runtime/__init__.py:11` | 14× F403 star-imports |
| TD-014 | P2 | PROVEN | `reports/quality/branch-coverage-gap-report.md:8` | 552 files &lt;85% branch |
| TD-015 | P2 | PROVEN | `configs/quality/public_lazy_facade_inventory.yaml:8` | 52 lazy facades |
| TD-016 | P2 | PROVEN | `reports/quality/hotspot-family-baseline.json:6` | snapshot_date 2026-07-27; LOC 7226 vs 7229 |
| TD-017 | P2 | PROVEN | `configs/quality/compatibility_facade_inventory.yaml:22` | 12 entrypoints + 4 facades freeze |
| TD-018 | P2 | PROVEN | `reports/quality/live-residual-snapshot.json:74` | 51 closeout files / 10488 LOC |
| TD-019 | P2 | PROVEN | `reports/quality/debt-governance-gates.json:40` | no-growth not evaluated without `--changed-from-ref` |
| TD-020 | P3 | PROVEN | `reports/quality/dead-code-inventory.json:2` | stale supporting inventories |

Полная схема: `findings.json`. Реестр: `technical-debt-register.csv`. Тепловая карта: `debt-heatmap.md`.

## Classification

| Class | Items |
| --- | --- |
| Deliberate tradeoff | TD-010 ADR-051; TD-017 permanent public CLI seams |
| Historical constraint | TD-011 xenon expiry 2026-12-31; TD-009 PD2-8 cycles |
| Maintainability | TD-012 type ignores; TD-013 F403; TD-018 closeout suite |
| Test debt | TD-001 unmeasured 84; TD-014 branch tail; TD-008 assertless 87/87 |
| Architecture drift | TD-008 freezes; TD-015 lazy facades |
| CI / evidence integrity | **TD-002..TD-007, TD-019** |
| Dependencies | optional orjson; VCR 126MB/150MB (chembl ~113MB) |
| Security | Sonar vulns=0; uuid4=0; `.env` не менялся |

Не долг: пустые exemption registries; flaky `[]`; twin `families: []`; отсутствие TODO/FIXME в `src/bioetl`.

## Quick wins vs strategic vs dependency

**Quick wins (S, budget-neutral):** связанный `refresh_governance_artifacts`; assertion `sum(weighted)==integral` и `summary.failing_gates`; `_module_coverage_residuals` → `summary.*`; перепин audit registry.

**Strategic (M/L, shrink-only):** coverage.xml + измерение 84 модулей; lazy 98→60; private pairs 15→0; control_plane fan-in split; cycles 30→0; F403→explicit exports; branch tail owner-tests; fold closeouts.

**Dependency:** orjson optional; pandera 0.31 comments; VCR chembl size — не P0.

## Top remediations

1. Обновить `coverage.xml` / coverage-verify и `report-module-coverage` (TD-001). **Не** поднимать `unmeasured max_count`.
2. `python -m scripts.engineering.qa.refresh_governance_artifacts` затем `--check --changed-from-ref origin/main` (TD-002..TD-006).
3. Починить `_module_coverage_residuals` на `summary.*` (TD-007).
4. Тест: `sum(weighted_score)==integral_score` и `summary.failing_gates` == fail gates.
5. Shrink lazy_import / private_import / fan-in **без** роста `max_count`.
6. Заменить F403 star-imports явными `__all__`.
7. Ломать basedpyright cycles через `TYPE_CHECKING`.
8. Перепинить total-tech-debt audit только после coherent 45/45.

## Stop / guardrails

- Патч, поднимающий `max_count` / exemption / hotspot cap / unmeasured ratchet — **reject**.
- `.env` не изменялся.
- MODE=`audit`: патчи не применяются без отдельного approval.

## Skipped checks

| Check | Reason |
| --- | --- |
| memory pre-task/post-task | нет shell tool |
| `git blame` | нет shell; приоритет по blast radius |
| Live generator `--check` | нет shell; читался payload |
| Recompute tree hash | нет shell |
| GitHub issues | `REQUIRE_GH_TRACKING=false` |

## Artifacts

- `reports/audit/tech-debt/report.md`
- `reports/audit/tech-debt/findings.json`
- `reports/audit/tech-debt/technical-debt-register.csv`
- `reports/audit/tech-debt/debt-heatmap.md`
