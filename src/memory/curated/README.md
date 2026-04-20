# Curated Memory

Curated memory stores promoted, durable project knowledge.

Current curated note families:

- `decisions/`
- `incidents/`
- `lessons/`
- `domain_knowledge/`
- `archive/`

Use the tooling helpers:

```bash
python -m memory.tooling.create_note --kind curated-lesson --title "Example"
python -m memory.tooling.promote_note --source src/memory/episodic/sessions/example.md --target-kind lesson --summary "Durable lesson worth reusing."
python -m memory.tooling.archive_note --source src/memory/curated/lessons/example.md --reason "Superseded by newer guidance."
```

Curated notes are expected to include:

- durable title and `id`
- `kind`
- `source_refs`
- `confidence`
- `last_verified`
- a concise body that captures reusable knowledge
- the required markdown sections for the note kind

Curated memory should grow slowly:

- promote only repeatable, source-backed knowledge
- reject placeholder summaries and placeholder source refs
- avoid duplicate ids and duplicate normalized titles
- archive superseded notes instead of silently overwriting history
