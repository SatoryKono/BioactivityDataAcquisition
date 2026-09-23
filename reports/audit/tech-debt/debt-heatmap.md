# Debt heatmap (`src`, 2026-09-23)

Heat = probability × blast. Не TODO-count.

```
                    blast →
                 low          medium              high
prob high    | AUD-005     | AUD-004 FK     | AUD-001 gates
             | type-ignore | 10 partial     | AUD-002 _core.py
prob med     | waiver      | AUD-003 util   |
             | aggregates  |                |
prob low     | pragma      | CLI ~410 LOC   | memory/query.py 1978
             | facades     | outside family |
```

## Layer map

| Layer | Heat | Notes |
| --- | --- | --- |
| `src/memory/graph/sync_pkg` | **critical** | `_core.py` 17740; `query.py` 1978; `expanded_json.py` 1831 |
| `src/bioetl/infrastructure/storage` | **high** | FK reconciliation coverage tail; several 410+ LOC helpers outside named hotspot families |
| `src/bioetl/composition` | **medium** | 280/295; 0 files_ge_250 in hotspot family |
| `src/bioetl/application/core` | **low** | hotspot `files_ge_250_loc=0`; fan-in 5/7 |
| `src/bioetl/domain` | **low** | exemptions 0; aggregates hold-flat 8/8 |
| `src/bioetl/interfaces` | **low-med** | CLI command modules ~410 LOC, not in family budget |

## Named hotspot families (live residual)

All five families: `files_ge_250_loc=0`, budgets not raised.
