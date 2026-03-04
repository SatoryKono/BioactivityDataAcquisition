# Quality Debt Scorecard (2026-Q1)

- Snapshot date: 2026-03-04
- Source registry: `configs/quality/architecture_metric_exemptions.yaml`
- Scorecard policy: `configs/quality/debt_scorecard.yaml`

## Baseline Decomposition

Total exemptions: **485**

### By Registry

| Registry | Count |
|---|---:|
| `file_size_limits` | 97 |
| `function_complexity` | 97 |
| `function_length` | 118 |
| `class_size` | 82 |
| `class_method_count` | 1 |
| `god_object` | 49 |
| `domain_complexity` | 41 |

### By Owner

| Owner | Count |
|---|---:|
| `@bioetl-architecture` | 485 |

### By Expiry Quarter

| Quarter | Count |
|---|---:|
| `2026-Q2` | 485 |

## Governance Targets

### Burndown Targets (Quarterly)

| Quarter | Max Exemptions | Min Integral Score |
|---|---:|---:|
| `2026-Q1` | 485 | 70 |
| `2026-Q2` | 466 | 73 |
| `2026-Q3` | 443 | 76 |
| `2026-Q4` | 419 | 79 |
| `2027-Q1` | 390 | 82 |

### Group Budgets

Groups:
- `size_shape`: `file_size_limits`, `function_length`, `class_size`, `class_method_count`, `god_object`
- `complexity`: `function_complexity`, `domain_complexity`

Growth guard:
- CI fails on group/regression growth beyond quarter budget.
- Temporary growth is allowed only via approved `RF-*` grace windows.

## Operating Rules

1. New exemptions must keep mandatory metadata (`owner`, `reason`, `expires_on`, `removal_step`).
2. Registry/group growth beyond target budget is blocking by default.
3. Grace windows are valid only when:
   - RF task is explicitly approved,
   - window dates are active,
   - allowances are declared in scorecard.
