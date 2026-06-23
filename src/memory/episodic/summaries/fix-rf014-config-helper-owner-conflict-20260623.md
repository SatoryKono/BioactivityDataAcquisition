---
id: fix-rf014-config-helper-owner-conflict-20260623
title: Fix RF014 config helper owner conflict
task_id: fix-rf014-config-helper-owner-conflict-20260623
created_at: '2026-06-23T04:40:58Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/architecture/test_rf014_composition_bootstrap_closeout.py
summary: 'Updated RF014 composition bootstrap closeout ratchet for cli/config.py to
  require bioetl.composition.runtime_builders.config_access instead of the retired
  direct bioetl.infrastructure.config.pipeline_config_api helper import. This resolves
  the conflict with issue 5507 owner-seam guard without reintroducing direct infrastructure
  config API imports in CLI bootstrap. Validation: RF014 bounded/helper-backed guard
  passed, issue 5507 closeout guard passed, full RF014 plus 5507/5509 closeout files
  passed, ruff on touched test passed.'
---

# Episodic summary

## Task

- Title: Fix RF014 config helper owner conflict

## Outcome

- Updated RF014 composition bootstrap closeout ratchet for cli/config.py to require bioetl.composition.runtime_builders.config_access instead of the retired direct bioetl.infrastructure.config.pipeline_config_api helper import. This resolves the conflict with issue 5507 owner-seam guard without reintroducing direct infrastructure config API imports in CLI bootstrap. Validation: RF014 bounded/helper-backed guard passed, issue 5507 closeout guard passed, full RF014 plus 5507/5509 closeout files passed, ruff on touched test passed.

## Lessons learned

- Replace with durable follow-up if needed
