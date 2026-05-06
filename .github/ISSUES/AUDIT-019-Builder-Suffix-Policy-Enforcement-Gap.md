# AUDIT-019: Enforce composition-only Builder suffix policy in QA gate

## 1. Title
[governance] Enforce composition-only Builder suffix policy in QA gate

## 2. Problem
The naming/package consistency gate explicitly enforces Factory placement outside composition via `_factory_violations()`, but does not enforce equivalent Builder placement. The audit suffix family groups *Factory and *Builder as creation-role suffixes, and the `non_composition_builder_suffix` rule exists in `layered_suffix_policy.yaml`, but the QA script lacks builder enforcement logic.

This leaves a governance gap where future public *Builder classes can appear outside composition without the same boundary protection as *Factory.

## 3. Evidence
- `configs/quality/layered_suffix_policy.yaml::suffix_boundary_rules.non_composition_builder_suffix` (lines 43-122): Rule exists with allowed_module_exceptions for modules containing "Builder" in filename but no public Builder symbols
- `scripts/engineering/qa/check_naming_package_consistency.py::run_checks()` (lines 873-880): Calls `_factory_violations()` but has no equivalent `_builder_violations()`
- `scripts/engineering/qa/check_naming_package_consistency.py::_factory_violations()` (lines 835-848): Enforces factory-only-in-composition but no parallel builder enforcement
- Grep results show current baseline is clean: all Builder classes outside composition are either private (start with `_`) or Protocols

## 4. Root Cause
Naming enforcement gap: creation-role suffix policy covers Factory in the QA script but not the equivalent Builder suffix family. The policy configuration exists but the enforcement logic was never added to the script.

## 5. Architectural Impact
- Layer boundaries: Medium future-risk. Public builders outside composition can move DI/construction semantics into application/domain/infrastructure.
- Dependency direction: Future-risk only; this issue does not claim an active cycle.
- Determinism / idempotency: No runtime behavior change expected.
- DQ / validation: No direct DQ impact.
- Observability: No direct impact.
- Repducibility: Prevents construction logic from drifting into runtime layers where it could later affect replay consistency.

## 6. Required Outcome
After the fix:
- Public *Builder classes and builder modules outside `src/bioetl/composition/` are blocked by CI unless explicitly allowlisted with owner, issue, expiry, and removal step.
- Private/internal helper names are either renamed away from public *Builder, or explicitly private and excluded by the AST symbol iterator.
- Current baseline passes with zero unregistered builder violations.
- Future builder exceptions are visible in `configs/quality/layered_suffix_policy.yaml`.

## 7. File-level Implementation Plan
### Changes
- `scripts/engineering/qa/check_naming_package_consistency.py`
  - Add constants:
    - `FORBIDDEN_BUILDER_LAYERS = (SRC_ROOT / "application", SRC_ROOT / "infrastructure", SRC_ROOT / "domain", SRC_ROOT / "interfaces")`
    - `ALLOWED_BUILDER_FACADES = {}` initially (unless truly required)
  - Add helper functions:
    - `_builder_module_violation(py_file: Path, *, repo_root: Path) -> Violation | None`
    - `_builder_class_violations(py_file: Path, *, repo_root: Path) -> list[Violation]`
    - `_builder_violations(repo_root: Path) -> list[Violation]`
  - Include builder violations in `run_checks()` after factory violations
  - Keep private symbols starting with `_` excluded, consistent with current AST iterator behavior

- `configs/quality/layered_suffix_policy.yaml`
  - No changes needed - `non_composition_builder_suffix` rule already exists with allowed_module_exceptions
  - Current allowed_module_exceptions are all marked with issue "#3722" and expire on "2026-12-31"

- `tests/architecture/test_layer_aware_suffix_policy.py`
  - Add assertion that `non_composition_builder_suffix` rule exists
  - Add AST fixture test that detects:
    - class `FooBuilder` in application
    - `FooBuilder = BarBuilder` public alias
    - public re-export of `FooBuilder`
  - Add clean-baseline assertion

- `configs/naming_exceptions.yaml`
  - No suffix family rename required
  - Optionally add comment that Builder is governed by layer-aware policy

- `tests/architecture/test_naming_package_consistency.py` (or nearest existing naming-gate tests)
  - Add test case for Builder outside composition failing the gate
  - Add test case for Builder inside composition passing

### Refactoring actions
- No runtime refactoring unless current baseline contains unregistered public *Builder outside composition
- If violations are found, rename them to precise roles: *Assembler, *Resolver, *Planner, *Spec, or move creation logic to composition

### Contracts impact
- Ports: No port changes
- Schemas: No schema impact
- DQ rules: No DQ impact
- Config contracts: Naming policy config changes only

### Migration
- No data migration
- No contract version bump
- No Bronze/Silver/Gold rewrite
- If existing public *Builder symbols are discovered, handle as staged rename with temporary re-export

## 8. Constraints
Forbidden:
- importing infrastructure into domain
- adding I/O to domain
- violating dependency direction
- changing payload in Quarantine
- weakening Gold strict validation
- creating cyclic dependencies
- using governance allowlist as a permanent trash bin for exceptions

## 9. Acceptance Criteria
- `python scripts/engineering/qa/check_naming_package_consistency.py --check` passes
- `pytest tests/architecture/test_layer_aware_suffix_policy.py -q` passes
- New tests prove public *Builder outside composition is detected
- Current baseline has zero unregistered builder violations
- No new dependency cycles
- Runtime behavior unchanged
- Determinism and idempotency unchanged

## 10. Priority
P2. This is a prevention issue, not a current data defect, but it closes the same suffix family as Factory. Leaving half a family unguarded is how naming policy becomes decorative wallpaper.

## 11. Size
M. Policy config, QA script, and architecture tests must be changed, but no runtime refactor is expected unless violations are discovered.

## 12. Labels
architecture, technical-debt, testing, configs, governance

## 13. Dependencies
None.
