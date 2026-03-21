# Compatibility Registry Refactor Plan

*Status: active execution plan (status refreshed to current repo state)*
*Date: 2026-03-21*

## Basis

- [Compatibility Registry Refactor Summary](../reports/evidence/compatibility-registry-refactor/SUMMARY.md)
- [Compatibility Registry Refactor Cross-Synthesis](../reports/evidence/compatibility-registry-refactor/03-synthesis/CROSS-SYNTHESIS-compatibility-registry-refactor.md)
- [Compatibility Registry Refactor Decision Summary](../reports/evidence/compatibility-registry-refactor/04-decisions/SUMMARY.md)

## Goal

Make the compatibility facade registry less fragile by moving curated registry data to one machine-readable source of truth, while keeping markdown as the human-readable governance layer and generated snapshot sections as downstream artifacts.

Target outcomes:

1. one machine-readable SSOT for curated compatibility rows
2. markdown inventory remains the canonical guide/governance page
3. measured snapshot sections stop being hand-maintained
4. architecture tests and CI helpers stop acting like second hidden registries
5. future compatibility modules follow an explicit measured-only vs curated promotion rule

## Current State Refresh

The repository has already completed a meaningful part of the originally proposed migration:

- `configs/quality/compatibility_facade_inventory.yaml` already exists and acts as the structured compatibility ledger
- `scripts/ci/_compatibility_registry.py` already loads the YAML and exposes the shared registry contract
- `scripts/qa/generate_compatibility_facade_snapshot.py` already provides `--check` / `--update` snapshot tooling
- `docs/02-architecture/07-compatibility-facade-snapshot.md` already serves as the generated measured snapshot companion
- `tests/architecture/test_compatibility_facade_inventory.py` already validates YAML shape plus markdown-table sync
- `scripts/ci/_compatibility_telemetry.py` and `tests/architecture/test_compatibility_telemetry_reporting.py` already derive counters from YAML

So this plan is no longer a greenfield design. It is now a bounded alignment and completion plan for the remaining gaps.

## Scope Rules

- Treat the curated compatibility ledger and the measured snapshot as separate artifact classes.
- Keep markdown as the readable policy surface; do not replace it with raw generated output.
- Refactor telemetry, architecture tests, and generated snapshot sections in the same program, not as disconnected follow-ups.
- Move historical review-wave narrative out of the operational ledger before or during generator adoption.
- Avoid opening a repo-wide compatibility-policy rewrite; focus on the registry surfaces already identified in the evidence pack.

## Primary Surfaces

- `docs/02-architecture/07-compatibility-facade-inventory.md`
- `tests/architecture/test_compatibility_facade_inventory.py`
- `tests/architecture/test_compatibility_telemetry_reporting.py`
- `tests/architecture/test_compatibility_freeze_guards.py`
- `scripts/ci/_compatibility_telemetry.py`
- `scripts/ci/_compatibility_registry.py`
- `scripts/qa/generate_compatibility_facade_snapshot.py`
- `configs/quality/compatibility_facade_inventory.yaml`
- `docs/02-architecture/07-compatibility-facade-snapshot.md`

## Execution Waves

### CR-01. Introduce YAML SSOT Schema And Curated Ledger

- **Priority**: P0
- **Status**: completed
- **Objective**: create one machine-readable curated registry for compatibility rows
- **Target files**:
  - `configs/quality/compatibility_facade_inventory.yaml`
  - `scripts/ci/_compatibility_registry.py`
- **Content to move into YAML**:
  - curated rows
  - compatibility role
  - canonical target
  - status
  - owner
  - introduced_in
  - remove/review date
  - allowed call sites
  - migration path
  - exit criteria
- **Expected result**:
  - curated row ownership no longer depends on markdown parsing or hardcoded test constants
  - retained-entrypoint and transition-debt rows live in one machine-readable ledger
