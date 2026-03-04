# Architecture Debt Baseline (Phase A Freeze)

- Phase window: 2026-03-04 to 2026-03-07
- Snapshot date: 2026-03-04
- Scope: `src/bioetl`, quality exemption registry, architecture+docs quality gates
- Status: Baseline refreshed, awaiting owner sign-off

## Objective

Fix a reproducible zero point for architecture debt and quality gates, so follow-up refactoring is measured against stable numbers instead of ad-hoc checks.

## Registry Governance Status

Registry under governance:
- `configs/quality/architecture_metric_exemptions.yaml`

Validation checks:
- Required metadata per entry: `value`, `owner`, `reason`, `expires_on`, `removal_step`
- Validation command: `./.venv/Scripts/python.exe scripts/check_quality_exemptions.py --mode warn`

Snapshot results (2026-03-04):
- Registry buckets: `7`
- Registry entries: `485`
- Metadata errors: `0`
- Expired entries: `0`

Conclusion:
- Registry is valid and remains the canonical architecture-debt source of truth.

## Baseline Metrics (Zero Point)

### 1) LOC of large modules (top)

| Module | LOC |
|---|---:|
| `src/bioetl/domain/mapping/generated/publication_type_classification_data.py` | 2158 |
| `src/bioetl/domain/composite/config.py` | 1152 |
| `src/bioetl/domain/contracts/gold/chembl.py` | 833 |
| `src/bioetl/domain/models/metadata.py` | 831 |
| `src/bioetl/composition/factories/pipeline_factory.py` | 789 |
| `src/bioetl/infrastructure/quality/debt_scorecard.py` | 739 |
| `src/bioetl/composition/factories/storage_adapter.py` | 734 |
| `src/bioetl/composition/providers/registration.py` | 710 |
| `src/bioetl/composition/factories/services_factory.py` | 703 |
| `src/bioetl/composition/bootstrap/runtime/composite.py` | 703 |

### 2) CC hotspots (max cyclomatic complexity)

| Function | CC |
|---|---:|
| `metadata_coordinator.create_silver_metadata` | 23 |
| `extract_isoform_details` (UniProt comments extractor) | 20 |
| `OpenAlexAdapter.fetch_filtered_with_fallback` | 19 |
| `SilverWriterArrowMixin._prepare_arrow_data` | 17 |
| `CrossRefAdapter.fetch_filtered_with_fallback` | 17 |
| `metadata_coordinator.create_gold_metadata` | 17 |
| `SilverDQAnalyzer._check_value_distribution` | 17 |
| `DependencyCoordinator._get_effective_keys` | 17 |
| `debt_scorecard._validate_grace_windows_section` | 16 |
| `config_loader._validate_schema_config` | 16 |

### 3) `Any` usage in `src/bioetl`

- `Any` in annotations (`: Any` / `-> Any`): `374`
- Total `Any` token occurrences: `1826`

### 4) Broad catches in `src/bioetl`

- `except Exception`: `4`
- `except BaseException`: `1`
- Bare `except:`: `0`

Layer split (`except Exception`):
- `domain`: 0
- `application`: 0
- `infrastructure`: 0
- `composition`: 0
- `interfaces`: 4

## Quality Gate Alignment (Phase A)

### Blocking gates

| Gate | Command | Status (2026-03-04) |
|---|---|---|
| Debt registry validity | `./.venv/Scripts/python.exe scripts/check_quality_exemptions.py --mode warn` | PASS |
| Debt scorecard consistency | `./.venv/Scripts/python.exe -m pytest tests/architecture/test_quality_debt_scorecard.py -q -p no:xdist --tb=short` | PASS |
| Docs architecture sync | `./.venv/Scripts/python.exe -m pytest tests/architecture/test_documentation_sync.py tests/architecture/test_docs_version_sync.py tests/architecture/test_docs_kpi_workflow.py -q -p no:xdist --tb=short` | PASS |
| Docs link/spec/config validity | `./.venv/Scripts/python.exe scripts/check_doc_links.py` | PASS |

### Non-blocking / observational gates

| Gate | Reason |
|---|---|
| `tests/performance/test_hotspot_budgets.py -m benchmark` | Benchmark-heavy scenario shows timeout instability on current environment; tracked separately to avoid baseline distortion. |

Policy decision:
- Only reproducible gates above are used for Phase A freeze and sign-off.
- Benchmark-heavy suites remain outside Phase A blocking criteria.

## Control Commands Used

```bash
./.venv/Scripts/python.exe scripts/check_quality_exemptions.py --mode warn
./.venv/Scripts/python.exe -m pytest tests/architecture/test_quality_debt_scorecard.py tests/architecture/test_documentation_sync.py tests/architecture/test_docs_version_sync.py tests/architecture/test_docs_kpi_workflow.py -q -p no:xdist --tb=short
./.venv/Scripts/python.exe scripts/check_doc_links.py
rg -n ': Any|-> Any' src/bioetl -g '*.py'
rg -n '\bAny\b' src/bioetl -g '*.py'
rg -n 'except\s+Exception\b' src/bioetl -g '*.py'
rg -n 'except\s+BaseException\b' src/bioetl -g '*.py'
find src/bioetl -type f -name '*.py' -exec wc -l {} + | sed '$d' | sort -nr | head -n 12
./.venv/Scripts/python.exe - <<'PY'\nfrom pathlib import Path\nfrom radon.complexity import cc_visit\n...\nPY
```

## Sign-off

- Architecture owner: `@bioetl-architecture` — pending
- Platform owner: `@bioetl-platform` — pending
- Sign-off requested on: `2026-03-04`

Sign-off criteria:
1. Registry stays metadata-valid and non-expired in `warn` mode.
2. Blocking gates listed above stay green.
3. Baseline metrics are accepted as reference for RF roadmap tracking.

## Phase A Exit Criteria Mapping (target: 2026-03-07)

- [x] Baseline metrics refreshed and archived in `docs/reports`.
- [x] Registry confirmed as canonical debt source.
- [x] Blocking vs non-blocking gate scope explicitly fixed.
- [ ] Owner approvals recorded in this report.
