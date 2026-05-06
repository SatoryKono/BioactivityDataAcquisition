---
id: publication-issn-standardization
title: Standardize ISSN fields in publication pipelines
task_id: publication-issn-standardization
created_at: '2026-05-06T09:07:08Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/pipelines
summary: 'Implemented unified publication issn_list support: added shared ISSN scalar/list
  helper, added issn_list to common publication entity/schema/gold contract, populated
  OpenAlex and PubMed issn_list, made Semantic Scholar emit explicit None, updated
  publication configs/field groups, normalization profiles, fixtures, and focused
  tests. Validation: focused transformer/helper tests 8 passed; publication schema/profile
  suite 323 passed; CrossRef/ChemBL publication schema smoke 155 passed; ruff check
  passed. One attempted smoke selector was invalid and rerun with valid suites.'
---

# Episodic summary

## Task

- Title: Standardize ISSN fields in publication pipelines

## Outcome

- Implemented unified publication issn_list support: added shared ISSN scalar/list helper, added issn_list to common publication entity/schema/gold contract, populated OpenAlex and PubMed issn_list, made Semantic Scholar emit explicit None, updated publication configs/field groups, normalization profiles, fixtures, and focused tests. Validation: focused transformer/helper tests 8 passed; publication schema/profile suite 323 passed; CrossRef/ChemBL publication schema smoke 155 passed; ruff check passed. One attempted smoke selector was invalid and rerun with valid suites.

## Lessons learned

- Replace with durable follow-up if needed
