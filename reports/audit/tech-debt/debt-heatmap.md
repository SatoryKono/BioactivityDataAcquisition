# Debt heatmap

SCOPE: `src/bioetl/` + `configs/quality/`. Дата: 2026-08-27. run_id: `20260827T0726Z-debt-cycle-8a4a5028a8`.  
Шкала: **P0** блокер / **P1** высокий / **P2** cost-of-change / **P3** локально / **OK** под контролем / **FREEZE** shrink-only cap.

## Surfaces

| Surface | Integrity | Coverage | Architecture | Compat | Complexity | Tests | Docs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `reports/quality/` | OK 45/45 gates | OK hotspot floors 5/5 | OK score 9.41 | OK 0 transition | OK 0 duplicate clusters | **P2** assertless 87 | OK |
| `configs/quality/` | OK YAML | FREEZE floors must not drop | FREEZE lazy 97; private 15; fan-in 2 | **P2** 2026-09-30 review | **P2** xenon paths | FREEZE assertless 87→77 | OK expected_action synced this cycle |
| `src/bioetl/` | OK no conflict markers | OK floors pass | **P2** 30 cycles | hold | **P2** xenon exemptions | n/a | n/a |

## Hotspot families (after cycle-1 ratchet)

| Family | files | fan-in (live/budget) | files≥250 | Heat |
| --- | ---: | --- | --- | --- |
| `application_core` | 194 | 6/7 | 0 | near-budget (was 6/10) |
| `application_services_control_plane` | 133 | **2/2** | 0 | FREEZE |
| `composition_bootstrap_runtime` | 51 | 2/3 | 0 | OK headroom (`#6034`) |
| `composition_factories_pipeline` | 35 | 2/3 | 0/2 | pin `#5648` blocks 2→0 |
| `composition_runtime_builders` | 57 | **3/3** | 0 | at-budget after 5→3 |

## Paydown lanes

```text
P0  none this cycle                 (closed #9717)
P1  none this cycle                 (closed #9718)
P2  freeze lazy/private/config      ████████████  hold, shrink only
P2  remaining slack / closeout pins ██
```
