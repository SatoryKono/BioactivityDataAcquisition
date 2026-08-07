# basedpyright Project Diagnostics vs CI mypy

Linked campaigns:

- PD–PD5 (closed): product errors → 0; tests unit surface burn; suppressions inventory
- **PD6 (closed):** `#7042` … `#7052` — ~15k IDE figure = product **warnings**
- **PD7 (closed):** `#7078` … `#7087` — ~15.9k warnings residual; pyarrow stubs + workspace regen

## Gate semantics

| Surface | Tool | Role | Merge-blocking? |
| --- | --- | --- | --- |
| Product type gate | `mypy` on `src/bioetl` | Merge contract | **Yes** |
| Product basedpyright **errors** | basedpyright `src/bioetl` | Must stay **0** | No (advisory) |
| Product basedpyright **warnings** | basedpyright `src/bioetl` | Shrink-only advisory ledger | **No** |
| Product `# pyright:` suppressions | file-level flags | Shrink-only debt ledger | No |
| Workspace / tests diagnostics | basedpyright full tree | IDE UX | **No** |

### Interpreting large IDE counts

| Figure | Meaning |
| --- | --- |
| IDE “~15062 / ~15890 errors” | **Product warnings** (~13.2k–15.9k era); **not** product errors |
| Live product **errors** | **0** |
| Live product **warnings** (PD7 closeout) | **~13175** |
| Workspace **errors** (PD7 regen) | **~1375** (tests ~82) |
| Suppressions | **~196 files / ~250 rules** |

**Do not** treat large IDE diagnostics as product CI failure. Product truth = error snapshot + mypy.

## Product KPIs

| KPI | Artifact | Guard |
| --- | --- | --- |
| Product errors = 0 | `basedpyright-error-snapshot.json` | `--check` |
| Warnings shrink-only | `basedpyright-warning-snapshot.json` | `--check` |
| Suppressions shrink-only | `basedpyright-suppression-inventory.json` | `--check` |
| Tests/scripts advisory | `basedpyright-tests-snapshot.json` | optional `--check` |

**PD7 floors (residual close):** errors **0**; warnings **≤13346**; suppressions **≤46 files / ≤60 rules**; workspace **≤1375 errors**.

### Regen

The warning snapshot command is implemented by
`scripts/engineering/qa/report_basedpyright_warning_snapshot.py`.

```bash
basedpyright --outputjson src/bioetl > reports/bp_live.json
python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json --check
python -m scripts.engineering.qa.report_basedpyright_warning_snapshot --source reports/bp_live.json --check
python -m scripts.engineering.qa.report_basedpyright_suppression_inventory --check

basedpyright --outputjson > reports/bp_workspace_live.json
python -m scripts.engineering.qa.report_basedpyright_tests_snapshot --source reports/bp_workspace_live.json
```

### PR checklist

1. Product error snapshot `--check` (errors stay 0)
2. Warning snapshot `--check` (no growth)
3. Suppression inventory `--check` (no growth)
4. Removing `# pyright:` requires structural fix in same PR
5. Prefer Host Protocols over host-default `cast(Any, None)` for uninit
6. Schema megatrees: maintain `configs/typing-stubs/pyarrow` stubs / generator — no bulk silver hand-edit
7. mypy CI remains green

### Optional IDE filter

Locally exclude `tests/**`, `scripts/**`, `src/memory/**` if Problems floods.

## Schema / pyarrow note (PD7-4)

Local stubs live in `configs/typing-stubs/pyarrow/`
(`pyproject.toml` → `[tool.basedpyright].stubPath = "configs/typing-stubs"`).
Optional rewrite generator: `scripts/schema/generation/generate_typed_arrow_schema_sources.py`.
See `reports/quality/pd7-schema-generator-implementation.md`.

## Related

- Plan (~15.9k): `reports/quality/PROJECT_DIAGNOSTICS_15890_AUDIT_AND_PLAN_2026-07-29.md`
- PD7 pack: `.github/ISSUES/PD7-2026-07-29-PROJECT-DIAGNOSTICS-WARNINGS-RESIDUAL-ISSUE-PACK.md`
- PD7 closeout: `reports/quality/pd7-campaign-closeout-2026-07-29.md`
- PD6 closeout: `reports/quality/pd6-campaign-closeout-2026-07-29.md`
- `docs/00-project/governance/05-github-policy.md` — `gate.types` = mypy
