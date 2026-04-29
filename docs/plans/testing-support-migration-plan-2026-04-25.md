# Testing Support Migration Plan (2026-04-25)

*Status: Supporting operational context*
*Freshness note: refreshed on 2026-04-29 against the live workspace snapshot*

## Objective

Move the remaining root-level `testing_support/` package into
`tests/testing_support/`, update all test consumers, and then delete the
root-level `testing_support/` directory entirely.

## Live Baseline

Current root package contents:

- `testing_support/__init__.py`
- `testing_support/bronze_writer.py`
- `testing_support/neo4j_memory_sync.py`

Current direct consumers are test-only:

- `tests/unit/infrastructure/storage/bronze_writer/test_write_modes.py`
- `tests/unit/infrastructure/storage/bronze_writer/test_validation.py`
- `tests/unit/infrastructure/storage/bronze_writer/test_sidecar_and_atomicity.py`
- `tests/unit/infrastructure/storage/bronze_writer/test_control_plane_and_observability.py`
- `tests/integration/infrastructure/storage/test_bronze_writer_cleanup_and_sidecar.py`
- `tests/unit/scripts/ops/neo4j_memory_sync/test_targeted_apply_and_filters.py`
- `tests/unit/scripts/ops/neo4j_memory_sync/test_snapshot_topology.py`
- `tests/unit/scripts/ops/neo4j_memory_sync/test_snapshot_invariants.py`
- `tests/unit/scripts/ops/neo4j_memory_sync/test_paths_and_connection.py`
- `tests/unit/scripts/ops/neo4j_memory_sync/test_audit_runtime_and_transport.py`

Observed constraints from the live repo:

- `tests/__init__.py` already exists, so `tests.testing_support.*` is a valid
  package target.
- `pyproject.toml` already exposes `.` on `pythonpath`, so no extra pytest path
  hack is needed for `tests.testing_support`.
- current known consumers are all under `tests/**`; no `src/**` or `scripts/**`
  runtime callers were found.
- root governance still explicitly ratifies `testing_support/` in:
  - `configs/quality/repo_structure_catalog.yaml`
  - `docs/00-project/governance/03-file-policy.md`
  - root/structure audit tests

## Decision

Use a **single main migration wave**, not the older two-PR shim plan, unless a
new non-test caller appears during execution.

Why the single-wave path is now preferred:

- the package is small: 3 files total
- direct imports are limited and known
- all live callers are test-only
- `tests.testing_support` is already structurally viable
- keeping a temporary root shim would add extra governance churn without
  reducing much real risk

Fallback rule:

- If hidden non-test callers appear during implementation, downgrade to the
  older two-step approach with temporary re-export shims.

## Target State

- canonical test helper package lives at `tests/testing_support/`
- all test imports use `tests.testing_support.*`
- root-level `testing_support/` is deleted
- root policy no longer reserves a dedicated root-level test-support package
- structure and root hygiene tests reflect the new canonical location

## Implementation Plan

### Phase 1. Baseline Capture

Run and record the current baseline before edits:

```bash
rg -n "from testing_support\\.|import testing_support\\.|testing_support\\." tests src scripts docs .github configs
UV_CACHE_DIR=/tmp/.uv-cache PYTHONPYCACHEPREFIX=/tmp/pycache uv run pytest \
  tests/unit/infrastructure/storage/bronze_writer \
  tests/unit/scripts/ops/neo4j_memory_sync \
  tests/integration/infrastructure/storage/test_bronze_writer_cleanup_and_sidecar.py \
  tests/unit/scripts/repo/test_audit_root_cleanliness.py \
  tests/unit/scripts/repo/test_audit_structure.py -q
```

Exit criteria:

- current import set is captured
- focused helper/governance suites are green before migration

### Phase 2. Introduce Canonical Test Package

Create:

- `tests/testing_support/__init__.py`
- `tests/testing_support/bronze_writer.py`
- `tests/testing_support/neo4j_memory_sync.py`

Recommended move semantics:

- copy contents first, then switch imports, then delete the root package in the
  same wave once all checks pass

Exit criteria:

