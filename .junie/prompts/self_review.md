# Промпт: Самопроверка и Аудит (BioETL)

## Описание

Этот промпт предназначен для проведения аудита предложенного решения на соответствие инвариантам проекта.

## Промпт (Скопируйте и вставьте агенту):

```markdown
# TASK: Audit the following code/plan against BioETL Project Invariants.

## INVARIANTS CHECKLIST:
1. **Determinism**: Identical inputs produce bit-identical outputs.
   - Fixed column order? Stable sort? UTC timestamps?
2. **Logging**: Structured only? UnifiedLogger used? `run_context` bound? No `print()`?
3. **Validation**: Validate-before-write? Schema check before every write?
4. **Architecture**: No domain-to-infra imports? Proper layering?
5. **Testing**: Fast unit tests? >=85% coverage? Integration tests with VCR?
6. **Error Handling**: Fail-fast on missing config/secrets? No sentinel values?
7. **Secrets**: Pydantic Config for secrets? No hardcoded keys?

## AUDIT THE FOLLOWING:
[Paste your code, plan, or PR description here]
```
