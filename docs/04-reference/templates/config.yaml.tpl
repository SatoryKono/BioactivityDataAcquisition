# Unified Entity Config Template
# Location: configs/entities/<provider>/<entity>.yaml

version: "1.0.0"
provider: {{provider}}
entity: {{entity}}

pipeline:
  pipeline_name: {{provider}}_{{entity}}
  provider: {{provider}}
  entity_type: {{entity}}
  description: "Extract {{entity}} records from {{provider}} API"
  business_primary_keys:
    - {{primary_key}}
  batch_size: 100

schema:
  content_hash:
    include: []
    exclude: []
  column_groups:
    - name: system
      fields:
        - entity_id
        - content_hash
        - _source
        - _index
    - name: business
      fields:
        - {{primary_key}}
        # - field_1
        # - field_2
    - name: dq
      pattern: ^_dq_
  silver:
    include_groups: [system, business, dq]
    exclude_fields: []
    alias_policy: preserve
  gold:
    include_groups: [system, business]
    exclude_fields: [_dq_*, _index]
    alias_policy: canonical

quality:
  version: "1.0.0"
  provider: {{provider}}
  entity: {{entity}}
  field_validations:
    - field: {{primary_key}}
      type: required
      nullable: false
      error_message: "{{primary_key}} is required"
  cross_field_validations: []
  conditional_validations: []

filters:
  version: "1.0.0"
  provider: {{provider}}
  entity: {{entity}}
  input_filter:
    enabled: false
  gold_filters:
    required_fields:
      - {{primary_key}}
    columns: {}

contracts:
  primary_key:
    - {{primary_key}}
  merge_keys:
    - {{primary_key}}
  rename_map:
    source: _source
  hash_include: []
  hash_exclude:
    - _dq_error
    - _dq_warn
    - _index
