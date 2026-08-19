# Iteration 9 — DQ, filters, and schema parity

## Evidence

- `python -m scripts.schema check-required-fields` passed.
- `python -m scripts.schema audit-optionality --check` reports INV-CFG-008 PASS.
- `python -m scripts.schema check-config-paths configs` reports no legacy paths.
- `python -m scripts.schema verify-schema-parity --mode blocking` reports no new
  blocking Silver/Gold parity or primary-key issue.
- The default parity mode exits 1 on any warning by design; its Silver-only
  inventory is explicitly non-blocking. The blocking mode is the applicable
  closure gate.
- Full `tests/integration/config` passed.

## Result

PASS. DQ/filter contracts are consistent and blocking parity is green.
Delta: unchanged. Debt effect: unchanged.
