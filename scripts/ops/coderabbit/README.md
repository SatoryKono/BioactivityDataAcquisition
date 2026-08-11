# CodeRabbit residual campaign operators

Operator utilities for scoped CodeRabbit CLI residual campaigns.

| Script | Role |
| --- | --- |
| `build_matrix.py` | Build leaf scope matrix (writes under `reports/quality/coderabbit/`) |
| `run_leaves.py` | Sequential leaf runner (logs under reports; requires API key) |
| `normalize_findings.py` | Normalize bounded campaign logs into reproducible finding and de-duplication ledgers |
| `scripts/temp/resolve_coderabbit_merge_conflicts.py` | Bounded merge-recovery helper for campaign artifacts |

Do **not** place Python tooling under `reports/` (structure audit PYTHON_LOCATION).
