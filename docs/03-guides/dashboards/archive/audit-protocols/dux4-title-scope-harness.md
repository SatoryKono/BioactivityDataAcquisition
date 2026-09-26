> **ARCHIVED** (issue #8632) — historical DUX audit protocol. Not operator guidance. See [archive index](../README.md).

# DUX4-01 title/scope harness decision

**Issue:** #7089

## Decision: Approach B (primary) + Approach A helpers

### Approach B (shipped)

Panel **titles stay exact** for integration contracts. Visible operator grammar:

- panel descriptions (`DUX3-*` / `DUX4-*` markers)
- Provenance / context strips with scope legend
- `dux3-residual-contracts.md`

### Approach A (optional; helpers ready)

ASCII title prefix pattern:

```text
[NOW/HEALTH] Status
```

Regex: `^\[(NOW|RANGE|RUN|WORKFLOW|GLOBAL)/(HEALTH|EXEC|EVIDENCE|IMPACT|APPLICABILITY)\]\s+`

Helpers in `tests/integration/_grafana_test_support.py`:

- `SCOPE_TITLE_PREFIX_RE`
- `strip_scope_title_prefix`
- `panel_base_title`
- `index_panels_by_base_title`

Contracts may match **base titles** via helpers without requiring prefixes today.

## Acceptance

- [x] Decision documented
- [x] Helpers present
- [x] Existing exact-title tests remain the default path
