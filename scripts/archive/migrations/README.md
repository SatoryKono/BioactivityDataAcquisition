# Historical Migrations

This directory keeps a very small set of historical one-off migration scripts
that still have audit or upgrade-reference value.

Rules:
- Do not add new migration scripts here.
- New migration entrypoints belong under `scripts/migrations/active/` or
  `scripts/migrations/oneoff/`.
- Files in this directory are retained only for historical reference when no
  canonical replacement exists.
- Repository-local references to files in this directory should not by
  themselves promote these scripts to active operational status in lifecycle
  reporting.
- If a document points here, it should say explicitly that the script is a
  historical migration reference rather than a standard operational path.

Current retained historical migrations:
- `scripts/archive/migrations/migrate_openalex_citation_count.py`
- `scripts/archive/migrations/migrate_pmid_to_string.py`
- `scripts/archive/migrations/rename_structure_fields.py`
