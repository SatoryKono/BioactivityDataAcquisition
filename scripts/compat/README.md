# Compatibility Entry Points

This folder reserves compatibility-only assets for script path migrations.

Current policy:
- Backward-compatible wrappers currently remain in `scripts/` root.
- New canonical automation must use grouped paths under `scripts/*/`.
- New wrappers should be temporary and linked to a deprecation/removal step.
