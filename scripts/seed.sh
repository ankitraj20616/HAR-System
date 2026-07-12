#!/usr/bin/env bash
set -Eeuo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"
cd "$project_root"

mode="replace"
if [[ "${1:-}" == "--if-empty" ]]; then
  mode="if-empty"
elif [[ $# -gt 0 ]]; then
  die "Usage: ./scripts/seed.sh [--if-empty]"
fi

require_compose

container_id="$("${COMPOSE[@]}" ps -q postgres)"
[[ -n "$container_id" ]] || die "PostgreSQL is not running. Run './dev.sh up' first."

if [[ "$mode" == "if-empty" ]]; then
  row_count="$("${COMPOSE[@]}" exec -T postgres sh -eu -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -qAtc "SELECT count(*) FROM activity_timeline"')"
  if [[ "$row_count" != "0" ]]; then
    info "Database already contains activity data; automatic seed skipped."
    exit 0
  fi
fi

if [[ "$mode" == "replace" ]]; then
  info "Replacing activity, event, and feedback rows with prototype data..."
else
  info "Seeding empty database with prototype data..."
fi

"${COMPOSE[@]}" exec -T postgres sh -eu -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < scripts/seed.sql

info "Prototype data is ready."
