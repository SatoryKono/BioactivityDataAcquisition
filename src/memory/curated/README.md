# Curated Memory

Curated memory stores promoted, durable project knowledge.

Current curated note families:

- `decisions/`
- `incidents/`
- `lessons/`
- `domain_knowledge/`

Use the tooling helpers:

```bash
python -m memory.tooling.create_note --kind curated-lesson --title "Example"
python -m memory.tooling.promote_note --source src/memory/episodic/sessions/example.md --target-kind lesson
```

Curated notes are expected to include:

- durable title and `id`
- `kind`
- `source_refs`
- `confidence`
- `last_verified`
- a concise body that captures reusable knowledge
