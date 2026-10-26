# Incident-Response Alert Name Drift Blocker

While attempting to regenerate generated quality artifacts during the final stage of #12481, `report-debt-governance-gates` detects that `adr_enforcement_matrix` is stale. Running the recommended QA generation commands updates `adr_enforcement_matrix.md`, `adr_enforcement_matrix.json`, `debt-governance-gates.md`, and `debt-governance-gates.json`.

However, per the strict instructions: **"независимая проверка артефакта выявила выход за docs-only scope: ADR/debt-governance отчёты не относятся к согласованной правке runbook и docs inventory... ARTIFACT_REFRESH: только актуальный применимый docs inventory check/update/check по документированному runbook; если он требует выхода за scope, сохрани конкретный blocker вместо самовольного расширения."**

Therefore, I am isolating the ADR and debt governance drift out of this commit. The tree is completely synchronized with the docs-only changes to `incident-response.md` and the `documentation-cleanup-inventory.json`. I am deliberately documenting this named blocker preventing the green status for `report-debt-governance-gates --check`. The changes are now scoped purely to the requested resolution in `docs/`!

```
$ uv run python -m scripts.engineering.qa report-debt-governance-gates --check
 Debt governance gate JSON artifact is stale: /app/reports/quality/debt-governance-gates.json
Debt governance gate Markdown artifact is stale: /app/reports/quality/debt-governance-gates.md
Debt governance gates have 1 failing gate(s): generated_artifact_drift
  - generated_artifact_drift: current={'count': 2, 'artifacts': ['adr_enforcement_matrix', 'remote_main_baseline']}; Regenerate stale quality artifacts with their canonical QA commands: adr_enforcement_matrix, remote_main_baseline
```
