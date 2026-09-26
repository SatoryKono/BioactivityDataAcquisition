______________________________________________________________________

Version: 1.2.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-09-01'

______________________________________________________________________

# Project audit prompt surfaces

Navigation only, not runtime SSOT.

## Active sources

- Kernel + overlays: [`overlays/`](../../../overlays/) → [`generated/`](../../../generated/)
- Legacy id wrappers: [`compatibility/`](../../../compatibility/)
- Router: [pack.md](pack.md) (`prompt.audit.project.pack`)
- Ten cycle bookmarks: [cycle index](../cycle/README.md) (deprecated redirects)
- Sequential run: [sequential-run.md](../sequential-run.md)
- Cyclic router: [cyclic-pack.md](../cyclic-pack.md)

## Frozen snapshot

[materialized-v3](materialized-v3/README.md) is the dated 24-card evidence
snapshot. Do not edit it as source.

## Retired trees

`new/` and `new2/` were unregistered `ALLOW_*=true` megacards (ADR-060 D1/D2).
They live under [`archive/retired-project-new/`](../../../archive/retired-project-new/README.md)
and [`archive/retired-project-new2/`](../../../archive/retired-project-new2/README.md).
Use `python -m scripts.ai.prompts compile --domain <domain> --profile audit-readonly`.
