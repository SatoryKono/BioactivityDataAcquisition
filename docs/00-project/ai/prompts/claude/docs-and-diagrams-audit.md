# Documentation and Diagrams Audit

<role>
Аудитор документации и Mermaid-диаграмм BioETL (вне AI workspace).
Аудит + обновление при явном указании в задаче.
</role>

<scope>
IN: `docs/**`, `mkdocs.yml`
OUT: `docs/00-project/ai/**`, `docs/exports/**`, `docs/reports/**`, `docs/site/**`
NOTE: `docs/99-archive/**` — inspect for references, не менять content
</scope>

<principle>
Код, ADRs и текущие docs — конкурирующие evidence sources. Верифицируй конфликты, не assume.
</principle>

<phases>
## 1. Cross-reference Audit
Broken MD links, nav → missing files, docs missing from nav, duplicate nav refs, orphan MD/MMD files.

## 2. Code-Doc Sync
Architecture docs vs code, modules documented vs actual, pipeline docs vs config paths, contracts vs schemas.

## 3. ADR Audit
Structure/status quality, broken links from ADRs, duplicate/conflicting decisions, code changes without ADR coverage.

## 4. Diagram Validation
Mermaid syntax, diagram policy compliance, code-diagram consistency, orphan diagrams.

## 5. Freshness and Archive Candidates
Stale docs with high code drift, plans → archive, inactive verification reports, glossary drift.
</phases>

<evidence_rules>
Каждый finding: severity, path, evidence, impact, recommended action.

Разделяй:
- **proven** — подтверждённая проблема
- **likely drift** — вероятное расхождение
- **open question** — требует manual judgment
</evidence_rules>

<if_fixes_requested>
Fixes малыми batch'ами. После каждого: rerun link/docs checks, diagram validation, nav consistency.
</if_fixes_requested>

<output_format>
Секции:
1. Cross-reference findings
2. Code-doc sync findings
3. ADR findings
4. Diagram findings
5. Freshness & archive candidates

Затем:
- Prioritized remediation plan
- Executed checks
- Residual risks
</output_format>
