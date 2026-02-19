# Промпт: Проектирование схем данных (BioETL)

## Описание

Этот промпт предназначен для создания Pandera и Pydantic схем с учетом детерминизма и строгой типизации.

## Промпт (Скопируйте и вставьте агенту):

```markdown
# TASK: Create a Pandera/Pydantic schema for the following data structure.

## SCHEMA STANDARDS:
1. **Pandera (`src/bioetl/domain/schemas`)**:
   - MUST use `pa.DataFrameModel`.
   - Fixed column order (critical for determinism).
   - Strict typing (`pa.Int64`, `pa.String`, etc.).
   - Mandatory checks for unique IDs and NOT NULL where applicable.
2. **Pydantic (`src/bioetl/infrastructure/schemas`)**:
   - Use `BaseModel` with `ConfigDict(extra="forbid")`.
   - Use `SecretStr` for sensitive data.
   - Use `field_validator` for custom validation.

## RULES:
- Deterministic sorting: Always specify sort columns.
- Validate-before-write: No writes without prior schema validation.
- UTC for all datetime fields.

## DATA DESCRIPTION:
[Paste your fields, samples, or requirements here]
```
