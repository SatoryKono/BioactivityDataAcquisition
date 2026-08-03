## Summary

ID / Processed Records panel dataLinks point health checks at **`http://localhost:8081/health/live`**, but BioETL Ops HTTP serves on **`:8000`** (8081 is image renderer).

## Fix

Update dataLinks on all boards to `http://localhost:8000/health/live` (or relative/docs link).

## Acceptance

- No dashboard JSON health link targets :8081 for Ops HTTP
