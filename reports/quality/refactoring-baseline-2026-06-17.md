# Clean Refactoring Baseline - 2026-06-17

This baseline locks the evidence used for issues #5287-#5292. It records the
post-refresh state for the next debt-reduction wave without increasing any debt
budget, max count, hotspot cap, or exemption limit.

## Artifact Hashes

| Artifact | SHA256 |
| --- | --- |
| `reports/quality/architecture-quality-scorecard.json` | `b1ce82563964739a51c7f0a8c7f4c420867f36b0a8f42f8ca0dd1f89a4396a88` |
| `reports/quality/debt-governance-gates.json` | `82059e5b63bd0ef39fcb1360648f738d7913ae6388234284927a8d10302e1b01` |
| `reports/quality/compatibility-importer-census.json` | `c215afe21e2c6287fa0c6a77d7b0b3725d7af1b8dfc741aa80bf6efaddfa0977` |
| `reports/quality/dead-code-inventory.json` | `0726fc35d771bf139155faa4731bf01590d7c90a477989589dfab53ecc629b7c` |
| `reports/quality/module-coverage-inventory.json` | `a3943b51b995934471d331887aad8ad8240859a404ed36b7c7b291dadf463d35` |
| `reports/observability/runtime_cardinality_inventory.json` | `fd542c696901ee76b4eae7bc7b20394256f409a6bd18457c70bdc3eb225cd570` |
| `reports/quality/adr-enforcement-matrix.json` | `c82c3dc12226c40be484a2b0226726627bc461878d76f8e75725781282ac6079` |
| `reports/quality/hotspot-family-baseline.json` | `cdd0efd80265474baa53104c79d34bd7d11a3e5661c61b1562ca2d71438e76f6` |
| `docs/filters/inventory-baseline.json` | `8ff6388f88df2dd5573eda687afc14aad1476b07c35ae209c1c9cc2416863be1` |
| `reports/coverage/coverage.xml` | `2bf9d220aa37d58297b69fe6f549d285bb63371ef79064ee041b0ee69c0f452e` |

## Locked Metrics

| Metric | Value |
| --- | ---: |
| Architecture score | `7.98` |
| Architecture interpretation | `satisfactory_system_refactoring_required` |
| Layer violations | `0` |
| Retained public entrypoints | `13` |
| Retained public export facades | `4` |
| Config root src importers | `0` |
| Twin pairs | `0` |
| ADR enforcement blocking gaps | `0` |
| Observability dashboarded-without-emission | `0` |
| Observability dashboarded-without-declaration | `0` |
| Debt governance gates | `24 pass / 1 warn / 0 fail` |
| Hotspot budget warnings | `6` |
| Source modules | `2147` |
| Uncovered modules | `0` |
| Unmeasured modules | `0` |
| Below-85 modules | `105` |

## Workstream Classification

| Issue | Classification | Closeout evidence |
| --- | --- | --- |
| #5287 | active debt baseline frozen | Scorecard, governance gates, compatibility census, dead-code, coverage, observability, ADR, and hotspot artifacts refreshed or verified. Generated-artifact drift is zero. |
| #5288 | improved active hotspot debt | `composition_bootstrap_runtime.files_ge_250_loc` reduced from `2` to `1`; hotspot warnings reduced from `7` to `6`; budgets unchanged. |
| #5289 | verified no-op classification | Retained entrypoints remain `13`; config-root src importers remain `0`; remaining first-party callers are sanctioned public seams, not private-internal bypass candidates. |
| #5290 | closed debt with regression guard | Canonical runtime identity is `structural_only_compat`; `structural_only_auto_promote` remains only a historical persisted alias. Silver inventory and parity checks pass. |
| #5291 | closed debt with deprecated compatibility window | `--silver-filter-only` help text explicitly marks the alias deprecated with 2026-09-30 sunset and points to `--error-code FILTERED_OUT_SILVER` for Silver structural rejects only. |
| #5292 | improved coverage debt shard | Below-85 module count reduced from `112` to `105`; uncovered and unmeasured module counts remain zero. |

## Validation

- `./.venv/bin/ruff check ...` on changed Python files: pass.
- Targeted pytest bundle for runtime identity, quarantine alias, coverage shard, and Silver guardrails: pass.
- Targeted coverage run for the same bundle: pass; merged positive line hits into `reports/coverage/coverage.xml`.
- `python scripts/data_quality/inventory_silver_filters_migration.py`: pass.
- `python scripts/data_quality/run_silver_gold_filter_parity.py`: pass.
- `python -m scripts.engineering.qa report-module-coverage --check`: pass.
- `python -m scripts.engineering.qa report-family-baseline --check`: pass.
- `python -m scripts.engineering.qa report-compatibility-importer-census --check`: pass.
- `python -m scripts.engineering.qa report-debt-governance-gates --check`: pass.
- Architecture bundle covering scorecard, hotspot, debt scorecard, coverage inventory,
  compatibility census, ADR matrix, and Silver compatibility surface: pass.
