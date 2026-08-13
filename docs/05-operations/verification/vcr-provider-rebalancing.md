______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# VCR Provider Rebalancing (RF-013)

> **Status:** Historical verification and operations artifact (non-normative).
> Use this note as dated workflow evidence only; current policy source of truth remains `docs/00-project/RULES.md`, active ADRs, and current test architecture/docs.

## Goal

Maintain balanced VCR cassette coverage across bibliography providers.

- OpenAlex: `>= 20` cassettes
- PubMed: `>= 20` cassettes
- SemanticScholar: `>= 20` cassettes
- CrossRef: `>= 20` cassettes

## Prerequisites

```bash
uv sync --frozen --extra dev --extra tests --extra tracing
```

## Record Commands (Provider-Specific)

Use `new_episodes` mode to create missing cassettes without rewriting existing ones.

```bash
VCR_RECORD_MODE=new_episodes uv run python -m pytest -q tests/integration/adapters/test_openalex_vcr_rebalance.py
VCR_RECORD_MODE=new_episodes uv run python -m pytest -q tests/integration/adapters/test_pubmed_vcr_rebalance.py
VCR_RECORD_MODE=new_episodes uv run python -m pytest -q tests/integration/adapters/test_semanticscholar_vcr_rebalance.py
VCR_RECORD_MODE=new_episodes uv run python -m pytest -q tests/integration/adapters/test_crossref_vcr_rebalance.py
```

## Playback Validation

Run in strict playback mode after recording:

```bash
VCR_RECORD_MODE=none uv run python -m pytest -q \
  tests/integration/adapters/test_openalex_vcr_rebalance.py \
  tests/integration/adapters/test_pubmed_vcr_rebalance.py \
  tests/integration/adapters/test_semanticscholar_vcr_rebalance.py \
  tests/integration/adapters/test_crossref_vcr_rebalance.py
```

## Secret-Safety Validation

```bash
uv run python -m pytest -q tests/security/test_security.py
```

## Coverage Verification

```bash
uv run python -m pytest -q tests/architecture/test_vcr_provider_balance.py
```

Quick count helper:

```bash
for p in openalex pubmed semanticscholar crossref; do
  c=$(find tests/fixtures/vcr/$p -type f \( -name "*.yaml" -o -name "*.yml" \) | wc -l)
  echo "$p $c"
done
```

## Operational Policy

- Record new cassettes with deterministic test names.
- Never commit real credentials or personal emails.
- Prefer `query_ignore_email` matcher for providers requiring email parameters.
- Re-run playback validation and security checks before merging.
