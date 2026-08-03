# Semantic Audit 2026-05-15 Issue Pack

This file reconciles the user-provided 2026-05-15 semantic ETL audit summary
with the current repository state on `main` and maps only confirmed residuals
to publish-ready GitHub issue drafts already stored under `.github/ISSUES/`.

## Decision Summary

| # | Audit theme | Current repo actuality | Action | Draft / issue source |
|---|---|---|---|---|
| 1 | Publication taxonomy / `publication_class` drift | Confirmed residual governance work | Publish / track | `NONCHEMBL-010-Enforce-Shared-Publication-Taxonomy-Parity-Across-Profile-DQ-And-Gold.md` |
| 2 | UniProt accession / `component_accessions` partial semantics and DQ asymmetry | Confirmed residual governance work | Publish / track | `NONCHEMBL-012-Align-UniProt-Reference-Array-DQ-With-Profile-Owned-Canonicalization.md` |
| 3 | Composite join and lineage drift around identifiers | Confirmed residual guardrail work | Publish / track | `NONCHEMBL-003-Harden-Composite-Boundaries-Against-Non-Chembl-Normalization-Drift.md` |
| 4 | Publication identifier edge coverage and provider vocabulary confidence | Confirmed residual test coverage work | Publish / track | `NONCHEMBL-013-Expand-Publication-Identifier-And-Vocabulary-Edge-Fixture-Inventory.md` |
| 5 | DOI normalization mismatch across publication providers | Not confirmed on current `main` | stale_not_reproduced | Covered by current normalization/tests |
| 6 | PubChem `molecule_id` int/string canonicalization gap | Already fixed on current `main` | stale_not_reproduced | Historical follow-up already superseded |
| 7 | CrossRef structured publication payload fidelity gap | Confirmed, but outside the user summary's top risks | Optional follow-up | `NONCHEMBL-011-Add-Raw-Sidecars-For-CrossRef-Structured-Publication-Payloads.md` |
| 8 | Date-format incompatibility across publication family | Not confirmed as an active root-cause issue | Do not create new issue | Current shared date normalization already present |

## Publish-Ready Set

### 1. Publication taxonomy parity across providers

- Draft: `NONCHEMBL-010-Enforce-Shared-Publication-Taxonomy-Parity-Across-Profile-DQ-And-Gold.md`
- Why it stays in scope:
  - The shared derived taxonomy fields `publication_type_unified`,
    `publication_subclass`, and `publication_class` are central to the audit
    summary and remain the strongest publication-family governance seam.
  - The residual issue is not DOI canonicalization; it is cross-layer parity
    for the derived shared taxonomy.
- Evidence:
  - `src/bioetl/domain/contracts/gold/_publication_common_schema.py`
  - `src/bioetl/application/pipelines/common/base_publication_transformer.py`
  - `configs/entities/crossref/publication.yaml`
  - `configs/entities/openalex/publication.yaml`
  - `configs/entities/pubmed/publication.yaml`
  - `configs/entities/semanticscholar/publication.yaml`
  - `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`

### 2. UniProt reference-array and partial-identity governance

- Draft: `NONCHEMBL-012-Align-UniProt-Reference-Array-DQ-With-Profile-Owned-Canonicalization.md`
- Why it stays in scope:
  - The user audit correctly identifies a high-risk partial semantic boundary
    between UniProt primary identifiers and composite target component/accession
    surfaces.
  - The confirmed residual is DQ/profile parity for normalized identifier and
    array fields, not absence of normalization.
- Evidence:
  - `src/bioetl/domain/normalization/profiles/uniprot_idmapping.py`
  - `src/bioetl/domain/normalization/profiles/uniprot_protein.py`
  - `configs/entities/uniprot/idmapping.yaml`
  - `configs/entities/uniprot/protein.yaml`
  - `configs/composites/target.yaml`
  - `tests/contract/test_non_chembl_cross_layer_contract_matrix.py`