- **Observed repo state**:
  - implemented
  - YAML currently contains `tracked_docstring_prefixes`, `transition_debt`, `retained_entrypoints`, and `measured_only_modules`
  - shared loader contract already exists and is consumed by tests/tooling

### CR-02. Rewire Test And Telemetry Consumers To YAML

- **Priority**: P0
- **Status**: mostly completed
- **Objective**: stop architecture tests and CI helpers from acting as second registries
- **Target files**:
  - `tests/architecture/test_compatibility_facade_inventory.py`
  - `tests/architecture/test_compatibility_telemetry_reporting.py`
  - `tests/architecture/test_compatibility_freeze_guards.py`
  - `scripts/ci/_compatibility_telemetry.py`
- **Expected result**:
  - retained-entrypoint row sets are read from YAML, not hardcoded
  - telemetry counts derive from the canonical ledger plus explicit measured-scan logic
  - test coverage validates one source of truth instead of replaying hidden registry state in multiple places
- **Observed repo state**:
  - `test_compatibility_facade_inventory.py` already loads YAML through `_compatibility_registry.py`
  - `test_compatibility_telemetry_reporting.py` already validates telemetry counters against YAML-derived registry state
  - `_compatibility_telemetry.py` already reads the canonical YAML
- **Remaining focus**:
  - verify whether `test_compatibility_freeze_guards.py` and any adjacent freeze/allowlist checks still duplicate registry intent outside the shared loader contract
  - do not migrate freeze-guard allowlists wholesale; only extract the narrow subset that truly restates curated or measured-only registry semantics
  - tighten schema validation only if needed, without reintroducing parallel constants

### CR-03. Add Generated Snapshot Tooling

- **Priority**: P1
- **Status**: partially completed
- **Objective**: replace manually maintained measured snapshot sections with `--check` / `--update` tooling
- **Actual script**:
  - `scripts/qa/generate_compatibility_facade_snapshot.py`
- **Modes**:
  - `--check`
  - `--update`
- **Responsibilities**:
  - read YAML SSOT
  - scan measured compatibility modules using the current compatibility measurement rule
  - compute measured-only module set
  - render snapshot counters and tracked-path appendix
- **Expected result**:
  - the most drift-prone sections become generated
  - maintenance flow matches existing dependency-map governance precedent
- **Observed repo state**:
  - the script already exists
  - the generated companion file already exists at `docs/02-architecture/07-compatibility-facade-snapshot.md`
  - `--check` is already green in the current repository state
- **Remaining focus**:
  - keep plan and docs aligned to the real script name
  - decide whether any additional wrapper/alias script is needed; do not create a second generator unless there is a real governance benefit

### CR-04. Split Manual Governance From Generated Snapshot In Markdown

- **Priority**: P1
- **Status**: mostly completed
- **Objective**: keep the inventory doc readable while making edit boundaries explicit
- **Target files**:
  - `docs/02-architecture/07-compatibility-facade-inventory.md`
  - `docs/02-architecture/07-compatibility-facade-snapshot.md`
- **Implementation rule**:
  - either use explicit generated block markers
  - or use a separate generated companion file linked from the main inventory
- **Manual sections to retain**:
  - purpose
  - status model
  - governance freeze
  - curated ledgers
  - usage notes
- **Generated sections to move out of manual editing**:
  - measured registry counters
  - tracked module paths
  - current import inventory snapshot
- **Expected result**:
  - maintainers know exactly which sections are editable by hand and which are generator-owned
- **Observed repo state**:
  - the repository already chose the companion-file approach
  - the manual inventory doc links to the generated snapshot and explicitly says not to copy counters back by hand
- **Remaining focus**:
  - keep the operational doc free of measured snapshot regressions
  - avoid reintroducing measured-registry sections into the manual doc

### CR-05. Formalize Measured-Only Policy

