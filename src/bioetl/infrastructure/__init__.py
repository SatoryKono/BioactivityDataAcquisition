"""Infrastructure layer - adapters and implementations.

Contains concrete implementations for domain ports:
- HTTP adapters (ChEMBL, PubChem, etc.)
- Storage adapters (S3, Delta Lake)
- Locking adapters (Redis)
- Metrics exporters (Prometheus)

See RULES.md Section 1.1 for architecture details.
"""
