# AUDIT-011: Remove misleading factory naming from lineage metadata assemblers

## 1. Title
[refactor] Remove misleading factory naming from lineage metadata assemblers

## 2. Problem
Lineage metadata assembler services use parameter names ending in _factory, while the referenced types are Protocol callables and there are no concrete RuntimeMetadataFactory or PipelineMetadataFactory classes.

## 3. Evidence
- `src/bioetl/application/services/lineage/metadata_assembler_support.py::RuntimeMetadataProtocol`
- `src/bioetl/application/services/lineage/metadata_assembler_support.py::PipelineMetadataProtocol`
- `src/bioetl/application/services/lineage/metadata_assemblers.py::SilverMetadataService` (lines 45-46): `runtime_metadata_factory`, `pipeline_metadata_factory`
- `src/bioetl/application/services/lineage/metadata_assemblers.py::GoldMetadataService` (lines 135-136): `runtime_metadata_factory`, `pipeline_metadata_factory`

## 4. Root Cause
Naming drift: callable builder dependencies were named as factories without a concrete *Factory implementation or explicit factory abstraction.

## 5. Architectural Impact
- Layer boundaries: no direct boundary violation, but naming weakens DI readability
- Dependency direction: unchanged if fixed inside application
- Reproducibility: no data effect
- Observability: metadata sidecar assembly becomes clearer and easier to audit
- Governance: suffix policy is currently misleading

## 6. Required Outcome
Lineage metadata assembler dependencies must use names that reflect their actual role. Either:
- introduce real *Factory classes in the appropriate layer and inject those; or
- rename callable Protocols and fields to builder/provider terminology

Preferred outcome: keep them as application-local *Protocol callable contracts and rename _factory fields to _builder.

## 7. File-level Implementation Plan
### Changes
- `src/bioetl/application/services/lineage/metadata_assembler_support.py`
  - Rename: `RuntimeMetadataProtocol → RuntimeMetadataBuilderProtocol`
  - Rename: `PipelineMetadataProtocol → PipelineMetadataBuilderProtocol`
  - Keep Protocol suffix because these are application-local structural contracts, not domain ports
  - Update `__all__`

- `src/bioetl/application/services/lineage/metadata_assemblers.py`
  - Update imports
  - Rename dataclass fields: `runtime_metadata_factory → runtime_metadata_builder`, `pipeline_metadata_factory → pipeline_metadata_builder`
  - Update calls: `self.runtime_metadata_factory(...) → self.runtime_metadata_builder(...)`, `self.pipeline_metadata_factory() → self.pipeline_metadata_builder()`
  - Update docstrings

- `src/bioetl/application/services/lineage/metadata_assembler_factory.py`
  - Update construction kwargs: `runtime_metadata_builder=self._build_runtime_metadata`, `pipeline_metadata_builder=self._build_pipeline_metadata`

- `tests/unit/application/services/lineage/...`
  - Update constructor calls
  - Add a regression test that assembler fields use builder naming
  - Remove or update tests asserting legacy _factory names

### Refactoring actions
- Rename only. Do not change metadata assembly semantics
- Do not move these Protocols to domain.ports
- Do not add a concrete factory unless the implementation genuinely needs lifecycle/state

### Contracts impact
- No external data contract change
- Application constructor API changes
- If public compatibility is required, provide a temporary compatibility wrapper with deprecation test and removal date

### Migration
- No data migration. Internal API migration only

## 8. Constraints
Forbidden:
- importing infrastructure into domain
- adding I/O to domain
- creating fake *Factory classes with no responsibility
- creating cyclic imports between lineage services
- weakening Gold strict validation
- changing payloads in Quarantine

## 9. Acceptance Criteria
- No references to runtime_metadata_factory or pipeline_metadata_factory remain in first-party application code
- New names end with BuilderProtocol and fields end with _builder
- Unit tests pass
- Mypy passes for changed modules
- Architecture tests pass
- No new dependency cycles
- Metadata sidecar output is byte-for-byte unchanged for the same inputs

## 10. Priority
P2. This is design clarity, not a production outage. Still worth fixing before the naming drift breeds more aliases.

## 11. Size
M. Several imports and tests, no behavioral rewrite.

## 12. Labels
refactor, technical-debt

## 13. Dependencies
None.
