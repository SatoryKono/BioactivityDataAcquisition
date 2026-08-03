# BioETL Test System Architecture Audit

| Field | Value |
| --- | --- |
| Date | 2026-07-29 |
| Branch / SHA | `main` @ `73bc2ac3c6` |
| Mode | Fact-based audit (repo inventory + quality artifacts) |
| Scope | `tests/**`, `configs/quality/test_*`, fixtures, coverage inventory, scorecard |
| Architecture lens | Hexagonal + DDD aggregates + Medallion + Composite + determinism/replay + composition-only DI |

**Evidence anchors (primary):**

- `reports/quality/module-coverage-inventory.json` (snapshot tied to `source_tree_sha256`)
- `reports/quality/architecture-quality-scorecard.json` (integral **9.41**)
- `configs/quality/test_matrix.yaml`, `configs/quality/pytest_shards.yaml`
- `configs/quality/fixture_governance_ledger.yaml`, `configs/base/bronze_fixture_manifest.yaml`, `configs/base/bronze_fixture_gaps.yaml`
- Filesystem inventory of `tests/**` and `tests/fixtures/**`

No runtime full-suite timing was executed in this audit (would be hours); performance conclusions use **structural** signals (shard policy, VCR mass, e2e/integration layout, bootstrap mentions) rather than fabricated durations.

---

## 1. Executive verdict

BioETL has a **mature, governance-heavy test system** that is strongly aligned with architecture (layer purity gates, fixture governance, determinism policies, contract snapshots). Quantitative coverage is excellent at module level (**0 uncovered / 2310** source modules; scorecard **Test strategy / testability = 9.9**).

The dominant risks are **not** “missing tests for domain purity,” but:

1. **Cost / speed:** architecture + closeout ratchets are ~22% of all test files; VCR mass (**~139 MB / 402 files**) dwarfs Bronze fixtures (**~1.7 MB / 40 files**); **13/15** shards force `workers_override: 0` (serial-by-default, intentional for determinism).
2. **Partial coverage tail:** **744 / 2310 (32.2%)** modules are `partially_covered` (many still high 90%+; lowest observed ~**62%** on `domain/entities/bioactivity/_converters.py`).
3. **Governance test debt:** ~**16%** of architecture tests are closeout/tech-debt issue ratchets (historical freeze tests), which protect budgets but inflate collection/runtime and duplicate themes (CodeRabbit ARCH-CR2-09 already touched honesty).
4. **Fixture imbalance:** Bronze replay gaps registry is **empty** (`bronze_fixture_gaps.yaml` `gaps: {}`), but **ChEMBL dominates** bronze fixture files (26/40); non-ChEMBL providers have thin exact-replay fixture presence relative to VCR depth.
5. **E2E thin but critical:** only **27** e2e modules cover multi-provider matrix + resilience; high leverage, high cost — must stay curated.

Overall quality of the **test architecture** is high; optimization should **prune governance bloat and I/O weight**, not weaken hexagonal/determinism gates.

---

## 2. Quantitative inventory (facts)

### 2.1 Test file census (`test_*.py` under `tests/`)

| Lane / top-level | Files | Share of 2115 |
| --- | ---: | ---: |
| `tests/unit` | 1378 | **65.2%** |
| `tests/architecture` | 464 | **21.9%** |
| `tests/integration` | 176 | **8.3%** |
| `tests/contract` | 43 | **2.0%** |
| `tests/e2e` | 27 | **1.3%** |
| `tests/security` | 10 | 0.5% |
| `tests/smoke` | 7 | 0.3% |
| `tests/benchmarks` + `performance` | 9 | 0.4% |
| **Total** | **2115** | 100% |

Additional: `tests/unit/repo_backed` ~43 (repo-touching “unit” hybrid); `tests/fixtures/**` ~**502** files (not tests).

### 2.2 Coverage (module inventory)

