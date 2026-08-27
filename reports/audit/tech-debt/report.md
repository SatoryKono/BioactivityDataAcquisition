# Technical debt audit

| Field | Value |
| --- | --- |
| `domain_id` | `tech-debt` |
| `prompt_id` | `prompt.audit.tech-debt` |
| `cycle` | `prompt.audit.cycle.tech-debt` |
| `run_id` | `20260827T0726Z-debt-cycle-8a4a5028a8` |
| `version` | `1.2.0` |
| `MODE` | `full` |
| `AUDIT_MODE` | `full` |
| `LANGUAGE` | `ru` |
| `SCOPE` | `src/bioetl/` `configs/quality/` |
| `origin/main` (на момент аудита) | `8a4a5028a8` |
| `work_branch` | `fix/audit-cycle-tech-debt-20260827` |
| `audited_on` | `2026-08-27` |
| `surface_score` | **2** / 3 |
| `blocked` | `false` |
| `debt_outcome` | **improved** |
| `debt_budget_policy` | **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ** бюджеты / exemptions / hotspot caps |

Легенда `surface_score`: 3 = долг с owner/risk/effort; 2 = основной долг под контролем, часть пунктов informal; 1 = suppressions без системного управления; 0 = критическое накопление.

Оценка **2**: exemption-долг = 0, hotspot coverage floors pass 5/5, inventory валидный JSON, gates 45/45. P0 conflicted inventory и P1 hotspot floors с аудита 2026-08-26 закрыты (`#9717`, `#9718`). Freeze-метрики на потолке остаются.

## Paydown this cycle

| Family | Metric | Before | After | Live |
| --- | --- | ---: | ---: | ---: |
| `application_core` | `max_internal_fan_in` | 10 | **7** | 6 |
| `composition_runtime_builders` | `max_internal_fan_in` | 5 | **3** | 3 |

`application_core` не сжат до live 6: `test_issue_6032` требует `live < budget`. `expected_action` hotspot families выровнен с `duplication_clusters=0`.

## Executive summary

1. Материальных `current>max` в scorecard/gates **нет**. Не предлагать поднять caps.
2. Slack fan-in уменьшен (REQ-GOV-012). `runtime_builders` теперь at-budget 3/3.
3. Freeze: lazy 97/97 (target 60), private 15/15, config 27/419, control_plane fan-in 2/2, assertless 87→target 77. Owners — closed `#9727`.
4. Closeout `#5648` pin `files_ge_250_loc == 2` блокирует ratchet 2→0 (live 0). Пин не удалять без SSOT.

**REJECTED_POLICY:** любое повышение `max_count` / exemptions / hotspot floors; `application_core` 10→6; bootstrap 3→2; factories `files_ge_250_loc` 2→0 без пересмотра closeout.

## Trend

| Сигнал | Было | Стало | Направление |
| --- | --- | --- | --- |
| Architecture exemptions | 0 | 0 | hold |
| Integral score | 9.41 | 9.41 | hold |
| Hotspot coverage floors | pass 5/5 | pass 5/5 | hold |
| `application_core` fan-in budget | 10 | 7 | улучшение |
| `runtime_builders` fan-in budget | 5 | 3 | улучшение |
| Debt-governance gates | 45/45 | 45/45 | hold |
| Lazy / private / config | at cap | at cap | freeze |

## Findings

Полная схема: `reports/audit/tech-debt/findings.json` (зеркало цикла).

| ID | Pri | Path | Observation |
| --- | --- | --- | --- |
| AUD-TD-021 | P2 | `debt_scorecard.yaml:456` | Paydown fan-in 10→7 и 5→3 |
| AUD-TD-005 | P2 | `lazy_import_ratchet.yaml:5` | 97/97, target 60 |
| AUD-TD-006 | P2 | `private_import_ratchet.yaml:6` | 15/15, `strict_mode: false` |
| AUD-TD-007 | P2 | `debt_scorecard.yaml:256` | config 27/27, params 419/419 |
| AUD-TD-008 | P2 | `debt_scorecard.yaml:537` | control_plane fan-in 2/2 |
| AUD-TD-010 | P2 | `assertless_ratchet.yaml:5` | 87 vs target 77 |
| AUD-TD-022 | P2 | `test_tech_debt_issues_5648_5654_closeout.py:234` | pin `files_ge_250_loc == 2` vs live 0 |

## Freeze register (shrink-before-grow)

| Metric | current/max | Owner | Notes |
| --- | --- | --- | --- |
| `config_surface_ratchet.config_count` | 27/27 | `@bioetl-config` | hard freeze |
| `config_surface_ratchet.unique_parameter_count` | 419/419 | `@bioetl-config` | hard freeze |
| `application_services_control_plane.max_internal_fan_in` | 2/2 | `@bioetl-platform` | hard freeze |
| `composition_runtime_builders.max_internal_fan_in` | 3/3 | `@bioetl-platform` | at-budget after this cycle |
| `application_core.max_internal_fan_in` | 6/7 | `@bioetl-architecture` | near-budget; headroom for `#6032` |
| `lazy_import_ratchet.max_count` | 97/97 | `@bioetl-architecture` | target 60 |
| `private_import_ratchet.max_count` | 15/15 | `@bioetl-architecture` | residual pairs |
| `assertless` | 87 / target 77 | `@bioetl-architecture` | `#9605` |

## GitHub

- Не открывать `#9717` `#9718` `#9727`.
- Новых issues нет (нет нового P0–P1 кластера).

## Validation

```text
python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main
pytest tests/architecture/test_hotspot_fan_in_family_ratchets.py tests/architecture/test_tech_debt_issues_6032_6034_6037_closeout.py tests/architecture/test_tech_debt_issues_5642_5645_closeout.py
```

## Guard

- `.env` не изменялся.
- Бюджеты техдолга не повышались.
- `ALLOW_MERGE=false`.