- `tests.testing_support.*` imports resolve
- helper module code remains byte-for-byte or functionally identical during the
  move

### Phase 3. Rewrite Imports

Replace:

- `from testing_support.bronze_writer import ...`
- `from testing_support.neo4j_memory_sync import ...`

with:

- `from tests.testing_support.bronze_writer import ...`
- `from tests.testing_support.neo4j_memory_sync import ...`

Expected direct import migration scope is the 10 known test files listed above.

Exit criteria:

- no test file imports the root package anymore
- `rg -n "from testing_support\\.|import testing_support\\." tests` returns no
  live test callers

### Phase 4. Governance and Structure Policy Cleanup

Update policy and audit surfaces together:

- `configs/quality/repo_structure_catalog.yaml`
  - remove the dedicated root-level `test_support_roots` allowance for
    `testing_support`
- `docs/00-project/governance/03-file-policy.md`
  - remove `testing_support` from approved root directories
  - rewrite section `0.4.1` from “root-level test support family” to
    “test-tree shared support modules under tests/testing_support/”
- `tests/unit/scripts/repo/test_audit_root_cleanliness.py`
  - remove the expectation that `testing_support` is an approved root directory
- `tests/unit/scripts/repo/test_audit_structure.py`
  - replace the cataloged root fixture with a `tests/testing_support/` fixture
- any additional root/structure governance assertions discovered during test
  execution

Important design choice:

- do **not** replace root-level approval with a new special root catalog entry
  for `tests/testing_support`
- after migration, this helper family should live under the already-approved
  `tests/` tree and no longer require a dedicated root exception

Exit criteria:

- root and structure governance no longer depend on a root-level
  `testing_support/` family

### Phase 5. Delete Root Package

Delete:

- `testing_support/__init__.py`
- `testing_support/bronze_writer.py`
- `testing_support/neo4j_memory_sync.py`

Then verify:

```bash
rg -n "from testing_support\\.|import testing_support\\.|testing_support\\." tests src scripts docs .github configs
```

Expected result:

- no live code/test imports remain
- only historical plan/archive references may remain until separately cleaned

### Phase 6. Final Validation

Run:

```bash
UV_CACHE_DIR=/tmp/.uv-cache PYTHONPYCACHEPREFIX=/tmp/pycache uv run pytest \
  tests/unit/infrastructure/storage/bronze_writer \
  tests/unit/scripts/ops/neo4j_memory_sync \
  tests/integration/infrastructure/storage/test_bronze_writer_cleanup_and_sidecar.py \
  tests/unit/scripts/repo/test_audit_root_cleanliness.py \
  tests/unit/scripts/repo/test_audit_structure.py \
  tests/architecture/test_root_hygiene_review_registry.py \
  tests/architecture/test_root_hygiene_workflow.py -q
```

Optional follow-up:

```bash
UV_CACHE_DIR=/tmp/.uv-cache PYTHONPYCACHEPREFIX=/tmp/pycache uv run pytest \
  tests/architecture/test_scripts_catalog_governance.py \
  tests/architecture/test_scripts_inventory_discovery.py -q
```

Exit criteria:

- migrated helper suites are green
- governance/root-structure suites are green
- root-level `testing_support/` no longer exists

## Risks

1. Import regressions from stale direct imports.
Reason:
- all callers are test files, but the migration still touches multiple suites.
Mitigation:
- migrate imports with a global `rg`-based sweep and run focused suites
  immediately.

2. Governance drift.
Reason:
- current structure policy explicitly allows the root-level package.
Mitigation:
- update catalog, file policy doc, and audit tests in the same change window.

3. Hidden local or ad-hoc usage not captured by tracked code search.
Reason:
- a developer may have local-only references outside the repo.
Mitigation:
- if execution reveals new non-test callers, reintroduce a temporary shim and
  split the wave.

## Recommendation

Preferred execution shape:

1. one migration PR that moves helpers into `tests/testing_support/`
2. same PR rewrites all known imports
3. same PR removes the root package and root-level governance exception

Only fall back to a temporary shim if implementation uncovers non-test callers
that were not present in the tracked repository snapshot.
