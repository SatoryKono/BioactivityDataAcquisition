# Architecture Audit Report

Date: 2026-02-11
Scope: `configs/**`, `src/bioetl/infrastructure/config/**`, `src/bioetl/infrastructure/config_loader.py`, architecture tests related to config/layers.

## Executive Summary

- Total findings: 3
- Critical (MUST): 1
- Moderate (SHOULD): 2
- Informational (MAY): 0

## Critical Findings

## [MUST] Broken `data_schema_file` reference in ChEMBL subcellular_fraction pipeline

**Location**: `configs/pipelines/chembl/subcellular_fraction.yaml:45`

**Rule Violated**: Configuration integrity invariant (pipeline file references must resolve to existing files for deterministic schema loading).

**Evidence**:

```yaml
data_schema_file: ../../data_schema/chembl/subcellular_fraction.yaml
```

The referenced file is absent in repository tree (`configs/data_schema/chembl/subcellular_fraction.yaml` does not exist).

**Impact**:

- Layer-specific schema (`silver`/`gold`) and column groups for this pipeline are not loaded.
- Loader silently degrades to `None`, so the pipeline may run with default/implicit schema instead of intended explicit schema.
- Raises risk of undetected schema drift and inconsistent Silver/Gold outputs.

**Recommendation**:

1. Add missing schema file `configs/data_schema/chembl/subcellular_fraction.yaml` with explicit `silver` and `gold` sections.
1. Add architecture test that validates all explicit `data_schema_file` references resolve.
1. Optionally fail-fast in loader when explicit `data_schema_file` is set but missing.

**Verification**:

```bash
python - <<'PY'
from pathlib import Path
import yaml
missing=[]
for f in Path('configs/pipelines').glob('*/*.yaml'):
    if f.name.startswith('_'): continue
    d=yaml.safe_load(f.read_text()) or {}
    if d.get('data_schema_file'):
        p=(f.parent/d['data_schema_file']).resolve()
        if not p.exists():
            missing.append((str(f),d['data_schema_file']))
print(missing)
PY
```

## Moderate Findings

## [SHOULD] Silent fallback for missing explicit config files masks misconfiguration

**Location**:

- `src/bioetl/infrastructure/config_loader.py:128-131` (`data_schema_file`)
- `src/bioetl/infrastructure/config_loader.py:242-244` (`filter_config_file`)

**Rule Violated**: Fail-fast principle for explicit configuration references (deviation from robust config validation expectations).

**Evidence**:

```python
schema_path = config_path.parent / data_schema_file
if not schema_path.exists():
    return None
```

```python
filter_path = config_path.parent / filter_config_file
if not filter_path.exists():
    return None
```

**Impact**:

- Typos and stale paths are downgraded to implicit defaults.
- Runtime behavior can diverge from pipeline author intent without any warning/error.

**Recommendation**:

- When a reference is explicitly present in pipeline YAML, raise `FileNotFoundError` (or emit warning + strict mode flag).
- Keep current permissive behavior only for convention-derived defaults.

**Verification**:

```bash
nl -ba src/bioetl/infrastructure/config_loader.py | sed -n '112,150p'
nl -ba src/bioetl/infrastructure/config_loader.py | sed -n '230,248p'
```

## [SHOULD] Config inventory drift between pipeline, DQ, filter, and schema trees

**Location**: `configs/` hierarchy (`pipelines/`, `dq/entities/`, `filter/entities/`, `data_schema/`).

**Rule Violated**: Consistency recommendation for externalized config structure (ADR-027/028/029 lifecycle hygiene).

**Evidence** (inventory diff script):

- DQ entity configs missing for composite pipelines: `composite/{activity,assay,molecule,publication,target}`.
- Extra DQ entity config without matching pipeline: `uniprot/target`.
- Filter entity config missing for an active pipeline: `chembl/tissue`.
- Data schema missing for active pipelines: `chembl/subcellular_fraction`, `composite/activity`, `composite/target`.

**Impact**:

- Harder operability and reviewability of pipeline behavior.
- Increased chance of accidental fallback to defaults for entities expected to be explicitly governed.

**Recommendation**:

- Add CI check comparing `(provider, entity)` sets across config trees.
- For intentional exceptions, maintain allowlist (e.g., example files or staged entities).
- Create missing filter/schema files or remove stale references.

**Verification**:

```bash
python - <<'PY'
from pathlib import Path
root=Path('configs')
pairs={(p.parent.name,p.stem) for p in (root/'pipelines').glob('*/*.yaml') if not p.name.startswith('_')}
for name,sub in [('dq_entities',root/'dq'/'entities'),('filter_entities',root/'filter'/'entities'),('data_schema',root/'data_schema')]:
    sp={(p.parent.name,p.stem) for p in sub.glob('*/*.yaml')}
    print(name,'missing',sorted(pairs-sp)[:10],'extra',sorted(sp-pairs)[:10])
PY
```

## Positive Observations

- Layer dependency and domain purity architecture tests passed on selected suite.
- Config synchronization tests for docs and source usage passed.
- DQ/filter externalization structure follows ADR-027/028 hierarchy (`_defaults` → `providers` → `entities` → inline overrides).

## Verification Log

- `pytest -q tests/architecture/test_config_golden_master.py tests/architecture/test_source_config_usage.py tests/architecture/test_docs_version_sync.py tests/architecture/test_documentation_sync.py`
- `pytest -q tests/architecture/test_layer_dependencies.py tests/architecture/test_forbidden_imports.py tests/architecture/test_domain_purity.py tests/architecture/test_medallion_invariants.py tests/architecture/test_naming_conventions.py`
- `python - <<'PY' ...` (config reference existence check)
- `python - <<'PY' ...` (cross-tree config inventory drift check)