### 3. Composite identifier boundary drift

- Draft: `NONCHEMBL-003-Harden-Composite-Boundaries-Against-Non-Chembl-Normalization-Drift.md`
- Why it stays in scope:
  - The user audit highlights join-role sensitivity for identifiers. Current
    repo state confirms that the remaining risk is boundary regression, not
    missing normalization seams.
  - This issue covers publication, molecule, and target composite join anchors.
- Evidence:
  - `configs/composites/publication.yaml`
  - `configs/composites/molecule.yaml`
  - `configs/composites/target.yaml`
  - `src/bioetl/domain/normalization/join_keys.py`
  - `tests/unit/application/composite/`

### 4. Publication identifier and vocabulary edge coverage

- Draft: `NONCHEMBL-013-Expand-Publication-Identifier-And-Vocabulary-Edge-Fixture-Inventory.md`
- Why it stays in scope:
  - The user audit identifies residual uncertainty around publication-family
    identifier and vocabulary breadth. Current `main` still has the core policy
    in place, but fixture depth remains intentionally limited.
  - This is the right issue to raise confidence without inventing a false DOI
    normalization bug.
- Evidence:
  - `tests/fixtures/normalization/non_chembl_observed_values.yaml`
  - `tests/fixtures/normalization/non_chembl_identifier_cases.yaml`
  - `tests/fixtures/bronze/crossref/publication/`
  - `tests/fixtures/bronze/openalex/publication/`
  - `tests/fixtures/bronze/pubmed/publication/`
  - `tests/fixtures/bronze/semanticscholar/publication/`
  - `tests/integration/normalization/test_non_chembl_edge_observed_values.py`
  - `tests/integration/test_cross_provider_doi_normalization.py`

## Claims Rejected For New Issue Creation

### DOI normalization mismatch

Do not create a new DOI-normalization issue from this audit snapshot.

Current repo evidence shows the opposite:

- `tests/integration/test_cross_provider_doi_normalization.py` asserts that the
  same DOI normalizes identically across CrossRef, PubMed, OpenAlex, and
  Semantic Scholar.
- Publication configs on current `main` enforce the same DOI regex surface:
  - `configs/entities/crossref/publication.yaml`
  - `configs/entities/openalex/publication.yaml`
  - `configs/entities/pubmed/publication.yaml`
  - `configs/entities/semanticscholar/publication.yaml`
- Publication profiles already use shared DOI field families:
  - `src/bioetl/domain/normalization/profiles/crossref_publication.py`
  - `src/bioetl/domain/normalization/profiles/pubmed_publication.py`
  - `src/bioetl/domain/normalization/profiles/openalex_publication.py`
  - `src/bioetl/domain/normalization/profiles/semanticscholar_publication.py`

### PubChem `molecule_id` int/string gap

Do not create a new PubChem identifier-normalization issue from this snapshot.

Current repo evidence shows the dedicated canonicalizer is already active:

- `src/bioetl/domain/normalization/profiles/pubchem_compound.py`
  uses `normalize_profile_pubchem_cid` for `molecule_id`.
- `tests/integration/test_pubchem_pipeline.py` already asserts canonical string
  output for numeric molecule identifiers.

### Date-format incompatibility

Do not create a new date-format issue without a fresh failing artifact.

Current repo evidence shows publication-family date fields are already governed
through shared date normalization surfaces and canonical field registry notes:

- `src/bioetl/domain/normalization/profiles/crossref_publication.py`
- `src/bioetl/domain/normalization/profiles/pubmed_publication.py`
- `configs/field_registry/canonical_registry.json`

## Historical Notes

- Memory artifacts record that semantic follow-up GitHub issues were already
  created on 2026-05-15 (`#4116-#4123` and `#4124-#4133`), but that GitHub
  state was not revalidated in this shell because `gh` is unavailable here.
- This pack therefore serves as the current-repo publish map and anti-duplication
  reference, not as proof of present open/closed issue state on GitHub.
