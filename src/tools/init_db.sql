-- =============================================================================
-- init_db.sql - PostgreSQL schema initialization for BioETL
-- =============================================================================
--
-- Purpose:
--   Initialize PostgreSQL schema for Docker-based deployment scenarios.
--   This script creates tables for pipeline metadata, audit logs, and
--   operational data.
--
-- Usage:
--   psql -f src/tools/init_db.sql
--   OR
--   docker compose exec postgres psql -U bioetl -f /docker-entrypoint-initdb.d/init_db.sql
--
-- Notes:
--   - For Local-Only deployment (ADR-010), this script is NOT required.
--   - The project primarily uses Delta Lake for data storage.
--   - PostgreSQL is optional for metadata/audit storage in production deployments.
--
-- References:
--   - ADR-010: Local-Only Deployment
--   - RULES.md §5.5: Disaster Recovery
--
-- Aligned with RULES.md v5.10 (2026-01-06)
-- =============================================================================

-- =============================================================================
-- Schema setup
-- =============================================================================

-- Create schema for BioETL metadata
CREATE SCHEMA IF NOT EXISTS bioetl;

-- Set search path
SET search_path TO bioetl, public;

-- =============================================================================
-- Enum types
-- =============================================================================

-- Pipeline run types
CREATE TYPE run_type AS ENUM ('INCREMENTAL', 'BACKFILL', 'REBUILD');

-- Pipeline run status
CREATE TYPE run_status AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED');

-- Lock status
CREATE TYPE lock_status AS ENUM ('ACQUIRED', 'RELEASED', 'EXPIRED');

-- Quarantine error categories
CREATE TYPE error_category AS ENUM ('VALIDATION', 'SCHEMA', 'TRANSFORM', 'NETWORK', 'UNKNOWN');


-- =============================================================================
-- Pipeline Runs table
-- =============================================================================

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL UNIQUE,
    pipeline_name VARCHAR(255) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    run_type run_type NOT NULL DEFAULT 'INCREMENTAL',
    status run_status NOT NULL DEFAULT 'PENDING',

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER,

    -- Metrics
    records_extracted INTEGER DEFAULT 0,
    records_transformed INTEGER DEFAULT 0,
    records_loaded INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_rate DECIMAL(5, 4),

    -- Configuration snapshot (JSON)
    config JSONB,

    -- Error details (if failed)
    error_message TEXT,
    error_traceback TEXT,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for pipeline_runs
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline ON pipeline_runs(pipeline_name);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_provider_entity ON pipeline_runs(provider, entity_type);


-- =============================================================================
-- Checkpoints table
-- =============================================================================

CREATE TABLE IF NOT EXISTS checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_name VARCHAR(255) NOT NULL,
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id),

    -- Checkpoint data
    offset_value VARCHAR(1024),
    offset_type VARCHAR(50),  -- 'page', 'cursor', 'timestamp', etc.
    batch_id UUID,
    records_processed INTEGER DEFAULT 0,

    -- State
    checkpoint_data JSONB,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(pipeline_name, run_id)
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_pipeline ON checkpoints(pipeline_name);
CREATE INDEX IF NOT EXISTS idx_checkpoints_run_id ON checkpoints(run_id);


-- =============================================================================
-- Locks table (for distributed locking)
-- =============================================================================

CREATE TABLE IF NOT EXISTS locks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lock_key VARCHAR(512) NOT NULL UNIQUE,
    owner_id UUID NOT NULL,
    status lock_status NOT NULL DEFAULT 'ACQUIRED',

    -- TTL
    acquired_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    released_at TIMESTAMPTZ,

    -- Metadata
    lock_type VARCHAR(50) DEFAULT 'exclusive',
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_locks_key ON locks(lock_key);
CREATE INDEX IF NOT EXISTS idx_locks_owner ON locks(owner_id);
CREATE INDEX IF NOT EXISTS idx_locks_expires ON locks(expires_at);


-- =============================================================================
-- Quarantine table
-- =============================================================================

