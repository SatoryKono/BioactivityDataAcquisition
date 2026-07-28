# basedpyright Project Diagnostics vs CI mypy

Linked campaigns:

- PD (closed): parent `#6925`, PD-0 `#6926` … PD-9 `#6935`
- PD2 (closed): parent `#6949`, PD2-0 `#6950` … PD2-10 `#6960` (product errors → 0)
- **PD3 (structural suppression debt):** parent `#6961`, PD3-0 `#6962` … PD3-9 `#6971`

## Gate semantics (normative for contributors)

| Surface | Tool | Role | Merge-blocking? |
| --- | --- | --- | --- |
| Product type gate | `mypy` on `src/bioetl` (strict, CI `type-check`) | Contract for merge | **Yes** |
| Product basedpyright residual | basedpyright on `src/bioetl` | Shrink-only burn-down | **No** (advisory unless ADR promotes) |
| Product `# pyright:` suppressions | file-level residual flags | Structural debt ledger | **No** — shrink-only inventory |
| Tests/scripts basedpyright residual | basedpyright on workspace / tests | IDE UX / advisory | **No** |
| basedpyright **warnings** | high volume (`reportAny`, `reportUnknown*`, …) | Noise budget | **Not** merge-blocking |

Do **not** treat the IDE error count as the CI type gate. Green CI mypy remains sufficient for type-merge policy.

### Dual baseline (PD2-0)

| Artifact | Scope | Generator | Shrink-only? |
| --- | --- | --- | --- |
| `reports/quality/basedpyright-error-snapshot.json` | **product** `src/bioetl` | `report_basedpyright_error_snapshot` | **Yes** (canonical) |
| `reports/quality/basedpyright-tests-snapshot.json` | **tests + scripts** (advisory) | `report_basedpyright_tests_snapshot` | **Yes** (advisory; not CI) |
| `reports/quality/basedpyright-suppression-inventory.json` | product `# pyright:` flags | `report_basedpyright_suppression_inventory` | **Yes** (debt ledger) |

Typical live magnitudes (post-PD2/PD3 start): product **errors = 0**; product **warnings ≈ 15k** (advisory); suppression files baseline **~308**.

### Regen recipe (product)

```bash
basedpyright --outputjson src/bioetl > reports/bp_live.json
python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json
python -m scripts.engineering.qa.report_basedpyright_error_snapshot --source reports/bp_live.json --check
```

**Invariant (PD3):** product `error_count` must stay **0** (shrink-only non-growth). Snapshot `--check` fails if residual regrows.

### Regen recipe (tests/scripts advisory)

```bash
basedpyright --outputjson > reports/bp_workspace.json
python -m scripts.engineering.qa.report_basedpyright_tests_snapshot --source reports/bp_workspace.json
python -m scripts.engineering.qa.report_basedpyright_tests_snapshot --source reports/bp_workspace.json --check
```

If CLI is unavailable, keep an IDE-exported JSON and re-run the matching snapshot command only.

### Suppression debt governance (PD3-0 / PD3-9)

Product open errors can be 0 while **file-level suppressions** remain (`# pyright: reportX=false`). That is tracked debt, not a free pass.

```bash
python -m scripts.engineering.qa.report_basedpyright_suppression_inventory
python -m scripts.engineering.qa.report_basedpyright_suppression_inventory --check
```

**Rules for contributors:**

1. **Do not add** new product `# pyright: reportX=false` without linking a GH issue and a one-line rationale in the same PR.
2. When **editing** a suppressed file: try **removing** the directive first; fix structurally (`self: HostProtocol`, `TYPE_CHECKING`, typed boundaries) so basedpyright stays clean.
3. Prefer Protocol host contracts over permanent suppressions.
4. Suppression inventory is **shrink-only** (file count and rule-assignment count must not grow).
5. Import cycles: `configs/quality/basedpyright_import_cycle_allowlist.json` is also shrink-only.

### Wave success metrics

| Campaign | Target |
| --- | --- |
| PD2 (done) | product errors → 0 |
| PD3 | suppressions file count ↓ ≥40% from ~308; product errors stay 0 |
| Structural tracks S1–S4 | remove uninit/attr/cast/arg flags via Host Protocols |

## Warning budget policy

1. **CI blocking** remains mypy on `src/bioetl`.
2. **Product basedpyright errors** must stay **0** (snapshot guard).
3. **Suppression debt** is the active burn-down target (PD3).
4. **Tests/scripts basedpyright errors** are advisory.
5. **Warnings** stay advisory. Optional personal IDE demotion of warning-class rules only — never silent global disable of product **error** rules.
6. Import cycles: allowlist shrink-only. Prefer `TYPE_CHECKING` / types modules.

### Optional personal IDE filter

Contributors may exclude `tests/**` from IDE type checking locally if the Problems panel is dominated by test fixture noise. Do **not** commit repo-wide disable of product error rules.

## Related

- Audit: `reports/quality/PROJECT_DIAGNOSTICS_AUDIT_2026-07-28.md`
- PD3 issue pack: `.github/ISSUES/PD3-2026-07-28-PROJECT-DIAGNOSTICS-STRUCTURAL-DEBT-ISSUE-PACK.md`
- Plan: `reports/quality/PROJECT_DIAGNOSTICS_REMEDIATION_PLAN_2026-07-28.md`
- `docs/00-project/ai/agents/guides/TEST_LANE_MENTAL_MODEL.md` — test lane vs type gates
- `docs/00-project/governance/05-github-policy.md` — CI `gate.types` = mypy
