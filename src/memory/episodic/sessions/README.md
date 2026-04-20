# Episodic Sessions

Short-lived task or session notes belong here.

Expected metadata for machine-managed notes:

- `created_at`
- `ttl_days`
- `task_id`

Expired notes can be reported or removed with:

```bash
python -m memory.tooling.prune
python -m memory.tooling.prune --apply
```
