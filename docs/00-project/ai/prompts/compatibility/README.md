# Compatibility wrappers — legacy `prompt.audit.*` → compiled overlay

> Deprecated shims for `prompt.audit.cycle.*` and `prompt.audit.project.new2.*`.
> Each wrapper delegates to the kernel+overlay compiler. See ADR-060 §7.

## Purpose

Preserve operator bookmarks and `REGISTRY.yaml` `prompt.*` IDs while SSOT
moves to `fragments/` + `overlays/<domain>.yaml` + `profiles/*.yaml`.
Wrappers are not SSOT — they forward to `generated/<domain>/<profile>.md`.

## Deprecation window

Per ADR-060 §7 / `MIGRATION-PLAN.md` §4: wrappers stay at least one release
after parity + pilot (P2). Removal needs a migration guide and redirect catalog
(P3). `status: deprecated` + `successor` are set only after parity is proven.

## Resolve legacy ID → generated file

1. Read `compatibility/<legacy-id>.md` frontmatter `successor`.
2. Or map via `overlays/<domain>.yaml` field `id` (equals the legacy ID).
3. Generated path: `generated/<domain>/<profile>.md` (profile = `audit-readonly` | `full-write`).

## Render new overlay

```bash
python -m scripts.ai.prompts.compile --domain <domain> --profile audit-readonly
python -m scripts.ai.prompts.compile --domain <domain> --profile full-write
python -m scripts.ai.prompts.compile --all --check   # CI drift gate
```

Provenance: `materialized-v3 @ main@3aba8559` — `BIOETL-PROMPT-ARCH-KERNEL-V3-003`.
