-- BioETL Database Initialization
-- Creates schemas and core tables for local development

-- System schema for metadata
CREATE SCHEMA IF NOT EXISTS sys;

-- Lineage tracking table (RULES.md §2.3)
CREATE TABLE IF NOT EXISTS sys.lineage_log (
    batch_id UUID PRIMARY KEY,
    pipeline VARCHAR(255) NOT NULL,
    bronze_files TEXT[] NOT NULL,
    transform_version VARCHAR(50) NOT NULL,
    run_params JSONB,
    run_type VARCHAR(50) NOT NULL CHECK (run_type IN ('incremental', 'backfill', 'rebuild')),
    run_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    record_count BIGINT,
    error_count BIGINT
);

CREATE INDEX idx_lineage_pipeline ON sys.lineage_log(pipeline);
CREATE INDEX idx_lineage_created_at ON sys.lineage_log(created_at DESC);
CREATE INDEX idx_lineage_run_id ON sys.lineage_log(run_id);

-- Checkpoint storage table (for non-S3 checkpoints)
CREATE TABLE IF NOT EXISTS sys.checkpoints (
    pipeline VARCHAR(255) PRIMARY KEY,
    watermark JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    run_id UUID NOT NULL
);

-- Schema drift tracking (RULES.md §2.2)
CREATE TABLE IF NOT EXISTS sys.schema_drift_log (
    id SERIAL PRIMARY KEY,
    pipeline VARCHAR(255) NOT NULL,
    drift_level VARCHAR(20) NOT NULL CHECK (drift_level IN ('INFO', 'WARN', 'CRITICAL')),
    field_name VARCHAR(255),
    drift_type VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    owner VARCHAR(255),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT
);

CREATE INDEX idx_drift_pipeline ON sys.schema_drift_log(pipeline);
CREATE INDEX idx_drift_level ON sys.schema_drift_log(drift_level);
CREATE INDEX idx_drift_detected ON sys.schema_drift_log(detected_at DESC);

-- Provider health monitoring (RULES.md §3.5)
CREATE TABLE IF NOT EXISTS sys.provider_health_log (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('HEALTHY', 'DEGRADED', 'UNHEALTHY')),
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    checked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_health_provider ON sys.provider_health_log(provider);
CREATE INDEX idx_health_checked ON sys.provider_health_log(checked_at DESC);

-- DQ metrics baseline (RULES.md §3.4.1)
CREATE TABLE IF NOT EXISTS sys.dq_baseline (
    id SERIAL PRIMARY KEY,
    pipeline VARCHAR(255) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    baseline_value DOUBLE PRECISION NOT NULL,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sample_days INTEGER DEFAULT 30,
    UNIQUE (pipeline, metric_name)
);

CREATE INDEX idx_dq_baseline_pipeline ON sys.dq_baseline(pipeline);

-- Common schema for unified quarantine
CREATE SCHEMA IF NOT EXISTS common;

-- Note: Quarantine will be Delta Lake table, this is just for reference
-- Actual schema defined in: src/bioetl/infrastructure/quarantine/schemas.py
COMMENT ON SCHEMA common IS 'Common schema for unified quarantine and shared tables';

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA sys TO bioetl;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA sys TO bioetl;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA sys TO bioetl;

GRANT ALL PRIVILEGES ON SCHEMA common TO bioetl;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA common TO bioetl;
