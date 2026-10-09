# Application Services Ownership Map

**ARCH-QA-07 / #6746** — explicit ownership for `src/bioetl/application/services/`.

## Policy

1. **New services land in a subdomain package**, not package root.
2. Root-level modules are **legacy / transitional**; do not add new root
   `*.py` modules without an architecture note and owner.
3. DI wiring of concrete infrastructure remains in **Composition Root** only.

## Subdomain ownership

| Package / surface | Responsibility | Primary owner |
|---|---|---|
| `control_plane/` | Run manifests, ledgers, workflow state, resume/replay orchestration | `@bioetl-platform` |
| `lineage/` | Lineage graph assembly and persistence collaborators | `@bioetl-platform` |
| `dq/` | DQ report flows, silver statistics helpers | `@bioetl-data-model` |
| `execution/` | Pipeline runner service collaborators | `@bioetl-architecture` |
| `run_reports/` | Run-report enrichment, markdown, writer | `@bioetl-architecture` |
| `protein/` | Protein classification hierarchy resolution | `@bioetl-data-model` |
| `medallion/` | Medallion lifecycle clear/vacuum/prepare orchestration | `@bioetl-architecture` |
| `quality/` | Quarantine + data-quality services | `@bioetl-data-model` |
| `ops/` | Health, metrics, lock, vacuum, shutdown, config | `@bioetl-platform` |
| `export_lineage/` | Export + debug export + audit inspection | `@bioetl-architecture` |
| `workflow/` | Workflow runner + observability workflow | `@bioetl-architecture` |
| `checkpoint/` | Checkpoint + compatibility | `@bioetl-platform` |
| `contract/` | Contract migration | `@bioetl-architecture` |
| package root | **Only** `__init__.py` (ARCH-REF-R2 / #7728) | `@bioetl-architecture` |

## No-growth rule (root modules)

- Root is package-first: **only** `__init__.py` is allowed at
  `application/services/` root after #7728.
- New services **must** land in a subdomain package above.
- Machine ratchet: `configs/quality/application_services_root_ratchet.yaml`
  (`tests/architecture/test_application_services_root_ratchet.py`,
  `tests/architecture/test_arch_ref_services_bc_root_guard.py`).

## Cross-context import policy (#7608)

- Subdomain packages (`control_plane/`, `dq/`, `execution/`, …) **SHOULD**
  depend on `domain/*` and `application/core/*`, not on sibling service
  subdomains, unless the collaboration is intentional and reviewed.
- Machine ownership inventory:
  `configs/quality/application_services_ownership.yaml`.
- New permanent cross-subdomain edges require an architecture note in the PR
  and an update to that ownership inventory when hard bans are introduced.

## Related

- Hotspot family: `application_services_control_plane` in
  `reports/quality/hotspot-family-baseline.json`
- Layer rules: `docs/00-project/RULES.md` §1
- Epic: #7605
