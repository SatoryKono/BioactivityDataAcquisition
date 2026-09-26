# Iteration 6 — composite join identifiers

## Evidence

- `.codex/agents/py-config-bot.md:46-48` requires stable identifier join keys
  and forbids `title` as the primary join key.
- `configs/composites/publication.yaml:101-109` declares `doi` and `pmid` as
  primary join keys and `title` as fallback only.
- `src/bioetl/domain/composite/config_models.py:174-181` defines the first
  configured key as `primary_join_key`; all publication enrichers place `doi`
  or `pmid` first.
- `tests/integration/config/test_semantic_field_unification_contract.py:145-155`
  and `tests/unit/config/test_non_chembl_composite_boundary_policy.py:101-108`
  pass and enforce the intentional fallback policy.
- Closed issue #3907 documents the same DOI/PMID-first, title-fallback contract.

The lower-precedence external checklist wording `never title` is broader than
the active profile. Changing the config would remove a governed fallback and
break accepted tests, so no config mutation was made.

## Result

PASS against the canonical runtime profile. Out-of-scope prompt wording
observation recorded in the final report. No config finding.
