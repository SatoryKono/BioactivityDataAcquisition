---
id: run-chembl-target-gold-diagnostics-20260601
title: Run chembl_target and diagnose Gold persistence
task_id: run-chembl-target-gold-diagnostics-20260601
created_at: '2026-06-01T05:51:21Z'
ttl_days: 14
confidence: episodic
source_refs:
- configs/entities/chembl/target.yaml
summary: 'Ran chembl_target with limit=5 and diagnosed missing Gold persistence. Run
  succeeded at CLI level but wrote only Bronze data and DQ reports. Silver write failed
  strict Pandera validation because Target domain entity now includes protein_classifications
  and entity_to_silver_record uses dataclasses.asdict, leaking that field into Silver
  records while TargetSchema has strict=True and no protein_classifications column.
  Gold was not persisted because transformed gold_records was empty: ledger shows
  records_gold=0 and records_gold_excluded_by_contract=4, so write_gold was never
  invoked. Postrun also logged silver_compact_failed for missing silver table and
  gold_dq_report_skipped because no gold data was available. No code changes made.'
---

# Episodic summary

## Task

- Title: Run chembl_target and diagnose Gold persistence

## Outcome

- Ran chembl_target with limit=5 and diagnosed missing Gold persistence. Run succeeded at CLI level but wrote only Bronze data and DQ reports. Silver write failed strict Pandera validation because Target domain entity now includes protein_classifications and entity_to_silver_record uses dataclasses.asdict, leaking that field into Silver records while TargetSchema has strict=True and no protein_classifications column. Gold was not persisted because transformed gold_records was empty: ledger shows records_gold=0 and records_gold_excluded_by_contract=4, so write_gold was never invoked. Postrun also logged silver_compact_failed for missing silver table and gold_dq_report_skipped because no gold data was available. No code changes made.

## Lessons learned

- Replace with durable follow-up if needed
