# Docs CLI Wrapper Closeout 2026-04-28

*Status: Supporting operational context*
*Date: 2026-04-28*

## Purpose

This note closes the low-risk `scripts/docs` compatibility-wrapper wave and
records the explicit retained-vs-removed decisions for the remaining docs CLI
surface.

## Closed Removals

Removed on `2026-04-28`:

- `scripts/docs/run_mkdocs_build.py`
- `scripts/docs/check_doc_links.py`

Both files reached a state where repo-internal operational callers were gone
and tests could be migrated onto canonical package modules:

- `scripts.docs.checks.check_links`
- `scripts.docs.checks.check_drift`
- other packaged `scripts.docs.*` command modules

The `check_doc_links.py` removal is now backed by:

- `tests/architecture/test_check_doc_links_guardrails.py`, which imports
  `scripts.docs.checks.check_links` directly
- `tests/architecture/test_docs_compat_shim_governance.py`, which no longer
  treats the removed shim as a required compatibility file
- the wrapper caller matrix, which no longer tracks `check_doc_links.py`

## Retained Surface

Retained:

- `scripts/docs/build_docs_site.sh`

Classification:

- shell transport adapter

Why it stays:

1. It is not a thin alias. It still carries shell-facing transport behavior:
   repo-local `.venv` fallback, WSL-to-Windows `python.exe` fallback, staged
   output normalization, and `docs/site` final placement.
2. It now delegates to a working packaged backend:
   `scripts.docs.build.mkdocs_build`.
3. Removing it would be a public contract change for shell-oriented callers,
   not a dead-wrapper cleanup.

## Fixed Parity Defect

During the closeout, the canonical route `python -m scripts.docs build-site`
was found to be broken because `scripts.docs.build.mkdocs_build` did not exist.

The wave fixed that by adding:

- `scripts/docs/build/__init__.py`
- `scripts/docs/build/mkdocs_build.py`

Current state:

- `python -m scripts.docs build-site --help` is importable and routable
- `scripts/docs/build_docs_site.sh` now sits on top of a real packaged backend
  instead of a missing module path

## Current Rule

- Remove docs wrappers only when the remaining work is pure governance cleanup.
- Keep `build_docs_site.sh` until a separate redesign proves that its transport
  behavior is either no longer needed or is fully preserved elsewhere.