| Metric | Value | Source |
| --- | ---: | --- |
| Source modules | 2310 | `module-coverage-inventory.json` → `summary.source_module_count` |
| Fully covered | 1476 | `status_counts.fully_covered` |
| Partially covered | **744 (32.2%)** | `status_counts.partially_covered` |
| Uncovered | **0** | `uncovered_module_count` |
| Unmeasured | **0** | `unmeasured_module_count` |
| No executable lines | 90 | `no_executable_lines` |
| Hotspot families (avg line cov) | 95.6–96.8% covered lines | `hotspot_family_coverage` |

**Lowest partial examples (line_coverage %):**

| % | Module |
| ---: | --- |
| 62.16 | `src/bioetl/domain/entities/bioactivity/_converters.py` |
| 68.75 | `src/bioetl/infrastructure/observability/__init__.py` |
| 73.33 | `src/bioetl/composition/bootstrap/__init__.py` |
| 74.42 | `src/bioetl/infrastructure/adapters/_health_check_policy.py` |
| 74.51 | `src/bioetl/domain/normalization/profiles/_profile_governed_value_normalizers.py` |

Many “partial” modules are **already >95%** — formal tail, not black holes.

### 2.3 Scorecard alignment

| Category | Score | Weight |
| --- | ---: | ---: |
| Test strategy / testability | **9.9** | 0.12 |
| Determinism / replay / observability | **9.0** | 0.08 |
| DDD / aggregates / invariants | **9.0** | 0.09 |
| Integral | **9.41** (`good_targeted_improvements`) | — |

### 2.4 Fixtures & VCR

| Surface | Count | Size | Notes |
| --- | ---: | ---: | --- |
| VCR cassettes (`tests/fixtures/vcr`) | 402 | **~138.6 MB** | chembl 105, pubchem 63, openalex/crossref/pubmed/s2 ~49 each, uniprot 35 |
| Bronze fixtures | 40 | **~1.7 MB** | chembl **26**, others 2–4 each |
| Golden fixtures | 31 | small | governed via ledger |
| Contract snapshots | per-provider `v1.json` | — | ledger status **enforced** |
| Bronze gaps registry | `gaps: {}` | — | residual history empty |
| Bronze manifest families | **22** | — | heavy ChEMBL set |

VCR:Bronze size ratio ≈ **82×** — primary disk/CI artifact weight is HTTP replay, not medallion bronze.

### 2.5 Parallelization policy (explicit)

From `configs/quality/test_matrix.yaml`:

- `local_pytest_default: **serial**`
- `forbid_global_xdist_addopts: **true**`
- Parallelism **opt-in** via maintained shards / `unit-parallel-safe`
- VCR lanes: serial/bounded unless isolation proven
- `pytest-xdist` is a dependency (`pyproject.toml`) but **not** default addopts

From `pytest_shards.yaml`:

- **15** shards
- **13/15** set `workers_override: 0` (effectively serial workers inside shard)
- **7** shards are architecture variants all rooted at `tests/architecture` with different ignore globs (collection fan-out cost)

### 2.6 Markers (occurrence counts in sources)

Top: `unit` 6237, `asyncio` 5701, `parametrize` 1490, `architecture` 1427, `integration` 538, `vcr` 239, `e2e` 199, `slow` 65, `hypothesis` 29, `serial` 11.

### 2.7 Critical invariant tests (present)

| Concern | Evidence (examples) |
| --- | --- |
| Batch aggregate / FSM | `tests/unit/domain/aggregates/test_batch*.py` (incl. `test_batch_fsm_exhaustive.py`, property tests) |
| PipelineRun | `test_pipeline_run*.py` under unit aggregates + property tests |
| Quarantine immutability | `tests/architecture/test_quarantine_immutability.py` + unit `test_quarantine_entry*.py` |
| Determinism / identity | arch `test_determinism_*`, `test_deterministic_*`, unit helpers |
| Replay / bronze baseline | `test_bronze_fixture_replay_baseline.py`, replay seam inventories |
| Idempotency gates | `tests/integration/idempotency/*`, `tests/integration/determinism/*` |
| Domain no infra in unit/domain | **0** unit/domain files import `bioetl.infrastructure` (scan) |

---

## 3. Structure assessment (unit / integration / e2e / architecture)

### Strengths

