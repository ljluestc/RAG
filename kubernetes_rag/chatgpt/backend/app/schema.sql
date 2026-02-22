-- ChatGPT RAG — PostgreSQL schema
-- Run: psql -U chatgpt -d chatgpt -f schema.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username    VARCHAR(128) UNIQUE NOT NULL,
    email       VARCHAR(256) UNIQUE,
    api_key     VARCHAR(256),
    rpm_limit   INT DEFAULT 60,
    tpm_limit   INT DEFAULT 100000,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(256) DEFAULT 'New conversation',
    model       VARCHAR(128) DEFAULT 'gpt-4o-mini',
    status      VARCHAR(32) DEFAULT 'active',  -- active, archived, deleted
    plugins     JSONB DEFAULT '[]',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_updated ON conversations(updated_at DESC);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(16) NOT NULL,  -- system, user, assistant, tool
    content         TEXT NOT NULL,
    name            VARCHAR(128),          -- plugin/tool name
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(created_at);

-- Plugins registry (admin-managed)
CREATE TABLE IF NOT EXISTS plugins (
    id          VARCHAR(64) PRIMARY KEY,
    name        VARCHAR(128) NOT NULL,
    description TEXT,
    enabled     BOOLEAN DEFAULT true,
    config      JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Usage / audit log
CREATE TABLE IF NOT EXISTS usage_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    model           VARCHAR(128),
    prompt_tokens   INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens    INT DEFAULT 0,
    latency_ms      REAL,
    endpoint        VARCHAR(64),
    status          VARCHAR(16) DEFAULT 'ok',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usage_user ON usage_logs(user_id);
CREATE INDEX idx_usage_created ON usage_logs(created_at);

-- Seed default plugins
INSERT INTO plugins (id, name, description) VALUES
    ('web_search',       'Web Search',        'Search the web for up-to-date information'),
    ('code_interpreter', 'Code Interpreter',  'Execute Python code in a sandbox'),
    ('rag_lookup',       'RAG Lookup',        'Search the knowledge base using RAG')
ON CONFLICT (id) DO NOTHING;
