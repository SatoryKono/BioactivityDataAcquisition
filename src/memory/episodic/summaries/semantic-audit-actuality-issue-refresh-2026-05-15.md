---
id: semantic-audit-actuality-issue-refresh-2026-05-15
title: Check semantic audit actuality and create current issues
task_id: semantic-audit-actuality-issue-refresh-2026-05-15
created_at: '2026-05-15T08:46:38Z'
ttl_days: 14
confidence: episodic
source_refs:
- reports/semantic_pipeline_audit/semantic_pipeline_audit_manifest_2026-05-15.json
summary: 'Checked the 2026-05-15 06:23 architecture-semantic audit against current
  generated semantic artifacts and gates. Current semantic_pipeline_audit_manifest_2026-05-15
  reports 287 clusters, 3248 pair rows, risk LOW=3248 only, no MEDIUM/HIGH/CRITICAL,
  no Normalization=DIFFERENT, no Typing=CONFLICTING, and no Validation=STRICTNESS_MISMATCH.
  Verified DOI pubmed/crossref, UniProt/composite target accession, PubChem/composite
  molecule_id, and assay_id rows are LOW. No new GitHub issues were created because
  the listed findings are stale and already remediated by closed #4124-#4133; open
  issues are unrelated test-surface tasks #4134-#4144.'
---

# Episodic summary

## Task

- Title: Check semantic audit actuality and create current issues

## Outcome

- Checked the 2026-05-15 06:23 architecture-semantic audit against current generated semantic artifacts and gates. Current semantic_pipeline_audit_manifest_2026-05-15 reports 287 clusters, 3248 pair rows, risk LOW=3248 only, no MEDIUM/HIGH/CRITICAL, no Normalization=DIFFERENT, no Typing=CONFLICTING, and no Validation=STRICTNESS_MISMATCH. Verified DOI pubmed/crossref, UniProt/composite target accession, PubChem/composite molecule_id, and assay_id rows are LOW. No new GitHub issues were created because the listed findings are stale and already remediated by closed #4124-#4133; open issues are unrelated test-surface tasks #4134-#4144.

## Lessons learned

- Replace with durable follow-up if needed
