---
id: techdebt-implementation-wave-4
title: Remove legacy semantic silver compatibility residue
task_id: techdebt-implementation-wave-4
created_at: '2026-05-13T15:41:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/infrastructure/config/silver_filter_migration.py
summary: 'Removed legacy semantic Silver residue from active runtime/config surfaces
  by simplifying single-mode silver_filter_migration helpers, collapsing FilterConfigLoader
  cache key away from retired mode branching, deleting legacy rollback test expectations,
  updating domain fingerprint/runtime-config/checkpoint tests to the canonical structural_only_auto_promote
  contract, and adding an architecture guard against reintroducing legacy_semantic_silver
  or BIOETL_LEGACY_SILVER_SEMANTIC in active Silver filter surfaces. Updated docs/filters
  ADR and migration plan to match the current hard-locked runtime behavior. Validation:
  bash scripts/engineering/dev/run_pytest.sh --skip-preflight tests/unit/domain/test_runtime_config.py
  tests/unit/domain/types/test_checkpoint_metadata.py tests/unit/domain/normalization/test_fingerprints.py
  tests/unit/infrastructure/config/test_filter_config_loader.py tests/architecture/test_silver_filter_compatibility_surface.py.
  Debt outcome for touched surfaces: improved.'
---

# Episodic summary

## Task

- Title: Remove legacy semantic silver compatibility residue

## Outcome

- Removed legacy semantic Silver residue from active runtime/config surfaces by simplifying single-mode silver_filter_migration helpers, collapsing FilterConfigLoader cache key away from retired mode branching, deleting legacy rollback test expectations, updating domain fingerprint/runtime-config/checkpoint tests to the canonical structural_only_auto_promote contract, and adding an architecture guard against reintroducing legacy_semantic_silver or BIOETL_LEGACY_SILVER_SEMANTIC in active Silver filter surfaces. Updated docs/filters ADR and migration plan to match the current hard-locked runtime behavior. Validation: bash scripts/engineering/dev/run_pytest.sh --skip-preflight tests/unit/domain/test_runtime_config.py tests/unit/domain/types/test_checkpoint_metadata.py tests/unit/domain/normalization/test_fingerprints.py tests/unit/infrastructure/config/test_filter_config_loader.py tests/architecture/test_silver_filter_compatibility_surface.py. Debt outcome for touched surfaces: improved.

## Lessons learned

- Replace with durable follow-up if needed
