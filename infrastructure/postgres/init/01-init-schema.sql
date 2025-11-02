-- ============================================
-- Database Initialization Script
-- Agentic BI Platform
-- Version: 1.0.0
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for additional cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- Core Tables
-- ============================================

-- Companies table
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE,
    logo_url VARCHAR(500),
    settings JSONB DEFAULT '{}' NOT NULL,
    style_config JSONB DEFAULT '{}',
    subscription_tier VARCHAR(50) DEFAULT 'free',
    subscription_expires_at TIMESTAMP,
    user_limit INTEGER DEFAULT 10,
    query_limit_monthly INTEGER DEFAULT 1000,
    storage_limit_gb INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    department VARCHAR(100),
    role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('admin', 'analyst', 'viewer', 'user')),
    permissions JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- Database connections configuration
CREATE TABLE IF NOT EXISTS database_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    connection_type VARCHAR(50) NOT NULL,
    mindsdb_datasource_name VARCHAR(255) NOT NULL UNIQUE,
    config JSONB NOT NULL DEFAULT '{}',
    ssl_required BOOLEAN DEFAULT true,
    read_only BOOLEAN DEFAULT false,
    allowed_users UUID[],
    allowed_departments VARCHAR(100)[],
    is_active BOOLEAN DEFAULT true,
    last_tested_at TIMESTAMP,
    last_test_status VARCHAR(50),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis sessions
CREATE TABLE IF NOT EXISTS analysis_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,

    -- Query information
    query TEXT NOT NULL,
    query_type VARCHAR(50),
    generated_sql TEXT,
    final_sql TEXT,

    -- Execution details
    database_connection_id UUID REFERENCES database_connections(id) ON DELETE SET NULL,
    execution_time_ms INTEGER,
    rows_returned INTEGER,
    data_size_bytes BIGINT,

    -- Results and state
    results JSONB,
    visualizations JSONB,
    workflow_state JSONB,
    agent_interactions JSONB,

    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'created',
    error_message TEXT,
    error_details JSONB,

    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_status CHECK (status IN (
        'created', 'analyzing', 'awaiting_approval', 'executing',
        'visualizing', 'completed', 'failed', 'cancelled'
    ))
);

-- Human interventions
CREATE TABLE IF NOT EXISTS human_interventions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Intervention details
    intervention_type VARCHAR(50) NOT NULL,
    intervention_reason VARCHAR(255),

    -- Request and response
    request_data JSONB NOT NULL,
    response_data JSONB,

    -- Timing
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    responded_at TIMESTAMP,
    timeout_at TIMESTAMP,
    response_time_ms INTEGER,

    -- Outcome
    outcome VARCHAR(50),
    automated_fallback BOOLEAN DEFAULT false,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_intervention_type CHECK (intervention_type IN (
        'approve_query', 'modify_query', 'select_visualization',
        'modify_parameters', 'confirm_results'
    ))
);

-- Saved visualizations
CREATE TABLE IF NOT EXISTS saved_visualizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES analysis_sessions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,

    -- Visualization details
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[],

    -- Chart configuration
    chart_type VARCHAR(50) NOT NULL,
    chart_config JSONB NOT NULL,
    data_snapshot JSONB,

    -- Display options
    thumbnail_url VARCHAR(500),
    full_image_url VARCHAR(500),
    interactive_url VARCHAR(500),

    -- Sharing and access
    is_public BOOLEAN DEFAULT false,
    is_template BOOLEAN DEFAULT false,
    share_token VARCHAR(100) UNIQUE,
    view_count INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP
);

-- Query templates
CREATE TABLE IF NOT EXISTS query_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Template details
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    tags TEXT[],

    -- Query information
    natural_language_template TEXT NOT NULL,
    sql_template TEXT,
    parameters JSONB DEFAULT '[]',

    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    average_execution_time_ms INTEGER,

    -- Access control
    is_public BOOLEAN DEFAULT false,
    allowed_users UUID[],

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Audit and Analytics Tables
-- ============================================

-- Audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    company_id UUID REFERENCES companies(id) ON DELETE SET NULL,

    -- Action details
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,

    -- Context
    details JSONB,
    metadata JSONB,

    -- Request information
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(100),

    -- Result
    success BOOLEAN DEFAULT true,
    error_message TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Usage analytics
CREATE TABLE IF NOT EXISTS usage_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    -- Metrics
    date DATE NOT NULL,
    queries_count INTEGER DEFAULT 0,
    visualizations_count INTEGER DEFAULT 0,
    data_processed_bytes BIGINT DEFAULT 0,
    compute_time_seconds INTEGER DEFAULT 0,

    -- Cost tracking
    llm_tokens_used INTEGER DEFAULT 0,
    estimated_cost_cents INTEGER DEFAULT 0,

    -- Unique constraint for daily aggregation
    CONSTRAINT unique_daily_usage UNIQUE (company_id, user_id, date)
);

-- ============================================
-- Indexes
-- ============================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_company ON users(company_id);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;

-- Sessions indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user ON analysis_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_company ON analysis_sessions(company_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON analysis_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON analysis_sessions(created_at DESC);

-- Interventions indexes
CREATE INDEX IF NOT EXISTS idx_interventions_session ON human_interventions(session_id);
CREATE INDEX IF NOT EXISTS idx_interventions_user ON human_interventions(user_id);
CREATE INDEX IF NOT EXISTS idx_interventions_type ON human_interventions(intervention_type);

-- Visualizations indexes
CREATE INDEX IF NOT EXISTS idx_viz_user ON saved_visualizations(user_id);
CREATE INDEX IF NOT EXISTS idx_viz_company ON saved_visualizations(company_id);
CREATE INDEX IF NOT EXISTS idx_viz_public ON saved_visualizations(is_public) WHERE is_public = true;
CREATE INDEX IF NOT EXISTS idx_viz_tags ON saved_visualizations USING gin(tags);

-- Audit indexes
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_company ON audit_logs(company_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);

-- Analytics indexes
CREATE INDEX IF NOT EXISTS idx_analytics_company_date ON usage_analytics(company_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_user_date ON usage_analytics(user_id, date DESC);

-- ============================================
-- Triggers
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON analysis_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_viz_updated_at BEFORE UPDATE ON saved_visualizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Seed Data (Development Only)
-- ============================================

-- Insert default company for development
INSERT INTO companies (id, name, domain, subscription_tier, is_active)
VALUES
    ('00000000-0000-0000-0000-000000000001', 'Demo Company', 'demo.local', 'enterprise', true)
ON CONFLICT DO NOTHING;

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
END $$;
