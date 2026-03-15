# Expand RF-006 and RF-008 into Execution Backlog

<role>
Refactor planner для BioETL инициатив RF-006 и RF-008.
Strategy-level intent → implementation backlog. Код НЕ менять.
</role>

<constraints>
- Read-only analysis
- Сохраняй intent и non-goals из source plans
- Не вводи speculative redesigns без evidence из репозитория
</constraints>

<per_rf_output>
1. Objective
2. Non-goals
3. Target files and modules
4. Execution order
5. Task breakdown (stable IDs)
6. Characterization tests
7. Unit/integration/architecture checks
8. Risks + mitigations
9. Exit criteria
</per_rf_output>

<rf006_focus>
- Dependency coordinator seams
- Runtime factory decomposition
- Runner остаётся thin
- Characterization coverage ПЕРЕД movement
</rf006_focus>

<rf008_focus>
- Сначала trustworthy high-level test signal
- Thin `run_all.py`
- Remove hidden composition из provider clients
- Align OpenAlex/CrossRef patterns без needless churn
</rf008_focus>

<final_section>
Combined dependency-aware roadmap: какие RF-006 и RF-008 tasks параллельны, какие sequential.
</final_section>
