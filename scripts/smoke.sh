#!/usr/bin/env bash
set -Eeuo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

compose=(docker compose)
if ! "${compose[@]}" version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required (the 'docker compose' command)." >&2
  exit 1
fi

cleanup() {
  if [[ "${SMOKE_KEEP_RUNNING:-false}" != "true" ]]; then
    down_args=(down --remove-orphans)
    if [[ "${SMOKE_REMOVE_VOLUMES:-false}" == "true" ]]; then
      down_args+=(--volumes)
    fi
    "${compose[@]}" "${down_args[@]}"
  fi
}
trap cleanup EXIT

echo "Validating Compose configuration..."
"${compose[@]}" config --quiet

echo "Building and starting the Milestone 1 stack..."
up_args=(up --detach --wait --wait-timeout "${SMOKE_TIMEOUT_SECONDS:-180}")
if [[ "${SMOKE_SKIP_BUILD:-false}" == "true" ]]; then
  up_args+=(--no-build)
else
  up_args+=(--build)
fi
"${compose[@]}" "${up_args[@]}"

echo "Checking backend health endpoints..."
for port in \
  "${FUSION_SERVICE_PORT:-8001}" \
  "${FEEDBACK_SERVICE_PORT:-8002}" \
  "${SENSOR_SERVICE_PORT:-8003}" \
  "${VIDEO_SERVICE_PORT:-8004}"; do
  curl --fail --silent --show-error "http://localhost:${port}/health" >/dev/null
done
curl --fail --silent --show-error "http://localhost:${DASHBOARD_PORT:-5173}/health" >/dev/null

echo "Checking MQTT publish/subscribe..."
"${compose[@]}" exec -T mosquitto sh -eu -c '
  output=/tmp/har-smoke-message
  rm -f "$output"
  mosquitto_sub -h localhost -p 1883 -t har/smoke -q 1 -C 1 -W 5 >"$output" &
  subscriber_pid=$!
  sleep 1
  mosquitto_pub -h localhost -p 1883 -t har/smoke -q 1 -m milestone-1-ok
  wait "$subscriber_pid"
  test "$(cat "$output")" = milestone-1-ok
'

echo "Checking PostgreSQL readiness, initialized tables, and persistence..."
"${compose[@]}" exec -T postgres sh -eu -c '
  pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
  table_count="$(psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema = '\''public'\'' AND table_name IN ('\''activity_timeline'\'', '\''events'\'', '\''feedback'\'');")"
  test "$table_count" = 3
'

"${compose[@]}" exec -T postgres sh -eu -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -qAt' <<'SQL' \
  | grep --quiet --line-regexp '3'
BEGIN;
INSERT INTO activity_timeline (ts, activity, confidence, sensor_label, video_label)
VALUES ('2026-01-01T00:00:00Z', 'UNKNOWN', 0, 'UNKNOWN', 'UNKNOWN')
RETURNING id AS activity_id \gset
INSERT INTO events (ts, type, severity, confidence, evidence)
VALUES ('2026-01-01T00:00:00Z', 'INACTIVITY', 'info', 0, '{"smoke":true}')
RETURNING id AS event_id \gset
INSERT INTO feedback (ts, mode, headline, detail, severity, payload)
VALUES (
  '2026-01-01T00:00:00Z',
  'feedback',
  'Smoke test',
  'Temporary persistence verification',
  'info',
  '{"smoke":true}'
)
RETURNING id AS feedback_id \gset
SELECT
  (SELECT count(*) FROM activity_timeline WHERE id = :activity_id)
  + (SELECT count(*) FROM events WHERE id = :event_id)
  + (SELECT count(*) FROM feedback WHERE id = :feedback_id);
ROLLBACK;
SQL

echo "Milestone 1 infrastructure smoke test passed."
