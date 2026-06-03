---
id: docs-audit-p0-wave-1
title: P0/P1 documentation audit fixes completed
task_id: docs-audit-p0-wave-1
created_at: '2026-06-03T06:54:13Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: "Successfully completed P0 and P1 documentation audit fixes for BioETL project.\n\
  \nP0 Fixes (operator-facing false instructions):\n1. README.md bootstrap commands:\n\
  \   - Removed non-existent 'make setup-skills' command\n   - Fixed 'make install'\
  \ description to include --extra tests\n   - Updated documentation site commands\
  \ to include --extra tests\n   - Clarified 'make test-deps' configures pytest tooling\n\
  \   - Clarified 'make setup-plugins' configures pre-commit tooling\n   - Removed\
  \ legacy 'python -m scripts.engineering.dev setup' mention\n   - Fixed manual setup\
  \ to include --extra tests\n\n2. docs/04-reference/contracts/dq-contracts.md:\n\
  \   - Updated disposition policy from outdated (transform/allow/escalate) to canonical\
  \ DQDisposition enum values (pass/warn/quarantine/skip/fail)\n   - Fixed decision\
  \ tree to reflect actual severity handling (ERROR/WARN)\n   - Updated Quarantine\
  \ Contract fields to match QuarantineEntry aggregate:\n     * entry_id (not record_id)\n\
  \     * pipeline_name (not pipeline_id)\n     * error_code (not violation_type)\n\
  \     * payload (not original_payload)\n     * payload_hash, run_id, batch_id\n\
  \     * status: NEW/UNDER_REVIEW/IGNORED/REPROCESSED/EXPIRED\n     * resolution_info\
  \ with resolution_type, resolved_at, resolved_by, reason\n   - Updated recovery\
  \ workflow to use actual aggregate methods (start_review, mark_ignored, mark_reprocessed,\
  \ mark_expired)\n\n3. docs/03-guides/dashboards/README.md:\n   - Clarified that\
  \ '6. Alerts & SLO' exists as separate dashboard but is NOT included in primary\
  \ navigation panels (0-5)\n   - Fixed navigation contract drift claim\n\nP1 Fixes\
  \ (architectural semantics alignment):\n1. src/bioetl/domain/README.md:\n   - Replaced\
  \ 'services/' with 'behavior/' in package navigation table\n   - Updated description\
  \ to reflect actual behavior/ package with normalization, DQ evaluation, identity\
  \ generation\n\n2. docs/02-architecture/01-domain-layer.md:\n   - Fixed header from\
  \ '\u0414\u043E\u043C\u0435\u043D\u043D\u044B\u0435 \u0441\u0435\u0440\u0432\u0438\
  \u0441\u044B (`services/`)' to '\u0414\u043E\u043C\u0435\u043D\u043D\u043E\u0435\
  \ \u043F\u043E\u0432\u0435\u0434\u0435\u043D\u0438\u0435 (`behavior/`)'\n   - Eliminated\
  \ mixed logical/physical naming\n\n3. docs/02-architecture/decisions/ADR-045-dq-contract-system.md:\n\
  \   - Updated DQDisposition enum to include all shipped values (PASS, WARN, QUARANTINE,\
  \ SKIP, FAIL)\n   - Aligned ADR with runtime contract surface\n\nAll fixes based\
  \ on runtime code verification:\n- Makefile targets\n- src/bioetl/domain/config/dq.py\
  \ DQConfig\n- src/bioetl/domain/config/validation.py FieldValidation\n- src/bioetl/domain/aggregates/_quarantine_aggregate.py\
  \ QuarantineEntry\n- src/bioetl/domain/types/dq_contracts.py DQDisposition enum\n\
  - grafana/dashboards/ inventory\n- src/bioetl/domain/ package tree"
---

# Episodic summary

## Task

- Title: P0/P1 documentation audit fixes completed

## Outcome

- Successfully completed P0 and P1 documentation audit fixes for BioETL project.

P0 Fixes (operator-facing false instructions):
1. README.md bootstrap commands:
   - Removed non-existent 'make setup-skills' command
   - Fixed 'make install' description to include --extra tests
   - Updated documentation site commands to include --extra tests
   - Clarified 'make test-deps' configures pytest tooling
   - Clarified 'make setup-plugins' configures pre-commit tooling
   - Removed legacy 'python -m scripts.engineering.dev setup' mention
   - Fixed manual setup to include --extra tests

2. docs/04-reference/contracts/dq-contracts.md:
   - Updated disposition policy from outdated (transform/allow/escalate) to canonical DQDisposition enum values (pass/warn/quarantine/skip/fail)
   - Fixed decision tree to reflect actual severity handling (ERROR/WARN)
   - Updated Quarantine Contract fields to match QuarantineEntry aggregate:
     * entry_id (not record_id)
     * pipeline_name (not pipeline_id)
     * error_code (not violation_type)
     * payload (not original_payload)
     * payload_hash, run_id, batch_id
     * status: NEW/UNDER_REVIEW/IGNORED/REPROCESSED/EXPIRED
     * resolution_info with resolution_type, resolved_at, resolved_by, reason
   - Updated recovery workflow to use actual aggregate methods (start_review, mark_ignored, mark_reprocessed, mark_expired)

3. docs/03-guides/dashboards/README.md:
   - Clarified that '6. Alerts & SLO' exists as separate dashboard but is NOT included in primary navigation panels (0-5)
   - Fixed navigation contract drift claim

P1 Fixes (architectural semantics alignment):
1. src/bioetl/domain/README.md:
   - Replaced 'services/' with 'behavior/' in package navigation table
   - Updated description to reflect actual behavior/ package with normalization, DQ evaluation, identity generation

2. docs/02-architecture/01-domain-layer.md:
   - Fixed header from 'Доменные сервисы (`services/`)' to 'Доменное поведение (`behavior/`)'
   - Eliminated mixed logical/physical naming

3. docs/02-architecture/decisions/ADR-045-dq-contract-system.md:
   - Updated DQDisposition enum to include all shipped values (PASS, WARN, QUARANTINE, SKIP, FAIL)
   - Aligned ADR with runtime contract surface

All fixes based on runtime code verification:
- Makefile targets
- src/bioetl/domain/config/dq.py DQConfig
- src/bioetl/domain/config/validation.py FieldValidation
- src/bioetl/domain/aggregates/_quarantine_aggregate.py QuarantineEntry
- src/bioetl/domain/types/dq_contracts.py DQDisposition enum
- grafana/dashboards/ inventory
- src/bioetl/domain/ package tree

## Lessons learned

- Replace with durable follow-up if needed
