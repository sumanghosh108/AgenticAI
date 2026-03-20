-- ============================================
-- AgenticAI — Migration Script (v1 → v2)
-- Adds FK constraints, CHECK constraints, and
-- ACID-safe functions to EXISTING tables.
-- Run this in the Supabase SQL Editor.
-- ============================================

-- ─────────────────────────────────────────────
-- 1. Add CHECK constraints to users table
-- ─────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints
        WHERE constraint_name = 'users_age_check'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_age_check
            CHECK (age IS NULL OR (age >= 0 AND age <= 150));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints
        WHERE constraint_name = 'users_gender_check'
    ) THEN
        ALTER TABLE users ADD CONSTRAINT users_gender_check
            CHECK (gender IS NULL OR gender IN ('male', 'female', 'other', 'prefer_not_to_say'));
    END IF;
END $$;

-- Ensure indexes exist
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_users_email    ON users (email);


-- ─────────────────────────────────────────────
-- 2. Add FK + constraints to user_report
-- ─────────────────────────────────────────────

-- Add default to research_domain if missing
ALTER TABLE user_report ALTER COLUMN research_domain SET DEFAULT '';
ALTER TABLE user_report ALTER COLUMN document SET DEFAULT '';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'user_report_user_name_fkey'
          AND table_name = 'user_report'
    ) THEN
        ALTER TABLE user_report
            ADD CONSTRAINT user_report_user_name_fkey
            FOREIGN KEY (user_name) REFERENCES users(username)
            ON UPDATE CASCADE ON DELETE CASCADE;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints
        WHERE constraint_name = 'user_report_domain_check'
    ) THEN
        ALTER TABLE user_report ADD CONSTRAINT user_report_domain_check
            CHECK (research_domain IN ('', 'general', 'finance', 'healthcare'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_report_user    ON user_report (user_name);
CREATE INDEX IF NOT EXISTS idx_user_report_created ON user_report (created_at DESC);


-- ─────────────────────────────────────────────
-- 3. Add FK + constraints to daily_usage
-- ─────────────────────────────────────────────

-- Add updated_at column if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'daily_usage' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE daily_usage ADD COLUMN updated_at TIMESTAMPTZ NOT NULL DEFAULT now();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'daily_usage_username_fkey'
          AND table_name = 'daily_usage'
    ) THEN
        ALTER TABLE daily_usage
            ADD CONSTRAINT daily_usage_username_fkey
            FOREIGN KEY (username) REFERENCES users(username)
            ON UPDATE CASCADE ON DELETE CASCADE;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.check_constraints
        WHERE constraint_name = 'daily_usage_count_check'
    ) THEN
        ALTER TABLE daily_usage ADD CONSTRAINT daily_usage_count_check
            CHECK (request_count >= 0);
    END IF;
END $$;

-- Add unique constraint for upsert support
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'daily_usage_username_request_date_key'
          AND table_name = 'daily_usage'
    ) THEN
        ALTER TABLE daily_usage
            ADD CONSTRAINT daily_usage_username_request_date_key
            UNIQUE (username, request_date);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date ON daily_usage (username, request_date);


-- ─────────────────────────────────────────────
-- 4. Create report_files table (if not exists)
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

-- If table already existed without FKs, add them
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'report_files_username_fkey'
          AND table_name = 'report_files'
    ) THEN
        ALTER TABLE report_files
            ADD CONSTRAINT report_files_username_fkey
            FOREIGN KEY (username) REFERENCES users(username)
            ON UPDATE CASCADE ON DELETE CASCADE;
    END IF;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'report_files_report_id_fkey'
          AND table_name = 'report_files'
    ) THEN
        ALTER TABLE report_files
            ADD CONSTRAINT report_files_report_id_fkey
            FOREIGN KEY (report_id) REFERENCES user_report(id)
            ON DELETE CASCADE;
    END IF;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_report_files_user   ON report_files (username);
CREATE INDEX IF NOT EXISTS idx_report_files_report ON report_files (report_id);

-- Prevent duplicate file types per report (one PDF, one DOCX max)
CREATE UNIQUE INDEX IF NOT EXISTS idx_report_files_unique_type
    ON report_files (report_id, file_type);


-- ─────────────────────────────────────────────
-- 5. Row Level Security
-- ─────────────────────────────────────────────
ALTER TABLE users        ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_report  ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_usage  ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_files ENABLE ROW LEVEL SECURITY;

-- Service-role (backend) gets full access — DROP first to avoid duplicates
DROP POLICY IF EXISTS "service_role_users"        ON users;
DROP POLICY IF EXISTS "service_role_user_report"  ON user_report;
DROP POLICY IF EXISTS "service_role_daily_usage"  ON daily_usage;
DROP POLICY IF EXISTS "service_role_report_files" ON report_files;

CREATE POLICY "service_role_users"        ON users        FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_user_report"  ON user_report  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_daily_usage"  ON daily_usage  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_role_report_files" ON report_files FOR ALL USING (true) WITH CHECK (true);


-- ─────────────────────────────────────────────
-- 6. ACID-safe PL/pgSQL functions
-- ─────────────────────────────────────────────

-- 6a. Atomic daily usage increment
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
    INSERT INTO daily_usage (username, request_date, request_count, updated_at)
    VALUES (p_username, CURRENT_DATE, 1, now())
    ON CONFLICT (username, request_date)
    DO UPDATE SET
        request_count = daily_usage.request_count + 1,
        updated_at = now()
    RETURNING request_count INTO v_count;

    v_allowed := v_count <= p_limit;

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

-- 6b. Atomic report save (transactional)
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

-- 6c. Get daily usage (read-only)
CREATE OR REPLACE FUNCTION get_daily_usage(p_username TEXT, p_limit INTEGER DEFAULT 5)
RETURNS JSONB
LANGUAGE plpgsql
STABLE
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
    IF NOT EXISTS (
        SELECT 1 FROM user_report
        WHERE id = p_report_id AND user_name = p_username
    ) THEN
        RAISE EXCEPTION 'Report % does not belong to user %', p_report_id, p_username;
    END IF;

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
-- 7. Auto updated_at trigger
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

DROP TRIGGER IF EXISTS trg_daily_usage_updated_at ON daily_usage;
CREATE TRIGGER trg_daily_usage_updated_at
    BEFORE UPDATE ON daily_usage
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ─────────────────────────────────────────────
-- Done! Verify with:
--   SELECT conname FROM pg_constraint WHERE conrelid = 'user_report'::regclass;
--   SELECT conname FROM pg_constraint WHERE conrelid = 'daily_usage'::regclass;
--   SELECT conname FROM pg_constraint WHERE conrelid = 'report_files'::regclass;
-- ─────────────────────────────────────────────
