\set ON_ERROR_STOP on

BEGIN;

TRUNCATE TABLE feedback, events, activity_timeline RESTART IDENTITY;

-- Six hours of deterministic, varied activity keeps timeline and trend views
-- useful immediately. Timestamps remain relative to startup so every dashboard
-- range (1h/24h/7d/30d) can display the prototype.
WITH activity_pattern(position, activity, confidence) AS (
  VALUES
    (0, 'STANDING',   0.91::double precision),
    (1, 'WALKING',    0.88::double precision),
    (2, 'WALKING',    0.93::double precision),
    (3, 'SITTING',    0.90::double precision),
    (4, 'SITTING',    0.94::double precision),
    (5, 'EXERCISING', 0.86::double precision),
    (6, 'STANDING',   0.89::double precision),
    (7, 'LYING',      0.92::double precision),
    (8, 'UNKNOWN',    0.42::double precision)
), samples AS (
  SELECT
    sample_no,
    date_trunc('second', CURRENT_TIMESTAMP)
      - interval '6 hours'
      + sample_no * interval '5 minutes' AS ts
  FROM generate_series(0, 71) AS series(sample_no)
)
INSERT INTO activity_timeline (ts, activity, confidence, sensor_label, video_label)
SELECT
  samples.ts,
  pattern.activity,
  pattern.confidence,
  pattern.activity,
  pattern.activity
FROM samples
JOIN activity_pattern AS pattern ON pattern.position = samples.sample_no % 9;

INSERT INTO events (ts, type, severity, confidence, evidence, acknowledged)
VALUES
  (
    date_trunc('second', CURRENT_TIMESTAMP) - interval '4 hours 20 minutes',
    'ABNORMAL_PATTERN', 'warning', 0.78,
    '{"prototype_seed":true,"reason":"Activity duration exceeded the learned baseline","observed_minutes":47}'::jsonb,
    TRUE
  ),
  (
    date_trunc('second', CURRENT_TIMESTAMP) - interval '2 hours 10 minutes',
    'INACTIVITY', 'warning', 0.84,
    '{"prototype_seed":true,"inactive_minutes":32,"motion_intensity":0.03}'::jsonb,
    TRUE
  ),
  (
    date_trunc('second', CURRENT_TIMESTAMP) - interval '35 minutes',
    'FALL', 'critical', 0.96,
    '{"prototype_seed":true,"sensor_spike":3.8,"video_orientation":"horizontal","correlation_ms":420}'::jsonb,
    FALSE
  );

INSERT INTO feedback
  (ts, mode, headline, detail, severity, payload, idempotency_key)
VALUES (
  date_trunc('second', CURRENT_TIMESTAMP) - interval '4 minutes',
  'summary',
  'Prototype activity summary',
  'The demo contains a varied activity timeline and three explainable safety events. Review the unacknowledged fall alert first.',
  'warning',
  jsonb_build_object(
    'schema_version', '1.0',
    'ts', to_char(date_trunc('second', CURRENT_TIMESTAMP) - interval '4 minutes', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
    'mode', 'summary',
    'headline', 'Prototype activity summary',
    'detail', 'The demo contains a varied activity timeline and three explainable safety events. Review the unacknowledged fall alert first.',
    'severity', 'warning',
    'recommendations', jsonb_build_array(
      'Acknowledge the sample fall after reviewing its evidence.',
      'Compare the activity timeline with the trend distribution.',
      'Generate a fresh summary to exercise the configured feedback provider.'
    ),
    'disclaimer', 'This is automated assistive information, not a medical diagnosis.'
  ),
  'prototype-seed-v1'
);

COMMIT;

SELECT 'activity_timeline' AS table_name, count(*) AS rows FROM activity_timeline
UNION ALL
SELECT 'events', count(*) FROM events
UNION ALL
SELECT 'feedback', count(*) FROM feedback
ORDER BY table_name;