CREATE TABLE IF NOT EXISTS quarantine (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL,
    pipeline_name VARCHAR(255) NOT NULL,
    batch_id UUID,

    -- Record data
    entity_id VARCHAR(512),
    record_data JSONB NOT NULL,

    -- Error information
    error_category error_category NOT NULL DEFAULT 'UNKNOWN',
    error_code VARCHAR(100),
    error_message TEXT NOT NULL,
    error_details JSONB,

    -- Processing stage
    stage VARCHAR(50),  -- 'extract', 'transform', 'load'

    -- Retry tracking
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMPTZ,
    replayable BOOLEAN DEFAULT TRUE,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_quarantine_run ON quarantine(run_id);
CREATE INDEX IF NOT EXISTS idx_quarantine_pipeline ON quarantine(pipeline_name);
CREATE INDEX IF NOT EXISTS idx_quarantine_category ON quarantine(error_category);
CREATE INDEX IF NOT EXISTS idx_quarantine_created ON quarantine(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_quarantine_entity ON quarantine(entity_id);


-- =============================================================================
-- Audit Log table
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID,
    pipeline_name VARCHAR(255),

    -- Event details
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB,

    -- Context
    stage VARCHAR(50),
    component VARCHAR(255),

    -- Timing
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_log(run_id);
CREATE INDEX IF NOT EXISTS idx_audit_pipeline ON audit_log(pipeline_name);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);

-- Partitioning by month (optional, for large deployments)
-- CREATE TABLE audit_log_y2026m01 PARTITION OF audit_log
--     FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');


-- =============================================================================
-- Data Quality Metrics table
-- =============================================================================

CREATE TABLE IF NOT EXISTS dq_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL,
    pipeline_name VARCHAR(255) NOT NULL,

    -- Thresholds
    soft_threshold DECIMAL(5, 4) NOT NULL DEFAULT 0.05,
    hard_threshold DECIMAL(5, 4) NOT NULL DEFAULT 0.20,

    -- Actual values
    total_records INTEGER NOT NULL,
    failed_records INTEGER NOT NULL,
    error_rate DECIMAL(5, 4) NOT NULL,

    -- Checks
    soft_threshold_exceeded BOOLEAN DEFAULT FALSE,
    hard_threshold_exceeded BOOLEAN DEFAULT FALSE,

    -- Details
    validation_errors JSONB,

    -- Timing
    check_duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dq_metrics_run ON dq_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_dq_metrics_pipeline ON dq_metrics(pipeline_name);
CREATE INDEX IF NOT EXISTS idx_dq_metrics_created ON dq_metrics(created_at DESC);


-- =============================================================================
-- Salt Rotation Audit table
-- =============================================================================

CREATE TABLE IF NOT EXISTS salt_rotation_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Rotation details
    action VARCHAR(50) NOT NULL,  -- 'initiate', 'complete', 'emergency', 'cancel'
    old_salt_id VARCHAR(16),
    new_salt_id VARCHAR(16),

    -- Result
    success BOOLEAN NOT NULL,
    error_message TEXT,

    -- Audit
    initiated_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_salt_rotation_created ON salt_rotation_audit(created_at DESC);


-- =============================================================================
-- Functions
-- =============================================================================

-- Update updated_at timestamp on row update
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to pipeline_runs
DROP TRIGGER IF EXISTS update_pipeline_runs_updated_at ON pipeline_runs;
CREATE TRIGGER update_pipeline_runs_updated_at
    BEFORE UPDATE ON pipeline_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- Cleanup expired locks function
CREATE OR REPLACE FUNCTION cleanup_expired_locks()
RETURNS INTEGER AS $$
DECLARE
    cleaned INTEGER;
BEGIN
    WITH expired AS (
        UPDATE locks
        SET status = 'EXPIRED'
        WHERE expires_at < NOW() AND status = 'ACQUIRED'
        RETURNING id
    )
    SELECT COUNT(*) INTO cleaned FROM expired;

    RETURN cleaned;
END;
$$ LANGUAGE plpgsql;


-- =============================================================================
-- Views
-- =============================================================================

-- Recent pipeline runs with metrics
CREATE OR REPLACE VIEW recent_runs AS
SELECT
    pr.run_id,
    pr.pipeline_name,
    pr.provider,
    pr.entity_type,
    pr.run_type,
    pr.status,
    pr.started_at,
    pr.completed_at,
    pr.duration_ms,
    pr.records_extracted,
    pr.records_loaded,
    pr.records_failed,
    pr.error_rate,
    dq.soft_threshold_exceeded,
    dq.hard_threshold_exceeded
FROM pipeline_runs pr
LEFT JOIN dq_metrics dq ON pr.run_id = dq.run_id
ORDER BY pr.started_at DESC
LIMIT 100;


-- Quarantine summary by pipeline
CREATE OR REPLACE VIEW quarantine_summary AS
SELECT
    pipeline_name,
    error_category,
    COUNT(*) as total_count,
    SUM(CASE WHEN resolved_at IS NULL THEN 1 ELSE 0 END) as unresolved_count,
    SUM(CASE WHEN replayable THEN 1 ELSE 0 END) as replayable_count,
    MAX(created_at) as latest_error
FROM quarantine
GROUP BY pipeline_name, error_category
ORDER BY pipeline_name, total_count DESC;


-- =============================================================================
-- Initial data
-- =============================================================================

-- (No initial data required - tables populated by pipeline runs)


-- =============================================================================
-- Grants (adjust for your deployment)
-- =============================================================================

-- Grant usage on schema
-- GRANT USAGE ON SCHEMA bioetl TO bioetl_app;

-- Grant permissions on tables
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA bioetl TO bioetl_app;
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA bioetl TO bioetl_app;


-- =============================================================================
-- Completion message
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE 'BioETL database schema initialized successfully.';
    RAISE NOTICE 'Tables created: pipeline_runs, checkpoints, locks, quarantine, audit_log, dq_metrics, salt_rotation_audit';
    RAISE NOTICE 'Views created: recent_runs, quarantine_summary';
END $$;
