# Configuration Merge Strategy

## Overview

This document defines the merge strategy for handling duplicate fields between base configuration (`configs/base/pipeline.yaml`) and entity-specific configurations (`configs/entities/*/`). The merge system ensures that entity-specific configurations can override or extend base defaults while maintaining configuration consistency.

## Configuration Hierarchy

### Base Configuration
**Location:** `configs/base/pipeline.yaml`

**Purpose:** Provides consolidated defaults for all pipeline configurations

**Key Fields:**
- `version`: Base pipeline version (currently "1.2.0")
- `technical_primary_key`: Default primary key field (currently "entity_id")
- `loading_strategy`: Default loading strategy (null = incremental)
- `source`: Default source configuration
- `transform`: Default transformation steps
- `dq_overrides`: Default DQ overrides
- `sink`: Default sink configuration

### Entity Configuration
**Location:** `configs/entities/{provider}/{entity}.yaml`

**Purpose:** Provider-specific and entity-specific configuration overrides

**Key Fields:**
- `version`: Entity-specific version (e.g., "1.0.0")
- `provider`: Data provider name (e.g., "chembl")
- `entity`: Entity name (e.g., "activity")
- `pipeline`: Pipeline-specific configuration
- `quality`: Quality validation configuration
- `filters`: Filter configuration
- `hash_policy`: Hash policy configuration

## Merge Strategy

### Field-Level Merge Rules

#### 1. Version Fields

**Base Config:** `version: "1.2.0"`
**Entity Config:** `version: "1.0.0"`

**Merge Strategy:** Entity config version takes precedence

**Rationale:** Entity configs track their own versioning independent of base config. The base config version applies to the configuration structure, while entity config version applies to the specific entity implementation.

**Example:**
```yaml
# Base config
version: "1.2.0"

# Entity config
version: "1.0.0"  # Takes precedence for this entity
```

#### 2. Primary Key Fields

**Base Config:** `technical_primary_key: "entity_id"`
**Entity Config:** `business_primary_keys: [...]`

**Merge Strategy:** No conflict - different purposes

**Rationale:** Base config defines the technical primary key used by the pipeline framework, while entity config defines business primary keys specific to the domain model.

**Example:**
```yaml
# Base config
technical_primary_key: "entity_id"

# Entity config
business_primary_keys:
  - activity_id
  - molecule_id
  - assay_id
```

#### 3. Provider and Entity Fields

**Base Config:** Not applicable (base config is provider-agnostic)
**Entity Config:** `provider: "chembl"`, `entity: "activity"`

**Merge Strategy:** Entity config fields only

**Rationale:** Provider and entity fields are entity-specific and don't exist in base config.

**Example:**
```yaml
# Entity config only
provider: chembl
entity: activity
```

#### 4. Structural Fields

**Base Config:** `source: {}`, `transform: { steps: [] }`, `dq_overrides: {}`
**Entity Config:** Can override or extend these

**Merge Strategy:** Deep merge with entity config taking precedence

**Rationale:** Entity configs can override base defaults or add entity-specific configuration.

**Example:**
```yaml
# Base config
source: {}
transform:
  steps: []

# Entity config
source:
  api_endpoint: "https://example.com/api"
transform:
  steps:
    - name: custom_transform
      type: python
      module: custom.module
```

#### 5. Nested Configuration Sections

**Base Config:** `quality: {}` (via DQConfigLoader)
**Entity Config:** `quality: { version: "1.1.0", ... }`

**Merge Strategy:** Entity config quality section completely replaces base

**Rationale:** Quality configuration is loaded via DQConfigLoader from base/quality.yaml, but entity configs can provide their own quality configuration with specific validation rules.

**Example:**
```yaml
# Entity config
quality:
  version: 1.1.0
  provider: chembl
  entity: activity
  entity_field_validations:
    - field: activity_id
      type: required
      nullable: false
```

## Merge Implementation

### Configuration Loading Process

1. **Load Base Config:** Read `configs/base/pipeline.yaml` for defaults
2. **Load Entity Config:** Read entity-specific configuration
3. **Apply Merge Rules:** Apply field-level merge rules
4. **Validate Result:** Validate merged configuration against schema
5. **Return Merged Config:** Return final configuration for pipeline execution

