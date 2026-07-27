## Summary

<!-- Brief description of changes (1-3 sentences) -->

## Changes

-

## Type

- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring (no functional changes)
- [ ] Config / pipeline change
- [ ] Documentation
- [ ] CI / infrastructure

## Affected layers

- [ ] Domain
- [ ] Application
- [ ] Infrastructure
- [ ] Composition
- [ ] Interfaces
- [ ] Configs

## Test plan

- [ ] Unit tests pass (`pytest tests/unit/`)
- [ ] Architecture tests pass (`pytest tests/architecture/`)
- [ ] Type check passes (`mypy --strict src/bioetl/`)
- [ ] Manual verification (describe below if applicable)

## Architecture verification evidence

<!-- Required for architecture/debt/gate/refactor changes. -->

<!-- Record concrete before/after values and the exact gates you ran. -->

- Before metrics:
- After metrics:
- Gates / verification:
- Outcome: `improved` / `unchanged` / `worsened`
- Justification (required for `unchanged` or `worsened`):

## Compatibility / tech-debt prevention (TD-10)

Keep twin / transition / expired compatibility metrics at zero:

- [ ] No new transition shims, twin modules, or package-root compatibility facades
      without inventory updates and owner review
- [ ] No first-party `src` imports of `bioetl.infrastructure.config` package root
      (see `docs/02-architecture/compatibility/infrastructure-config-package-root-sunset.md`)
- [ ] No debt budget / threshold / exemption growth (shrink-only scorecard)
- [ ] Permanent public CLI/composition entrypoints stay inventory-listed (not “dead code”)

## Checklist

- [ ] No new import boundary violations (ARCH-001)
- [ ] No hardcoded secrets (AP-005)
- [ ] Type annotations on all public functions (TYPE-001)
- [ ] Tests added/updated for new code (TEST-002)
- [ ] If `checks-complete` fails, I first triage `lint` → `c901-governance` →
      `arch-tests` and do not debug `checks-complete` separately

- [ ] If many jobs fail quickly, I inspected `dependency-preflight` first (`reports/ci/dependency-preflight.log`)
