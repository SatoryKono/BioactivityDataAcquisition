# basedpyright Project Diagnostics vs CI mypy

Linked campaigns:

- PD–PD4 (closed): product errors → 0; suppression inventory; Host Protocol partial burn-down
- **PD5 (closed):** `#6994` … `#7004` — workspace ~10k → ~2.2k (tests unit surface) + product suppression residual
- **Next (planned):** ~15k IDE figure is primarily **product warnings** (~15.5k), not product errors — see `reports/quality/PROJECT_DIAGNOSTICS_15062_AUDIT_AND_PLAN_2026-07-29.md`

## Gate semantics

| Surface | Tool | Role | Merge-blocking? |
| --- | --- | --- | --- |
| Product type gate | `mypy` on `src/bioetl` | Merge contract | **Yes** |
| Product basedpyright **errors** | basedpyright `src/bioetl` | Must stay **0** | No (advisory) |
| Product `# pyright:` suppressions | file-level flags | Shrink-only debt ledger | No |
| Workspace / tests diagnostics | basedpyright full tree | IDE UX (post-PD5 ~2.2k errors) | **No** |
| Warnings | basedpyright | Noise budget ~15.5k product | **No** |

### Interpreting large IDE counts (~12k / ~15k)

| Figure | Meaning |
| --- | --- |
| IDE “~12662 errors” (pre-PD5) | Problems panel composite; not exact CLI total |
| IDE “~15062 errors” (post-PD5) | **Best match: product warnings ~15523** (±3%); **not** product errors |
| Live workspace errors (PD5 start) | **~10005** |
| Live workspace errors (**after PD5**) | **~2174** |
| of which tests (after PD5) | **~909** |
| Product `src/bioetl` **errors** | **0** |
| Product `src/bioetl` **warnings** | **~15523** (advisory; Any/Unknown ~67%) |
| Entity unit tests errors | **0** |
| `tests/unit/{application,composition,infrastructure}` | **0** each (PD5 surface) |

**Do not** treat large IDE diagnostics as product CI failure. Product truth = error snapshot + mypy.

## Dual product KPIs

| KPI | Artifact | Guard |
| --- | --- | --- |
| Product errors = 0 | `basedpyright-error-snapshot.json` | `report_basedpyright_error_snapshot --check` |
| Suppressions shrink-only | `basedpyright-suppression-inventory.json` | `report_basedpyright_suppression_inventory --check` |
| Tests/scripts advisory | `basedpyright-tests-snapshot.json` | optional `--check` |

**PD5 floors (closeout):** product errors **0**; suppressions **≤220 files / ≤274 rules**; workspace advisory **≤2174 errors** (shrink-only from here).

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
6. Unit test packages under `tests/unit/{application,composition,infrastructure}` carry PD5 mock/fixture surface headers — do not weaken product NewTypes/Ports
7. mypy CI remains green

### Optional IDE filter

Locally exclude `tests/**`, `scripts/**`, and/or `src/memory/**` if Problems floods. Do not commit product error-rule disables.

## Warning policy

Warnings are advisory. Prefer narrow pilots (`reportImplicitOverride` / Port `Any`). Avoid bulk `silver_*.py` without generator plan. See `reports/quality/pd5-warnings-pilot-note.md`.

## Related

- Plan (~15k / warnings-era): `reports/quality/PROJECT_DIAGNOSTICS_15062_AUDIT_AND_PLAN_2026-07-29.md`
- Plan (~12k / workspace-era): `reports/quality/PROJECT_DIAGNOSTICS_12662_AUDIT_AND_PLAN_2026-07-28.md`
- PD5 pack: `.github/ISSUES/PD5-2026-07-29-PROJECT-DIAGNOSTICS-WORKSPACE-ISSUE-PACK.md`
- PD5 closeout: `reports/quality/pd5-campaign-closeout-2026-07-29.md`
- Scripts/memory advisory: `reports/quality/pd5-scripts-memory-advisory-note.md`
- `docs/00-project/governance/05-github-policy.md` — `gate.types` = mypy
