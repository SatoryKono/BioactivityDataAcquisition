# Weak-assert advisory inventory

Generated: 2026-08-07T13:33:23.305501+00:00 (#8330)

Mode: **advisory only** — not a merge gate.

- Total without direct assert/raises: **1149**
- Under tests/unit: **1020**

## Top owner buckets

| Bucket | Count |
| --- | ---: |
| `tests/unit/domain` | 406 |
| `tests/unit/application` | 255 |
| `tests/unit/infrastructure` | 234 |
| `tests/unit/composition` | 62 |
| `tests/unit/interfaces` | 37 |
| `tests/contract/silver_schemas` | 27 |
| `tests/architecture/test_code_metrics.py` | 12 |
| `tests/unit/repo_backed` | 11 |
| `tests/integration/test_grafana_dashboard_links.py` | 9 |
| `tests/unit/scripts` | 9 |
| `tests/architecture/test_aggregate_boundaries.py` | 5 |
| `tests/integration/chembl` | 5 |
| `tests/integration/test_grafana_config.py` | 5 |
| `tests/architecture/test_medallion_invariants.py` | 4 |
| `tests/architecture/test_normalization_surface_coverage_ratchet.py` | 4 |

## Priority review

Focus triage on tests/unit/application/core and tests/unit/scripts.
No mass-delete without review.

