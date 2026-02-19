# Промпт: Рефакторинг под Hexagonal Architecture (BioETL)

## Описание

Этот промпт предназначен для проверки и исправления нарушения границ слоев в проекте BioETL.

## Промпт (Скопируйте и вставьте агенту):

```markdown
# TASK: Refactor the following code to adhere to the BioETL Hexagonal Architecture.

## CORE RULES:
1. **Domain Layer (`src/bioetl/domain`)**: MUST be pure logic. 
   - NO I/O, NO databases, NO HTTP calls.
   - NO imports from `infrastructure` or `application`.
   - Use Protocols (Ports) for any external dependency.
2. **Application Layer (`src/bioetl/application`)**: Orchestration only.
   - Depends on `domain`. 
   - NO direct infrastructure calls. Use Ports defined in `domain`.
3. **Infrastructure Layer (`src/bioetl/infrastructure`)**: Adapters (implementation of Ports).
   - Can depend on `domain` and `application`.
   - Implements HTTP clients, storage writers, etc.
4. **Composition Layer (`src/bioetl/composition`)**: Dependency injection root.
   - Assembles all components.

## INSTRUCTIONS:
- Identify layer violations (e.g., `import bioetl.infrastructure` inside `bioetl.domain`).
- Move implementation details to `infrastructure`.
- Define Protocols in `domain` for abstract dependencies.
- Ensure all logic is covered by unit tests (fast, no I/O).

## CODE TO ANALYZE:
[Paste your code here]
```
