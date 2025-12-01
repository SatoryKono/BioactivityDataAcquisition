# 00 - Documentation Naming Conventions

This document outlines the standard naming conventions for documentation files
within the `bioetl` project. Following these conventions ensures consistency and
predictability in the documentation structure.

## 1. General Principles

- **Language**: All filenames **MUST** be in English.
- **Case**: All filenames **MUST** be in `lowercase`.
- **Separators**: Words in filenames **MUST** be separated by hyphens (`-`).
  **Underscores (`_`) MUST NOT be used** in documentation filenames.

> Rationale: hyphen-separated filenames (kebab-case) ensure deterministic
> ordering and compatibility with the docs tooling. This is the canonical rule
> for documentation filenames and overrides any conflicting fragment that
> suggests using underscores.

### 1.1. Pipeline Documentation File Naming

**Format**: `NN-<entity>-<provider>-<topic>.md`

Pipeline documentation files **MUST** follow this canonical naming convention:

- `NN`: Two-digit sequential number (`00`–`99`) for stable sorting and ordering.
- `entity`: Domain entity name (`activity`, `assay`, `target`, `document`, `testitem`) — **kebab-case in filenames**, canonical id for code/configs is `snake_case` (see §1.3).
- `provider`: Data provider identifier (`chembl`, `pubchem`, `iuphar`, `pubmed`, `crossref`, `openalex`, `semantic-scholar`).
- `topic`: Fixed token for the documentation section (see table below).

**Example**: `09-document-chembl-extraction.md`.

#### 1.1.1. Topic Tokens and Stage/Contract Mapping

| Architecture/Stage    | Topic Token      | Notes                                             |
| --------------------- | ---------------- | ------------------------------------------------- |
| extract               | `extraction`     | Matches pipeline `extract` stage                  |
| transform             | `transformation` | Matches pipeline `transform` stage                |
| validate (Pandera)    | `validation`     | Version/column freeze policy                      |
| write / I/O           | `io`             | Format, stable sort-keys, atomic write            |
| run (orchestration)   | `run`            | If a separate file is needed                      |
| determinism & lineage | `determinism`    | `hash_row`, `hash_business_key`, `meta.yaml`, UTC |
| QC/QA & golden tests  | `qc`             | Metrics and thresholds                            |
| logging/tracing       | `logging`        | Format and mandatory fields                       |
| cli                   | `cli`            | Exact commands and exit-codes                     |
| configuration         | `config`         | Keys/profiles/defaults                            |
| schema (Pandera)      | `schema`         | `schema_id/version`, dtypes                       |

#### 1.1.2. File-level rules

- The H1 heading **MUST** duplicate the filename in Title Case (example: `# 09 Document ChEMBL Extraction`).
- Internal anchors are derived from second-level headings (`##`) and **MUST** be kebab-case.
- All relative links **MUST** pass the project's link-checker (`.lychee.toml`).
- Auto-generated sections **MUST** be marked: `<!-- generated -->`.

### 1.2. Sequenced Content Documents

Documents that are part of a logical sequence **SHOULD** be prefixed with a two-digit number (`NN-`).

- **Format**: `NN-topic-name.md`
- **Examples**:
  - `docs/cli/00-cli-overview.md`
  - `docs/cli/01-cli-commands.md`
  - `docs/qc/02-golden-tests.md`

### 1.3. Canonical identifiers for code / configs vs. docs filenames

- **Code / configs**: provider and entity canonical identifiers **MUST** use `snake_case` and match `^[a-z0-9_]+$`. Canonical list SHOULD be stored in `configs/providers.yaml` and `configs/entities.yaml`.
- **Docs filenames**: provider and entity parts **MUST** use kebab-case and hyphens: e.g. provider `semantic_scholar` (code) → docs folder/file name `semantic-scholar`.
- This separation avoids ambiguity between filesystem naming for docs (kebab) and code/config identifiers (snake).

### 1.4. Index and Landing Page Documents

Primary index files or landing pages for a directory **SHOULD** be named `INDEX.md` or `README.md`.
They **SHOULD NOT** have a numeric prefix.

- **Format**: `INDEX.md` or `OVERVIEW.md`

### 1.5. README Files

`README.md` files **SHOULD** be used as landing pages for specific subdirectories to provide a brief overview.

## 2. Summary of Conventions

| Document Type      | Naming Convention           | Example                 |
| ------------------ | --------------------------- | ----------------------- |
| Sequenced Content  | `NN-topic-name.md`          | `01-metrics-catalog.md` |
| Pipeline doc       | `NN-<entity>-<provider>-<topic>.md` | `05-assay-chembl-extraction.md` |
| Main Index File    | `INDEX.md`                  | `docs/INDEX.md`         |
| Directory Overview | `README.md`                 | `README.md`             |

## 3. References & Cross-links

- The canonical rules for pipeline code layout and pipeline names are defined in the repository naming policy and pipelines architecture (see `02-new-entity-naming-policy.md` and `docs/pipelines/00-pipeline-base.md`).
- New entity-specific naming rules are defined in `02-new-entity-naming-policy.md` and should be followed for any new provider/entity introduced in the project.
