# domain/exceptions residual closeout (#8155–#8165)

- Branch: `grok-260807-108155`
- Fixed: **10**
- Rejected: **1**
- Total: **11**

## Dispositions

- **#8155** `fixed` — _redact_sequence materializes plain list/tuple instead of type(value)(generator).
- **#8156** `fixed` — Added residual unit coverage for BioETLError.to_structured_context, domain context, PipelineShutdownError, and storage compatibility constructors.
- **#8157** `fixed` — Schema validation messages include one-sided column diffs when only expected or actual columns are present.
- **#8158** `fixed` — ValidationError/SchemaViolationError always expose record_id and field (None when omitted).
- **#8159** `fixed` — Parametrized tests cover resolve_rate_limit_params provider/message/service_name fallbacks.
- **#8160** `reject` — infrastructure/ is already a re-export facade over storage/; no duplicate _storage/_delta modules present.
- **#8161** `fixed` — BucketNotFoundError/UploadError/BronzeValidationError/CachedBronzeEmptyError and Delta* aliases are concrete exception classes preserving constructors/attrs.
- **#8162** `fixed` — Contract tests cover ApiError, ServiceUnavailableError, RateLimitError modes, and DataValidationError class.
- **#8163** `fixed` — Lazy __getattr__ facade contract tests resolve every __all__ name and reject unknowns; removed dead TYPE_CHECKING branch.
- **#8164** `fixed` — Canonical classes live in storage/_storage.py; infrastructure remains re-export facade (no separate broken alias module).
- **#8165** `fixed` — BioETLDomainError freezes nested context via MappingProxyType/tuples; to_dict returns plain dict snapshot.

## Validation
- `pytest tests/unit/domain/exceptions` green
- No tech-debt budget growth
