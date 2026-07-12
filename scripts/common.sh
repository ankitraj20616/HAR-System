#!/usr/bin/env bash

# Shared shell helpers for repository-local developer commands.

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

info() {
  echo "==> $*"
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Required command '$1' was not found."
}

compose_command() {
  COMPOSE=(docker compose)
  if [[ "${HAR_WEBCAM:-false}" == "true" ]]; then
    COMPOSE+=(-f docker-compose.yml -f docker-compose.webcam.yml)
  fi
}

require_compose() {
  require_command docker
  docker compose version >/dev/null 2>&1 || die \
    "Docker Compose v2 is required (the 'docker compose' command)."
  docker info >/dev/null 2>&1 || die \
    "Docker is not reachable. Start Docker Engine/Desktop and retry."
  compose_command
}

ensure_local_env() {
  if [[ ! -f .env ]]; then
    cp .env.example .env
    info "Created .env from .env.example (safe local defaults)."
  fi
  mkdir -p data/models
}

require_auth_env() {
  [[ -f .env ]] || die "Run './dev.sh setup', then configure Supabase in .env."
  if grep --quiet '^SUPABASE_URL=https://your-project-id\.supabase\.co$' .env \
    || grep --quiet '^SUPABASE_PUBLISHABLE_KEY=sb_publishable_replace_me$' .env \
    || grep --quiet '^AUTH_TICKET_SECRET=replace-with-at-least-32-random-characters$' .env; then
    die "Configure SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, and AUTH_TICKET_SECRET in .env. See core_docs/milestones/milestone-6-auth-rbac/SUPABASE_SETUP.md."
  fi
}

service_exists() {
  local wanted="$1"
  "${COMPOSE[@]}" config --services | grep --fixed-strings --line-regexp --quiet "$wanted"
}
