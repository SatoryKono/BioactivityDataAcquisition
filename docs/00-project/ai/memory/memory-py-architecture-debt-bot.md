# Memory: py-architecture-debt-bot

*Статус: internal-only (agent memory)*

*Version: 1.0.1 | Date: 2026-07-24 | Parent: agent-memory.md*

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

## 4. Governance hash closeouts (after src/bioetl writes)

Stale-hash architecture tests (examples: #5752 evidence surface, #6027 topology
SUMMARY, test-telemetry `source_tree_sha256`) require coordinated refresh — not
budget increases:

1. `python -m scripts.engineering.qa.report_module_coverage_inventory --allow-missing-coverage-xml`
1. Update `docs/reports/evidence/project-package-topology/SUMMARY.md` to match
   inventory `source_module_count` + `source_tree_sha256`
1. `python -m scripts.engineering.qa.report_debt_governance_gates`
1. Recompute and pin `evidence_surface_sha256` in
   `configs/quality/technical_debt_audit_registry.yaml` **and** the current
   audit report marker (pin **after** the last evidence-path write)
1. If `tests/**` changed: pin
   `configs/quality/test_telemetry_baseline.yaml` via
   `compute_test_telemetry_source_tree_sha256()` and sync
   `reports/test-telemetry/{slowest-tests,coverage-summary}.json`

Lesson: `src/memory/curated/lessons/run-reports-and-governance-hash-refresh.md`

## 5. Non-Negotiable Constraints

- Do not import infrastructure from domain.
- Do not add I/O to domain.
- Do not bypass Composition Root for DI.
- Do not introduce compatibility shims without explicit removal deadline.
- Do not weaken DQ-before-Silver/Gold and Gold strict validation defaults.
- **ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.** Это включает budgets,
  exemption limits, hotspot thresholds и family caps.

## 5. Closeout Requirements

- Every touched hotspot reports debt outcome: `improved|unchanged|worsened`.
- Exemption and scorecard surfaces remain synchronized.
- Final report includes executed commands and failing/passing evidence.
