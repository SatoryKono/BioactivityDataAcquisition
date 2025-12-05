> Scope:
> - USE WHEN adding logging; require UnifiedLogger, structured events, redaction, run context
> - Use when editing files matching: `src/**/*.py`
# Logging rules

## Mandatory

- Use `UnifiedLogger` only; no `print()` or stdlib `logging` in production code.
- Set run context at process/pipeline start; mandatory fields auto-injected (run_id, pipeline, stage, timestamp_utc).
- Redact secrets and sensitive identifiers.

## Levels

DEBUG, INFO (default), WARNING, ERROR, CRITICAL; include counts, durations, IDs.

## Example

```python
log.info("Extraction completed", source="chembl", rows=len(df), duration_ms=elapsed)
```

## Reference

See [docs/styleguide/02-logging-guidelines.md](../../docs/styleguide/02-logging-guidelines.md) for detailed documentation.
