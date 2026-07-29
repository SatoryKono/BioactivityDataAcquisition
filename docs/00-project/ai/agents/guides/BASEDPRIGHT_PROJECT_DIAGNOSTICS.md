# basedpyright Project Diagnostics vs CI mypy

Linked campaigns:

- PD–PD4 (closed): product errors → 0; suppression inventory; Host Protocol partial burn-down
- **PD5 (active):** `#6994` … `#7004` — workspace ~10k (tests-dominated) + product suppression residual

## Gate semantics

| Surface | Tool | Role | Merge-blocking? |
| --- | --- | --- | --- |
| Product type gate | `mypy` on `src/bioetl` | Merge contract | **Yes** |
| Product basedpyright **errors** | basedpyright `src/bioetl` | Must stay **0** | No (advisory) |
| Product `# pyright:` suppressions | file-level flags | Shrink-only debt ledger | No |
| Workspace / tests diagnostics | basedpyright full tree | IDE UX (~10k errors, tests ~88%) | **No** |
| Warnings | basedpyright | Noise budget ~15k product | **No** |

### Interpreting large IDE counts (~12k)

| Figure | Meaning |
| --- | --- |
| IDE “~12662 errors” | Problems panel composite; not exact CLI total |
| Live workspace errors | **~10005** (`reports/bp_workspace_live.json`) |
| of which tests | **~8784 (87.8%)** |
| Product `src/bioetl` errors | **0** |
| Entity unit tests errors | **0** |

**Do not** treat ~12k IDE diagnostics as product CI failure. Product truth = error snapshot + mypy.

## Dual product KPIs

| KPI | Artifact | Guard |
| --- | --- | --- |
| Product errors = 0 | `basedpyright-error-snapshot.json` | `report_basedpyright_error_snapshot --check` |
| Suppressions shrink-only | `basedpyright-suppression-inventory.json` | `report_basedpyright_suppression_inventory --check` |
| Tests/scripts advisory | `basedpyright-tests-snapshot.json` | optional `--check` |

**PD5 floors:** product errors **0**; suppressions **≤228 files** (start); workspace advisory baseline **10005 errors**.

### Regen

```bash
# Product
basedpyright --outputjson src/bioetl > reports/bp_live.json
python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json --check
python -m scripts.engineering.qa.report_basedpyright_suppression_inventory --check

# Workspace / IDE surface
basedpyright --outputjson > reports/bp_workspace_live.json
python -m scripts.engineering.qa.report_basedpyright_tests_snapshot --source reports/bp_workspace_live.json
```

### PR checklist (typing / diagnostics)

1. Product snapshot `--check` (errors stay 0)
2. Suppression inventory `--check` (no growth)
3. Removing a product `# pyright:` flag requires structural fix in the same PR
4. Adding a product `# pyright:` flag requires issue + rationale
5. Test diagnostics PRs should use `tests/helpers/typed_ids.py`, `protocol_stubs.py`, `settings_doubles.py` (see `tests/helpers/TYPED_DOUBLES.md`)
6. mypy CI remains green

### Optional IDE filter

Locally exclude `tests/**` and/or `scripts/**` if Problems floods. Do not commit product error-rule disables.

## Warning policy

Warnings are advisory. Prefer narrow pilots (`reportImplicitOverride` / Port `Any`). Avoid bulk `silver_*.py` without generator plan.

## Related

- Plan: `reports/quality/PROJECT_DIAGNOSTICS_12662_AUDIT_AND_PLAN_2026-07-28.md`
- PD5 pack: `.github/ISSUES/PD5-2026-07-29-PROJECT-DIAGNOSTICS-WORKSPACE-ISSUE-PACK.md`
- `docs/00-project/governance/05-github-policy.md` — `gate.types` = mypy
