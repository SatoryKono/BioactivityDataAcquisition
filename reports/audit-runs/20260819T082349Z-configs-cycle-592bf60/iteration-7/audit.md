# Iteration 7 — provider and Settings authority

## Evidence

- ADR-057 lines 27-50 defines precedence `explicit init/CLI > process ENV >
  repository-root .env > typed defaults`, forbids CWD `config.yaml` authority,
  and makes `configs/providers/<provider>.yaml::source` the sole provider
  transport authority.
- `configs/README.md:34-47` mirrors that contract without adding another source.
- `tests/architecture/test_source_config_usage.py`,
  `test_config_strict_keys.py`, `test_reproducibility_config_policy.py`, and
  `test_config_ci_invariants.py` passed.
- Active provider YAML contains no retired root `health_check`/runtime `retry`
  leaves and no inline entity transport override accepted by the validators.

## Result

PASS. Provider authority is deterministic and fail-closed. Delta: unchanged.
Debt effect: unchanged.
