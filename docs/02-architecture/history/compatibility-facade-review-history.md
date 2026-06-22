______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Compatibility Facade Review History

This document stores historical review narratives that were previously mixed into
the operational compatibility registry. The canonical operational policy and
curated ledgers now live in
[`../07-compatibility-facade-inventory.md`](../07-compatibility-facade-inventory.md).

## ADR-048 Alignment (2026-05-26)

Completed in this cycle:

- Promoted ADR-048 as the explicit boundary owner for domain schema contracts:
  Pandera/Pandas imports are sanctioned only inside
  `src/bioetl/domain/schemas/` and `src/bioetl/domain/contracts/`.
- Locked runtime compatibility ownership to the explicit composition seam
  `bioetl.composition.bootstrap.runtime.pipeline.apply_runtime_compatibility_patches`,
  with validation delegated to
  `bioetl.infrastructure.compat.pandera_compat.validate_supported_pandera_runtime`.
- Reworded requirements/glossary surfaces to remove ambiguity between domain
  contracts and infrastructure mapping responsibilities.

Operational implication:

- Domain schema contracts remain part of domain semantics and MUST NOT drift
  into infrastructure adapter ownership language.
- Import-time compatibility side effects in package `__init__` remain forbidden;
  runtime validation is explicit and testable at composition bootstrap only.

## Public Entrypoint Review Wave (2026-05-20)

Completed in this cycle:

- Normalized sanctioned package/domain facades in `bioetl.application.composite`,
  `bioetl.composition.bootstrap`, and the retained CLI domain packages from lazy
  `__getattr__` resolution to direct re-exports where the owner modules are
  stable and cycle-safe.
- Removed deprecated `orderer` and `priority_orderer` collaborator aliases from
  composite merge wiring; the sanctioned merge surface now passes only the
  canonical `order_service` ordering collaborator through
  `MergeCollaboratorGroup`.

Operational implication:

- Sanctioned public entrypoints remain intentionally retained, but the review
  confirmed they no longer need transitional lazy indirection on the reviewed
  package roots.
- Compatibility governance for the composite merge seam now audits only the
  canonical `order_service` collaborator path instead of carrying deprecated
  alias fields in runtime wiring.

## Reduction Wave (2026-05-05)

Completed reductions in this cycle:

- Removed `src/bioetl/composition/factories/storage/adapter.py`; canonical
  storage bundle imports now resolve through `bundle.py`.
- Removed `src/bioetl/application/composite/checkpoint/anchor_context.py`; the
  checkpoint package root is now the single sanctioned public seam.
- Moved Pandera compatibility activation out of
  `bioetl.composition.bootstrap.__getattr__` and into
  `bioetl.composition.bootstrap.runtime`, so lazy export resolution no longer
  carries import-time compatibility side effects.

Operational implication:

- The transition-debt ledger is now empty on the current baseline.
- Any future module-level compatibility shim must be explicitly reintroduced in
  the curated inventory instead of silently reappearing in source.

## Governance Reclassification Wave (2026-05-15)

Completed in this cycle:

- Stopped counting sanctioned `public-entrypoint` rows as compatibility debt in
  `configs/quality/debt_scorecard.yaml`.
- Rebased the compatibility debt KPI onto the real transition ledger
  (`transition_compat_count`), which is currently `0`.
- Added a separate sanctioned-public-entrypoint governance metric so stable
  public API seams remain visible without inflating technical-debt reporting.

Operational implication:

- Compatibility debt now measures only transition/sunset residue.
- Stable public CLI/composition/domain entrypoints remain governed through the
  curated inventory and review metadata, but they no longer appear as active
  compatibility debt unless they regress into transition-only shims again.

## Provider Client-Path Shim Removal (2026-05-05)

Removal outcome:

- `src/bioetl/infrastructure/adapters/pubmed/client.py`: `remove`
- `src/bioetl/infrastructure/adapters/semanticscholar/client.py`: `remove`

Rationale:

- Provider package roots already expose the canonical adapter surfaces.
- Dedicated architecture tests now assert that the removed client-path shim
  files and import paths do not reappear.
- `bioetl.infrastructure.adapters.pubmed.pubmed_client` remains a legacy
  implementation path confined to compatibility coverage.

## RF-035 Retained Entrypoint Decision

Historical decision for this cycle:

- `src/bioetl/infrastructure/adapters/pubmed/client.py`: `retain`
- `src/bioetl/infrastructure/adapters/semanticscholar/client.py`: `retain`

Superseded by the 2026-05-05 removal decision above.

Measured evidence for `retain`:

- PubMed canonical entrypoint is still part of active first-party code:
  - `src/bioetl/infrastructure/adapters/pubmed/__init__.py`
  - `src/bioetl/composition/providers/registration_biblio.py`
- Semantic Scholar canonical entrypoint is still part of active first-party code:
  - `src/bioetl/infrastructure/adapters/semanticscholar/__init__.py`
- Legacy implementation-module references in `src/` are already effectively zero outside the retained entrypoints themselves:
  - `bioetl.infrastructure.adapters.pubmed.pubmed_client` appears only inside
    `src/bioetl/infrastructure/adapters/pubmed/client.py`
  - `bioetl.infrastructure.adapters.semanticscholar.adapter` appears only inside
    `src/bioetl/infrastructure/adapters/semanticscholar/client.py`
- Test-only legacy references remain intentional and limited to compatibility coverage:
  - `tests/unit/infrastructure/adapters/test_provider_entrypoints.py`
  - `tests/architecture/test_adapter_contracts.py`

Policy implications:

- Do not start deprecation for these entrypoints in the current cycle.
- New first-party code should use provider package roots; retained `client.py`
  entrypoints exist for stability and dedicated compatibility coverage only.
- New first-party code must not import the older implementation modules
  `pubmed.pubmed_client` or `semanticscholar.adapter` directly.
- Any future deprecation proposal must include a fresh usage inventory and an explicit review
  of the retained public `create_pubmed_adapter` factory surface.

## Retained Entrypoint Review Wave (2026-03-15)

Review outcome for the remaining curated inventory rows:

- `src/bioetl/composition/entrypoints.py`: `retain`
  because active first-party interface code still uses it as the public seam while
  `_pipeline_execution`, `_resource_management`, and `_services` remain confined to
  `composition/` and dedicated entrypoint tests.
- `src/bioetl/domain/composite/config.py`: `retain`
  because application, composition, infrastructure, and tests depend on the root config
  entrypoint while split `config_*` internals remain confined to `domain/composite/`
  and the dedicated facade test.
- `src/bioetl/domain/value_objects/activity_values.py`: `removed`
  on 2026-06-16 after importer census showed no first-party source importers; activity
  value-object symbols remain available through `bioetl.domain.value_objects`.
- `src/bioetl/domain/value_objects/publication_field_groups.py`: `retain`
  because public field-group types are consumed through the root entrypoint while
  private `_publication_field_group_*` modules remain internal.
- `src/bioetl/infrastructure/adapters/pubmed/client.py`: `retain`
  superseded by the 2026-05-05 removal decision.
- `src/bioetl/infrastructure/adapters/semanticscholar/client.py`: `retain`
  superseded by the 2026-05-05 removal decision.

Wave decision:

- The `RunExecutionContext` compatibility export was retired early on `2026-05-08`
  with explicit maintainer approval after first-party callers were eliminated.
- Next action is absence enforcement through architecture tests, not a deferred
  `2026-09-30` re-review.
