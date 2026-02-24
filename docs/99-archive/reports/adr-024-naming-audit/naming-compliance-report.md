# Entity Naming Compliance Report

Date: 2026-02-24
Scope: `src/bioetl`, `configs`, architecture and terminology checks for ADR-024 + 5-layer boundaries

## Executive Summary

- Overall status: **Mostly compliant**.
- ADR-024 canonical entities are present: `ChemblPublication`, `PubchemMolecule`, `UniprotTarget`.
- No direct deprecated class aliases (`class Document`, `class Compound`, `class Protein`) were found.
- 5-layer architecture boundary checks are effectively green in architecture suite; one unrelated formatting failure exists in tests.
- Terminology lint script currently fails due to a runtime API mismatch and requires fix before it can be used as a gate.

## Compliance Scorecard

| Area                                                              | Status     | Evidence                                                                                   |
| ----------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------ |
| ADR-024 canonical class names                                     | ✅ Pass    | Canonical classes defined in domain entities.                                              |
| Deprecated class aliases                                          | ✅ Pass    | No deprecated class declarations found.                                                    |
| Known ChEMBL derived exceptions                                   | ✅ Pass    | `DocumentTerm` and `DocumentSimilarity` intentionally present.                             |
| Pipeline naming migration (`chembl_publication`)                  | ✅ Pass    | `configs/pipelines/chembl/publication.yaml` present; no `chembl_document` pipelines found. |
| CLI/API naming exceptions (`pubchem_compound`, `uniprot_protein`) | ✅ Pass    | Present in pipeline configs as allowed exceptions.                                         |
| Architecture boundaries                                           | ⚠️ Partial | Architecture suite: 1359 passed, 21 skipped, 1 failed (formatting-only).                   |
| `import_linter` contract check                                    | ⚠️ Blocked | `import_linter` module unavailable in environment.                                         |
| Terminology linter                                                | ❌ Fail    | `scripts/lint_terminology.py` crashes (`PYTHON_PATTERNS` attribute missing).               |

## Detailed Findings

## [P2 - Moderate] Terminology lint entrypoint is broken

**Location**: `scripts/lint_terminology.py:61`
**Rule**: Terminology audit command MUST be runnable for automated naming compliance.

**Evidence**:

```text
AttributeError: module 'tools.scripts.lint_terminology' has no attribute 'PYTHON_PATTERNS'
```

**Impact**: Naming terminology checks cannot currently be used as a CI-quality gate; manual grep/rg checks are required.

**Recommendation**:

- Align `scripts/lint_terminology.py` with exported API from `tools.scripts.lint_terminology`.
- Add a smoke test covering both normal and `--strict` execution.

**Verification command**: `uv run python scripts/lint_terminology.py src/bioetl/ --strict`

## [P3 - Informational] Backward-compatibility alias status differs from expected migration note

**Location**: `src/bioetl/domain/entities/__init__.py`
**Rule**: Migration notes should match real code behavior.

**Evidence**:

- Canonical exports are present (`ChemblPublication`, `PubchemMolecule`, `UniprotTarget`).
- Deprecated aliases (`Document`, `Compound`, `Protein`) are not exported.

**Impact**: Documentation/process notes may imply alias availability while codebase is already on direct canonical naming.

**Recommendation**:

- Keep docs/exception registry aligned with current codebase behavior.

**Verification command**: `rg -n "Document|Compound|Protein" src/bioetl/domain/entities/__init__.py`

## Positive Observations

- `ChemblPublication` is implemented as canonical ChEMBL publication domain entity.
- `PubchemMolecule` and `UniprotTarget` canonical entities are implemented in domain layer.
- Derived ChEMBL technical entities (`DocumentTerm`, `DocumentSimilarity`) remain explicit and justified.
- Config migration to `chembl_publication` pipeline naming is in place.

## Migration Progress (ADR-024)

- Canonical class migration: **100% complete** for targeted entities.
- Deprecated alias class declarations: **0 remaining**.
- No additional migration actions required for class names.

## Verification Log

1. Deprecated/canonical entity scans in source tree.
1. Architecture suite execution (`tests/architecture`).
1. Import boundary CLI check (`import_linter`) — environment package missing.
1. Terminology linter execution (`normal` and `--strict`) — runtime failure.
1. Config naming scans (`chembl_document`, `chembl_publication`, `pubchem_compound`).