### Merge Priority

**Priority Order (highest to lowest):**
1. Entity config explicit values
2. Entity config nested structures
3. Base config defaults
4. Framework defaults (hardcoded)

### Conflict Resolution

**Conflict Types:**

1. **Same Field, Different Values:** Entity config takes precedence
2. **Same Field, Same Value:** No conflict, use value
3. **Nested Structure:** Deep merge with entity config taking precedence
4. **Array Fields:** Entity config replaces base config (no array merging)

**Examples:**

**Conflict Resolution (Entity Wins):**
```yaml
# Base config
loading_strategy: null

# Entity config
loading_strategy: full  # Takes precedence
```

**Deep Merge (Entity Extends Base):**
```yaml
# Base config
dq_overrides: {}

# Entity config
dq_overrides:
  allow_missing_fields: true  # Extends base
```

## Common Merge Scenarios

### Scenario 1: Simple Override

**Use Case:** Entity needs different loading strategy than base default

**Implementation:**
```yaml
# Base config
loading_strategy: null

# Entity config
loading_strategy: full
```

**Result:** Entity config value used

### Scenario 2: Nested Extension

**Use Case:** Entity needs to add DQ overrides on top of base defaults

**Implementation:**
```yaml
# Base config
dq_overrides: {}

# Entity config
dq_overrides:
  allow_missing_fields: true
  custom_validation: true
```

**Result:** Entity config DQ overrides used (base empty dict replaced)

### Scenario 3: Structural Override

**Use Case:** Entity needs custom transformation steps

**Implementation:**
```yaml
# Base config
transform:
  steps: []

# Entity config
transform:
  steps:
    - name: custom_step
      type: python
      module: custom.module
```

**Result:** Entity config transform steps used (base empty list replaced)

### Scenario 4: No Override

**Use Case:** Entity accepts base defaults

**Implementation:**
```yaml
# Base config
loading_strategy: null

# Entity config
# No loading_strategy field
```

**Result:** Base config value used

## Version Management

### Base Config Version

**Purpose:** Track changes to base configuration structure

**Update Criteria:** When base config structure changes significantly

**Impact:** Requires review of all entity configs for compatibility

### Entity Config Version

**Purpose:** Track changes to entity-specific configuration

**Update Criteria:** When entity configuration changes

**Impact:** Independent of base config version

### Version Compatibility

**Guidelines:**
- Entity configs should document base config version compatibility
- Major base config changes may require entity config updates
- Minor base config changes should be backward compatible

## Validation

### Schema Validation

**Process:**
1. Load merged configuration
2. Validate against JSON schema
3. Check for required fields
4. Validate field types and constraints
5. Check for unknown fields

**Error Handling:**
- Schema validation errors block pipeline execution
- Warnings are logged for deprecated fields
- Unknown fields are rejected in strict mode

### Consistency Validation

**Checks:**
- Provider and entity fields must match file path
- Version fields must follow semantic versioning
- Required fields must be present
- Field types must match schema expectations

## Best Practices

### For Base Config
- Keep base config minimal and focused on true defaults
- Avoid entity-specific logic in base config
- Document the purpose of each base field
- Use clear, descriptive field names

### For Entity Config
- Only override fields that need to be different from base
- Keep entity config focused on entity-specific logic
- Document why overrides are needed
- Maintain consistency with base config structure

### For Merge Logic
- Keep merge rules simple and predictable
- Document merge priority clearly
- Avoid complex merge logic
- Test merge logic with representative examples

## Related Documents

- [ADR-031: Configuration Loading Strategy](../../02-architecture/decisions/ADR-031-configuration-loading-strategy.md)
- [Configuration File Policy](../../00-project/governance/03-file-policy.md)
- [Entity Configuration Schema](../../04-reference/configs/entity-config-schema.json)
- [Base Configuration Schema](../../04-reference/configs/base-config-schema.json)

## Revision History

- **2026-08-09:** Initial merge strategy documentation based on CFG-005 from configuration audit
