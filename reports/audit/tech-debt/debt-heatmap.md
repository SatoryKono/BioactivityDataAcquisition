# Debt heatmap (`src/bioetl`, 2026-09-24)

Heat = probability × blast. Не TODO-count.

```
                    blast →
                 low          medium              high
prob high    | F-003       | F-001 FK       | AUD-001 gates
             | 17 ignores  | 100% (rebind   | AUD-002 _core.py
             | watch       |  pending)      | (carry-over, src/mem)
prob med     | waiver      | F-004 util     |
             | aggregates  | (unmeasured)   |
prob low     | pragma      | CLI ~410 LOC   |
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
