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
  CONSTRAINT feedback_mode_check CHECK (mode IN ('alert', 'feedback', 'summary')),
  CONSTRAINT feedback_severity_check CHECK (severity IN ('info', 'warning', 'critical')),
  CONSTRAINT feedback_payload_object_check CHECK (jsonb_typeof(payload) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_timeline_ts ON activity_timeline(ts DESC);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_ts ON feedback(ts DESC);
