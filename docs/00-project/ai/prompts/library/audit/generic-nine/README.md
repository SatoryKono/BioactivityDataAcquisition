______________________________________________________________________

Version: 1.0.0
Status: active
Class: internal (repo-only index; not a paste card)
Owner: BioETL Team
Last verified: '2026-08-13'
Source kit: 2026-08-11 07:12 BST

______________________________________________________________________

# Generic nine-prompt audit kit

One-shot evidence-based audits of nine project surfaces. Not runtime SSOT.
Full generic megaprompt (opt-in):
`archive/campaigns/generic-nine-audit-kit-2026-08.md`.

| # | Id | Card | Domain |
| --- | --- | --- | --- |
| 1 | `prompt.audit.docs-content` | [../docs-content.md](../docs-content.md) | Documentation content / drift |
| 2 | `prompt.audit.tests-system` | [../tests-system.md](../tests-system.md) | Test system / CI gates |
| 3 | `prompt.audit.tech-debt` | [../tech-debt.md](../tech-debt.md) | Technical debt register |
| 4 | `prompt.audit.repo-tree` | [../repo-tree.md](../repo-tree.md) | Root / tree hygiene |
| 5 | `prompt.audit.github-actions` | [../github-actions.md](../github-actions.md) | GitHub Actions supply chain |
| 6 | `prompt.audit.agents-runtime` | [../agents-runtime.md](../agents-runtime.md) | Agents, skills, agent scripts |
| 7 | `prompt.audit.diagrams` | [../diagrams.md](../diagrams.md) | Diagrams + render scripts |
| 8 | `prompt.audit.docs-pipeline` | [../docs-pipeline.md](../docs-pipeline.md) | Docs build/publish pipeline |
| 9 | `prompt.architecture.review` | [../../architecture/review-assessment.md](../../architecture/review-assessment.md) | Architecture (C4 / arc42) |
| — | `prompt.audit.generic-nine.pack` | [pack.md](pack.md) | Routing card |

Domains are **independent**. `#1` (content) and `#8` (pipeline) must not
substitute for each other.

```powershell
.\.venv-win\Scripts\python.exe -m scripts.ai.prompts render prompt.audit.generic-nine.pack `
  --param SCOPE=. --param MODE=audit --param LANGUAGE=ru
```

Cyclic / fix loops: `prompt.audit.cyclic-pack` → `prompt.audit.cycle.*`.
Grafana dashboards: `prompt.observability.grafana-six.pack`.
