______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Last verified: '2026-08-10'

______________________________________________________________________

# ADR-057: Deterministic runtime configuration authority and identity

**Date:** 2026-08-10
**Status:** Accepted
**Linked issues:** #8557, #8558, #8559, #8560, #8561, #8562, #8563, #8564, #8565
**Related:** ADR-032, ADR-044, ADR-046, ADR-052

## Context

Runtime Settings previously accepted an implicit `config.yaml` from the current
working directory before explicit initialization and process environment values.
Provider YAML also accepted unknown nested transport keys, while HTTP composition
could obtain authenticated rates from a second hardcoded registry surface. These
behaviors made runtime authority dependent on CWD and allowed tracked no-op keys to
change forensic source hashes without changing effective behavior.

## Decision

1. Application Settings precedence is:

   ```text
   explicit init/CLI > process ENV > repository-root .env > typed defaults
   ```

   `.env` is resolved from the canonical repository root. Arbitrary CWD
   `config.yaml` files are not Settings sources.
2. `configs/providers/<provider>.yaml::source` is the sole provider HTTP
   transport authority. Its Pydantic boundary and nested transport models use
   `extra="forbid"`.
3. Entity `pipeline.source` may contain entity-specific request data, but it may
   not override provider `rate_limit`, `circuit_breaker`, or `provider_config`.
4. Anonymous and authenticated token-bucket values are declared together under
   `source.rate_limit`; credential presence is resolved through typed Settings
   using `provider_config.api_key_env`. Secret values never enter YAML or
   effective-config artifacts.
5. Provider `health_check` and `retry.use_retry_after` YAML sections are retired.
   Health probes and Retry-After handling remain code-owned until a separately
   accepted typed behavioral contract is introduced.
6. Effective-config artifact schema `2.0` publishes explicit identity versions:
   `canonical-yaml-sha256-v1` or `raw-bytes-sha256-v1` for file sources,
   `resolved-config-v1` for resolved config, and `effective-config-v1` after
   runtime overrides. Raw byte hashes remain forensic and are excluded from
   semantic identity.

## Consequences

- Settings and domain config loading are independent of current working directory.
- Unknown provider leaves and split-brain entity transport overrides fail closed.
- Formatting-only YAML changes preserve resolved/effective identity while changing
  only the separately versioned raw forensic hash.
- Registry HTTP rates remain fallback values for providers without a tracked source;
  they do not carry authenticated overrides.

## Migration and compatibility

- Operators who used CWD `config.yaml` must move values to `BIOETL_*` environment
  variables, the repository-root `.env`, or explicit constructor/CLI arguments.
- Historical effective-config artifacts with schema `1.0` remain readable and are
  labeled with `*-legacy-v0` identities when reconstructed. New writes use `2.0`.
- Historical manifests/checkpoints remain available for diagnostics. Exact replay
  continues to fail closed when required resolved/effective/checkpoint anchors are
  absent; dual-read does not synthesize missing semantic anchors.
- Removed provider health/retry leaves have no data backfill because they never
  affected runtime behavior.

## Rollback

Rollback may restore the previous artifact writer version while retaining dual-read
support. It must not restore implicit CWD authority, silent `extra="ignore"`, or a
second authenticated-rate registry. A new ADR is required to reintroduce a YAML
Settings source or configurable health/retry semantics.
