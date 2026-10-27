# PSC RF-006 — Track closeout verify on exact SHA

**Status:** `done` (all three §1.1 surfaces green; RF-001…RF-005 landed)  
**Issue:** [#12571](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/12571)  
**Verify tip (`origin/main` post RF-003 merge):** `9a1d2738053cc0bcaf08e1aba414aa13ca6e32a1`  
**Scope:** validation-only + status evidence; **no** feature code; **no** tech-debt budget expansion.

## 1. Prior slice provenance (preserve, do not overwrite)

| RF | Issue | PR | Merge tip on `main` |
| --- | --- | --- | --- |
| RF-001 | `#12566` | `#12572` | `3b8466d140` |
| RF-005 | `#12570` | `#12573` | `635e4dfe9e` |
| RF-004 | `#12569` | `#12574` | `6c4e21f150` |
| RF-002 | `#12567` | `#12575` | `5416aa7a1c` (`rf002_debt_cleared_sha`) |
| RF-003 | `#12568` | `#12578` | `9a1d273805` (verify tip) |

RF-001 inventory baseline SHA (frozen): `100854af874059f7a873a501518e2955f6eb5916`.

## 2. §1.1 surfaces @ verify tip

| Surface | Criterion | Evidence @ `9a1d273805…` |
| --- | --- | --- |
| CLI | SSOT loader/tests + RF-005 docs pointer | `test_cli_architecture_policy` / `test_interfaces_no_infrastructure` green; pointer in `docs/02-architecture/04-interfaces-layer.md` §3.1 (`.importlinter` `interfaces-no-direct-infrastructure` + `_cli_architecture_policy.py`) |
| Domain I/O | inventory `--check` + RF-004 Variant A / `#12477` residue | `report-domain-io-taint-inventory --check` exit 0; `violation_count=0`; closeout `reports/domain-io-psc-rf004-closeout.md`; residue **not** PASS (waiver ≠ PASS) |
| Config forbid | inventory + debt(a)=0 + ratchet + dual registries + DQ ingress≠projection | see §3 |

## 3. Full manifest reconcile

Command: `.venv/bin/python -m tests.architecture._config_extra_forbid_inventory --check` → **exit 0** (zero artifact drift vs live schemas scan).

| Metric | Value |
| --- | --- |
| `basemodel_total` | 105 |
| `effective_forbid` | 105 |
| `effective_ignore` | 0 |
| `migration_debt_identities` (a) | `[]` (exact empty) |
| `forbid_new_baseline_identities` ceiling | 36 (frozen frozenset; not widened) |
| `justified_exclusions` (b) | 4 (JsonDict, Settings, FilterConfigFile.metadata, adapters/**) with RF-003 anchor tests |
| `runtime_roots` | 13 (4 generator-covered, 9 runtime-only) |
| `nested_paths` | 123 (full reconcile, not changed-paths subset) |
| nested classifications | forbid=118, generator-covered=4, justified-exclusion=1 |

DQ YAML ingress remains `SinkLayerConfig.dq_report → SinkDQReportConfig` (no `checks`); Bronze/Silver/Gold DQ/Sink configs stay projection DTOs with composition mapping owning test.

## 4. Owning validation package (exit 0)

```bash
.venv/bin/python -m pytest \
  tests/architecture/test_cli_architecture_policy.py \
  tests/architecture/test_interfaces_no_infrastructure.py \
  tests/architecture/test_domain_io_taint_inventory.py \
  tests/architecture/test_config_strict_keys.py \
  tests/architecture/test_config_extra_forbid_inventory.py \
  tests/unit/infrastructure/schemas/test_dq_config.py \
  tests/unit/infrastructure/schemas/test_composite_config_schema.py \
  -q
# → exit 0

.venv/bin/python -m scripts.engineering.qa report-domain-io-taint-inventory --check
# → exit 0

.venv/bin/python -m scripts.schema generate-pipeline --check
# → OK pipeline/composite/source/dq.json; exit 0

.venv/bin/python -m tests.architecture._config_extra_forbid_inventory --check
# → exit 0
```

### Plus (plan RF-006)

```bash
.venv/bin/python -m pytest \
  tests/architecture/test_rf003_config_extra_forbid_ratchet.py \
  tests/unit/infrastructure/schemas/test_rf002_extra_forbid_migration.py \
  tests/unit/infrastructure/schemas/test_rf003_extra_forbid_negatives.py \
  tests/unit/composition/factories/dq/test_rf002_sink_projection_mapping.py \
  -q
# → exit 0 (composition + runtime-only matrix + unknown-key-by-classification + registry (b) anchors)
```

## 5. ARTIFACT_REFRESH

- `config-extra-forbid-inventory.json`: **no rebind** — `--check` matched generator bit-for-bit @ tip.
- `configs/_schema/*.json`: **no rebind** — `generate-pipeline --check` OK.
- `domain-io-taint-inventory.json`: **no rebind** — `--check` OK.
- This file is the RF-006 evidence receipt only (validation/status).

## 6. Skipped (by plan default)

- Docker / monitoring stack
- Ad-hoc full `tests/architecture` fullsuite (no issue authority; `#12477` residue remains documented under RF-004)
- Tech-debt budget increases (forbidden)

## 7. Track status

Policy Schema Cleanup track → **`done`**: RF-001…RF-005 merged; RF-006 verify green on exact SHA `9a1d2738053cc0bcaf08e1aba414aa13ca6e32a1`.

### Residual (documented, out of PSC `done` gate)

- `#12477` architecture fullsuite residue (10 failed / 5592 passed / 19 skipped) — **OPEN**, not PASS; owned by RF-004 evidence / `NAMED_BLOCKER_12464.md` KEEP path. Does **not** block PSC `done` once RF-004 documented it as residue.
