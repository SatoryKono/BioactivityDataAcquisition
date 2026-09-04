---
id: prompt.audit.project.gh-actions-cyclic-1000
version: 1.1.0
status: deprecated
class: operator-paste
owner: BioETL Team
successor: generated/github-actions/audit-readonly.md
summary: Weak 1000x stub retired; use compiled github-actions overlay
---

# Redirect — GH Actions cyclic stub

> **Removed as a weak duplicate.** A 1000-iteration empty loop is not an audit method.
>
> Use [`generated/github-actions/audit-readonly.md`](../../../generated/github-actions/audit-readonly.md)
> and `prompt.tests.fix-retest` for test→fix→retest.

```bash
python -m scripts.ai.prompts compile --domain github-actions --profile audit-readonly
python -m scripts.ai.prompts render prompt.tests.fix-retest
```
