# Reproducibility Audit Standards

## Purpose

This document defines the standards and requirements for reproducibility audits in the BioETL project. Reproducibility is a core invariant - all code changes must maintain deterministic behavior and replay capability.

## Core Principles

1. **Determinism**: All operations must produce identical results given identical inputs
2. **Replay Capability**: Code must be executable in different environments with the same outcome
3. **Test Coverage**: All code paths must have adequate test coverage
4. **Schema Validation**: All data must pass schema validation before processing
5. **Structured Logging**: All logging must use structured formats without secrets

## Determinism Requirements

### DataFrame Operations

All DataFrame operations must use stable sorting:

```python
# BAD: Non-deterministic
result = df.head(10)
result = df.sample(frac=0.1)

# GOOD: Deterministic
result = df.sort_values('id').head(10)
result = df.sort_values('id').sample(frac=0.1, random_state=42)
```

### Timestamp Handling

All timestamps must be in UTC:

```python
# BAD: Non-deterministic
timestamp = datetime.now()
timestamp = datetime.utcnow()

# GOOD: Deterministic
timestamp = datetime.now(timezone.utc)
```

### Random Operations

All random operations must use seeds:

```python
# BAD: Non-deterministic
value = random.random()
array = np.random.rand(10)

# GOOD: Deterministic
random.seed(42)
value = random.random()
np.random.seed(42)
array = np.random.rand(10)
```

### Iteration Stability

All iterations must be sorted:

```python
# BAD: Non-deterministic
for key in my_dict.keys():
    ...

# GOOD: Deterministic
for key in sorted(my_dict.keys()):
    ...
```

### File System Operations

All file system operations must be sorted:

```python
# BAD: Non-deterministic
files = os.listdir('data/')
files = glob.glob('data/*.csv')

# GOOD: Deterministic
files = sorted(os.listdir('data/'))
files = sorted(glob.glob('data/*.csv'))
```

## I/O Requirements

### Atomic Writes

All writes must be atomic:

```python
# BAD: Non-atomic
with open('output.json', 'w') as f:
    json.dump(data, f)

# GOOD: Atomic
write_dataset_atomic(data, 'output.json')
```

### File Operations

All file operations must use deterministic ordering:

```python
# BAD: Non-deterministic
for file in os.listdir('data/'):
    process(file)

# GOOD: Deterministic
for file in sorted(os.listdir('data/')):
    process(file)
```

## Test Coverage Requirements

### Coverage Thresholds

| Component Type | Minimum Coverage | Critical Path |
| -------------- | ---------------- | ------------- |
| New functions | 80% | 100% |
| New classes | 75% | 100% |
| Error handling | 90% | 100% |
| Integration | 70% | 100% |

### Test Types Required

- **Unit tests**: For individual functions and methods
- **Integration tests**: For workflows and pipelines
- **Edge case tests**: For boundary conditions
- **Error handling tests**: For exception paths

## Schema Validation Requirements

### Schema Definition

All data structures must have Pandera schemas:

```python
# GOOD: Schema defined
class ActivitySchema(pa.DataFrameModel):
    activity_id: Series[str]
    standard_type: Series[str]
    standard_value: Series[float]
```

### Schema Validation

All data must be validated before processing:

```python
# GOOD: Schema validated
df = schema.validate(df)
```

### Schema Evolution

Schema changes must be documented with:
- Version bump
- Migration plan
- Backward compatibility analysis
- Consumer impact assessment

## Logging Requirements

### Structured Logging

Only `UnifiedLogger` must be used:

```python
# BAD: Unstructured
print("Processing data")

# GOOD: Structured
logger.info("Processing data", context={"stage": "processing"})
```

### Context Binding

All logs must have context:

```python
# GOOD: Context bound
bind_pipeline_context(pipeline_code="chembl_activity", run_id="test-123")
pipeline_stage("processing")
```

### Secret Protection

No secrets in logs:

- No API keys
- No passwords
- No tokens
- No PII

## Environment Requirements

### Dependency Pinning

All dependencies must be version-pinned:

```python
# BAD: Floating range
pandas>=1.0.0

# GOOD: Pinned
pandas==1.5.3
```

### Security

All dependencies must pass security scan:
- No known vulnerabilities
- No deprecated packages
- No malicious packages

### Configuration

Configuration must be via environment variables:
- `.env` files not committed
- Secrets in environment variables
- Configuration documented

## Audit Checklist

### Determinism

- [ ] All DataFrame operations use stable sorting
- [ ] All timestamps are in UTC
- [ ] All random operations use seeds
- [ ] All iterations are sorted
- [ ] All file system operations are sorted

### I/O

- [ ] All writes are atomic
- [ ] All file operations use deterministic ordering
- [ ] Network calls have retry logic
- [ ] Database operations use transactions

### Test Coverage

- [ ] New functions have ≥80% coverage
- [ ] New classes have ≥75% coverage
- [ ] Critical paths have 100% coverage
- [ ] Error handling is fully covered

### Schema Validation

- [ ] All data structures have schemas
- [ ] All data is validated before processing
- [ ] Schema changes are documented
- [ ] Migration plans are provided

### Logging

- [ ] Only `UnifiedLogger` is used
- [ ] All logs have context
- [ ] No secrets in logs
- [ ] Proper log levels used

### Environment

- [ ] All dependencies are version-pinned
- [ ] Security scan passed
- [ ] No deprecated packages
- [ ] Configuration via environment variables

## Failure Criteria

A change fails reproducibility audit if:

- Any determinism violation is found
- Test coverage is below threshold
- Schema validation is missing
- Unstructured logging is present
- Secrets are exposed
- Dependencies are not pinned
- Breaking changes are not documented

## Approval Criteria

A change passes reproducibility audit if:

- All determinism checks pass
- Test coverage meets thresholds
- Schema validation is in place
- Structured logging is used
- No secrets are exposed
- Dependencies are pinned
- Breaking changes are documented

## Remediation

If a change fails audit:

1. Identify specific violations
2. Propose remediation steps
3. Implement fixes
4. Re-run audit
5. Document changes

## References

- `docs/styleguide/04-deterministic-io.md` - Deterministic I/O guidelines
- `docs/styleguide/05-testing-standards.md` - Testing standards
- `docs/00-project/RULES.md` - Project rules
- `docs/01-requirements/REQUIREMENTS.md` - Project requirements
