# basedpyright Project Diagnostics vs CI mypy

Linked campaigns:

- PD–PD4 (closed): product errors → 0; suppression inventory; Host Protocol partial burn-down
- **PD5 (closed):** `#6994` … `#7004` — workspace ~10k → ~2.2k (tests unit surface)
- **PD6 (closed):** `#7042` … `#7052` — ~15k IDE figure = product **warnings**; residual suppressions + tests/memory/scripts advisory
- **PD7 (open):** `#7078` … `#7087` — ~15.9k IDE figure = product **warnings** (~15.8k) + suppressions residual — plan `reports/quality/PROJECT_DIAGNOSTICS_15890_AUDIT_AND_PLAN_2026-07-29.md`

## Gate semantics

| Surface | Tool | Role | Merge-blocking? |
| --- | --- | --- | --- |
| Product type gate | `mypy` on `src/bioetl` | Merge contract | **Yes** |
| Product basedpyright **errors** | basedpyright `src/bioetl` | Must stay **0** | No (advisory) |
| Product basedpyright **warnings** | basedpyright `src/bioetl` | Shrink-only advisory ledger | **No** |
| Product `# pyright:` suppressions | file-level flags | Shrink-only debt ledger | No |
| Workspace / tests diagnostics | basedpyright full tree | IDE UX | **No** |

### Interpreting large IDE counts (~12k / ~15k)

| Figure | Meaning |
| --- | --- |
| IDE “~12662 errors” (pre-PD5) | Problems panel composite; not exact CLI total |
| IDE “~15062 errors” (post-PD5) | **Best match: product warnings ~15.5k–15.8k**; **not** product errors |
| IDE “~15890 errors” (post-PD6) | **Best match: product warnings ~15774** (±1%); **not** product errors |
| Live workspace errors (after PD5) | **~2174** (further residual tests burned in PD6) |
| Product `src/bioetl` **errors** | **0** |
| Product `src/bioetl` **warnings** | **~15.8k** advisory (Any/Unknown dominant) |
| Entity + unit app/comp/infra tests | **0** errors (PD5) |
| Residual tests (repo_backed / neo4j support / interfaces / domain) | PD6 surface → ~0 |

**Do not** treat large IDE diagnostics as product CI failure. Product truth = error snapshot + mypy.

## Dual / triple product KPIs

| KPI | Artifact | Guard |
| --- | --- | --- |
| Product errors = 0 | `basedpyright-error-snapshot.json` | `report_basedpyright_error_snapshot --check` |
| Suppressions shrink-only | `basedpyright-suppression-inventory.json` | `report_basedpyright_suppression_inventory --check` |
| Warnings shrink-only (advisory) | `basedpyright-warning-snapshot.json` | `report_basedpyright_warning_snapshot --check` |
| Tests/scripts advisory | `basedpyright-tests-snapshot.json` | optional `--check` |

**PD6 floors (closeout):** product errors **0**; suppressions **≤195 files / ≤249 rules**; warnings floor **≤15769** (post-pilot live; shrink-only from here); residual test packages near **0**.

### Regen

```bash
# Product
basedpyright --outputjson src/bioetl > reports/bp_live.json
python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json --check
python -m scripts.engineering.qa.report_basedpyright_warning_snapshot --source reports/bp_live.json --check
python -m scripts.engineering.qa.report_basedpyright_suppression_inventory --check

# Workspace / IDE surface
basedpyright --outputjson > reports/bp_workspace_live.json
python -m scripts.engineering.qa.report_basedpyright_tests_snapshot --source reports/bp_workspace_live.json
```

### PR checklist (typing / diagnostics)

1. Product error snapshot `--check` (errors stay 0)
2. Warning snapshot `--check` (no growth)
3. Suppression inventory `--check` (no growth)
4. Removing a product `# pyright:` flag requires structural fix in the same PR
5. Adding a product `# pyright:` flag requires issue + rationale
6. Test diagnostics: use `tests/helpers/{typed_ids,protocol_stubs,settings_doubles}` / PD5–PD6 surface headers — never weaken product NewTypes/Ports
7. Do **not** bulk-edit `infrastructure/schemas/silver_*.py` without generator plan
8. mypy CI remains green

### Optional IDE filter

Locally exclude `tests/**`, `scripts/**`, and/or `src/memory/**` if Problems floods. Do not commit product error-rule disables.

## Warning policy

Warnings are advisory. Prefer:

1. Host Protocol / boundary typing (suppressions + Any burn)
2. Schema **generator** strategy for silver_*/gold megatrees
3. Narrow pilots (`reportImplicitOverride`, unused, string concat)

Avoid bulk silver hand-edits. See `reports/quality/pd6-warnings-pilot-note.md` and `pd6-schema-generator-strategy.md`.

## Related

- Plan (~15.9k / post-PD6 warnings): `reports/quality/PROJECT_DIAGNOSTICS_15890_AUDIT_AND_PLAN_2026-07-29.md`
- PD7 pack: `.github/ISSUES/PD7-2026-07-29-PROJECT-DIAGNOSTICS-WARNINGS-RESIDUAL-ISSUE-PACK.md`
- Plan (~15k / warnings-era): `reports/quality/PROJECT_DIAGNOSTICS_15062_AUDIT_AND_PLAN_2026-07-29.md`
- Plan (~12k / workspace-era): `reports/quality/PROJECT_DIAGNOSTICS_12662_AUDIT_AND_PLAN_2026-07-28.md`
- PD6 pack: `.github/ISSUES/PD6-2026-07-29-PROJECT-DIAGNOSTICS-WARNINGS-ISSUE-PACK.md`
- PD6 closeout: `reports/quality/pd6-campaign-closeout-2026-07-29.md`
- PD5 closeout: `reports/quality/pd5-campaign-closeout-2026-07-29.md`
- Memory/scripts advisory: `reports/quality/pd6-memory-scripts-advisory-note.md`
- `docs/00-project/governance/05-github-policy.md` — `gate.types` = mypy
