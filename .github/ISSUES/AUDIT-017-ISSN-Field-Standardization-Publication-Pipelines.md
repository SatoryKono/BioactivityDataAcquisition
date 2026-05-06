# Standardize ISSN Fields in Publication Pipelines

**Status**: Open
**Priority**: P1 (High)
**Labels**: `normalization`, `data-quality`, `audit`, `publication`
**Epic**: Publication Pipeline Consistency 2024Q3

## 🎯 Problem

Inconsistent ISSN field representation across publication pipelines breaks Gold contract compatibility and complicates composite merges. Different providers use different formats:
- CrossRef: Both `issn` (scalar) and `issn_list` (JSON array)
- OpenAlex: `issn` (scalar) only, missing `issn_list`
- Semantic Scholar: Missing both `issn` and `issn_list`
- PubMed: `issn` (scalar) only, missing `issn_list`

This creates incompatible output schemas and violates between-provider consistency requirements.

## 🔍 Root Cause Analysis

1. **No Unified Standard**: ISSN handling logic scattered across different blocks without common normalization rule
2. **Missing Fields**: Semantic Scholar and PubMed pipelines don't generate `issn_list`
3. **Format Inconsistency**: Different pipelines represent ISSN as string, JSON list, or omit entirely
4. **Contract Violation**: Gold strict validation requires `issn` and `issn_list` columns in all outputs

## 📋 Scope

**Affected Components:**

- `src/bioetl/application/pipelines/semanticscholar/transformer.py` - Add ISSN fields
- `src/bioetl/application/pipelines/pubmed/block_definitions.py` - Add `issn_list`
- `src/bioetl/application/pipelines/openalex/transformer.py` - Add `issn_list`
- `src/bioetl/application/pipelines/crossref/transformer.py` - Verify existing dual-field logic
- Silver/Gold schemas - Update to require `issn_list` column
- Test files - Add validation for new fields

**Impact Analysis:**

```bash
# Check current ISSN usage
grep -rn "issn" src/bioetl/application/pipelines/*/transformer.py
```

## 🎯 Solution Plan

### Phase 1: Semantic Scholar (1 day)

1. **Add ISSN Fields to Extractor**

   ```python
   # src/bioetl/application/pipelines/semanticscholar/extractors.py
   def extract_journal_info(journal, venue):
       # Add ISSN extraction if available in API response
       return {
           "journal": ...,
           "issn": journal.get("issn") if journal else None,
       }
   ```

1. **Add Fields to Transformer**

   ```python
   # src/bioetl/application/pipelines/semanticscholar/transformer.py
   # In _extract_business_data, after journal_info extraction:
   "issn": journal_info.get("issn"),
   "issn_list": None,  # Will be populated in entity_to_silver_record
   ```

1. **Add Conversion in entity_to_silver_record**

   ```python
   # In entity_to_silver_record method:
   issn_raw = silver_record.get("issn")
   if issn_raw:
       silver_record["issn_list"] = self.serialize_json_list([issn_raw])
   else:
       silver_record["issn_list"] = None
   ```

### Phase 2: PubMed (1 day)

1. **Add issn_list to Journal Block**

   ```python
   # src/bioetl/application/pipelines/pubmed/_block_helpers.py
   def extract_journal_data(article):
       issn = get_text(issn_element)
       return {
           "issn": issn,
           "issn_list": [issn] if issn else None,  # Will be serialized in block
       }
   ```

1. **Serialize in Block Definition**

   ```python
   # src/bioetl/application/pipelines/pubmed/block_definitions.py
   # In _PubMedJournalBlock.extract(), add serialize_json_list call:
   "issn_list": self._serialize_json_list(journal_data.get("issn_list"))
   ```

### Phase 3: OpenAlex (1 day)

1. **Add issn_list to Publication Bundle**

   ```python
   # src/bioetl/application/pipelines/openalex/transformer.py
   # In _extract_publication_bundle:
   issn = journal_info.get("issn")
   return {
       "issn": issn,
       "issn_list": self._serialize_json_list([issn]) if issn else None,
       # ... other fields
   }
   ```

### Phase 4: CrossRef Verification (0.5 day)

