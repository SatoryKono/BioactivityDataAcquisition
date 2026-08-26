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
| `surface_score` | **1** (weak: механизм есть, evidence surface сейчас нецелостен) |
| Debt budgets | **не поднимались** (audit-only) |
| Debt outcome | `unchanged` |

## Executive summary

Система управления техдолгом в BioETL зрелая: нулевые exemption-реестры, flaky=0, uncovered=0, twins=0, uuid4=0, layer_violations=0, compatibility transition/sunset/expired=0, Sonar open=0 (снимок 2026-08-20). Это **не** «игнорируемый хаос».

Текущий checkout **нельзя** считать green closeout:

1. **P0.** `reports/quality/module-coverage-inventory.json` содержит незакрытые merge-конфликты (`HEAD` vs `fix/architecture-governance-23`, ancestor `1e64aaac80`) — JSON невалиден.
2. **P1.** Пара gates/scorecard внутренне противоречива: категории scorecard суммируются ≈**9.41**, `integral_score`=**7.41**; json-гейт `unmeasured`=`pass/0`, `summary` всё ещё `failing`/`unmeasured`; md-зеркало пишет **84** unmeasured.
3. **P1.** Несколько shrink-only freeze сидят в `current==max` (config 27/27, params 419/419, control_plane fan-in 2/2, lazy import 98/98, private import 15/15, assertless 87/87). Playbook #8714: рост только через shrink в том же PR, **не** через `max_count++`.

`surface_score=1`, а не 0: enforcement-контур существует и большинство zero-budget метрик держатся. Не 2: P0/P1 целостность quality SSOT ломает доказательность релиза.

**УВЕЛИЧИВАТЬ бюджеты техдолга ЗАПРЕЩЕНО.** Remediation только shrink или budget-neutral regenerate.

## Method

- Карта: `docs/00-project/ai/prompts/library/audit/tech-debt.md` + fragments (evidence-contract, finding-schema, debt-budget-ban, env-guardrail, reports-output, audit-scale).
- Норматив: `AGENTS.md` → `NORMATIVE_SOURCES.md` → `docs/00-project/governance/08-debt-ownership-playbook.md` → `configs/quality/debt_scorecard.yaml`.
- Маркеры: TODO/FIXME в `src/bioetl` **не найдены**; собраны suppressions (`type: ignore`, `noqa: F403`, `pragma: no cover`), ratchets, exemptions, inventories.
- Shell/memory workflow: **пропущены** (в этой runtime нет `run_terminal_command`). Claims сверены чтением файлов, не памятью.
- Worktree во время аудита менялся (merge quality-артефактов). Зафиксировано состояние на момент записи артефактов.

## Trend (без предложения поднять лимиты)

