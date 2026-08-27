# Cyclic technical-debt audit — iteration 1

| Field | Value |
| --- | --- |
| `run_id` | `20260827T0726Z-debt-cycle-8a4a5028a8` |
| `prompt_id` | `prompt.audit.cycle.tech-debt` |
| `domain` | `prompt.audit.tech-debt` |
| `MODE` | `full` |
| `AUDIT_MODE` | `full` |
| `LANGUAGE` | `ru` |
| `N` | `10` (stop after 1 real paydown; empty cycles forbidden) |
| `SCOPE` | `src/bioetl/` `configs/quality/` |
| `base` | `origin/main` `8a4a5028a8` |
| `work_branch` | `fix/audit-cycle-tech-debt-20260827` |
| `surface_score` | **2** / 3 |
| `debt_outcome` | **improved** |
| `ALLOW_MERGE` | `false` |
| `debt_budget_policy` | **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ** бюджеты / exemptions / hotspot caps |

## Executive summary

P0/P1 на текущем `origin/main` нет: inventory валиден, hotspot coverage floors 5/5 pass, debt-governance gates **45/45**, `#9717`/`#9718`/`#9727` уже CLOSED. Цикл 1 сжал slack fan-in (shrink-only, REQ-GOV-012):

| Family | Metric | Было | Стало | Live | Почему не в live |
| --- | --- | ---: | ---: | ---: | --- |
| `application_core` | `max_internal_fan_in` | 10 | **7** | 6 | closeout `#6032` требует `live < budget` |
| `composition_runtime_builders` | `max_internal_fan_in` | 5 | **3** | 3 | at-budget; `#6034` не требует headroom |

Дополнительно выровнен устаревший `expected_action` (текст «6/5/1 clusters» при `duplication_clusters=0`).

**REJECTED_POLICY:** `application_core` 10→6; `composition_bootstrap_runtime` 3→2; `composition_factories_pipeline` `files_ge_250_loc` 2→0; любой `max_count++` / exemption++.

## Residual delta

| Сигнал | До | После | Trend |
| --- | --- | --- | --- |
| `application_core` fan-in budget | 10 | 7 | ↓ |
| `composition_runtime_builders` fan-in budget | 5 | 3 | ↓ |
| families_at_budget | 1 (`control_plane`) | 2 (+ `runtime_builders`) | freeze шире, caps ниже |
| Gates `--check --changed-from-ref origin/main` | 45/45 | 45/45 | hold |
| Lazy / private / config / assertless | at cap | at cap | hold (owners via closed `#9727`) |

## Issues (Phase C)

- Не открывать заново `#9717`, `#9718`, `#9727`.
- Новых PROVEN P0–P1 нет. P2 freeze уже с dated owner в `#9727`.
- Closeout-пин `#5648` (`files_ge_250_loc == 2`) **не** удалять без SSOT; issue не создавался.

## Validation

```text
python -m scripts.engineering.qa report-debt-governance-gates --check --changed-from-ref origin/main
pytest tests/architecture/test_quality_debt_scorecard.py \
  tests/architecture/test_hotspot_growth_family_ratchets.py \
  tests/architecture/test_hotspot_duplication_family_ratchets.py \
  tests/architecture/test_hotspot_fan_in_family_ratchets.py \
  tests/architecture/test_tech_debt_issues_5564_5603_closeout.py \
  tests/architecture/test_tech_debt_issues_5642_5645_closeout.py \
  tests/architecture/test_tech_debt_issues_6032_6034_6037_closeout.py \
  tests/architecture/test_tech_debt_issues_5618_5625_closeout.py \
  tests/architecture/test_tech_debt_issues_5648_5654_closeout.py
```

Результат: gates exit 0; pytest 0 fail (4 skip — dirty residual snapshot до коммита).

## Skipped

- `python -m memory.tooling.workflow pre/post-task` — EPERM на `~/.cursor/cli-config.json` (DEGRADED).
- Junie mirror — runtime trees не менялись.
- Повторный coverage.xml / xenon live.
- Пустые итерации 2–10.

## Guard

- `.env` не изменялся.
- Бюджеты только вниз или flat.
- PR не merge (`ALLOW_MERGE=false`).
