# Architecture Audit Report

Date: 2026-02-24
Scope: Entity naming compliance (ADR-024 + glossary v2.0), deprecated-term drift, and 5-layer architecture boundary checks for `src/bioetl`, `configs`, and `tests/architecture`.

## Executive Summary

- Total findings: 3
- Critical (MUST): 0
- Moderate (SHOULD / tooling blockers): 3
- Informational: 3
- ADR-024 migration status: **100% complete** for canonical provider-prefixed domain entities.

## Moderate Findings

## [P2] Terminology linter entrypoint is broken

**Location**: `scripts/lint-terminology.py:61`
**Rule**: RULES.md §2 naming governance / mandatory terminology verification workflow.

**Evidence**:

```python
patterns = list(impl.PYTHON-PATTERNS)
```

Runtime error observed:

```text
AttributeError: module 'tools.scripts.lint-terminology' has no attribute 'PYTHON-PATTERNS'
```

**Impact**:

- Automated terminology validation cannot run in both normal and `--strict` modes.
- Requires manual grep-based fallback; increases false-negative risk.

**Recommendation**:

- Align wrapper expectations with `tools.scripts.lint-terminology` public API.
- Add a smoke test for the script entrypoint.

**Verification command**: `uv run python scripts/lint-terminology.py src/bioetl/ --strict`

----------------------------------------------------------------------

## [P2] `import-linter` check cannot execute in current environment

**Location**: environment dependency (missing module)
**Rule**: 5-layer architecture boundary verification phase.

**Evidence**:

```text
/workspace/BioactivityDataAcquisition/.venv/bin/python3: No module named import-linter
```

**Impact**:

- Import contract check from Phase 2 is skipped.
- Confidence relies on architecture tests only.

**Recommendation**:

- Add `import-linter` to project dev dependencies and CI architecture target.

**Verification command**: `uv run python -m import-linter`

----------------------------------------------------------------------

## [P2] Architecture suite fails due test formatting drift

**Location**: `tests/architecture/test-ci-test-strategy.py`
**Rule**: formatting compliance gate in architecture suite.

**Evidence**:

```text
Would reformat: tests/architecture/test-ci-test-strategy.py
1 file would be reformatted
```

**Impact**:

- `tests/architecture/` does not pass cleanly despite 1359 passing tests.
- Architecture gate reported as failed in CI-like execution.

**Recommendation**:

- Run `ruff format tests/architecture/test-ci-test-strategy.py` and re-run architecture suite.

**Verification command**: `uv run python -m pytest tests/architecture/ -v`

## Informational Findings

### [P3] ADR-024 canonical provider-prefixed entities are present

- `ChemblPublication` declared in domain entity module.
- `PubchemMolecule` declared in domain entity module.
- `UniprotTarget` declared in domain entity module.

### [P3] Deprecated alias classes are absent

- No direct class declarations `class Document`, `class Compound`, or `class Protein` were found in `src/bioetl`.

### [P3] Known exceptions remain explicitly intentional

- `DocumentSimilarity` and `DocumentTerm` kept as ChEMBL derived entities.
- CLI pipeline IDs `pubchem-compound` and `uniprot-protein` remain for compatibility.

## Positive Observations

- `scripts/naming-audit.py` reports **0 naming violations**.
- Config names include canonical `chembl-publication` pipeline and related derivative pipelines.
- Architecture tests show broad boundary compliance (high pass volume).

## Migration Progress (ADR-024)

- Canonical class migration (`ChemblPublication`, `PubchemMolecule`, `UniprotTarget`): **Complete**.
- Deprecated class aliases (`Document`, `Compound`, `Protein`): **Not present as active class definitions**.
- Exception handling: registered in `configs/naming-exceptions.yaml` (derived entities, CLI pipeline IDs, legacy fields).

## Verification Log

1. `grep -rn "class Document[^TS]" src/bioetl/ --include="*.py" | grep -v "Deprecated"`
1. `grep -rn "class Compound[^R]" src/bioetl/ --include="*.py" | grep -v "Deprecated"`
1. `grep -rn "class Protein[^C]" src/bioetl/ --include="*.py" | grep -v "Deprecated"`
1. `rg -n "^class Document\\b|^class Compound\\b|^class Protein\\b" src/bioetl -g '*.py'`
1. `grep -rn "class ChemblPublication" src/bioetl/ --include="*.py"`
1. `grep -rn "class PubchemMolecule" src/bioetl/ --include="*.py"`
1. `grep -rn "class UniprotTarget" src/bioetl/ --include="*.py"`
1. `uv run python -m pytest tests/architecture/ -v`
1. `uv run python -m import-linter`
1. `uv run python scripts/lint-terminology.py src/bioetl/`
1. `uv run python scripts/lint-terminology.py src/bioetl/ --strict`
1. `grep -rn "chembl-document[^-]" configs/`
1. `grep -rn "pubchem-compound" configs/`
1. `grep -rn "chembl-publication" configs/`
1. `uv run python scripts/naming-audit.py`
