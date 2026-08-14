# Documentation source-of-truth map

| Claim family | Source | Generator / checker | Artifact / consumer |
| --- | --- | --- | --- |
| Runtime governance | `AGENTS.md`, `.codex/**`, `.junie/**` | `scripts.docs check-drift` | Published mirrors |
| Project rules version | `docs/00-project/RULES.md` header | `scripts.engineering.repo check-versions` | `docs/00-project/index.md`, CI |
| Published navigation | `mkdocs.yml` | `scripts.docs check-links`, MkDocs | GitHub Pages site |
| Documentation lifecycle | `NORMATIVE_SOURCES.md` DOC-GOV-09 | `scripts.docs generate-cleanup-inventory` | generated cleanup JSON/Markdown |
| Navigation KPI | `report_docs_kpi.py` policy plus tracked baseline | `scripts.docs check-kpi` | weekly JSON/Markdown and job summary |
| Prompt methods | `docs/00-project/ai/prompts/library/**` | prompt library validators / docs checks | repo operators; not runtime SSOT |