1. **Verify Existing Logic**

   ```python
   # src/bioetl/application/pipelines/crossref/transformer.py
   # Lines 258-273 already handle issn -> issn + issn_list conversion
   # Verify this logic is correct and preserves data
   ```

### Phase 5: Schema & Contract Updates (1 day)

1. **Update Silver Schema**

   ```python
   # src/bioetl/domain/schemas/publication.py
   # Add issn_list column to PublicationBaseSchema
   issn_list: Series[str] = pa.Field(nullable=True)
   ```

1. **Update Gold Contract**

   - Add `issn_list` to Gold schema definition
   - Bump contract version for breaking change

1. **Add DQ Rules**

   ```python
   # configs/dq/publication.yaml
   rules:
     - name: issn_list_format
       condition: issn_list is null or is_valid_json_array(issn_list)
   ```

### Phase 6: Testing (1 day)

1. **Add Unit Tests**

   ```python
   # tests/unit/application/pipelines/test_semanticscholar_transformer.py
   def test_issn_fields_present():
       record = {...}
       result = transformer._extract_business_data(record)
       assert "issn" in result
       assert "issn_list" in result
   ```

1. **Add Golden Tests**

   - Update golden snapshots for all 4 providers
   - Verify `issn_list` column presence

1. **Integration Tests**

   ```bash
   pytest tests/integration/test_publication_merges.py -v
   ```

## ✅ Success Criteria

- [ ] All publication pipelines output both `issn` (string) and `issn_list` (JSON array)
- [ ] Semantic Scholar and PubMed generate `issn_list` field
- [ ] OpenAlex generates `issn_list` field
- [ ] CrossRef existing dual-field logic verified correct
- [ ] Silver/Gold schemas updated with `issn_list` column
- [ ] DQ rules validate `issn_list` format
- [ ] Unit/golden tests pass for all 4 providers
- [ ] Composite merge preserves ISSN data from all sources
- [ ] Content hash stability maintained (new fields excluded from hash)

## 📊 Verification Commands

```bash
# Check ISSN fields in transformers
grep -rn "issn" src/bioetl/application/pipelines/*/transformer.py

# Run publication transformer tests
pytest tests/unit/application/pipelines/test_*_transformer.py -v

# Validate silver schema
python -m bioetl.domain.schemas.publication

# Check DQ rules
python scripts/validate_data_quality.py --issn-check
```

## 📈 Impact Assessment

### Positive Impacts

- **Consistency**: Unified ISSN representation across all providers
- **Contract Compliance**: Gold strict validation satisfied
- **Merge Reliability**: Composite merges preserve ISSN data correctly
- **Data Quality**: Clear schema expectations

### Potential Risks

- **Breaking Change**: Schema change requires contract version bump
- **Content Hash**: New fields may affect content hashes (must be excluded)
- **Backfill**: Existing silver data may need migration

### Mitigation Strategies

- **Schema Evolution**: Use nullable `issn_list` for backward compatibility
- **Hash Exclusion**: Exclude `issn_list` from content hash computation
- **Migration Script**: Create backfill script for existing data
- **Gradual Rollout**: Deploy provider changes sequentially

## 🎯 Related Issues

- **Related To**: AUDIT-012 (RunExecutionRequest Naming Alias)
- **Related To**: AUDIT-015 (Provider Contract Snapshot Registry)
- **Blocks**: Composite merge improvements for publication entities

## ⏳ Time Estimate

**Total**: 5.5 days
**Start Date**: 2024-08-01
**Target Completion**: 2024-08-07

## 👥 Assignee

(TBD - comment on tracking issue to claim)

## 📋 Checklist

- [ ] Semantic Scholar ISSN fields added
- [ ] PubMed issn_list added
- [ ] OpenAlex issn_list added
- [ ] CrossRef logic verified
- [ ] Silver schema updated
- [ ] Gold contract updated
- [ ] DQ rules added
- [ ] Unit tests added
- [ ] Golden tests updated
- [ ] Integration tests passing
- [ ] Content hash exclusion verified
- [ ] Backfill script created
- [ ] Documentation updated

## 🎯 Notes

This issue ensures between-provider consistency for ISSN fields, enabling reliable composite merges and satisfying Gold strict validation requirements. The implementation follows the existing pattern established in CrossRef transformer for dual-field representation (scalar + JSON array).
