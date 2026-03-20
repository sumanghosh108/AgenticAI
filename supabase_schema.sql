-- ============================================
-- AgenticAI — Supabase Schema
-- Run this in the Supabase SQL Editor (Dashboard → SQL Editor → New query)
-- ============================================

-- 1. Users table
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    username    TEXT        NOT NULL UNIQUE,
    email       TEXT        NOT NULL UNIQUE,
    password    TEXT        NOT NULL,
    age         INTEGER,
    gender      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_email    ON users (email);

-- 2. User reports table
CREATE TABLE IF NOT EXISTS user_report (
    id               BIGSERIAL PRIMARY KEY,
    user_name        TEXT        NOT NULL,
    research_topic   TEXT        NOT NULL,
    research_domain  TEXT        NOT NULL DEFAULT '',
    document         TEXT        NOT NULL DEFAULT '',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_report_user ON user_report (user_name);

-- 3. Enable Row Level Security (recommended)
ALTER TABLE users       ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_report ENABLE ROW LEVEL SECURITY;

-- Allow the service_role key full access (backend uses service_role)
CREATE POLICY "Service role full access on users"
    ON users FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access on user_report"
    ON user_report FOR ALL
    USING (true)
    WITH CHECK (true);

-- 4. Daily usage tracking (rate limiting: 5 requests/user/day)
CREATE TABLE IF NOT EXISTS daily_usage (
    id              BIGSERIAL PRIMARY KEY,
    username        TEXT        NOT NULL,
    request_date    DATE        NOT NULL DEFAULT CURRENT_DATE,
    request_count   INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (username, request_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date ON daily_usage (username, request_date);

ALTER TABLE daily_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on daily_usage"
    ON daily_usage FOR ALL
    USING (true)
    WITH CHECK (true);
