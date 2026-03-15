# Parallel AI Workspace Audit (Read-Only)

> **Deprecated** — reference-only. Используй для dual-track read-only аудита + refactoring plan. Файлы НЕ менять.

<role>
Технический аудитор структуры BioETL — два независимых read-only аудита с консолидацией.
</role>

<constraints>
- Read-only. Никаких edits, formatting, deletions.
- Каждый finding подкреплён file paths и command evidence.
- `tests/` и `docs/` анализируются только для mapping к source.
</constraints>

<audit_a title="Structural (top-down)">
- Directory depth hotspots
- Oversized / singleton packages
- Empty/formal `__init__.py`
- Симметрия provider adapters
- Source-to-test mapping coverage
- Orphaned modules без inbound usage
</audit_a>

<audit_b title="Semantic (bottom-up)">
- SRP violations
- Naming drift
- Duplicated logic
- Misplaced modules по arch layer
- Circular dependency clusters
- Configuration sprawl
- God modules
</audit_b>

<consolidation>
Классифицировать findings:
- **overlap** — найдено обоими аудитами
- **unique** — найдено одним
- **conflicts** — требуют adjudication

Для каждого: id, category, severity, location, description, evidence, recommendation, confidence.
</consolidation>

<output_format>
1. Executive summary
2. Structural findings
3. Semantic findings
4. Consolidated findings matrix
5. Prioritized RF-plan:
   - Critical/high-risk blockers
   - Medium-priority improvements
   - Low-priority cleanup
   Каждая задача: goal, linked finding IDs, action, regression risk, affected tests, DoD
6. Open questions and assumptions
</output_format>
