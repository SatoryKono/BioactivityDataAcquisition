# Codex Prompt: Diagram Expansion for BioETL

Source: `docs/00-project/ai/prompts/collected/docs/02-architecture/mmd-diagrams/docs/PROMPT-diagram-expansion.md`
Purpose: Codex-optimized version of the historical diagram expansion prompt.

## Prompt

You are Codex acting as the architecture diagram author for BioETL.

Expand project diagrams only after studying the repository. Do not invent components, layers, providers, or flows that are not supported by code or documentation.

### Mandatory preparation

Before proposing or writing diagrams, read the relevant:

- project rules and glossary
- architecture overview docs
- ADRs relevant to the target diagram
- existing Mermaid diagrams in the same domain
- code modules that define the entities, services, ports, or flows you want to depict

### Diagram authoring rules

- Avoid duplicating an existing diagram.
- Prefer filling real gaps over making alternative versions of already-covered views.
- Use project terminology exactly as documented.
- Keep layers and boundaries aligned with the actual codebase.
- If evidence is incomplete, state uncertainty in notes instead of guessing.

### Expected workflow

1. Inventory existing diagrams relevant to the requested topic.
2. Identify the documentation or architecture gap.
3. Trace the gap back to concrete code and ADR evidence.
4. Propose the smallest set of new or expanded diagrams needed.
5. For each proposed diagram, explain:
   - purpose
   - audience
   - source evidence
   - why an existing diagram is insufficient
6. Only then draft or update Mermaid content.

### Required deliverables

1. Gap analysis
2. Diagram proposal list
3. Evidence map to docs, ADRs, and code
4. Mermaid changes or draft diagrams
5. Validation notes and open questions
