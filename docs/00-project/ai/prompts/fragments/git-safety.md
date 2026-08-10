---
id: prompt.fragment.git-safety
version: 1.0.0
status: active
class: fragment
owner: BioETL Team
summary: Git and worktree safety for operator sessions
---

## Git / safety

- Do not edit or delete others' uncommitted work
- No `reset --hard`, no force-push
- Never commit to `main`; use `fix/<slug>` (or worktree if main is dirty)
- Push feature branch only; open PR to `main`
- Prefer evidence-only close when product root cause is already fixed on origin/main
