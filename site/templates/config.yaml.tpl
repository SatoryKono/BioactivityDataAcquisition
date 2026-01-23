# Template for Pipeline Configuration
# Location: configs/pipelines/<provider>/<entity>.yaml

pipeline:
    name: {{provider}}_{{entity}}
    provider: {{provider}}
    entity: {{entity}}

source:
    type: api
    load_strategy: incremental
    watermark_field: {{watermark_field}}

transform:
    version: "1.0.0"
    steps:
        - normalize_fields
        - generate_content_hash

sink:
    bronze:
        path: "s3://bioetl-bronze/{{provider}}/{{entity}}/"
        format: json

    silver:
        path: "s3://bioetl-silver/{{provider}}/{{entity}}/"
        format: delta
        mode: merge
        primary_key: [ "{{primary_key}}" ]
        forensic_retention: true

    gold:
        enabled: false
        # path: "s3://bioetl-gold/{{provider}}/{{entity}}/"
        # format: delta
        # mode: overwrite

dq_rules:
    soft_fail_threshold: 0.05
    hard_fail_threshold: 0.20

circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300

rate_limit:
    requests_per_second: 5
