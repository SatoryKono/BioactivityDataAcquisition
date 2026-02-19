# Промпт: Генерация тестов (BioETL)

## Описание

Этот промпт предназначен для написания тестов, соответствующих стандартам BioETL (85% coverage, asyncio, vcr, pytest
markers).

## Промпт (Скопируйте и вставьте агенту):

```markdown
# TASK: Write pytest tests for the following code using BioETL standards.

## TESTING STANDARDS:
1. **Markers**: Use `@pytest.mark.unit` (no I/O, mocks only) or `@pytest.mark.integration` (uses I/O, VCR).
2. **Coverage**: Ensure >=85% branch coverage.
3. **Asyncio**: Use `async def` and `@pytest.mark.asyncio(scope="function")` where appropriate.
4. **VCR**: Use `@pytest.mark.vcr` for tests with HTTP calls.
5. **Types**: Add `-> None` for all test functions.
6. **Imports**: Use `from __future__ import annotations`.
7. **Mocking**: Use `respx` for HTTP mocking in unit tests, or `unittest.mock` for other dependencies.

## STRUCTURE:
- No network in unit tests.
- Use `Hypothesis` for property-based tests of transformations if logic is complex.
- All tests MUST have a clear docstring explaining the "Given/When/Then" logic.

## CODE TO TEST:
[Paste your code here]
```
