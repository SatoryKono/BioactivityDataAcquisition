# CodeRabbit residual campaign operators

Operator utilities for scoped CodeRabbit CLI residual campaigns.

| Script | Role |
| --- | --- |
| `build_matrix.py` | Build leaf scope matrix (writes under `reports/quality/coderabbit/`) |
| `run_leaves.py` | Sequential leaf runner (logs under reports; requires API key) |

Do **not** place Python tooling under `reports/` (structure audit PYTHON_LOCATION).
