# Architecture Debt Baseline (Phase 1)

- Phase window: 2026-03-03 to 2026-03-07
- Snapshot date: 2026-03-03
- Scope: `src/bioetl`, quality exemption registry, architecture quality gates
- Status: Baseline fixed, pending owner sign-off

## Objective

Formalize technical debt as a managed registry (single source of truth), not as ad-hoc embedded lists in tests, and freeze a measurable baseline for remediation tracking.

## Registry Governance Status

Registry under governance:
- `configs/quality/architecture_metric_exemptions.yaml`

Validation checks:
- Required metadata per entry: `value`, `owner`, `reason`, `expires_on`, `removal_step`
- Validation command: `./.venv/Scripts/python.exe scripts/check_quality_exemptions.py --mode warn`

Snapshot results (2026-03-03):
- Registry sections: `7`
- Registry entries: `464`
- Metadata errors: `0`
- Expired entries: `0`

Conclusion:
- Registry is structurally valid and can be treated as the canonical debt register for architecture metric exemptions.

## Baseline Metrics (Zero Point)

### 1) LOC of large modules (top)

| Module | LOC |
|---|---:|
| `src/bioetl/domain/mapping/publication_type_classification.py` | 1650 |
| `src/bioetl/infrastructure/storage/silver_writer.py` | 1233 |
| `src/bioetl/domain/composite/config.py` | 1152 |
| `src/bioetl/application/composite/runner.py` | 1143 |
| `src/bioetl/infrastructure/schemas/silver.py` | 1072 |
| `src/bioetl/infrastructure/adapters/chembl/client.py` | 1053 |
| `src/bioetl/composition/factories/pipeline_factory.py` | 986 |
| `src/bioetl/infrastructure/schemas/composite_config.py` | 982 |
| `src/bioetl/infrastructure/storage/gold_writer.py` | 966 |
| `src/bioetl/application/composite/merger.py` | 953 |

### 2) CC hotspots (max cyclomatic complexity)

| Function | CC |
|---|---:|
| `MetadataCoordinator.create_silver_metadata` | 23 |
| `ChemblAdapter._fetch_batch_with_reduction` | 20 |
| `extract_isoform_details` (UniProt comments extractor) | 20 |
| `OpenAlexAdapter.fetch_filtered_with_fallback` | 19 |
| `SilverWriter._prepare_arrow_data` | 17 |
| `CrossRefAdapter.fetch_filtered_with_fallback` | 17 |
| `MetadataCoordinator.create_gold_metadata` | 17 |
| `SilverDQAnalyzer._check_value_distribution` | 17 |
| `DependencyCoordinator._get_effective_keys` | 17 |
| `config_loader._validate_schema_config` | 16 |

### 3) `Any` usage in `src/bioetl`

- `Any` in annotations (`: Any` / `-> Any`): `332`
- Total `Any` token occurrences: `1487`

### 4) Broad catches in `src/bioetl`

- `except Exception`: `119`
- `except BaseException`: `0`
- Bare `except:`: `0`

Layer split (`except Exception`):
- `domain`: 0
- `application`: 51
- `infrastructure`: 57
- `composition`: 2
- `interfaces`: 8

## Control Commands Used

```bash
./.venv/Scripts/python.exe scripts/check_quality_exemptions.py --mode warn
rg -n ': Any|-> Any' src/bioetl -g '*.py'
rg -n '\bAny\b' src/bioetl -g '*.py'
rg -n 'except\s+Exception\b' src/bioetl -g '*.py'
find src/bioetl -type f -name '*.py' -print0 | xargs -0 wc -l | sort -nr | head -n 15
./.venv/Scripts/python.exe -c "from radon.complexity import cc_visit; ..."
```

## Sign-off

- Architecture owner: `@bioetl-architecture` — pending
- Platform owner: `@bioetl-platform` — pending

Sign-off criteria:
1. Registry remains metadata-valid and non-expired in gate mode `warn` during Phase 1.
2. Baseline numbers above are accepted as reference for RF roadmap tracking.
3. All new exemptions added after this date must include owner/reason/expires_on/removal_step.

## Phase 1 Exit Criteria Mapping (2026-03-07)

- [x] Registry established and validated as canonical source.
- [x] Zero-point metrics collected (LOC/CC/Any/broad catches/registry size).
- [ ] Owner approvals recorded in this report.
