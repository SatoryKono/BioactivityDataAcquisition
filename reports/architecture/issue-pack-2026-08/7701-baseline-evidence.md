# #7701 Baseline evidence (2026-08-05)

Evidence for ARCH-REF step 0 / GitHub issue **#7701**, including post burn-down
refresh for #7702 / #7703.

## Dependency map regen

- Command: `python scripts/engineering/qa/generate_architecture_dependency_map.py --update`
- Outputs:
  - `docs/02-architecture/generated/module-dependency-map.md`
  - `docs/02-architecture/generated/module-dependency-map.json`
- Result: **layer policy violations = 0**

## Family / hotspot baseline regen

- Command: `python -m scripts.engineering.qa report-family-baseline --update`
- Outputs:
  - `reports/quality/hotspot-family-baseline.json`
  - `reports/quality/hotspot-family-baseline.md`

## Live removable-complexity residual

Command:

```bash
source .venv/bin/activate && export PYTHONPATH=src:.
python reports/architecture/issue-pack-2026-08/measure_residual.py
```

### After #7702 / #7703 burn-down (final)

| Family | Live `ge250` | Scorecard budget `files_ge_250_loc` | Fan-in budget |
| --- | ---: | ---: | ---: |
| `adapter_layer` | **9** | **9** (was 22) | **19** (was 31) |
| `composite_layer` | **6** | **6** (was 21) | **17** (was 25) |

Both families meet Phase A targets (≤10 `files_ge_250_loc`). Budgets ratcheted
**down only** in `configs/quality/debt_scorecard.yaml`.

### Pre-burndown snapshot (issue open)

| Family | Live `ge250` | Budget |
| --- | ---: | ---: |
| adapter_layer | 22 | 22 |
| composite_layer | 19 | 21 |

## DoD checklist

- [x] Dependency map regenerated; layer violations remain 0
- [x] Family baseline updated
- [x] Live adapter/composite residual recorded on parent epic / this evidence
- [x] No tech-debt budget increases
