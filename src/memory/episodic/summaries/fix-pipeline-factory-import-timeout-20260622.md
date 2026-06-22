---
id: fix-pipeline-factory-import-timeout-20260622
title: Fix pipeline factory import timeout
task_id: fix-pipeline-factory-import-timeout-20260622
created_at: '2026-06-22T16:54:22Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/unit/interfaces/factories/test_pipeline_factories.py
summary: 'Fixed Windows/PyCharm timeout when tests import pubchem_compound_factory
  from pipeline registry. Root cause: GenericPipelineFactory.__init__ resolved get_data_source_creator
  through the public assembler facade, importing assembler/services assembly during
  factory export resolution. Added a lazy data-source creator callback so constructor
  stays light and assembler import happens only when create_data_source/build_services
  actually needs it. Validation passed for the offending test, full test_pipeline_factories.py,
  related pipeline factory tests, ruff, module coverage/scorecard guards; module coverage
  hash guard is skipped on WSL by policy.'
---

# Episodic summary

## Task

- Title: Fix pipeline factory import timeout

## Outcome

- Fixed Windows/PyCharm timeout when tests import pubchem_compound_factory from pipeline registry. Root cause: GenericPipelineFactory.__init__ resolved get_data_source_creator through the public assembler facade, importing assembler/services assembly during factory export resolution. Added a lazy data-source creator callback so constructor stays light and assembler import happens only when create_data_source/build_services actually needs it. Validation passed for the offending test, full test_pipeline_factories.py, related pipeline factory tests, ruff, module coverage/scorecard guards; module coverage hash guard is skipped on WSL by policy.

## Lessons learned

- Replace with durable follow-up if needed