| Signal | Historical | Current (checkout) | Direction |
| --- | --- | --- | --- |
| Architecture metric exemptions | 48 (2025-12-31) | **0** (empty registries) | improved |
| Exemption-debt integral (0..100) | — | **100** at zero exemptions (`program_done_criteria`) | held |
| Architecture quality integral (0..10) | audit pin **9.41** (2026-08-25, SHA `710930f4`) | file shows **7.41** header vs **≈9.41** categories | **incoherent** |
| Unmeasured modules | ratchet `max_count=0`; remote-main summary **84** | inventory **conflicted**; gates json `0` vs md `84` | **incoherent** |
| Uncovered modules | 1611 historical | **0** | improved |
| Flaky tests | — | **0** | held |
| Twin modules | — | **0** | held |
| Constructor waivers | 2 → 1 (#6760) | **1** (`QuarantineEntry`) | held freeze |
| Lazy imports | cap 98 / target 60 | **98/98** | freeze |
| Config surface | 27 configs / 419 params | **27/27**, **419/419** | freeze |
| Sonar open issues | baseline 308 | **0** (2026-08-20 RF-009) | improved |

Q3 scorecard: `max_total_exemptions=0` (exemption-debt 0..100). Architecture 0..10 track is separate (`program_done_criteria.score_semantics`).

## Findings (max 20)

| ID | Pri | Status | Path | Observation |
| --- | --- | --- | --- | --- |
| TD-001 | P0 | PROVEN | `reports/quality/module-coverage-inventory.json:7816` | 3 merge-conflict hunks; JSON invalid |
| TD-002 | P1 | PROVEN | `reports/quality/debt-governance-gates.json:77` | gate `unmeasured` pass/0 vs summary fail |
| TD-003 | P1 | PROVEN | `reports/quality/architecture-quality-scorecard.json:181` | categories ≈9.41 vs `integral_score` 7.41 |
| TD-004 | P1 | PROVEN | `reports/quality/debt-governance-gates.md:22` | md unmeasured=84 fail vs json pass/0 |
| TD-005 | P1 | PROVEN | `reports/quality/source-tree-manifest.json:4` | разные `source_tree_sha256` + baseline 9.41 vs unmeasured 84 |
| TD-006 | P1 | PROVEN | `reports/quality/total-tech-debt-audit-main-current.md:19` | registry pin 45/45 / 9.41 / 2465 modules vs live 7.41 / 2467 |
| TD-007 | P1 | PROVEN | `scripts/engineering/qa/report_live_residual_snapshot.py:85` | unmeasured считается по `rows`, не по `summary` |
| TD-008 | P1 | PROVEN | `configs/quality/debt_scorecard.yaml:256` | cluster `current==max` freezes |
| TD-009 | P2 | PROVEN | `configs/quality/basedpyright_import_cycle_allowlist.json:199` | 30 typing cycles, review_by 2026-10-28 |
| TD-010 | P2 | PROVEN | `configs/quality/constructor_waivers.yaml:6` | 1 waiver `max_args=9` expiry 2026-12-31 |
| TD-011 | P2 | PROVEN | `configs/quality/duplication_complexity_exemptions.yaml:9` | широкие xenon path exemptions |
| TD-012 | P2 | PROVEN | `src/bioetl/interfaces/cli/.../_observability_backend_startup.py:124` | ≥82 `type: ignore` in `src/bioetl` |
| TD-013 | P2 | PROVEN | `src/bioetl/application/core/transformer_runtime/__init__.py:11` | 14× `noqa: F403` star-import facades |
| TD-014 | P2 | PROVEN | `reports/quality/branch-coverage-gap-report.md:8` | 552 files &lt;85% branch при агрегате 86.152% |
| TD-015 | P2 | PROVEN | `configs/quality/public_lazy_facade_inventory.yaml:8` | 52 lazy facades; связано с lazy 98/98 |
| TD-016 | P2 | PROVEN | `reports/quality/hotspot-family-baseline.json:6` | snapshot_date 2026-07-27; LOC 7226 vs 7229 |
| TD-017 | P2 | PROVEN | `configs/quality/compatibility_facade_inventory.yaml:22` | 12 entrypoints + 4 facades freeze; review 2026-09-30 |
| TD-018 | P2 | PROVEN | `reports/quality/live-residual-snapshot.json:74` | 51 closeout files / 10488 LOC |
| TD-019 | P2 | PROVEN | `reports/quality/debt-governance-gates.json:40` | no-growth `not_evaluated_without_changed_from_ref` |
| TD-020 | P3 | PROVEN | `reports/quality/dead-code-inventory.json:2` | stale supporting inventories (08-01 / 08-07) |

Полная схема: `findings.json`. Реестр: `technical-debt-register.csv`. Тепловая карта: `debt-heatmap.md`.

## Classification

| Class | Items |
| --- | --- |
| Deliberate tradeoff | TD-010 ADR-051 constructor surface; TD-017 permanent public CLI seams; config duplicate clusters `#5568` retain_shared_composite_policy |
| Historical constraint | TD-011 xenon path exemptions expiry 2026-12-31; TD-009 PD2-8 cycles |
| Maintainability | TD-012 type ignores; TD-013 F403 barrels; TD-018 closeout suite size |
| Test debt | TD-014 branch tail; TD-008 assertless 87/87; TD-020 weak-assert advisory 1149 (stale) |
| Architecture drift | TD-008 fan-in/lazy/private/config freezes; TD-015 lazy facades |
| CI / evidence integrity | **TD-001..TD-007, TD-019** — доминирующий риск сейчас |
| Dependencies | Sonar/VCR/orjson optional — не P0; VCR 126MB/150MB (chembl ~113MB) |
| Security | Sonar vulns=0; uuid4 production=0; `.env` не трогался |

Не долг: пустые `architecture_metric_exemptions.yaml` registries; flaky inventory `[]`; twin `families: []`; TODO/FIXME в `src/bioetl` отсутствуют.

## Quick wins vs strategic vs dependency

**Quick wins (S, budget-neutral):**

1. Закрыть conflict markers в inventory (TD-001).
2. `python -m scripts.engineering.qa.refresh_governance_artifacts` затем `--check --changed-from-ref origin/main` (TD-002..TD-006, TD-016, TD-019).
3. `_module_coverage_residuals` читать `summary.unmeasured_module_count` (TD-007).
4. Перепинить `technical_debt_audit_registry.yaml` после coherent gates (TD-006).

**Strategic (M/L, shrink-only):**

1. Lazy import 98 → target 60 (TD-008/TD-015).
2. Private import pairs 15 → 0 via public owners (TD-008).
3. Control-plane fan-in split до снятия freeze 2/2 (TD-008).
4. Basedpyright cycles 30 → 0 (TD-009).
5. F403 barrels → explicit re-exports (TD-013).
6. Branch tail 552 files — ranked owner tests, не снижение 85% (TD-014).
7. Fold closeout tests в generic inventory (TD-018).

**Dependency debt:** optional `orjson` (`type: ignore[assignment]`); pandera 0.31 shim comments; VCR chembl corpus size. Не блокирует merge сами по себе.

## Top remediations

1. Разрешить merge-конфликты в `reports/quality/module-coverage-inventory.json` и не коммитить conflict JSON.
2. Связанный refresh: `python -m scripts.engineering.qa.refresh_governance_artifacts` + `report-debt-governance-gates --check --changed-from-ref origin/main`.
3. Починить `_module_coverage_residuals` на `summary.*` (TD-007).
4. Добавить assertion: `sum(weighted_score)==integral_score` и `summary.failing_gates` == fail gates.
5. Shrink lazy_import / private_import / control_plane fan-in **без** роста `max_count`.
6. Заменить F403 star-imports явными `__all__`.
7. Ломать basedpyright cycles через `TYPE_CHECKING`.
8. Перепинить total-tech-debt audit только после 45/45 на валидных артефактах.

## Stop / guardrails

- Любой патч, поднимающий `max_count`, exemption, hotspot cap, `unmeasured_module_count` ratchet — **reject**.
- `.env` не читался на предмет секретов в отчёт; файлы `.env` не изменялись.
- MODE=`audit`: патчи продукта не предлагаются к применению без отдельного approval.

## Skipped checks

| Check | Reason |
| --- | --- |
| `python -m memory.tooling.workflow pre-task/post-task` | нет shell tool |
| `git blame` / age of ignores | нет shell; приоритет по blast radius |
| Live `report-debt-governance-gates --check` | нет shell; читался committed payload |
| Recompute `source_tree_sha256` | нет shell |
| GitHub issue search/create | `REQUIRE_GH_TRACKING=false` |
| Full `rg` count of `pragma: no cover` as debt | mostly lazy `__getattr__`; not ranked above P2 |

## Artifacts

- `reports/audit/tech-debt/report.md` (этот файл)
- `reports/audit/tech-debt/findings.json`
- `reports/audit/tech-debt/technical-debt-register.csv`
- `reports/audit/tech-debt/debt-heatmap.md`
