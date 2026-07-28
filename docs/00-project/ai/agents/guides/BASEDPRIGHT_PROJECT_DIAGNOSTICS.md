# basedpyright Project Diagnostics vs CI mypy

Linked campaigns:

- PD (closed): `#6925` … `#6935`
- PD2 (closed): `#6949` … `#6960` (product errors → 0)
- PD3 (closed): `#6961` … `#6971` (suppression inventory + partial structural debt)
- **PD4 (active):** `#6972` … `#6981` — Host Protocol burn-down of remaining file-level suppressions

## Gate semantics (normative for contributors)

| Surface | Tool | Role | Merge-blocking? |
| --- | --- | --- | --- |
| Product type gate | `mypy` on `src/bioetl` (strict, CI `type-check`) | Contract for merge | **Yes** |
| Product basedpyright residual | basedpyright on `src/bioetl` | Shrink-only burn-down | **No** (advisory unless ADR promotes) |
| Product `# pyright:` suppressions | file-level residual flags | Structural debt ledger | **No** — shrink-only inventory |
| Tests/scripts basedpyright residual | basedpyright on workspace / tests | IDE UX / advisory | **No** |
| basedpyright **warnings** | high volume (`reportAny`, `reportUnknown*`, …) | Noise budget | **Not** merge-blocking |

Do **not** treat the IDE error count as the CI type gate. Green CI mypy remains sufficient for type-merge policy.

## Dual KPI lock (PD4-0)

| KPI | Artifact | Guard |
| --- | --- | --- |
| Product **errors = 0** | `reports/quality/basedpyright-error-snapshot.json` | `report_basedpyright_error_snapshot --check` |
| Suppression **files/rules shrink-only** | `reports/quality/basedpyright-suppression-inventory.json` | `report_basedpyright_suppression_inventory --check` |
| Tests/scripts advisory | `reports/quality/basedpyright-tests-snapshot.json` | optional `--check` |

**PD4 floor (start of campaign):** product errors **0**; suppressions **239 files / 296 rules** (do not grow).

### PR checklist for typing / diagnostics changes

When a PR touches `src/bioetl/**` typing, mixins, ports, or `# pyright:` directives:

1. [ ] `basedpyright --outputjson src/bioetl > reports/bp_live.json`
2. [ ] `python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json --check` → product errors non-growth (**must stay 0**)
3. [ ] `python -m scripts.engineering.qa.report_basedpyright_suppression_inventory --check` → suppressions non-growth
4. [ ] If you **remove** a `# pyright: reportX=false`, include structural fix (Host Protocol / `self: Host` / TYPE_CHECKING / typed boundary) and say so in the PR body
5. [ ] If you **add** a `# pyright: reportX=false`, link a GH issue and one-line rationale
6. [ ] mypy CI path still green (do not weaken strict product gate)

### Regen recipes

```bash
# Product errors
basedpyright --outputjson src/bioetl > reports/bp_live.json
python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json
python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json --check

# Suppression ledger
python -m scripts.engineering.qa.report_basedpyright_suppression_inventory
python -m scripts.engineering.qa.report_basedpyright_suppression_inventory --check

# Tests/scripts advisory (optional)
basedpyright --outputjson > reports/bp_workspace.json
python -m scripts.engineering.qa.report_basedpyright_tests_snapshot --source reports/bp_workspace.json
```

### Suppression debt rules

1. Prefer Protocol host contracts over permanent suppressions.
2. On edit of a suppressed file: **try remove the directive first**, then structural fix until basedpyright is clean.
3. Import cycles: `configs/quality/basedpyright_import_cycle_allowlist.json` shrink-only.
4. Warnings stay advisory (PD4-8 pilot only unless ADR promotes).

### Wave targets (PD4)

| Wave | Target |
| --- | --- |
| W1 Host Protocols | uninit ≤25; attr ≤20; files ≤190 |
| W2 InvalidCast | cast flags ≤15 |
| W3 Cycles | cycle flags ≤18 |
| W4 ArgumentType | arg flags ≤20 |
| Stretch epic close | suppression files ≤150; product errors=0 |

## Warning budget policy

1. **CI blocking** remains mypy on `src/bioetl`.
2. **Product basedpyright errors** must stay **0**.
3. **Suppression debt** is the active structural burn-down (PD4).
4. **Warnings** are advisory; optional personal IDE demotion only.
5. Do not bulk-edit `infrastructure/schemas/silver_*.py` megawarn modules without a generator strategy.

### Optional personal IDE filter

Contributors may exclude `tests/**` from IDE type checking locally. Do **not** commit repo-wide disable of product error rules.

## Related

- Plan/audit: `reports/quality/PROJECT_DIAGNOSTICS_AUDIT_AND_PLAN_2026-07-28.md`
- PD4 pack: `.github/ISSUES/PD4-2026-07-28-PROJECT-DIAGNOSTICS-HOST-PROTOCOL-ISSUE-PACK.md`
- `docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md`
- `docs/00-project/governance/05-github-policy.md` — CI `gate.types` = mypy