1. **Clear multi-lane taxonomy** with matrix SSOT (`test_matrix.yaml`) and shard inventory.
2. **Architecture tests** enforce Ports & Adapters, DI, naming, fixture governance, determinism policies — these are product-critical, not vanity.
3. **Contract lane** separate from unit (`tests/contract` + snapshots under `tests/fixtures/contracts`).
4. **Domain unit purity signal is green** (no domain→infrastructure imports in `tests/unit/domain` scan).
5. Aggregates have dedicated unit + architecture coverage (Batch / PipelineRun / QuarantineEntry).

### Issues

| ID | Category | Module / area | Problem | Impact | Pri |
| --- | --- | --- | --- | --- | --- |
| S1 | maintainability / performance | `tests/architecture` | **464** files; **~16%** closeout/tech_debt/issue ratchets; **7** shards re-collect same tree with ignore matrices | Slow CI collection; hard onboarding; risk of “governance theater” | P1 |
| S2 | architecture violation (lane hygiene) | `tests/unit/repo_backed`, some unit adapters | “Unit” lane includes repo-backed / network-capable tests (markers `repo_backed`, raw `httpx`/`requests` mentions in ~15 unit files) | Blurs unit purity; forces serial isolation | P1 |
| S3 | maintainability | basename dups | **70** duplicate `test_*.py` basenames (e.g. `test_request_metadata.py` ×7) | Navigation debt; accidental collect confusion | P2 |
| S4 | performance | integration layout | Integration mixes adapters, storage, grafana JSON, pipelines, chembl — uneven cost profiles in one broad lane | Hard to schedule cheap vs expensive | P1 |
| S5 | correctness (coverage of e2e) | `tests/e2e` only 27 | Provider matrix + resilience concentrated; failure of a few files loses system confidence | High leverage fragility | P1 |

**I/O in unit:** not zero by design for infrastructure unit tests (storage/adapters). Violation risk is **domain unit I/O** — not observed via infrastructure imports. Async unit tests (`asyncio` marker density) are appropriate for application/infra ports.

---

## 4. Coverage & relevance

| ID | Category | Evidence | Problem | Impact | Pri |
| --- | --- | --- | --- | --- | --- |
| C1 | correctness | inventory: 0 uncovered | Module floor is excellent | Low residual black-hole risk | — |
| C2 | maintainability | 744 partial modules | Long tail; some converters/normalization <75% | Blind spots on hash/normalization edge paths | P1 |
| C3 | correctness | golden 31 + contract snapshots enforced | Gold/DQ “golden” exists but **provider-imbalanced** vs VCR | Replay exactness stronger for HTTP than for Silver/Gold rows outside ChEMBL | P1 |
| C4 | maintainability | weak assert scan | Almost no assert-less tests (1 `no_assert` candidate: `tests/unit/domain/ports/test_protocol_stubs.py`) | Not a systemic hollow-assert epidemic | P2 |
| C5 | correctness | hypothesis marker only **29** | Property tests exist for aggregates but sparse outside | Missed invariant fuzzing for normalizers/ids | P2 |
| C6 | architecture | closeout tests dominate S7 shards | Many tests assert **JSON artifacts / budgets** rather than runtime behavior | Protects gates; weak as regression detectors for code paths | P1 |

### Critical invariants: status

| Invariant | Status | Notes |
| --- | --- | --- |
| Batch lifecycle / FSM | **Strong** | Exhaustive + property unit tests |
| PipelineRun FSM | **Strong** | Multiple unit modules + events |
| Quarantine immutability | **Strong** | Architecture gate + unit |
| Deterministic identity/sort | **Strong** | Dedicated architecture policies |
| Composite FSM | **Present** | application/composite FSM suite |
| Control-plane replay | **Present** | replay* architecture + CP unit services |
| Metrics/tracing emission | **Present but uneven** | 81 obs-named tests; integration emission tests exist; not all pipelines assert metric side-effects |

---

## 5. Obsolete / legacy / duplicate tests

