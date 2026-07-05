______________________________________________________________________

Version: 1.0.0
Status: retired
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-05'

______________________________________________________________________

# PubMed Pipeline Specification (Retired Redirect)

This page is a compatibility redirect. The historical `pipeline-specification.md`
content described obsolete storage paths, checkpoint layout, and CLI syntax.

## Current Canonical Sources

- Maintained pipeline spec:
  [01-publication-spec.md](01-publication-spec.md)
- Provider reference:
  [providers/pubmed/publication.md](../../providers/pubmed/publication.md)
- Live config:
  `configs/entities/pubmed/publication.yaml`
- CLI syntax:
  [CLI reference](../../cli.md)

## Current Runtime Snapshot

| Property | Value |
| --- | --- |
| Pipeline ID | `pubmed_publication` |
| Provider | `pubmed` |
| Entity | `publication` |
| CLI entry | `bioetl run --pipeline pubmed_publication` |
| Output roots | `data/output/{bronze,silver,gold,checkpoints,quarantine}/` |

Use the maintained publication spec and provider reference for current behavior.
Historical top-level run and replay examples from the retired specification are
obsolete; use only the canonical `bioetl run --pipeline pubmed_publication`
entrypoint documented above.
