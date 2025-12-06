> Scope:
> - Always apply core project invariants (determinism, schemas, logging, CI discipline)
> - Treat as global invariant; apply in all tasks, even without matching files.
# Core principles

## Purpose

Enforce non-negotiable invariants across the whole repo so the agent does not guess.

## Principles (mandatory)

- Deterministic I/O: identical inputs+config produce bit-identical outputs. Use stable row/column order, UTC timestamps, canonical JSON, atomic writes.
- Validate-before-write: every table is validated against a Pandera schema with fixed column order. No writes on validation failure.
- Structured logging only via UnifiedLogger; no print(); include run context and mandatory fields.
ц- Tests: no network in unit tests; golden tests for critical outputs; property-based tests for transformations; coverage ≥ 85% in CI.
- API access only through UnifiedAPIClient with retry/backoff, rate limiting, circuit breaker and strict timeouts.
- One source → one public pipeline; use unified components (Logger, Writer, Client, Schema); follow extract→transform→validate→export.
- Secrets in env/secret manager only; typed configs via Pydantic; profiles for shared defaults; CI secret scanning enabled.
- Python style: ruff/black, isort, mypy --strict; no wildcard imports, no global mutable state, no magic numbers.

## When to use

Always. Treat as global constraints for planning, codegen, edits and refactors.

## Do

- Refuse to emit write code without prior schema validation and deterministic sorting.
- Bind run context once, log with structured key-value.
- Fail fast on missing config or secret.
- Prefer composition over inheritance in components.

## Don't

- Don't emit print(), ad-hoc logging, local time, non-atomic writes, or unordered CSV/JSON.
- Don't call external APIs outside UnifiedAPIClient or without throttling/retry policy.
- Don't bypass tests or lower coverage thresholds.

## Reference

See [docs/INDEX.md](../../docs/INDEX.md) for overview and [docs/styleguide/](../../docs/styleguide/) for detailed style guides.
