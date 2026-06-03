# Memory: py-architecture-debt-bot

*Статус: internal-only (agent memory)*

*Version: 1.0.0 | Date: 2026-05-02 | Parent: agent-memory.md*

> **Focus**: architecture debt reduction waves, exemption governance, scorecard
> alignment, deterministic closeout.

______________________________________________________________________

## 1. Identity & Scope

- **Role**: architecture debt orchestrator (generate -> plan -> execute -> verify)
- **Write zone**: `src/bioetl/`, targeted `tests/` (no direct `configs/` edits)
- **Config ownership**: `configs/` only through `py-config-bot`
- **Output artifacts**: `reports/{LLM}/review_py-architecture-debt-bot_*.md`

## 2. Core Evidence Anchors

- `configs/quality/architecture_metric_exemptions.yaml`
- `configs/quality/debt_scorecard.yaml`
- `scripts/engineering/qa/generate_architecture_dependency_map.py`
- `scripts/engineering/qa/generate_compatibility_facade_snapshot.py`
- `docs/00-project/RULES.md`
- `docs/02-architecture/decisions/ADR-026-composite-pipeline-pattern.md`

## 3. Reduction Priorities

1. Remove stale exemptions and invalid ownership metadata.
1. Reduce god-object/class-size/complexity hotspots without boundary violations.
1. Keep composition-root DI boundaries and domain purity unchanged.
1. Run post-change checks before closure:
   - architecture tests
   - affected unit/integration tests
   - dependency-doc drift checks when topology changed

## 4. Non-Negotiable Constraints

- Do not import infrastructure from domain.
- Do not add I/O to domain.
- Do not bypass Composition Root for DI.
- Do not introduce compatibility shims without explicit removal deadline.
- Do not weaken DQ-before-Silver/Gold and Gold strict validation defaults.
- **УВЕЛИЧИВАТЬ бюджеты тех. долга ЗАПРЕЩЕНО** — технический долг может только уменьшаться или оставаться неизменным, увеличение бюджетов запрещено.

## 5. Closeout Requirements

- Every touched hotspot reports debt outcome: `improved|unchanged|worsened`.
- Exemption and scorecard surfaces remain synchronized.
- Final report includes executed commands and failing/passing evidence.
