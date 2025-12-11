# Terminology Glossary

This document maps equivalent terms used across different layers of the codebase.

## Hash Terminology

| Canonical Term       | Contract Method         | Schema Column        | Description                                      |
|---------------------|-------------------------|----------------------|--------------------------------------------------|
| `record_hash`       | `compute_fingerprint()` | `hash_row`           | SHA-256 hash of entire record (all fields)       |
| `business_key_hash` | `compute_entity_key()`  | `hash_business_key`  | SHA-256 hash of business key fields only         |

### Layer-specific Usage

- **Domain contracts** (`domain/transform/contracts.py`): Uses `fingerprint` and `entity_key` method names
- **Schema layer** (`infrastructure/validation/schemas/`): Uses `hash_row` and `hash_business_key` column names
- **Documentation**: Should prefer canonical terms (`record_hash`, `business_key_hash`)

### Why Different Names?

- **Contract methods**: Domain-focused, describe the *operation* (compute fingerprint, compute entity key)
- **Schema columns**: Data-focused, describe the *content* (hash of row, hash of business key)
- **Canonical terms**: Clear, unambiguous names for documentation and API design

## Model Naming

| Canonical Name         | Deprecated Alias     | Schema Name             | Entity Type  |
|-----------------------|---------------------|-------------------------|--------------|
| `PublicationRawModel` | `DocumentRawModel`  | `PublicationTableSchema`| `document`   |

### Notes

- `DocumentRawModel` is deprecated and will be removed in v3.0
- Use `PublicationRawModel` for all new code
- The ChEMBL API uses "document" as the entity type name (retained for API compatibility)

## Migration Timeline

### v2.x (Current)
- Both terms work, deprecated aliases emit warnings
- New code should use canonical terms

### v3.0 (Future)
- Deprecated aliases will be removed
- Breaking change for code using deprecated names
