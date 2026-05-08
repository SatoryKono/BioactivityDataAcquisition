---
id: repro-double-audit-chembl-assay-2026-05-08
title: Double reproducibility audit for chembl_assay pipeline
task_id: repro-double-audit-chembl-assay-2026-05-08
created_at: '2026-05-08T17:24:53Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: Completed double reproducibility audit for chembl_assay. Confirmed bronze
  sidecar output.content_hash drifted across identical runs because build_bronze_output_content_hash
  included run-specific output_path. Fixed helper to exclude occurrence-scoped path
  and added regression test. Re-ran two post-fix workflow audits; execution_fingerprint,
  input snapshot fingerprint, bronze published content_hash, silver content_hash,
  gold content_hash, and silver CSV hash all matched across reruns. No confirmed reproducibility
  defects remain for the audited chembl_assay lane.
---

# Episodic summary

## Task

- Title: Double reproducibility audit for chembl_assay pipeline

## Outcome

- Completed double reproducibility audit for chembl_assay. Confirmed bronze sidecar output.content_hash drifted across identical runs because build_bronze_output_content_hash included run-specific output_path. Fixed helper to exclude occurrence-scoped path and added regression test. Re-ran two post-fix workflow audits; execution_fingerprint, input snapshot fingerprint, bronze published content_hash, silver content_hash, gold content_hash, and silver CSV hash all matched across reruns. No confirmed reproducibility defects remain for the audited chembl_assay lane.

## Lessons learned

- Replace with durable follow-up if needed