| ID | Category | Evidence | Problem | Impact | Pri |
| --- | --- | --- | --- | --- | --- |
| O1 | duplication / maintainability | ~75 closeout/tech_debt architecture files | Historical issue freezes remain executable forever | Runtime + cognitive load | P1 |
| O2 | duplication | 7 architecture shards | Repeated collection of `tests/architecture` | CI wall-clock | P1 |
| O3 | maintainability | basename collisions (70) | Same names across providers | Hard search/debug | P2 |
| O4 | correctness | CR residual (#7010-style) missing nominal tests | New helpers under-tested while closeouts remain | Inverted effort: freeze old, miss new | P0–P1 |
| O5 | architecture | ARCH-CR2 config findings | Some governance YAML assertions may be stale/noisy | False confidence or noise | P2 |

**Not classified as obsolete without file-level proof:** e2e provider suite (still maps to live providers). Do **not** mass-delete without reachability + ledger rules (`fixture_governance_ledger.pruning_policy`).

---

## 6. Fixture & data strategy

### Strengths

- Ledger fields **enforced**: cassette metadata, staleness age, catalog, contract snapshots, bronze replay, golden masters, extensionless ban.
- `bronze_fixture_gaps.yaml` gaps empty → no *registered* active bronze gap.
- Contract snapshots for all main providers under `tests/fixtures/contracts/*/v1.json`.
- VCR max age **90 days** + metadata required (matrix).

### Gaps / risks

| ID | Category | Evidence | Problem | Impact | Pri |
| --- | --- | --- | --- | --- | --- |
| F1 | correctness / determinism | bronze files chembl 26 vs others 2 | Non-ChEMBL **exact-replay bronze** thin vs deep VCR | Replay confidence skewed to ChEMBL | P1 |
| F2 | performance | VCR 139MB | Clone/CI cache heavy; rec-record costly | Slow pipelines, disk | P1 |
| F3 | maintainability | golden_master `target_resolution_date` 2026-06-30 in ledger | Date passed; status still enforced — policy hygiene | Stale promotion metadata | P2 |
| F4 | correctness | cassette_metadata_backfill_workflow_present: **false** in matrix | Backfill script exists but workflow flag false | Ops friction on stale cassettes | P2 |
| F5 | determinism | fixture pruning forbids age-only delete | Correct for reproducibility | Limits aggressive cassette pruning | constraint |

---

## 7. Performance (structural hotspots)

| Hotspot | Why slow | Evidence |
| --- | --- | --- |
| Architecture S7 shards (×7) | Huge collection + many file reads of inventories | 464 tests; multi-shard path `tests/architecture` |
| Integration adapters + storage | Real FS / Delta / optional network isolation | `S5-infra-adapters` includes integration paths |
| E2E provider matrix | Full pipeline paths, VCR, multi-stage | 27 files covering chembl/pubchem/uniprot/pubs + resilience |
| VCR-backed integration/unit hybrids | Cassette load + HTTP stack | 239 `@pytest.mark.vcr` occurrences; 88 files mention vcr |
| Composition unit suite | DI graph / bootstrap mentions | 99 unit tests mention bootstrap/container patterns |
| Async unit density | Event-loop tests | 5701 `asyncio` marker hits |

**Inefficient patterns observed:**

1. **Serial default** is a deliberate determinism tradeoff — not a bug, but a speed ceiling.
2. **Closeout tests** add little runtime path coverage relative to cost.
3. **Repeated architecture collection** across S7-a/a2/a3/b/c/d/guardrails.
4. **Bootstrap mentions** in unit composition (expected for composition tests) — ensure session-scoped fixtures; risk if each test rebuilds full graph (needs profiling to quantify).

**Top-10 “zones” (not timed runs):**

1. `tests/architecture` closeout cluster
2. `tests/architecture` full collect (all S7)
3. `tests/fixtures/vcr/**` mass
4. `tests/e2e/test_pipeline_matrix_e2e.py` + full_pipeline*
5. `tests/integration/adapters`
6. `tests/integration/infrastructure`
7. `tests/unit/infrastructure/adapters` + storage
8. `tests/unit/application/services` (control_plane heavy)
9. `tests/unit/composition` bootstrap
10. Contract snapshot drift suite (cheaper but CI-critical)

---

## 8. Determinism / reproducibility

| Signal | Finding |
| --- | --- |
| `datetime.now` in tests | 37 hits — **mostly architecture policy tests that ban production use** |
| Domain unit infra import | **0** |
| Random in writers | Guarded by `test_no_random_in_writers.py` |
| Explicit serial markers | 11 |
| Flaky inventory | Not measured this run (no junit flaky report consumed) |
| Idempotency/replay gates | Present under integration + architecture |

**Risks:**

| ID | Category | Problem | Pri |
| --- | --- | --- | --- |
| D1 | correctness | Any residual live-network unit paths without VCR | P1 |
| D2 | correctness | Partial coverage on normalizers/converters can hide hash drift | P1 |
| D3 | performance vs determinism | Pushing global xdist without lane isolation would risk VCR races | constraint |

---

## 9. Observability testing

**Present:** metric naming/governance architecture tests; integration emission consistency; composition observability API/contract; tracing enforcement; storage observability guardrails; dashboard metric semantics integration.

**Gaps:**

| ID | Category | Problem | Pri |
| --- | --- | --- | --- |
| V1 | correctness | Not every pipeline unit asserts MetricsPort/TracingPort interactions | P2 |
| V2 | maintainability | Dashboard tests split across architecture + integration root files | P2 |
| V3 | architecture | Optional Grafana path must not become required for green unit/domain | constraint |

---

## 10. Problem map (consolidated)

| # | Category | Module / area | Problem | Impact | Priority |
| --- | --- | --- | --- | --- | --- |
| 1 | performance | `tests/architecture` + 7 S7 shards | Governance/closeout mass + multi-collect | Slow CI / local arch runs | **P1** |
| 2 | performance | `tests/fixtures/vcr` | 139MB / 402 cassettes | Clone & CI I/O | **P1** |
| 3 | correctness | partial coverage tail (744 mods) | Edge paths under-tested (esp. converters/normalizers) | Hash/DQ silent drift | **P1** |
| 4 | correctness | bronze fixtures non-ChEMBL thin | Replay depth imbalance | Provider inequality | **P1** |
| 5 | maintainability | closeout architecture tests (~16%) | Freeze historical issues forever | Noise, slow collect | **P1** |
| 6 | architecture violation (lane) | unit/repo_backed + some adapter unit | Unit lane not always pure | Parallelization blocked | **P1** |
| 7 | duplication | basename dups; arch shard fan-out | Repeated structure | Cost | **P2** |
| 8 | correctness | sparse Hypothesis outside aggregates | Weak generative coverage | Missed invariants | **P2** |
| 9 | maintainability | golden ledger target_resolution_date past | Stale governance metadata | Process drift | **P2** |
| 10 | performance | e2e concentration | Few files, high cost | Fragile confidence | **P1** |
| 11 | correctness | observability side-effect asserts uneven | Metrics may regress unnoticed | Ops blind spots | **P2** |
| 12 | maintainability | bootstrap-heavy composition unit | Possible repeated DI setup | Local slow unit | **P2** |

---

## 11. Top issues P0–P2

### P0 — correctness / reproducibility

| ID | Issue | Why P0 |
| --- | --- | --- |
| **P0-1** | Keep (and finish) **nominal tests for new control-plane / checkpoint / registry / bronze async** paths (ARCH-CR2-05 residual) | Architecture program ships helpers faster than closeouts retire |
| **P0-2** | **Non-ChEMBL bronze exact-replay fixtures** for families claiming exact replay | Determinism/replay is architectural mandate; VCR alone ≠ medallion replay |
| **P0-3** | **No silent regression of domain purity / no datetime.now in domain** gates | Already enforced — treat any red as P0; do not relax |

### P1 — developer velocity / CI cost

| ID | Issue |
| --- | --- |
| **P1-1** | Collapse architecture **closeout** tests into snapshot ledger + few meta-gates (retire per-issue files after sunset) |
| **P1-2** | Reduce S7 shard fan-out (single collect + filter, or prebuilt test node ids) |
| **P1-3** | Expand `unit-parallel-safe` membership; keep VCR/integration serial |
| **P1-4** | VCR cassette budgeting / provider caps + stale recertification workflow |
| **P1-5** | Raise partial coverage floors only on **normalization/hash/identity** modules <80% |
| **P1-6** | Clarify unit vs `repo_backed` marker enforcement in CI select |

### P2 — tech debt

| ID | Issue |
| --- | --- |
| **P2-1** | Rename duplicate basenames where confusing |
| **P2-2** | Hypothesis expansion for identifier/normalization families |
| **P2-3** | Observability interaction tests for top pipelines |
| **P2-4** | Refresh fixture ledger dates / matrix flags (`cassette_metadata_backfill_workflow_present`) |
| **P2-5** | Composition unit bootstrap session fixtures audit |

---

## 12. Optimization plan

### 12.1 Removal / cleanup

| Action | Target | Rule |
| --- | --- | --- |
| Sunset closeout tests | `tests/architecture/test_*closeout*.py`, `test_tech_debt_issues_*` | Only after `architecture_closeout_inventory.yaml` sunset + snapshot artifact supersedes |
| Merge duplicate scenario tests | provider `test_request_metadata.py` family | Keep one matrix-parametrized module per concern |
| Do **not** delete VCR by age alone | `tests/fixtures/vcr` | Ledger forbids age-only pruning |
| Do **not** delete architecture purity/determinism gates | `test_domain_purity`, `test_no_datetime_now_*`, quarantine immutability | Protects hexagonal + determinism |

### 12.2 Refactoring

1. **Shared builders:** extend `tests/testing_support` / helpers for deterministic IDs, clocks, batch fixtures (already partially present).
2. **Fixture factories:** Bronze/Silver sample builders per provider from manifest, not copy-paste.
3. **Composition tests:** session-scoped lightweight fakes for ports; full bootstrap only where testing composition itself.
4. **Architecture meta-suite:** one module reading `reports/quality/*closeout.json` inventory instead of N issue-specific tests.

### 12.3 Acceleration

| Lever | How | Expected effect | Risk |
| --- | --- | --- | --- |
| Opt-in xdist | Grow `unit-parallel-safe` only | Faster unit feedback | Medium if markers wrong |
| Shard rationalization | Merge S7-a/a2/a3/d where ignore sets allow | Less collect overhead | Medium |
| Closeout off PR path | Nightly-only closeout cluster | Faster PR | Low if snapshots stay on PR |
| VCR isolation | Provider-scoped jobs; cassette cache | Parallel integration later | High if shared writes |
| Avoid global xdist | Keep `forbid_global_xdist_addopts` | Determinism | — |
| Bootstrap cache | Session fixtures for pure unit | Faster composition-adjacent unit | Low |

### 12.4 Quality improvements

| Add | Where | Why |
| --- | --- | --- |
| Golden Silver/Gold row fixtures for non-ChEMBL critical entities | `tests/fixtures/golden/{provider}` | Balance medallion vs HTTP fidelity |
| Property tests for identifier families / normalizers | unit/domain/normalization | Invariants |
| Contract tests already strong | keep drift CI | External API |
| Metric emission asserts | unit app services with MetricsPort fakes | Observability regressions |
| PipelineRun/Batch already strong | maintain exhaustive FSM | Core DDD |

### 12.5 Determinism

| Action | Detail |
| --- | --- |
| Keep freezegun / clock ports in new tests | Prefer domain/runtime clock seams |
| Ban new `datetime.now` in production tests outside policy tests | Existing arch gates |
| VCR + fixed ordering | Maintain sort contracts (ADR-014) in pipeline tests |
| Flaky triage | Use junit history (not collected here) to quarantine serial |

---

## 13. Roadmap

| Stage | Actions | Effect | Risk |
| --- | --- | --- | --- |
| **W0 (1 week)** | Inventory closeout tests → sunset candidates; tag nightly-only; document unit-parallel-safe allowlist growth | Immediate CI relief plan | Low |
| **W1 (2 weeks)** | Implement architecture closeout consolidation meta-gate; reduce S7 shard count by 2–3 | Faster architecture lane | Medium (must not drop budget protection) |
| **W2 (2–3 weeks)** | Non-ChEMBL bronze/golden promotion for top entities (activity-like, publication, protein) | Replay parity | Medium (fixture authoring cost) |
| **W3 (2 weeks)** | Partial coverage burn on modules <80% in normalization/identity/hash | Higher real quality | Low |
| **W4 (ongoing)** | VCR budget per provider; recert workflow; optional parallel integration with proven isolation | Disk/CI time | High if rushed |
| **W5** | Hypothesis + MetricsPort asserts on critical paths | Long-term robustness | Low |

---

## 14. GitHub backlog (published 2026-07-29)

Pack: `.github/ISSUES/TEST-SYS-2026-07-29-ISSUE-PACK.md`
Publish JSON: `reports/quality/test-system-audit-2026-07-29-issue-publish.json`

| Code | Pri | Issue | Title | Modules |
| --- | --- | ---: | --- | --- |
| TEST-SYS-00 | meta | [#7020](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7020) | Epic: test system cost/quality optimization | tests/**, configs/quality |
| TEST-SYS-01 | P0 | [#7022](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7022) | Non-ChEMBL bronze exact-replay fixture promotion | `tests/fixtures/bronze`, bronze_fixture_manifest |
| TEST-SYS-02 | P0 | [#7024](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7024) | Nominal unit coverage for control-plane/checkpoint/registry helpers (continue ARCH-CR2-05) | application/services/control_plane, composition/factories |
| TEST-SYS-03 | P1 | [#7025](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7025) | Architecture closeout consolidation + nightly split | `tests/architecture/*closeout*` |
| TEST-SYS-04 | P1 | [#7026](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7026) | Collapse redundant S7 architecture shards | `configs/quality/pytest_shards.yaml` |
| TEST-SYS-05 | P1 | [#7027](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7027) | Expand unit-parallel-safe + enforce repo_backed exclusion | test_matrix, markers |
| TEST-SYS-06 | P1 | [#7028](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7028) | VCR size/age budget + recert workflow flag truth | fixtures/vcr, test_matrix fixture_governance |
| TEST-SYS-07 | P1 | [#7029](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7029) | Raise floors on partial modules <80% (normalization/hash) | coverage inventory |
| TEST-SYS-08 | P2 | [#7030](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7030) | Hypothesis for identifier/normalization families | unit/domain/normalization |
| TEST-SYS-09 | P2 | [#7031](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7031) | MetricsPort/TracingPort interaction tests for top pipelines | unit/application |
| TEST-SYS-10 | P2 | [#7032](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/7032) | Basename dedup / naming hygiene | multi-provider unit trees |

---

## 15. Constraints respected

- No invented greenfield test frameworks outside pytest/xdist/hypothesis/VCR already in tree.
- No suggestion to put I/O in domain tests.
- No global xdist mandate (would fight documented determinism policy).
- Fixture deletes only via ledger evidence requirements.
- Composite/control-plane/medallion treated as first-class invariants.

---

## 16. Bottom line

| Dimension | Grade | Comment |
| --- | --- | --- |
| Architectural alignment of tests | **A** | Purity, DI, determinism gates are real |
| Module coverage completeness | **A** | 0 uncovered modules |
| Signal vs noise | **B−** | Closeout/governance mass dilutes runtime signal |
| Speed / cost | **C+** | Serial default + arch×7 + VCR 139MB |
| Fixture balance (medallion vs HTTP) | **B−** | VCR rich; bronze/golden ChEMBL-skewed |
| Critical aggregate invariants | **A** | Batch / PipelineRun / Quarantine well covered |

**Strategy:** protect determinism and hexagonal gates; **harvest speed** from architecture closeout consolidation and shard design; **harvest correctness** from non-ChEMBL bronze/golden + partial coverage on normalization/hash; treat VCR as a **budgeted asset**, not an unbounded archive.

---

*End of audit. §14 published as GitHub issues #7020–#7032 (TEST-SYS-00..10; numbers non-contiguous: #7021/#7023 unused by this pack).*