- **Priority**: P1
- **Status**: mostly completed
- **Objective**: make measured-only governance explicit instead of convention-only
- **Target surfaces**:
  - `docs/02-architecture/07-compatibility-facade-inventory.md`
  - possibly `docs/03-guides/registry-pattern.md`
  - `configs/quality/compatibility_facade_inventory.yaml`
  - YAML schema/comments if measured-only classification needs machine-readable metadata
- **Policy to define**:
  - when a module may stay measured-only
  - when it must be promoted into the curated ledger
  - how docstring-prefix measurement relates to sanctioned public seam status
- **Expected result**:
  - future modules such as measured-only adapter/helper seams do not create governance ambiguity
- **Observed repo state**:
  - measured-only rows now carry machine-readable `new_code_policy` and `promotion_trigger` fields in the YAML SSOT
  - `_compatibility_registry.py` validates those fields
  - the generated snapshot renders the measured-only policy fields
  - the operational inventory doc now states the measured-only policy explicitly
- **Remaining focus**:
  - decide later whether measured-only policy needs broader reuse outside the compatibility registry family
  - keep future measured-only additions aligned with the YAML schema instead of prose-only exceptions

### CR-06. Move Historical Review Narrative Out Of Operational Ledger

- **Priority**: P2
- **Status**: mostly completed
- **Objective**: stop mixing operational registry data with dated review-wave prose
- **Target surfaces**:
  - `docs/02-architecture/07-compatibility-facade-inventory.md`
  - `docs/02-architecture/history/compatibility-facade-review-history.md`
- **Expected result**:
  - operational inventory becomes a stable ledger
  - historical rationale remains discoverable, but no longer lives inside the same active registry artifact
- **Observed repo state**:
  - historical review narrative has already been moved to `docs/02-architecture/history/compatibility-facade-review-history.md`
- **Remaining focus**:
  - keep new review-wave prose out of the operational inventory doc
  - treat the history doc as the only narrative sink for retained-entrypoint review history

## Verify Matrix

Run after each wave as appropriate:

1. `./.venv/Scripts/python.exe -m pytest tests/architecture/test_compatibility_facade_inventory.py -q`
2. `./.venv/Scripts/python.exe -m pytest tests/architecture/test_compatibility_telemetry_reporting.py -q`
3. `./.venv/Scripts/python.exe -m pytest tests/architecture/test_compatibility_freeze_guards.py -q`
4. `./.venv/Scripts/python.exe scripts/repo/check_scripts_catalog.py --catalog scripts/catalog.yaml`
5. `./.venv/Scripts/python.exe scripts/docs/check_doc_links.py --configs`
6. `git diff --check`

Additional generator checks:

1. `./.venv/Scripts/python.exe scripts/qa/generate_compatibility_facade_snapshot.py --check`
2. `./.venv/Scripts/python.exe scripts/qa/generate_compatibility_facade_snapshot.py --update`

## Recommended Order

1. close the remaining `CR-02` consumer alignment, especially freeze-guard duplication checks
2. complete `CR-05` measured-only policy formalization
3. keep `CR-03` and `CR-04` green via generator/doc guardrails, not by introducing parallel tooling
4. treat `CR-06` as completed baseline and prevent narrative regressions

## Change Safety Notes

- Do not introduce a second generator with overlapping responsibility unless the existing snapshot generator proves insufficient.
- Do not reintroduce hardcoded path sets when tightening tests; route shared registry semantics through `_compatibility_registry.py`.
- Do not move measured-only policy into prose alone if tests need a machine-readable distinction.
- Treat `source_test_facade_inventory.yaml` as an adjacent registry that needs explicit ownership boundaries, not silent overlap.

## Definition Of Done

- curated compatibility registry is stored in one YAML SSOT
- markdown inventory no longer hand-maintains measured snapshot sections
- architecture tests and telemetry no longer carry a hidden second curated registry
- `scripts/qa/generate_compatibility_facade_snapshot.py --check` / `--update` is available and deterministic
- measured-only governance is explicit
- historical review narrative is no longer embedded in the operational registry ledger
