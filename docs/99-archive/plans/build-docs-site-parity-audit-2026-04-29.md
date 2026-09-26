# build_docs_site.sh parity audit (2026-04-29)

## Scope

This note records the bounded parity/redesign decision for
`scripts/docs/build_docs_site.sh`.

## Findings

- The packaged backend `scripts.docs.build.mkdocs_build` is now the single
  source of truth for MkDocs site build behavior.
- That backend already owns:
  - default `docs/site` normalization
  - temporary staging for default builds
  - cleanup of the legacy top-level `site/` output
- The shell entrypoint still provided real value, but only as transport:
  - prefer a Python interpreter with `mkdocs` available
  - fall back to `./.venv/bin/python`
  - support WSL to Windows `.venv\\Scripts\\python.exe` dispatch

## Decision

Retain `scripts/docs/build_docs_site.sh`, but only as a shell transport
adapter. It should not implement build semantics, temp-site handling, or output
normalization.

## Resulting boundary

- Canonical public command:
  - `python -m scripts.docs build-site`
- Retained transport adapter:
  - `bash scripts/docs/build_docs_site.sh`
- Build semantics owner:
  - `scripts.docs.build.mkdocs_build`

## Why it stays

The shell surface still covers a real runtime gap for contributors who invoke
docs tooling from shell-first environments, especially WSL/Windows mixed
setups. Removing it would conflate transport concerns with CLI canonicalization.

## Why it should not grow

The adapter is explicitly not the place for:

- `docs/site` normalization logic
- temporary output staging policy
- direct `mkdocs build` orchestration semantics
- separate feature flags that diverge from `python -m scripts.docs build-site`

Any future behavior change should be implemented in
`scripts.docs.build.mkdocs_build` first and inherited by the shell adapter.
