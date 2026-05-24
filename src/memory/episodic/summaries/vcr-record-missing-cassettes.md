---
id: vcr-record-missing-cassettes
title: record-missing-vcr-cassettes
task_id: vcr-record-missing-cassettes
created_at: '2026-05-24T16:38:56Z'
ttl_days: 14
confidence: episodic
source_refs:
- tests/integration/chembl/extraction_params_support.py
summary: Removed ChEMBL extraction-params VCR skip guards, pointed cassette lookup
  at tests/fixtures/vcr/chembl, recorded/verified filtered API cassette playback,
  and ran VCR placement/naming/secrets validation.
---

# Episodic summary

## Task

- Title: record-missing-vcr-cassettes

## Outcome

- Removed ChEMBL extraction-params VCR skip guards, pointed cassette lookup at tests/fixtures/vcr/chembl, recorded/verified filtered API cassette playback, and ran VCR placement/naming/secrets validation.

## Lessons learned

- Replace with durable follow-up if needed
