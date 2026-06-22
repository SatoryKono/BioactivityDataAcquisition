---
id: fix-cli-bootstrap-config-dq-loader-seam-20260622
title: Fix CLI bootstrap config DQ loader patch seam
task_id: fix-cli-bootstrap-config-dq-loader-seam-20260622
created_at: '2026-06-22T17:22:03Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/composition/bootstrap/cli/config.py
summary: Fixed tests/unit/composition/bootstrap/cli/test_config.py::TestBootstrapConfigService::test_dq_loader_receives_explicit_configs_root
  by restoring load_dq_config_for_pipeline as a patchable composition-root seam in
  bioetl.composition.bootstrap.cli.config and binding configs_root via functools.partial.
  Target test, full CLI config unit file, ruff, architecture scorecard guard passed;
  module coverage source hash guard skipped on WSL. Refreshed module coverage source_tree_sha256
  and architecture scorecard evidence without regenerating coverage rows.
---

# Episodic summary

## Task

- Title: Fix CLI bootstrap config DQ loader patch seam

## Outcome

- Fixed tests/unit/composition/bootstrap/cli/test_config.py::TestBootstrapConfigService::test_dq_loader_receives_explicit_configs_root by restoring load_dq_config_for_pipeline as a patchable composition-root seam in bioetl.composition.bootstrap.cli.config and binding configs_root via functools.partial. Target test, full CLI config unit file, ruff, architecture scorecard guard passed; module coverage source hash guard skipped on WSL. Refreshed module coverage source_tree_sha256 and architecture scorecard evidence without regenerating coverage rows.

## Lessons learned

- Replace with durable follow-up if needed
