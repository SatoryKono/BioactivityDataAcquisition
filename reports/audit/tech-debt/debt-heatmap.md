# Debt heatmap

SCOPE: `reports/quality/` + `configs/quality/` + `src/`. Дата: 2026-08-26.  
Шкала ячейки: **P0** блокер / **P1** высокий / **P2** cost-of-change / **P3** локально / **OK** под контролем / **FREEZE** shrink-only cap.

## Surfaces

| Surface | Integrity | Coverage | Architecture | Compat | Complexity | Tests | Docs |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `reports/quality/` | **P0** conflicted inventory; **P1** stale 45/45 gates | **P1** 4/5 hotspot floors fail | OK score 9.41 (stale vs inventory) | OK 0/0/0 transition | OK 0 duplicate clusters | **P2** branch tail 552; assertless 87 | **P3** broken total-tech-debt md |
| `configs/quality/` | OK YAML registries | FREEZE coverage floors must not drop | FREEZE lazy 97; private 15; fan-in 2 | **P2** 2026-09-30 review cluster | **P2** xenon 15 paths | FREEZE assertless 87→77 | **P2** stale expected_action 6 clusters |
| `src/bioetl/` | OK no conflict markers | **P1** low-tail helpers 11.9–22% | **P2** 30 cycles; F403 barrels | **P2** ungoverned ports aliases | **P2** under xenon exemptions | n/a (product) | n/a |

## Hotspot families (live residual + inventory)

| Family | files | LOC | fan-in (live/budget) | files≥250 | duplication | coverage floor | Heat |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `application_core` | 194 | 23419 | 6/10 | 0 | 0 | 95.98&lt;96.34 **fail** | P1 |
| `application_services_control_plane` | 133 | 15091 | **2/2** | 0 | 0 | 95.21&lt;96.44 **fail** | P1+FREEZE |
| `composition_bootstrap_runtime` | 51 | 6199 | 2/3 | 0 | 0 | 96.39≥95.65 pass | OK |
| `composition_factories_pipeline` | 35 | 3947 | 2/3 | 0/2 | 0 | 95.36&lt;96.8 **fail** | P1 |
| `composition_runtime_builders` | 57 | 7225 | 3/5 | 0 | 0 | 92.63&lt;94.9 **fail** | P1 |

## Paydown lanes

```text
P0  inventory JSON conflict          ████████  do first
P1  gates snapshot trust + floors    ██████
P2  freezes (config/lazy/private)    ████████████  hold, shrink only
P2  cycles / xenon / aliases         ██████
P3  waiver / VCR / markdown / F403   ██
```

## Quick wins vs strategic vs dependency

| Lane | Items |
| --- | --- |
| Quick wins | AUD-TD-001, 003, 004, 013, 014, 019, 012 |
| Strategic | AUD-TD-002, 005, 006, 009, 010, 011, 015 |
| Dependency/calendar | AUD-TD-016 (2026-09-30), AUD-TD-009 (2026-10-28), AUD-TD-011/017 (2026-12-31) |
