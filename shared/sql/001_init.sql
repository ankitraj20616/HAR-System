CREATE TABLE IF NOT EXISTS activity_timeline (
  id           SERIAL PRIMARY KEY,
  ts           TIMESTAMPTZ NOT NULL,
  activity     VARCHAR(20) NOT NULL,
  confidence   DOUBLE PRECISION NOT NULL,
  sensor_label VARCHAR(20),
  video_label  VARCHAR(20),
  CONSTRAINT activity_timeline_activity_check
    CHECK (activity IN ('WALKING', 'SITTING', 'STANDING', 'LYING', 'EXERCISING', 'UNKNOWN')),
  CONSTRAINT activity_timeline_confidence_check CHECK (confidence >= 0 AND confidence <= 1),
  CONSTRAINT activity_timeline_sensor_label_check
    CHECK (sensor_label IS NULL OR sensor_label IN ('WALKING', 'SITTING', 'STANDING', 'LYING', 'EXERCISING', 'UNKNOWN')),
  CONSTRAINT activity_timeline_video_label_check
    CHECK (video_label IS NULL OR video_label IN ('WALKING', 'SITTING', 'STANDING', 'LYING', 'EXERCISING', 'UNKNOWN'))
);

CREATE TABLE IF NOT EXISTS events (
  id           SERIAL PRIMARY KEY,
  ts           TIMESTAMPTZ NOT NULL,
  type         VARCHAR(20) NOT NULL,
  severity     VARCHAR(10) NOT NULL,
  confidence   DOUBLE PRECISION NOT NULL,
  evidence     JSONB NOT NULL DEFAULT '{}'::jsonb,
  acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT events_type_check CHECK (type IN ('FALL', 'INACTIVITY', 'ABNORMAL_PATTERN')),
  CONSTRAINT events_severity_check CHECK (severity IN ('info', 'warning', 'critical')),
  CONSTRAINT events_confidence_check CHECK (confidence >= 0 AND confidence <= 1),
  CONSTRAINT events_evidence_object_check CHECK (jsonb_typeof(evidence) = 'object')
);

CREATE TABLE IF NOT EXISTS feedback (
  id           SERIAL PRIMARY KEY,
  ts           TIMESTAMPTZ NOT NULL,
  mode         VARCHAR(20) NOT NULL,
  headline     VARCHAR(100) NOT NULL,
  detail       TEXT NOT NULL,
  severity     VARCHAR(10) NOT NULL,
  payload      JSONB NOT NULL DEFAULT '{}'::jsonb,
  idempotency_key VARCHAR(255),
  CONSTRAINT feedback_mode_check CHECK (mode IN ('alert', 'feedback', 'summary')),
  CONSTRAINT feedback_severity_check CHECK (severity IN ('info', 'warning', 'critical')),
  CONSTRAINT feedback_payload_object_check CHECK (jsonb_typeof(payload) = 'object')
);

-- Repeatable upgrade for databases created before Milestone 4.
ALTER TABLE feedback ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(255);

-- These keys make persistence retries safe after an uncertain commit or a
-- service restart. The fusion service emits at most one authoritative record
-- for an interval timestamp and one event type at an event timestamp. Clean up
-- pre-Milestone-3 retry duplicates before installing the repeatable indexes so
-- this migration also works against an existing development volume.
DELETE FROM activity_timeline newer
USING activity_timeline older
WHERE newer.ts = older.ts AND newer.id > older.id;

DELETE FROM events newer
USING events older
WHERE newer.type = older.type AND newer.ts = older.ts AND newer.id > older.id;

CREATE INDEX IF NOT EXISTS idx_timeline_ts ON activity_timeline(ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_ts ON feedback(ts DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_feedback_idempotency_key
  ON feedback(idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_timeline_unique_ts ON activity_timeline(ts);
CREATE UNIQUE INDEX IF NOT EXISTS idx_events_unique_type_ts ON events(type, ts);

-- ============================================================
-- Local Auth + RBAC tables (replaces Supabase-hosted auth)
-- ============================================================

DO $$ BEGIN
  CREATE TYPE app_role AS ENUM ('pending', 'caregiver', 'doctor', 'admin');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id    UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    role       app_role NOT NULL DEFAULT 'pending',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS role_audit_log (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    UUID NOT NULL,
    old_role   app_role,
    new_role   app_role NOT NULL,
    changed_by UUID,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Trigger: auto-assign 'pending' role when a new user is created
CREATE OR REPLACE FUNCTION assign_pending_role()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO user_roles (user_id, role)
    VALUES (NEW.id, 'pending')
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_user_created ON users;
CREATE TRIGGER on_user_created
AFTER INSERT ON users
FOR EACH ROW EXECUTE FUNCTION assign_pending_role();

-- Trigger: audit log on role changes
CREATE OR REPLACE FUNCTION audit_role_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' OR OLD.role IS DISTINCT FROM NEW.role THEN
        INSERT INTO role_audit_log (user_id, old_role, new_role, changed_by)
        VALUES (NEW.user_id, CASE WHEN TG_OP = 'UPDATE' THEN OLD.role ELSE NULL END, NEW.role, NEW.updated_by);
    END IF;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS user_role_audit ON user_roles;
CREATE TRIGGER user_role_audit
BEFORE INSERT OR UPDATE ON user_roles
FOR EACH ROW EXECUTE FUNCTION audit_role_change();

