# Python Code Style

This document defines Python code style guidelines for the `bioetl` project, complementing the general naming policies.

## Entity & pipeline naming

This subsection complements the general Python naming rules with
entity- and pipeline-specific requirements (see `02-new-entity-naming-policy.md`).

### Canonical patterns (code / factories / impls)

- **Modules / packages (MUST)**: `^[a-z0-9_]+$` (snake_case).
- **Pipeline logical name (code/config)**: `{entity}_{provider}` (snake_case).
- **Default factories (MUST)**:
  - Canonical form: `default_<domain>_<entity>` (function name).
  - Location: `src/bioetl/clients/<domain>/factories.py`.
  - **Rationale**: required entrypoint for producing a ready-to-use client that conforms to the contract.
  - **Compatibility**: legacy form `default_<domain>_<entity>_client()` may be present for migration; new code **MUST** use the canonical `default_<domain>_<entity>` form.
- **Impl classes (MUST)**:
  - Pattern: `^[A-Z][A-Za-z0-9]+Impl$`
  - Examples: `ChemblDataClientHTTPImpl`, `PubchemTestitemImpl`.
  - Location: `src/bioetl/clients/<domain>/impl/`.
- **Contracts / ABC (MUST)**:
  - Suffix: `Protocol` or `ABC`, located under `src/bioetl/clients/<domain>/contracts.py`.
  - Docstring structured block is **MUST** (see next section).

### ABC docstring (MUST)

Every new ABC / Protocol **MUST** contain a structured docstring including:

1. Brief description (1–2 sentences).
2. Public interface (list of method signatures).
3. File path / localization.
4. Pointer to Default factory and `abc_impls.yaml` entry.

This docstring structure is used by documentation generators and CI checks.

### Tooling / CI integration (guidance)

- CI **MUST** verify:
  - Presence of `default_<domain>_<entity>` for every new ABC (or documented stub).
  - Registration updates in `abc_impls.yaml` when a new Impl is added.
  - The ABC docstring structured block is present and parsable.
- Linter regexes for the patterns above **SHOULD** be added to the naming linter configuration.

## General Python style

- Follow PEP 8 conventions.
- Public functions and dataclasses **MUST** have type annotations.
- `mypy` is required for public APIs.
- Prefer pure functions where possible.
- Consistent import formatting and sorting.
- `from x import *` is forbidden.

## Code organization

- One responsibility per file.
- Private modules start with `_`.
- Public symbols exported via `__all__` in `__init__.py`.

## References

- `01-new-entity-implementation-policy.md` — ABC/Default/Impl patterns
- `02-new-entity-naming-policy.md` — full naming policy

