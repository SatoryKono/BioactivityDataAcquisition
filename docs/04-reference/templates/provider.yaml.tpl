# Provider Source Config Template
# Location: configs/providers/<provider>.yaml

version: 1.0.0
provider: {{provider}}

source:
  batch_size: 100
  provider_config:
    provider: {{provider}}
    base_url: {{base_url}}
    auth_type: {{auth_type}} # public | api_key | oauth
    api_key_env: {{api_key_env}}
    client:
      timeout_sec: 60.0
      max_retries: 3
    pagination:
      page_size: 100
      id_batch_size: 100
      strategy: offset
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300
  rate_limit:
    requests_per_second: 3.0
    burst: 10
  health_check:
    endpoint: {{health_endpoint}}
    timeout: 10
  retry:
    use_retry_after: true

entities:
  - {{entity}}

entity_notes:
  {{entity}}:
    description: {{entity_description}}
    input_mode: {{input_mode}}

quality:
  version: 1.0.0
  provider: {{provider}}
  thresholds:
    soft_fail: 0.05
    hard_fail: 0.15
  field_validations: []

filters:
  version: 1.0.0
  provider: {{provider}}
  input_filter:
    batch_size: 100
  gold_filters:
    required_fields: []
    columns: {}
