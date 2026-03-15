# Scripts Inventory and Consolidation Analysis (Read-Only)

<role>
Script-layer аудитор BioETL. Read-only inventory и consolidation analysis.
</role>

<scope>
`scripts/**`, `src/tools/**`
</scope>

<constraints>
- НЕ модифицировать файлы
- Каждый вывод подкреплён path-based evidence
- Unknown usage → маркировать явно, не придумывать call sites
- Не рекомендуй deletion без backward-compatibility checks
- Учитывай возможность external agent orchestration usage
</constraints>

<audit>
Для каждого скрипта:
- Purpose, invocation context, invocation pattern
- Caller/owner, agent/skill usage
- Lifecycle status, risks

Detect: duplicates, orphans, poor placement/naming, arch/governance drift.
</audit>

<evidence_sources>
Read-only: `AGENTS.md`, `.codex/skills/**`, CI/workflow definitions, `pyproject.toml`/`Makefile`/`noxfile`/`justfile`/`tox.ini`, docs и tests referencing scripts.
</evidence_sources>

<output_format>
1. Executive summary
2. Inventory: `Script Path | Type | Purpose | Invocation | Caller/Owner | Agent Usage | Status | Evidence`
3. Agent-usage matrix
4. Issues by severity
5. Consolidation plan by phase
6. Removal candidates
7. Consolidation candidates
8. Roadmap (2-4 iterations)
9. Maturity score 0-10 + highest-ROI next actions
</output_format>
