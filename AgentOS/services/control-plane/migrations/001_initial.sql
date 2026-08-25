-- AgentOS Control Plane Initial Database Schema
-- Version: 001_initial.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Organizations
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    data_region VARCHAR(20) DEFAULT 'us-east-1',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oidc_sub VARCHAR(200) UNIQUE NOT NULL,
    email VARCHAR(200) NOT NULL,
    full_name VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organization Memberships (RBAC/ABAC)
CREATE TABLE IF NOT EXISTS memberships (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL, -- 'owner' | 'admin' | 'developer' | 'auditor'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, org_id)
);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (org_id, slug)
);

-- Agents
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (project_id, slug)
);

-- Immutable Agent Versions
CREATE TABLE IF NOT EXISTS agent_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    version VARCHAR(50) NOT NULL,
    manifest_hash VARCHAR(71) UNIQUE NOT NULL, -- 'sha256:' + 64 hex chars
    manifest_jsonb JSONB NOT NULL,
    schema_version VARCHAR(20) NOT NULL DEFAULT 'agentstudio/v1',
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (agent_id, version)
);

-- Runs
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_version_id UUID NOT NULL REFERENCES agent_versions(id) ON DELETE RESTRICT,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    triggered_by UUID REFERENCES users(id),
    status VARCHAR(30) NOT NULL DEFAULT 'QUEUED', -- QUEUED|VALIDATING|POLICY_CHECK|SCHEDULING|SANDBOX_PROVISIONING|RUNNING|COMPLETED|FAILED|CANCELLED|BLOCKED|ESCALATED
    policy_verdict VARCHAR(20),                   -- ALLOW|DENY|ESCALATE
    policy_bundle VARCHAR(100),
    estimated_cost_usd NUMERIC(10,6),
    actual_cost_usd NUMERIC(10,6),
    trace_id UUID,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Run Steps
CREATE TABLE IF NOT EXISTS run_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    step_type VARCHAR(50) NOT NULL, -- llm_call|tool_call|condition|parallel|loop|retry|human_approval
    status VARCHAR(30) NOT NULL,
    input_hash VARCHAR(71),
    output_hash VARCHAR(71),
    cost_usd NUMERIC(10,6),
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (run_id, seq)
);

-- Budget Accounts
CREATE TABLE IF NOT EXISTS budget_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    quota_usd NUMERIC(12,4) NOT NULL,
    used_usd NUMERIC(12,4) NOT NULL DEFAULT 0,
    UNIQUE (org_id, project_id, period_start)
);

-- Published Releases
CREATE TABLE IF NOT EXISTS releases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_version_id UUID NOT NULL REFERENCES agent_versions(id) ON DELETE RESTRICT,
    governance_verdict VARCHAR(20) NOT NULL, -- PASS|FAIL|PASS_WITH_WARNINGS
    policy_bundle VARCHAR(100) NOT NULL,
    sbom JSONB,
    signature TEXT,
    trust_score NUMERIC(5,2),
    published_at TIMESTAMPTZ DEFAULT NOW(),
    published_by UUID REFERENCES users(id)
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_agent_versions_hash ON agent_versions(manifest_hash);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_version_id ON runs(agent_version_id);
CREATE INDEX IF NOT EXISTS idx_run_steps_run_seq ON run_steps(run_id, seq);
