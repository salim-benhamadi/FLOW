-- ============================================================================
-- Complete Corrected SQL Schema for ML Training and Feedback System
-- VAMOS Distribution Analysis Tool Database Schema
-- Version 1.2 - PostgreSQL 9.6+ Compatible
-- ============================================================================

-- Create ENUM types
CREATE TYPE severity_level AS ENUM ('HIGH', 'CRITICAL', 'MEDIUM');
CREATE TYPE feedback_status AS ENUM ('PENDING', 'IGNORED', 'RESOLVED');
CREATE TYPE training_reason_type AS ENUM ('FEEDBACK', 'NEW_DATA', 'ADMIN_INITIATIVE');
CREATE TYPE training_status AS ENUM ('SUCCESS', 'FAILING');
CREATE TYPE label AS ENUM ('SIMILAR', 'MODERATELY_SIMILAR', 'COMPLETELY_DIFFERENT');
CREATE TYPE model_status AS ENUM ('active', 'inactive', 'training', 'failed');

-- ============================================================================
-- Core Data Tables
-- ============================================================================

-- Input Data Table
CREATE TABLE input_data (
    input_id VARCHAR(255) PRIMARY KEY,
    insertion VARCHAR(50) NOT NULL,
    test_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    lsl FLOAT,
    usl FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Input measurements table
CREATE TABLE input_measurements (
    input_id VARCHAR(255) REFERENCES input_data(input_id) ON DELETE CASCADE,
    chip_number INTEGER NOT NULL,
    value FLOAT,
    PRIMARY KEY (input_id, chip_number),
    CONSTRAINT check_value_valid CHECK (value IS NULL OR (value = value))
);

-- Reference Data Table
CREATE TABLE reference_data (
    reference_id VARCHAR(255) PRIMARY KEY,
    product VARCHAR(100) NOT NULL,
    lot VARCHAR(100) NOT NULL,
    insertion VARCHAR(50) NOT NULL,
    test_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    lsl FLOAT,
    usl FLOAT,
    used_for_training BOOLEAN DEFAULT FALSE,
    training_version VARCHAR(50),
    distribution_hash VARCHAR(255),
    quality_score FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Reference measurements table
CREATE TABLE reference_measurements (
    reference_id VARCHAR(255) REFERENCES reference_data(reference_id) ON DELETE CASCADE,
    chip_number INTEGER NOT NULL,
    value FLOAT,
    PRIMARY KEY (reference_id, chip_number),
    CONSTRAINT check_ref_value_valid CHECK (value IS NULL OR (value = value))
);

-- ============================================================================
-- Model and Training Tables
-- ============================================================================

-- Model Versions Table
CREATE TABLE model_versions (
    id BIGSERIAL PRIMARY KEY,
    version_number INTEGER NOT NULL UNIQUE,
    status model_status NOT NULL DEFAULT 'inactive',
    confidence_score FLOAT,
    model_path VARCHAR(255),
    training_data_ref VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Training Events Table
CREATE TABLE training_events (
    id BIGSERIAL PRIMARY KEY,
    model_version_id BIGINT REFERENCES model_versions(id) ON DELETE CASCADE,
    event_type VARCHAR(50),
    matched_insertion VARCHAR(50),
    matched_product VARCHAR(100),
    training_duration INTEGER,
    final_accuracy FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Version Metrics Table
CREATE TABLE version_metrics (
    id BIGSERIAL PRIMARY KEY,
    model_version_id BIGINT REFERENCES model_versions(id) ON DELETE CASCADE,
    accuracy FLOAT,
    confidence FLOAT,
    error_rate FLOAT,
    vamos_score FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Analysis Results Table
CREATE TABLE analysis_results (
    id BIGSERIAL PRIMARY KEY,
    test_name VARCHAR(255) NOT NULL,
    distribution_type VARCHAR(50) NOT NULL,
    confidence_score FLOAT,
    model_version_id BIGINT REFERENCES model_versions(id),
    input_id VARCHAR(255) REFERENCES input_data(input_id),
    reference_id VARCHAR(255) REFERENCES reference_data(reference_id),
    result_metadata TEXT, -- Using TEXT instead of JSONB for compatibility
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Model Metrics Table (Legacy)
CREATE TABLE model_metrics (
    id BIGSERIAL PRIMARY KEY,
    accuracy FLOAT,
    confidence FLOAT,
    error_rate FLOAT,
    model_version VARCHAR(50) NOT NULL,
    model_path VARCHAR(255) NOT NULL,
    training_reason training_reason_type NOT NULL,
    status training_status NOT NULL,
    training_duration INTEGER,
    vamos_triggered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Training Table
CREATE TABLE training (
    id BIGSERIAL PRIMARY KEY,
    reference_id_1 VARCHAR(255) NOT NULL,
    reference_id_2 VARCHAR(255) NOT NULL,
    status label NOT NULL DEFAULT 'COMPLETELY_DIFFERENT',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reference_id_1) REFERENCES reference_data(reference_id),
    FOREIGN KEY (reference_id_2) REFERENCES reference_data(reference_id)
);

-- Model Settings Table
CREATE TABLE model_settings (
    id BIGSERIAL PRIMARY KEY,
    sensitivity FLOAT DEFAULT 0.5 CHECK (sensitivity >= 0 AND sensitivity <= 1),
    selected_products TEXT,
    confidence_threshold FLOAT DEFAULT 0.95,
    critical_issue_weight FLOAT DEFAULT 1.0,
    high_priority_weight FLOAT DEFAULT 0.8,
    normal_priority_weight FLOAT DEFAULT 0.6,
    auto_retrain BOOLEAN DEFAULT FALSE,
    retraining_schedule VARCHAR(50) DEFAULT 'weekly',
    model_version VARCHAR(50) DEFAULT 'v1',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Feedback Table
CREATE TABLE feedback (
    id BIGSERIAL PRIMARY KEY,
    severity severity_level NOT NULL,
    status feedback_status NOT NULL DEFAULT 'PENDING',
    test_name VARCHAR(255) NOT NULL,
    test_number VARCHAR(50) NOT NULL,
    lot VARCHAR(100) NOT NULL,
    insertion VARCHAR(50) NOT NULL,
    initial_label VARCHAR(100) NOT NULL,
    new_label VARCHAR(100),
    reference_id VARCHAR(255) NOT NULL,
    input_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- API Logs Table
CREATE TABLE api_logs (
    id BIGSERIAL PRIMARY KEY,
    endpoint VARCHAR(255) NOT NULL,
    method VARCHAR(10) NOT NULL,
    status_code INTEGER NOT NULL,
    response_time FLOAT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Schema Migrations Table
CREATE TABLE schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================

CREATE INDEX idx_training_reference_id_1 ON training(reference_id_1);
CREATE INDEX idx_training_reference_id_2 ON training(reference_id_2);
CREATE INDEX idx_training_created_at ON training(created_at);

CREATE INDEX idx_feedback_created_at ON feedback(created_at);
CREATE INDEX idx_feedback_test_name ON feedback(test_name);
CREATE INDEX idx_feedback_status ON feedback(status);
CREATE INDEX idx_feedback_severity ON feedback(severity);

CREATE INDEX idx_input_test_name ON input_data(test_name);
CREATE INDEX idx_input_insertion ON input_data(insertion);
CREATE INDEX idx_reference_test_name ON reference_data(test_name);
CREATE INDEX idx_reference_insertion ON reference_data(insertion);
CREATE INDEX idx_reference_product ON reference_data(product);
CREATE INDEX idx_reference_training ON reference_data(used_for_training, training_version);

CREATE INDEX idx_model_metrics_version ON model_metrics(model_version);
CREATE INDEX idx_model_metrics_created_at ON model_metrics(created_at);
CREATE INDEX idx_model_versions_status ON model_versions(status);
CREATE INDEX idx_model_versions_created_at ON model_versions(created_at);
CREATE INDEX idx_model_versions_training_ref ON model_versions(training_data_ref);
CREATE INDEX idx_model_settings_created_at ON model_settings(created_at DESC);

CREATE INDEX idx_analysis_results_test_name ON analysis_results(test_name);
CREATE INDEX idx_analysis_results_input_id ON analysis_results(input_id);
CREATE INDEX idx_analysis_results_reference_id ON analysis_results(reference_id);
CREATE INDEX idx_analysis_results_created_at ON analysis_results(created_at);

CREATE INDEX idx_api_logs_created_at ON api_logs(created_at);
CREATE INDEX idx_api_logs_endpoint ON api_logs(endpoint);

-- ============================================================================
-- Functions and Stored Procedures
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to get reference data for training
CREATE OR REPLACE FUNCTION get_training_reference_data(
    p_insertion VARCHAR,
    p_product VARCHAR DEFAULT NULL
)
RETURNS TABLE(
    reference_id VARCHAR(255),
    product VARCHAR(255),
    lot VARCHAR(255),
    insertion VARCHAR(255),
    test_name VARCHAR(255),
    quality_score FLOAT,
    measurement_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        rd.reference_id,
        rd.product,
        rd.lot,
        rd.insertion,
        rd.test_name,
        rd.quality_score,
        COUNT(rm.chip_number)::INTEGER as measurement_count
    FROM reference_data rd
    LEFT JOIN reference_measurements rm ON rd.reference_id = rm.reference_id
    WHERE rd.insertion = p_insertion
        AND (p_product IS NULL OR rd.product = p_product)
        AND rd.used_for_training = FALSE
    GROUP BY rd.reference_id, rd.product, rd.lot, rd.insertion, rd.test_name, rd.quality_score
    ORDER BY 
        CASE WHEN rd.product = p_product THEN 0 ELSE 1 END,
        rd.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to update active model version
CREATE OR REPLACE FUNCTION update_active_model_version()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'active' THEN
        UPDATE model_versions SET status = 'inactive' WHERE status = 'active' AND id != NEW.id;
        
        UPDATE model_settings
        SET model_version = 'v' || NEW.version_number::TEXT,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = (SELECT id FROM model_settings ORDER BY created_at DESC LIMIT 1);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Function to get latest model comparison data
CREATE OR REPLACE FUNCTION get_model_version_comparison()
RETURNS TABLE(
    version_number INTEGER,
    created_at TIMESTAMP,
    training_data_ref VARCHAR(255),
    accuracy FLOAT,
    confidence FLOAT,
    error_rate FLOAT,
    vamos_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        mv.version_number,
        mv.created_at,
        mv.training_data_ref,
        vm.accuracy,
        vm.confidence,
        vm.error_rate,
        vm.vamos_score
    FROM model_versions mv
    LEFT JOIN version_metrics vm ON mv.id = vm.model_version_id
    WHERE vm.id = (
        SELECT vm2.id FROM version_metrics vm2 
        WHERE vm2.model_version_id = mv.id 
        ORDER BY vm2.created_at DESC 
        LIMIT 1
    )
    ORDER BY mv.version_number DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Triggers (PostgreSQL 9.6+ Compatible)
-- ============================================================================

CREATE TRIGGER update_model_settings_updated_at 
BEFORE UPDATE ON model_settings 
FOR EACH ROW 
EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_feedback_updated_at 
BEFORE UPDATE ON feedback 
FOR EACH ROW 
EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_model_versions_updated_at 
BEFORE UPDATE ON model_versions 
FOR EACH ROW 
EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER trg_update_active_model_version
AFTER INSERT OR UPDATE ON model_versions
FOR EACH ROW
EXECUTE PROCEDURE update_active_model_version();

-- ============================================================================
-- Views
-- ============================================================================

CREATE VIEW vamos_training_analytics AS
SELECT 
    mv.version_number,
    mv.created_at as version_created,
    mv.confidence_score as trigger_confidence,
    mv.status,
    mv.training_data_ref,
    te.event_type,
    te.matched_insertion,
    te.matched_product,
    te.training_duration,
    te.final_accuracy,
    vm.accuracy as current_accuracy,
    vm.confidence as current_confidence,
    vm.error_rate,
    vm.vamos_score,
    COUNT(DISTINCT rd.reference_id) as training_data_count
FROM model_versions mv
LEFT JOIN training_events te ON mv.id = te.model_version_id
LEFT JOIN version_metrics vm ON mv.id = vm.model_version_id
LEFT JOIN reference_data rd ON rd.training_version = 'v' || mv.version_number::TEXT
GROUP BY 
    mv.version_number, mv.created_at, mv.confidence_score, mv.status, mv.training_data_ref,
    te.event_type, te.matched_insertion, te.matched_product, 
    te.training_duration, te.final_accuracy,
    vm.accuracy, vm.confidence, vm.error_rate, vm.vamos_score
ORDER BY mv.version_number DESC;

CREATE VIEW feedback_analytics AS
SELECT 
    f.severity,
    f.status,
    f.test_name,
    f.insertion,
    COUNT(*) as feedback_count,
    AVG(CASE WHEN f.status = 'RESOLVED' THEN 1.0 ELSE 0.0 END) as resolution_rate,
    MAX(f.created_at) as latest_feedback,
    MIN(f.created_at) as earliest_feedback
FROM feedback f
GROUP BY f.severity, f.status, f.test_name, f.insertion
ORDER BY feedback_count DESC;

CREATE VIEW distribution_comparison_analytics AS
SELECT 
    ar.test_name,
    ar.distribution_type,
    COUNT(*) as comparison_count,
    AVG(ar.confidence_score) as avg_confidence,
    MIN(ar.confidence_score) as min_confidence,
    MAX(ar.confidence_score) as max_confidence,
    COUNT(CASE WHEN ar.confidence_score >= 0.95 THEN 1 END) as high_confidence_count,
    mv.version_number as model_version,
    DATE_TRUNC('day', ar.created_at) as comparison_date
FROM analysis_results ar
JOIN model_versions mv ON ar.model_version_id = mv.id
WHERE ar.distribution_type = 'comparison'
GROUP BY ar.test_name, ar.distribution_type, mv.version_number, DATE_TRUNC('day', ar.created_at)
ORDER BY comparison_date DESC, ar.test_name;

-- ============================================================================
-- Initial Data
-- ============================================================================

INSERT INTO model_settings (
    sensitivity,
    selected_products,
    confidence_threshold,
    critical_issue_weight,
    high_priority_weight,
    normal_priority_weight,
    retraining_schedule
) VALUES (
    0.5,
    '{}',
    0.95,
    1.0,
    0.8,
    0.6,
    'weekly'
);

INSERT INTO model_versions (version_number, status, confidence_score, training_data_ref)
VALUES (1, 'active', 0.95, 'initial_reference_data');

INSERT INTO version_metrics (model_version_id, accuracy, confidence, error_rate, vamos_score)
SELECT 
    mv.id, 
    0.95,
    0.95,
    0.05,
    0.90
FROM model_versions mv 
WHERE mv.version_number = 1;

INSERT INTO schema_migrations (version, description) 
VALUES ('v1.2.0', 'VAMOS database schema - PostgreSQL 9.6+ compatible version');

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE input_data IS 'Stores input test data for ML model processing and distribution comparison';
COMMENT ON TABLE input_measurements IS 'Individual chip measurements for input data';
COMMENT ON TABLE reference_data IS 'Reference dataset used for model training and distribution comparison';
COMMENT ON TABLE reference_measurements IS 'Individual chip measurements for reference data';
COMMENT ON TABLE model_versions IS 'Tracks different versions of the ML model with training data references';
COMMENT ON TABLE training_events IS 'Logs training events and their outcomes';
COMMENT ON TABLE version_metrics IS 'Performance metrics for each model version';
COMMENT ON TABLE analysis_results IS 'Results from distribution comparison and analysis operations';
COMMENT ON TABLE feedback IS 'User feedback on model predictions for continuous improvement';
COMMENT ON TABLE model_settings IS 'Configuration settings for the ML model';