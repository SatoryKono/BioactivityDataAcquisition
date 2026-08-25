## Parent

#9639.

## Факт — точечные падения того же прогона

| Поверхность | Гейт | Деталь |
|---|---|---|
| Ruff F401 | `test_ruff_error_count` | `composition/observability_runtime.py:43-44` unused `get_settings`, `get_audit_service` |
| TYPE-002 Any | `test_any_budget_*` | `composition/contracts/services.py:10` `JsonDict = dict[str, Any]` без `# Any:` |
| Domain LOC | `test_domain_files_under_limit` | `_pipeline_run_mixins.py` 307 > 305 |
| Test LOC | `test_no_test_files_over_2000_loc` | `tests/integration/test_prometheus_rules_config.py` 2086 |
| Hotspot | `test_debt_scorecard_hotspot_family_metrics_match_committed_baseline` | `composition_bootstrap_runtime.total_loc` 6236 > baseline 6198 |
| Entrypoints | `test_entrypoints_*` | `get_bronze_cleanup_service` всё ещё в `composition.entrypoints` / `__all__` |
| Silver wiring | `test_silver_composition_wiring_passes_grouped_runtime_services` | `workflow_calls` пустой |
| Observability | metric governance | coverage class violations (`bioetl-control-plane-v1` panel 130); stale cardinality evidence |
| Lazy export | `test_public_lazy_facade_inventory_*` | drift AST vs inventory (часть закроется ARCH-VG-02) |
| Mkdocs nav | `test_not_in_nav_growth_guard` | 225 > 223 из‑за ADR-058/059 — предпочтительно закрыть в #9624 |

## Цель

Зелёные точечные гейты **без** роста LOC/hotspot/Any бюджетов.

## Правки

1. Удалить unused imports; типизировать или пометить `Any`.
2. Сжать mixins / разрезать prometheus rules test; не поднимать cap.
3. Либо вернуть `total_loc` ≤ 6198, либо обновить committed baseline **вниз по другим метрикам, без роста cap**.
4. Убрать legacy getter из public entrypoints (совместимость — только через sunset ledger, без роста expired_compat).
5. Вернуть grouped runtime services в silver composition wiring.
6. Regen observability inventory/evidence; починить coverage class refs.

## Definition of Done

- Перечисленные тесты зелёные.
- Ни один cap/threshold не увеличен.
- Nav/ADR-058/059 не дублировать, если уже закрыто #9624.
