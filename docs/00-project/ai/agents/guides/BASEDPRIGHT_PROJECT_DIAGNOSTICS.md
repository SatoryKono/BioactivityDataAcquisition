# basedpyright Project Diagnostics vs CI mypy

Linked campaigns:

- PD (closed): parent `#6925`, PD-0 `#6926` … PD-9 `#6935`
- **PD2 (active residual):** parent `#6949`, PD2-0 `#6950` … PD2-10 `#6960`

## Gate semantics (normative for contributors)

| Surface | Tool | Role | Merge-blocking? |
| --- | --- | --- | --- |
| Product type gate | `mypy` on `src/bioetl` (strict, CI `type-check`) | Contract for merge | **Yes** |
| Product basedpyright residual | basedpyright on `src/bioetl` | Shrink-only burn-down | **No** (advisory unless ADR promotes) |
| Tests/scripts basedpyright residual | basedpyright on workspace / tests | IDE UX / advisory | **No** |
| basedpyright **warnings** | high volume (`reportAny`, `reportUnknown*`, …) | Noise budget | **Not** merge-blocking |

Do **not** treat the IDE error count as the CI type gate. Green CI mypy remains sufficient for type-merge policy.

### Dual baseline (PD2-0)

| Artifact | Scope | Generator | Shrink-only? |
| --- | --- | --- | --- |
| `reports/quality/basedpyright-error-snapshot.json` | **product** `src/bioetl` | `report_basedpyright_error_snapshot` | **Yes** (canonical) |
| `reports/quality/basedpyright-tests-snapshot.json` | **tests + scripts** (advisory) | `report_basedpyright_tests_snapshot` | **Yes** (advisory; not CI) |

Typical live magnitudes (2026-07-28): product **~989** errors; workspace **~16k** (tests dominate); `tests/unit/domain/entities` alone **~5.1k** (IDE «~4543» cluster hypothesis).

### Regen recipe (product)

```bash
basedpyright --outputjson src/bioetl > reports/bp_live.json
python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json
python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json --check
```

### Regen recipe (tests/scripts advisory)

```bash
basedpyright --outputjson > reports/bp_workspace.json
python -m scripts.engineering.qa.report_basedpyright_tests_snapshot --source reports/bp_workspace.json
python -m scripts.engineering.qa.report_basedpyright_tests_snapshot --source reports/bp_workspace.json --check
```

If CLI is unavailable, keep an IDE-exported JSON and re-run the matching snapshot command only.

### Wave success metrics (PD2)

| Wave | Target |
| --- | --- |
| W1–W2 mixins + casts | product errors ≤ 550 |
| W3–W4 arg/overrides | product ≤ 350 |
| W6 entity fixtures | entity-tests errors ≤ 500 |
| Stretch | product ≤ 150; entity-tests ≤ 100 |

## Warning budget policy

1. **CI blocking** remains mypy on `src/bioetl`.
2. **Product basedpyright errors** are the residual burn-down target (PD2-1…PD2-8).
3. **Tests/scripts basedpyright errors** are advisory (PD2-9/PD2-10); do not fail merge solely on them.
4. **Warnings** stay advisory. Optional personal IDE demotion of warning-class rules only — never silent global disable of product **error** rules.
5. Import cycles: `configs/quality/basedpyright_import_cycle_allowlist.json` (shrink-only). Prefer `TYPE_CHECKING` / types modules.

### Optional personal IDE filter

Contributors may exclude `tests/**` from IDE type checking locally if the Problems panel is dominated by test fixture noise. Do **not** commit repo-wide disable of product error rules.

## Related

- Plan: `reports/quality/PROJECT_DIAGNOSTICS_REMEDIATION_PLAN_2026-07-28.md`
- Issue pack: `.github/ISSUES/PD2-2026-07-28-PROJECT-DIAGNOSTICS-POST-PD-ISSUE-PACK.md`
- `docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md` — test lane vs type gates
- `docs/00-project/governance/05-github-policy.md` — CI `gate.types` = mypy
