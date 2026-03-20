-- ============================================
-- AgenticAI — Supabase Schema (v2)
-- Foreign keys + ACID-safe operations
-- Run this in the Supabase SQL Editor
-- ============================================

-- ─────────────────────────────────────────────
-- 1. Users (root table — all others reference this)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL   PRIMARY KEY,
    username    TEXT        NOT NULL UNIQUE,
    email       TEXT        NOT NULL UNIQUE,
    password    TEXT        NOT NULL,
    age         INTEGER     CHECK (age IS NULL OR (age >= 0 AND age <= 150)),
    gender      TEXT        CHECK (gender IS NULL OR gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_email    ON users (email);

-- ─────────────────────────────────────────────
-- 2. User reports — FK to users(username)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_report (
    id               BIGSERIAL   PRIMARY KEY,
    user_name        TEXT        NOT NULL
                     REFERENCES users(username) ON UPDATE CASCADE ON DELETE CASCADE,
    research_topic   TEXT        NOT NULL,
    research_domain  TEXT        NOT NULL DEFAULT ''
                     CHECK (research_domain IN ('', 'general', 'finance', 'healthcare')),
    document         TEXT        NOT NULL DEFAULT '',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_report_user      ON user_report (user_name);
CREATE INDEX IF NOT EXISTS idx_user_report_created    ON user_report (created_at DESC);

-- ─────────────────────────────────────────────
-- 3. Daily usage — FK to users(username)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_usage (
    id              BIGSERIAL   PRIMARY KEY,
    username        TEXT        NOT NULL
                    REFERENCES users(username) ON UPDATE CASCADE ON DELETE CASCADE,
    request_date    DATE        NOT NULL DEFAULT CURRENT_DATE,
    request_count   INTEGER     NOT NULL DEFAULT 0 CHECK (request_count >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (username, request_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date ON daily_usage (username, request_date);

-- ─────────────────────────────────────────────
-- 4. Report files — FK to users(username) + user_report(id)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS report_files (
    id              BIGSERIAL   PRIMARY KEY,
    username        TEXT        NOT NULL
                    REFERENCES users(username) ON UPDATE CASCADE ON DELETE CASCADE,
    report_id       BIGINT      NOT NULL
                    REFERENCES user_report(id) ON DELETE CASCADE,
    file_type       TEXT        NOT NULL CHECK (file_type IN ('pdf', 'docx')),
    file_name       TEXT        NOT NULL,
    b2_file_id      TEXT        NOT NULL,
    b2_file_path    TEXT        NOT NULL,
    file_size       INTEGER     NOT NULL DEFAULT 0 CHECK (file_size >= 0),
    content_sha1    TEXT        NOT NULL DEFAULT '',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_report_files_user   ON report_files (username);
CREATE INDEX IF NOT EXISTS idx_report_files_report ON report_files (report_id);

-- Prevent duplicate file types per report (one PDF, one DOCX max)
CREATE UNIQUE INDEX IF NOT EXISTS idx_report_files_unique_type
    ON report_files (report_id, file_type);


-- ─────────────────────────────────────────────
-- 5. User Frequency Tracking (one row per user)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_frequency (
    id                      BIGSERIAL   PRIMARY KEY,
    username                TEXT        NOT NULL UNIQUE
                            REFERENCES users(username) ON UPDATE CASCADE ON DELETE CASCADE,
    login_count             INTEGER     NOT NULL DEFAULT 0 CHECK (login_count >= 0),
    report_generate_count   INTEGER     NOT NULL DEFAULT 0 CHECK (report_generate_count >= 0),
    report_download_count   INTEGER     NOT NULL DEFAULT 0 CHECK (report_download_count >= 0),
    last_login_at           TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_frequency_username ON user_frequency (username);


-- ─────────────────────────────────────────────
-- 6. Row Level Security
-- ─────────────────────────────────────────────
ALTER TABLE users        ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_report  ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_usage  ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_files  ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_frequency ENABLE ROW LEVEL SECURITY;

-- Service-role (backend) gets full access
CREATE POLICY "service_role_users"          ON users          FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_user_report"    ON user_report    FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_daily_usage"    ON daily_usage    FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_report_files"   ON report_files   FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_user_frequency" ON user_frequency FOR ALL USING (true) WITH CHECK (true);


-- ─────────────────────────────────────────────
-- 6. ACID-safe functions (run inside a single transaction)
-- ─────────────────────────────────────────────

-- 6a. Atomic daily usage increment (upsert + return in one transaction)
CREATE OR REPLACE FUNCTION increment_daily_usage(
    p_username TEXT,
    p_limit    INTEGER DEFAULT 5
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_count   INTEGER;
    v_allowed BOOLEAN;
BEGIN
    -- Upsert: insert or increment atomically (no race conditions)
    INSERT INTO daily_usage (username, request_date, request_count, updated_at)
    VALUES (p_username, CURRENT_DATE, 1, now())
    ON CONFLICT (username, request_date)
    DO UPDATE SET
        request_count = daily_usage.request_count + 1,
        updated_at = now()
    RETURNING request_count INTO v_count;

    v_allowed := v_count <= p_limit;

    -- If we incremented past the limit, roll it back
    IF NOT v_allowed THEN
        UPDATE daily_usage
        SET request_count = request_count - 1, updated_at = now()
        WHERE username = p_username AND request_date = CURRENT_DATE;
    END IF;

    RETURN jsonb_build_object(
        'username',      p_username,
        'date',          CURRENT_DATE,
        'request_count', CASE WHEN v_allowed THEN v_count ELSE v_count - 1 END,
        'remaining',     GREATEST(0, p_limit - (CASE WHEN v_allowed THEN v_count ELSE v_count - 1 END)),
        'allowed',       v_allowed,
        'limit_reached', NOT v_allowed
    );
END;
$$;

-- 6b. Atomic report save + file metadata (transactional)
CREATE OR REPLACE FUNCTION save_report_with_files(
    p_username        TEXT,
    p_research_topic  TEXT,
    p_research_domain TEXT DEFAULT '',
    p_document        TEXT DEFAULT ''
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_report_id BIGINT;
BEGIN
    -- Verify user exists (FK will catch this too, but explicit error is clearer)
    IF NOT EXISTS (SELECT 1 FROM users WHERE username = p_username) THEN
        RAISE EXCEPTION 'User % does not exist', p_username;
    END IF;

    INSERT INTO user_report (user_name, research_topic, research_domain, document)
    VALUES (p_username, p_research_topic, p_research_domain, p_document)
    RETURNING id INTO v_report_id;

    RETURN jsonb_build_object(
        'id',              v_report_id,
        'user_name',       p_username,
        'research_topic',  p_research_topic,
        'research_domain', p_research_domain,
        'created_at',      now()
    );
END;
$$;

-- 6c. Get daily usage (read-only, consistent snapshot)
CREATE OR REPLACE FUNCTION get_daily_usage(p_username TEXT, p_limit INTEGER DEFAULT 5)
RETURNS JSONB
LANGUAGE plpgsql
STABLE  -- marks as read-only for optimizer
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    SELECT COALESCE(request_count, 0) INTO v_count
    FROM daily_usage
    WHERE username = p_username AND request_date = CURRENT_DATE;

    IF NOT FOUND THEN
        v_count := 0;
    END IF;

    RETURN jsonb_build_object(
        'username',      p_username,
        'date',          CURRENT_DATE,
        'request_count', v_count,
        'remaining',     GREATEST(0, p_limit - v_count),
        'limit_reached', v_count >= p_limit
    );
END;
$$;

-- 6d. Atomic file metadata save (validates report ownership)
CREATE OR REPLACE FUNCTION save_report_file(
    p_username     TEXT,
    p_report_id    BIGINT,
    p_file_type    TEXT,
    p_file_name    TEXT,
    p_b2_file_id   TEXT,
    p_b2_file_path TEXT,
    p_file_size    INTEGER DEFAULT 0,
    p_content_sha1 TEXT DEFAULT ''
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_file_id BIGINT;
BEGIN
    -- Verify report belongs to this user
    IF NOT EXISTS (
        SELECT 1 FROM user_report
        WHERE id = p_report_id AND user_name = p_username
    ) THEN
        RAISE EXCEPTION 'Report % does not belong to user %', p_report_id, p_username;
    END IF;

    -- Upsert: replace existing file of same type for same report
    INSERT INTO report_files (username, report_id, file_type, file_name, b2_file_id, b2_file_path, file_size, content_sha1)
    VALUES (p_username, p_report_id, p_file_type, p_file_name, p_b2_file_id, p_b2_file_path, p_file_size, p_content_sha1)
    ON CONFLICT (report_id, file_type)
    DO UPDATE SET
        file_name    = EXCLUDED.file_name,
        b2_file_id   = EXCLUDED.b2_file_id,
        b2_file_path = EXCLUDED.b2_file_path,
        file_size    = EXCLUDED.file_size,
        content_sha1 = EXCLUDED.content_sha1,
        created_at   = now()
    RETURNING id INTO v_file_id;

    RETURN jsonb_build_object(
        'id',         v_file_id,
        'report_id',  p_report_id,
        'file_type',  p_file_type,
        'file_name',  p_file_name
    );
END;
$$;


-- ─────────────────────────────────────────────
-- 7. Updated_at auto-trigger (for any table that has it)
-- ─────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_daily_usage_updated_at
    BEFORE UPDATE ON daily_usage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_user_frequency_updated_at
    BEFORE UPDATE ON user_frequency
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ─────────────────────────────────────────────
-- 8. User Frequency ACID-safe functions
-- ─────────────────────────────────────────────

-- 8a. Atomic login count increment
CREATE OR REPLACE FUNCTION increment_login_count(p_username TEXT)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_row user_frequency%ROWTYPE;
BEGIN
    INSERT INTO user_frequency (username, login_count, last_login_at, updated_at)
    VALUES (p_username, 1, now(), now())
    ON CONFLICT (username)
    DO UPDATE SET
        login_count   = user_frequency.login_count + 1,
        last_login_at = now(),
        updated_at    = now()
    RETURNING * INTO v_row;

    RETURN jsonb_build_object(
        'username',              v_row.username,
        'login_count',           v_row.login_count,
        'report_generate_count', v_row.report_generate_count,
        'report_download_count', v_row.report_download_count,
        'last_login_at',         v_row.last_login_at
    );
END;
$$;

-- 8b. Atomic report generate count increment
CREATE OR REPLACE FUNCTION increment_report_generate_count(p_username TEXT)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_row user_frequency%ROWTYPE;
BEGIN
    INSERT INTO user_frequency (username, report_generate_count, updated_at)
    VALUES (p_username, 1, now())
    ON CONFLICT (username)
    DO UPDATE SET
        report_generate_count = user_frequency.report_generate_count + 1,
        updated_at            = now()
    RETURNING * INTO v_row;

    RETURN jsonb_build_object(
        'username',              v_row.username,
        'login_count',           v_row.login_count,
        'report_generate_count', v_row.report_generate_count,
        'report_download_count', v_row.report_download_count
    );
END;
$$;

-- 8c. Atomic download count increment
CREATE OR REPLACE FUNCTION increment_report_download_count(p_username TEXT)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
    v_row user_frequency%ROWTYPE;
BEGIN
    INSERT INTO user_frequency (username, report_download_count, updated_at)
    VALUES (p_username, 1, now())
    ON CONFLICT (username)
    DO UPDATE SET
        report_download_count = user_frequency.report_download_count + 1,
        updated_at            = now()
    RETURNING * INTO v_row;

    RETURN jsonb_build_object(
        'username',              v_row.username,
        'login_count',           v_row.login_count,
        'report_generate_count', v_row.report_generate_count,
        'report_download_count', v_row.report_download_count
    );
END;
$$;

-- 8d. Get user frequency stats (read-only)
CREATE OR REPLACE FUNCTION get_user_frequency(p_username TEXT)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_row user_frequency%ROWTYPE;
BEGIN
    SELECT * INTO v_row FROM user_frequency WHERE username = p_username;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'username',              p_username,
            'login_count',           0,
            'report_generate_count', 0,
            'report_download_count', 0,
            'last_login_at',         NULL
        );
    END IF;

    RETURN jsonb_build_object(
        'username',              v_row.username,
        'login_count',           v_row.login_count,
        'report_generate_count', v_row.report_generate_count,
        'report_download_count', v_row.report_download_count,
        'last_login_at',         v_row.last_login_at
    );
END;
$$;
