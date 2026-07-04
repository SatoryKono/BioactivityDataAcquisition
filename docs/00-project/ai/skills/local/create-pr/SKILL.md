> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source:
> - Codex: `.codex/skills/create-pr/SKILL.md`
> Governance: [AI Runtime Mirror Ownership](../../../agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md), [Memory Usage](../../../agents/guides/MEMORY_USAGE.md), [Post-Change Validation](../../../agents/policy/POST_CHANGE_VALIDATION.md).
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

## name: create-pr description: "Creates GitHub PRs with Conventional Commits titles adapted for BioETL project." context: none agent: general-purpose

# Create Pull Request

Creates GitHub PRs with Conventional Commits titles adapted for BioETL project.

## BioETL Runtime Policy

- Project runtime contract: `../../../AGENTS.md`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

## PR Title Format

```
<type>(<scope>): <summary>
```

### Types (required)

| Type       | Description                         | Changelog |
| ---------- | ----------------------------------- | --------- |
| `feat`     | New feature / pipeline / adapter    | Yes       |
| `fix`      | Bug fix                             | Yes       |
| `perf`     | Performance improvement             | Yes       |
| `refactor` | Code change (no bug fix or feature) | No        |
| `test`     | Adding/correcting tests             | No        |
| `docs`     | Documentation only                  | No        |
| `build`    | Build system or dependencies        | No        |
| `ci`       | CI configuration / workflows        | No        |
| `chore`    | Routine tasks, maintenance          | No        |

### Scopes (optional but recommended)

**By provider:**

- `chembl` - ChEMBL adapter/pipeline
- `pubchem` - PubChem adapter/pipeline
- `pubmed` - PubMed adapter/pipeline
- `opentargets` - Open Targets adapter/pipeline
- `fda` - FDA adapter/pipeline

**By layer:**

- `domain` - Domain layer (ports, entities, types)
- `application` - Application layer (services, use cases)
- `infrastructure` - Infrastructure layer (adapters, storage)
- `composition` - Composition root (bootstrap, factories)
- `interfaces` - CLI, API interfaces

**By feature:**

- `tests` - Test infrastructure
- `configs` - YAML configurations
- `schemas` - Pandera schemas (Silver/Gold)
- `dq` - Data quality rules
- `diagrams` - Mermaid diagrams
- `storage` - Delta Lake / Bronze / Silver / Gold
- `observability` - Logging, metrics, tracing

### Summary Rules

- Use imperative present tense: "add" not "added"
- Lowercase first letter
- No period at the end
- Keep under 72 characters total

## Steps

1. **Check current state**:

   ```bash
   git status
   git diff --stat
   git log origin/main..HEAD --oneline
   ```

1. **Analyze changes** to determine:

   - Type: What kind of change is this?
   - Scope: Which provider/layer/feature is affected?
   - Summary: What does the change do?

1. **Run checks before PR**:

   ```bash
   make lint
   make test
   pytest tests/architecture/ -v
   ```

1. **Push branch if needed**:

   ```bash
   git push -u origin HEAD
   ```

1. **Create PR** using gh CLI:

   ```bash
   gh pr create --draft --title "<type>(<scope>): <summary>" --body "$(cat <<'EOF'
   ## Summary

   <Brief description of what this PR does>

   ## Changes

   - <change 1>
   - <change 2>

   ## Checklist

   - [ ] `make lint` passes
   - [ ] `make test` passes
   - [ ] No hardcoded secrets or credentials
   - [ ] Architecture tests pass (`pytest tests/architecture/ -v`)
   - [ ] Documentation updated if behavior changed
   - [ ] Follows Conventional Commits format
   EOF
   )"
   ```

## Examples

### New pipeline

```
feat(chembl): add mechanism pipeline with Silver/Gold schemas
```

### Bug fix in adapter

```
fix(pubchem): handle rate limit 429 response
```

### Refactoring infrastructure

```
refactor(infrastructure): extract common HTTP retry logic
```

### Schema changes

```
feat(schemas): add PublicationBaseSchema for cross-provider fields
```

### Config updates

```
chore(configs): update DQ rules for pubmed publication dates
```

### Performance optimization

```
perf(storage): optimize Delta Lake merge for large datasets
```

### Documentation

```
docs: update architecture diagrams for medallion flow
```

### Tests

```
test(chembl): add VCR cassettes for activity endpoint
```

### Breaking change

```
feat(domain)!: redesign DataSourcePort async generator interface
```

### No scope (affects multiple areas)

```
refactor: standardize error handling across all adapters
```

## Validation

The PR title must match this pattern:

```
^(feat|fix|perf|test|docs|refactor|build|ci|chore|revert)(\([a-zA-Z0-9_]+\))?!?: .+[^.]$
```

Key validation rules:

- Type must be one of the allowed types
- Scope is optional but must be in parentheses if present
- Exclamation mark for breaking changes goes before the colon
- Summary must not end with a period

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

