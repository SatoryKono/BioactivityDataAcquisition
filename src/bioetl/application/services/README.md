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
| package root (legacy) | Cross-cutting services not yet rehomed (metrics, quarantine, export, checkpoints, …) | `@bioetl-architecture` |

## No-growth rule (root modules)

- Ratchet: do not increase the count of root-level service modules without
  moving an existing root module into a subdomain or documenting an intentional
  permanent root entry with owner.
- Prefer extracting collaborators under the closest subdomain package above.

## Related

- Hotspot family: `application_services_control_plane` in
  `reports/quality/hotspot-family-baseline.json`
- Layer rules: `docs/00-project/RULES.md` §1
